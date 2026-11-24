"""Build a demand atlas from the original Capital Bikeshare hourly observations."""
import csv
import hashlib
import io
import json
import sqlite3
import urllib.request
import zipfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import polars as pl
import seaborn as sns
from scipy.stats import bootstrap

SOURCE = "https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip"
SITE = Path("site")


def acquire():
    cache = Path("data/hour.csv")
    if not cache.exists():
        cache.parent.mkdir(exist_ok=True)
        with urllib.request.urlopen(SOURCE, timeout=60) as response:
            with zipfile.ZipFile(io.BytesIO(response.read())) as archive:
                path = next(n for n in archive.namelist() if n.split("/")[-1] == "hour.csv")
                payload = archive.read(path)
        temp = cache.with_suffix(".tmp")
        temp.write_bytes(payload)
        temp.replace(cache)
    return cache


def validate(frame):
    keys = ["dteday", "hr"]
    if frame.select(keys).n_unique() != frame.height:
        raise ValueError("Duplicate day/hour")
    required = keys + ["casual","registered","cnt","workingday"]
    if any(frame.select(required).null_count().row(0)):
        raise ValueError("Null observation")
    if frame.filter((pl.col("casual") + pl.col("registered") != pl.col("cnt"))
                    | ~pl.col("hr").is_between(0, 23)
                    | ~pl.col("workingday").is_in([0,1])
                    | (pl.min_horizontal("casual","registered") < 0)).height:
        raise ValueError("Inconsistent rental observation")


def estimate(values, seed):
    avg = float(np.mean(values))
    if len(values) < 2:
        return [round(avg, 2), None, None]
    result = bootstrap((np.asarray(values),), np.mean, method="percentile", random_state=seed,
                       confidence_level=0.95, n_resamples=1500, batch=100)
    return [round(n, 2) for n in (avg, result.confidence_interval.low, result.confidence_interval.high)]


def main():
    raw = acquire()
    frame = pl.read_csv(raw)
    validate(frame)
    frame = frame.with_columns(pl.col("dteday").str.slice(0, 4).cast(pl.Int32).alias("year"))
    raw_pd = pd.DataFrame(frame.to_dict(as_series=False))
    SITE.mkdir(exist_ok=True)
    rows = []
    for (year, working, hour), g in raw_pd.groupby(["year", "workingday", "hr"]):
        for group in ["casual","registered","cnt"]:
            mean, lo, hi = estimate(g[group], 177 + int(hour))
            rows.append(dict(year=int(year), working=int(working), hour=int(hour), group=group,
                             days=len(g), mean=mean, lo=lo, hi=hi))
    with sqlite3.connect(":memory:") as db:
        raw_pd.to_sql("rides", db, index=False)
        annual = pd.read_sql_query("""SELECT year, COUNT(*) AS observed_hours,
          COUNT(DISTINCT dteday) AS days, SUM(cnt) AS rentals, SUM(casual) AS casual,
          SUM(registered) AS registered FROM rides GROUP BY year ORDER BY year""", db)
    output = {"annual":annual.to_dict("records"), "series":rows,
              "source_sha256":hashlib.sha256(raw.read_bytes()).hexdigest()}
    (SITE/"atlas.json").write_text(json.dumps(output, allow_nan=False), encoding="utf-8")
    with (SITE/"hourly.csv").open("w",encoding="utf-8",newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
    data = raw_pd.groupby(["weekday","hr"]).cnt.mean().unstack().reindex([1,2,3,4,5,6,0])
    fig, ax = plt.subplots(figsize=(10,3.5), layout="constrained")
    sns.heatmap(data, cmap="YlGnBu", ax=ax, yticklabels=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
                cbar_kws={"label":"rentals / observed hour"})
    ax.set(xlabel="Local hour", ylabel="", title="Capital Bikeshare  /  2011–2012")
    fig.savefig(SITE/"week.png",dpi=160)
    plt.close(fig)
    print(annual.to_string(index=False))


if __name__ == "__main__":
    main()
