let DATA=null;
async function load(){
  const r=await fetch('/api/demo'); DATA=await r.json();
  const item=DATA.content[0];
  document.getElementById('chain').innerHTML=item.chain.map(x=>`<div class="chain-step"><b>${x.step}</b><div><strong>${x.label}</strong><small>${x.detail}</small></div></div>`).join('');
  document.getElementById('sources').innerHTML=item.sources.map(s=>`<div class="source"><a href="${s.url}" target="_blank" rel="noopener">${s.name}</a></div>`).join('');
  document.getElementById('institutionsList').innerHTML=DATA.institutions.map(i=>`<article class="institution"><span class="eyebrow">SOURCE</span><h3>${i.name}</h3><p>${i.role}</p><small>${i.note}</small><p><a href="${i.url}" target="_blank" rel="noopener">زيارة الموقع الرسمي ↗</a></p></article>`).join('');
  const labels=[['verified_items','سجلات موثقة'],['learning_journeys','رحلات تعلم'],['institutional_sources','مصادر مؤسسية']];
  document.getElementById('metrics').innerHTML=labels.map(([k,l])=>`<div class="metric"><b>${DATA.impact[k].toLocaleString('en-US')}</b><span>${l}</span></div>`).join('') + `<div class="metric"><b>100%</b><span>تصميم الخصوصية كقاعدة</span></div>`;
}
async function verify(){
  const code=document.getElementById('code').value.trim();
  const r=await fetch('/api/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code})});
  const x=await r.json(); const el=document.getElementById('verifyResult');
  el.className=x.verified?'result ok':'result'; el.innerHTML=x.verified?`<b>✓ ${x.message}</b><br>${x.title} — الإصدار ${x.version}`:`${x.message}`;
}
async function ask(){
  const input=document.getElementById('question'), q=input.value.trim(); if(!q)return;
  const chat=document.getElementById('chat'); chat.innerHTML+=`<div class="bubble user">${q}</div>`; input.value='';
  const r=await fetch('/api/assistant',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})});
  const x=await r.json(); chat.innerHTML+=`<div class="bubble bot">${x.answer}<br><small>المصادر: ${x.sources.map(s=>s.name).join(' • ')}</small></div>`;
}
function copyCode(){navigator.clipboard?.writeText('ATHAR-001'); alert('تم نسخ ATHAR-001');}
load(); 
