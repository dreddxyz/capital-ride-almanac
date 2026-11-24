const el = id => document.getElementById(id);
async function start(){
 const response=await fetch('atlas.json');
 if(!response.ok)throw Error('data unavailable');
 const data=await response.json();
 const fmt=n=>n===null?'—':n.toLocaleString('ru-RU',{maximumFractionDigits:1});
 function draw(){
  const year=Number(el('year').value), working=Number(el('working').value), group=el('group').value;
  const rows=data.series.filter(r=>r.year===year&&r.working===working&&r.group===group);
  const peak=rows.reduce((a,b)=>a.mean>=b.mean?a:b);
  el('peak').textContent='Пик в '+peak.hour+':00 · '+fmt(peak.mean)+' поездок в среднем за час';
  const max=Math.max(1,...rows.map(r=>r.hi??r.mean)),x=h=>50+h*33,y=n=>215-n/max*183;
  const points=(a,k)=>a.map(r=>x(r.hour)+','+y(r[k]??r.mean)).join(' ');
  let axes='';
  for(let i=0;i<=4;i++){const v=max*i/4;axes+='<path stroke="#c8d3c7" d="M50 '+y(v)+' H809"/><text x="4" y="'+(y(v)+4)+'">'+Math.round(v)+'</text>';}
  for(const h of [0,4,8,12,16,20,23])axes+='<text x="'+(x(h)-10)+'" y="244">'+h+':00</text>';
  el('chart').innerHTML=axes+'<polygon fill="#c9deba" points="'+points(rows,'hi')+' '+points([...rows].reverse(),'lo')+'"/><polyline fill="none" stroke="#176451" stroke-width="4" points="'+points(rows,'mean')+'"/>';
  document.querySelector('tbody').innerHTML=rows.map(r=>'<tr>'+[r.hour+':00',r.days,fmt(r.mean),fmt(r.lo),fmt(r.hi)].map(v=>'<td>'+v+'</td>').join('')+'</tr>').join('');
  const a=data.annual.find(r=>r.year===year);
  el('coverage').textContent='За '+year+' год в источнике '+fmt(a.rentals)+' поездок и '+fmt(a.observed_hours)+' почасовых наблюдений.';
 }
 document.querySelectorAll('select').forEach(s=>s.addEventListener('change',draw));draw();
}
start().catch(()=>{el('peak').textContent='Данные не загрузились. Обновите страницу или скачайте CSV ниже.';});
