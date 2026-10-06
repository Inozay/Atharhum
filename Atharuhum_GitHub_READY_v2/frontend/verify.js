const API='';
const id=new URLSearchParams(location.search).get('id')||'ATHAR-2026-0001';
async function load(){
  const box=document.getElementById('verifyState');
  try{
    const r=await fetch(`${API}/api/verify/${encodeURIComponent(id)}`); const d=await r.json();
    if(!r.ok) throw new Error(d.detail||'Content not found');
    box.innerHTML=`<div class="verify-top"><div><span class="kicker">CONTENT VERIFICATION</span><h1>✓ Verified Content</h1><p>Authenticity and provenance checks are available for this record.</p></div><span class="verified-badge">VERIFIED</span></div>
    <div class="verify-id">${d.content.id}</div>
    <div class="verify-grid"><div><span>Title</span><b>${d.content.title}</b></div><div><span>Organization</span><b>${d.content.organization}</b></div><div><span>Version</span><b>${d.content.version}</b></div><div><span>Language</span><b>${d.content.language}</b></div><div><span>Integrity</span><b>${d.content.hash}</b></div><div><span>Review status</span><b>${d.content.status}</b></div></div>
    <div class="passport-check"><h3>Content Passport</h3>${d.passport.map(x=>`<div><i>✓</i><span>${x.label}</span><b>${x.status==='live'?'LIVE':'COMPLETE'}</b></div>`).join('')}</div>
    <div class="source-callout"><span class="kicker">SOURCE RECORD</span><h3>${d.source.title}</h3><p>${d.source.type} · ${d.source.language} · ${d.source.license}</p><span>Human-reviewed before publication</span></div>
    <a class="btn btn-gold btn-lg" href="/?verified=${encodeURIComponent(id)}">Continue to learning journey →</a>`;
    fetch('/api/events',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'CONTENT_VERIFIED',content_id:id,source_channel:'VERIFY'})}).catch(()=>{});
  }catch(e){box.innerHTML=`<div class="error-state"><span>!</span><h1>Verification unavailable</h1><p>${e.message}</p><a class="btn btn-ghost" href="/">Return to Atharuhum</a></div>`}
}
load();
