import { useEffect, useState } from 'react';
import { percentageJourney, PercentageJourney } from '../api';

export default function PercentageJourneyPage() {
  const [state,setState]=useState<PercentageJourney|null>(null);
  const [selected,setSelected]=useState<number|undefined>();
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [clock,setClock]=useState(Date.now);
  useEffect(()=>{const timer=window.setInterval(()=>setClock(Date.now()),30000);return()=>window.clearInterval(timer);},[]);
  useEffect(()=>{let active=true;percentageJourney().then(s=>{if(active)setState(s);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[]);
  async function act(action:string) {
    if(!state||busy)return;
    setBusy(true);setError('');
    try {setState(await percentageJourney({expected_revision:state.revision,action,selected}));setSelected(undefined);}
    catch(e){setError(e instanceof Error?e.message:'Request failed');}
    finally{setBusy(false);}
  }
  return <main className="shell">
    <h1>Successive percentages: name the base</h1>
    <p>Original SSC-style learning pilot. Not an authentic PYQ or an exam-readiness score.</p>
    {error&&<div role="alert"><p>{error}</p><button onClick={()=>window.location.reload()}>Reload saved journey</button></div>}
    {!state&&!error&&<p role="status">Loading your saved journey…</p>}
    {state&&<>
      <p role="status">Stage: {state.phase} · {state.stage}</p>
      {(state.phase==='teach'||state.phase==='repair')&&<section>
        <h2>{state.phase==='teach'?'Build the foundations':'Repair the mistake'}</h2>
        {state.feedback&&<p>{state.feedback.repair}</p>}
        <p>{state.lesson.objective}</p>
        <ul>{state.lesson.prerequisites.map(x=><li key={x}>{x}</li>)}</ul>
        <h3>Worked example</h3><ol>{state.lesson.worked_example.map(x=><li key={x}>{x}</li>)}</ol>
        <p>{state.lesson.shortcut}</p><p>{state.lesson.limit}</p>
        <button disabled={busy} onClick={()=>act(state.phase==='teach'?'start':'retry')}>{state.phase==='teach'?'Start diagnosis':'Try a fresh question'}</button>
      </section>}
      {state.phase==='check'&&state.question&&<section>
        <fieldset disabled={busy}><legend>{state.question.stem}</legend>
          {state.question.options.map((text,i)=><label key={i} style={{display:'block',padding:12}}>
            <input type="radio" name="answer" value={i+1} checked={selected===i+1} onChange={()=>setSelected(i+1)}/> {text}
          </label>)}
        </fieldset>
        <button disabled={busy||selected===undefined} onClick={()=>act('answer')}>Check answer</button>
        <button disabled={busy||state.assisted} onClick={()=>act('hint')}>Use a hint (assisted)</button>
        {state.hint&&<p role="note">{state.hint}</p>}
      </section>}
      {state.phase==='feedback'&&state.feedback&&<section>
        <h2>{state.feedback.correct?'Correct':'Let’s examine the choices'}</h2>
        <p>{state.feedback.independent?'Fresh, unassisted check recorded.':'This response is learning evidence, not an independent pass.'}</p>
        <h3>Understand all four options</h3>
        <ol>{state.feedback.options.map((option,i)=><li key={i}><strong>{option}{i+1===state.feedback!.correct_option?' — correct':''}</strong><p>{state.feedback!.explanations[i]}</p></li>)}</ol>
        <p>{state.feedback.repair}</p><button disabled={busy} onClick={()=>act('continue')}>Continue</button>
      </section>}
      {(state.phase==='waiting'||state.phase==='complete')&&<section>
        <h2>{state.phase==='complete'?'Pilot retention checks completed':'Spaced revision scheduled'}</h2>
        <p>Next revision: {state.due_at?new Date(state.due_at+'Z').toLocaleString():''}</p>
        <p>{state.evidence_label}</p>
        <button disabled={busy||!state.due_at||clock<Date.parse(state.due_at+'Z')} onClick={()=>act('revise')}>Start due revision</button>
      </section>}
    </>}
  </main>;
}
