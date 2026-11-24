import polars as pl
import pytest
from pipeline import estimate, validate

def test_conservation_and_key():
    f = pl.DataFrame({"dteday":["2011-01-01"],"hr":[8],"casual":[1],"registered":[2],"cnt":[3],"workingday":[0]})
    validate(f)
    for bad in [pl.concat([f,f]),f.with_columns(pl.lit(4).alias("cnt"))]:
        with pytest.raises(ValueError):
            validate(bad)

def test_interval():
    assert estimate([2], 1) == [2, None, None]
    assert estimate([3,3,3], 1) == [3, 3, 3]
