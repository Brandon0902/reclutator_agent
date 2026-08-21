(() => {
  const state = { jobs: [], current: null, execution: null, timer: null };
  const $ = (id) => document.getElementById(id);
  const statusLabels = {BORRADOR:'Borrador',ESPERANDO_CONFIRMACION:'Esperando confirmación',CONFIRMADA:'Confirmada',EVALUANDO:'Evaluando',COMPLETADA:'Completada',ERROR:'Con error'};

  function cookie(name){ return document.cookie.split('; ').find(x=>x.startsWith(name+'='))?.split('=').slice(1).join('=') || ''; }
  async function api(url, options={}){
    const config={...options,headers:{'Content-Type':'application/json','X-CSRFToken':decodeURIComponent(cookie('csrftoken')),...(options.headers||{})}};
    const response=await fetch(url,config);
    let data={}; try{data=await response.json();}catch{}
    if(!response.ok) throw new Error(data.detail || Object.values(data).flat().join(' ') || `Error ${response.status}`);
    return data;
  }
  function toast(message,error=false){const node=document.createElement('div');node.className='toast'+(error?' error':'');node.textContent=message;$('toasts').append(node);setTimeout(()=>node.remove(),4200);}
  function escapeHtml(value=''){const d=document.createElement('div');d.textContent=value;return d.innerHTML;}
  function dateText(value){return value?new Intl.DateTimeFormat('es-MX',{hour:'2-digit',minute:'2-digit'}).format(new Date(value)):'';}

  async function loadJobs(selectId=null){
    const data=await api('/api/vacantes/'); state.jobs=data.results||data; renderJobs();
    const target=selectId || state.current?.id || state.jobs[0]?.id;
    if(target) await selectJob(target); else showEmpty();
  }
  function renderJobs(){
    $('job-list').innerHTML=state.jobs.map(job=>`<button class="job-item ${state.current?.id===job.id?'active':''}" data-id="${job.id}"><span class="job-dot"></span><span><strong>${escapeHtml(job.titulo||'Nueva vacante')}</strong><small>${statusLabels[job.estado]||job.estado}</small></span></button>`).join('');
    document.querySelectorAll('.job-item').forEach(btn=>btn.onclick=()=>selectJob(Number(btn.dataset.id)));
  }
  function showEmpty(){state.current=null;$('workspace').classList.add('hidden');$('empty-state').classList.remove('hidden');}
  async function selectJob(id){
    clearTimeout(state.timer); clearRanking(); state.current=await api(`/api/vacantes/${id}/`); state.execution=null;
    $('empty-state').classList.add('hidden');$('workspace').classList.remove('hidden'); renderJobs(); renderHeader();
    await Promise.all([loadMessages(),loadExecutions()]); renderCriteria(); schedulePoll();
  }
  function renderHeader(){$('job-title').textContent=state.current.titulo||'Nueva conversación';$('job-status').textContent=statusLabels[state.current.estado]||state.current.estado;const publish=$('publish-job');const link=$('public-job-link');publish.classList.toggle('hidden',!!state.current.publicada);link.classList.toggle('hidden',!state.current.publicada);if(state.current.publicada){link.href=`/aplicar/${state.current.public_slug}/`;link.textContent='Abrir formulario';}publish.onclick=async()=>{try{state.current=await api(`/api/vacantes/${state.current.id}/publicar/`,{method:'POST',body:'{}'});renderHeader();toast('Vacante publicada. Puedes copiar el enlace.');}catch(error){toast(error.message,true);}};}

  async function loadMessages(){
    const messages=await api(`/api/vacantes/${state.current.id}/mensajes/`);
    $('messages').innerHTML=messages.map(m=>`<article class="message ${m.rol==='RECLUTADOR'?'recruiter':'agent'}"><div class="message-avatar">${m.rol==='RECLUTADOR'?'T':'✦'}</div><div class="bubble"><p>${escapeHtml(m.contenido)}</p><time>${dateText(m.created_at)}</time></div></article>`).join('');
    $('messages').scrollTop=$('messages').scrollHeight;
    const waiting=!!state.current.tarea_activa;
    $('typing').classList.toggle('hidden',!waiting);
    const locked=['CONFIRMADA','EVALUANDO','COMPLETADA'].includes(state.current.estado);
    $('message-input').disabled=locked;$('message-form').querySelector('button').disabled=locked;
  }
  function renderCriteria(){
    const proposal=state.current.propuesta||{}; const criteria=proposal.criterios||[];
    $('criteria-empty').classList.toggle('hidden',criteria.length>0);$('criteria-content').classList.toggle('hidden',!criteria.length);
    if(!criteria.length)return;
    const total=criteria.reduce((sum,c)=>sum+Number(c.peso),0);const required=criteria.filter(c=>c.obligatorio).length;const top=Math.max(...criteria.map(c=>Number(c.peso)||0));const questions=proposal.preguntas||[];
    $('weight-total').textContent=`${total.toFixed(2).replace('.00','')}%`;$('required-total').textContent=required;$('top-weight').textContent=`${top.toFixed(0)}%`;$('questions-total').textContent=questions.length;
    $('rubric-distribution').innerHTML=criteria.map((c,i)=>`<span title="${escapeHtml(c.nombre)} · ${Number(c.peso).toFixed(0)}%" style="--w:${Math.max(Number(c.peso)||0,2)}"><b>${i+1}</b></span>`).join('');
    $('criteria-list').innerHTML=criteria.map((c,i)=>{const peso=Number(c.peso)||0;return `<div class="criterion" style="--weight:${peso}"><div class="criterion-meter"><span></span></div><div class="criterion-head"><span class="criterion-index">${i+1}</span><div class="criterion-main"><strong>${escapeHtml(c.nombre)}</strong><p>${escapeHtml(c.descripcion)}</p>${c.obligatorio?'<span class="required-tag">OBLIGATORIO</span>':''}</div><span class="criterion-weight"><b>${peso.toFixed(0)}%</b><small>peso</small></span></div></div>`}).join('');
    $('questions-block').classList.toggle('hidden',!questions.length);$('questions-list').innerHTML=questions.map(q=>`<li>${escapeHtml(q)}</li>`).join('');
    $('confirm-job').classList.toggle('hidden',state.current.estado!=='ESPERANDO_CONFIRMACION');
  }

  async function loadExecutions(){
    const jobId=state.current.id; const data=await api(`/api/vacantes/${jobId}/ejecuciones/`); if(state.current?.id!==jobId)return;
    const runs=data.results||data; state.execution=runs[0]||null; renderProgress();
    if(!state.execution||['PENDIENTE','PROCESANDO'].includes(state.execution.estado)){clearRanking();return;}
    await loadRanking(jobId,state.execution.id);
  }
  function renderProgress(){
    const run=state.execution;$('progress-empty').classList.toggle('hidden',!!run);$('progress-content').classList.toggle('hidden',!run);
    $('start-evaluation').classList.toggle('hidden',!!run || state.current.estado!=='CONFIRMADA');
    if(!run)return; const done=run.completados+run.sin_texto+(run.omitidos||0)+run.errores;const pct=run.total?Math.round(done/run.total*100):100;
    $('progress-ring').style.setProperty('--progress',pct);$('progress-percent').textContent=`${pct}%`;$('stat-complete').textContent=run.completados;$('stat-processing').textContent=run.procesando||0;$('stat-pending').textContent=run.pendientes||0;$('stat-skipped').textContent=run.omitidos||0;$('stat-errors').textContent=run.errores;$('stat-total').textContent=run.total;
    const omitted=run.omitidos_detalle||[];$('omitted-summary').classList.toggle('hidden',!omitted.length);$('omitted-list').innerHTML=omitted.map(item=>`<li><strong>${escapeHtml(item.documento)}</strong><br>${escapeHtml(item.motivo)}</li>`).join('');
    $('retry-errors').classList.toggle('hidden',!['PARCIAL','ERROR'].includes(run.estado)||!run.errores);
  }
  function clearRanking(){$('ranking-empty').classList.remove('hidden');$('ranking-list').innerHTML='';}
  async function loadRanking(jobId=state.current?.id,executionId=state.execution?.id){
    const data=await api(`/api/vacantes/${jobId}/ejecuciones/${executionId}/ranking/`);
    if(state.current?.id!==jobId||state.execution?.id!==executionId||['PENDIENTE','PROCESANDO'].includes(state.execution?.estado))return;
    const candidates=data.results||[];
    $('ranking-empty').classList.toggle('hidden',candidates.length>0);
    $('ranking-list').innerHTML=candidates.map((c,i)=>`<article class="candidate"><div class="candidate-top"><span class="rank-number">${i+1}</span><div><h4>${escapeHtml(c.nombre)}</h4><small>${c.criterios.length} criterios evaluados</small></div><span class="score">${c.puntuacion}</span></div><p class="candidate-summary">${escapeHtml(c.resumen)}</p><div class="candidate-actions"><span class="missing">${c.obligatorios_no_demostrados.length?`⚠ ${c.obligatorios_no_demostrados.map(x=>escapeHtml(x.nombre)).join(', ')}`:'✓ Obligatorios demostrados'}</span><a class="pdf-link" href="${c.pdf_url}" target="_blank" rel="noopener">Ver currículum ↗</a></div><details><summary>Ver evidencia y hallazgos</summary><ul class="evidence-list">${c.criterios.map(x=>`<li><strong>${x.puntuacion}/100</strong> · ${escapeHtml(x.evidencia||'Sin evidencia')}</li>`).join('')}${c.fortalezas.map(x=>`<li><strong>Fortaleza:</strong> ${escapeHtml(x)}</li>`).join('')}${c.brechas.map(x=>`<li><strong>Brecha:</strong> ${escapeHtml(x)}</li>`).join('')}</ul></details></article>`).join('');
  }
  function activateTab(name){document.querySelectorAll('.detail-tabs button').forEach(x=>x.classList.toggle('active',x.dataset.tab===name));document.querySelectorAll('.tab-panel').forEach(x=>x.classList.add('hidden'));$(`tab-${name}`).classList.remove('hidden');}
  function schedulePoll(){clearTimeout(state.timer);if(!state.current)return;const active=['BORRADOR','ESPERANDO_CONFIRMACION','EVALUANDO'].includes(state.current.estado)||state.execution?.estado==='PROCESANDO'||state.execution?.estado==='PENDIENTE';if(active)state.timer=setTimeout(()=>refreshCurrent(),5000);}
  async function refreshCurrent(){try{const id=state.current.id;state.current=await api(`/api/vacantes/${id}/`);renderHeader();renderCriteria();await Promise.all([loadMessages(),loadExecutions()]);schedulePoll();}catch(e){toast(e.message,true);}}

  async function createJob(message){const job=await api('/api/vacantes/',{method:'POST',body:JSON.stringify({mensaje:message})});$('new-job-dialog').close();$('new-job-message').value='';await loadJobs(job.id);toast('Vacante creada. Gemma está preparando la propuesta.');}
  async function sendMessage(message){await api(`/api/vacantes/${state.current.id}/mensajes/`,{method:'POST',body:JSON.stringify({contenido:message})});$('message-input').value='';await refreshCurrent();toast('Mensaje enviado al agente.');}
  async function confirmJob(){if(!confirm('La rúbrica quedará congelada. ¿Deseas confirmarla?'))return;state.current=await api(`/api/vacantes/${state.current.id}/confirmar/`,{method:'POST',body:'{}'});renderHeader();renderCriteria();await loadMessages();renderProgress();activateTab('progress');toast('Rúbrica confirmada. La evaluación aún no ha iniciado.');}
  async function startEvaluation(){clearRanking();state.execution=await api(`/api/vacantes/${state.current.id}/evaluar/`,{method:'POST',body:'{}'});state.current=await api(`/api/vacantes/${state.current.id}/`);renderHeader();renderProgress();activateTab('progress');schedulePoll();toast('Evaluación iniciada en segundo plano.');}
  async function retryErrors(){state.execution=await api(`/api/vacantes/${state.current.id}/ejecuciones/${state.execution.id}/reintentar/`,{method:'POST',body:'{}'});renderProgress();schedulePoll();toast('Se reintentará únicamente lo que falló.');}

  $('new-job').onclick=$('empty-new').onclick=()=>$('new-job-dialog').showModal();$('refresh-jobs').onclick=()=>loadJobs();
  $('new-job-close').onclick=()=>{$('new-job-dialog').close();$('new-job-message').value='';};
  $('new-job-form').onsubmit=async(e)=>{e.preventDefault();const msg=$('new-job-message').value.trim();if(!msg){toast('Describe la vacante antes de iniciar la conversación.',true);$('new-job-message').focus();return;}try{await createJob(msg);}catch(err){toast(err.message,true);}};
  $('message-form').onsubmit=async(e)=>{e.preventDefault();const msg=$('message-input').value.trim();if(!msg)return;try{await sendMessage(msg);}catch(err){toast(err.message,true);}};
  $('message-input').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('message-form').requestSubmit();}};
  $('confirm-job').onclick=()=>confirmJob().catch(e=>toast(e.message,true));$('start-evaluation').onclick=()=>startEvaluation().catch(e=>toast(e.message,true));$('retry-errors').onclick=()=>retryErrors().catch(e=>toast(e.message,true));document.querySelectorAll('.detail-tabs button').forEach(b=>b.onclick=()=>activateTab(b.dataset.tab));
  loadJobs().catch(e=>toast(e.message,true));
})();
