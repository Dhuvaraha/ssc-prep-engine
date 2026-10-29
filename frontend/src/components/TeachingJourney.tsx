import { useEffect, useRef, useState } from 'react';
import type { TeachingJourneyState, JourneyAction } from '../api';
import TeachingFigure, { TeachingSceneView } from './TeachingFigure';

type Props = {
  title: string;
  load: (action?: JourneyAction) => Promise<TeachingJourneyState>;
};

export default function TeachingJourney({title,load}: Props) {
  const [state,setState]=useState<TeachingJourneyState|null>(null);
  const [selected,setSelected]=useState<number|undefined>();
  const [reason,setReason]=useState<number|undefined>();
  const [guessed,setGuessed]=useState(false);
  const [model,setModel]=useState<string[][]>([]);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [clock,setClock]=useState(Date.now);
  const stageHeading=useRef<HTMLParagraphElement>(null);
  const previousStage=useRef<string|undefined>(undefined);
  useEffect(()=>{
    if(!state)return;
    const stage=state.phase+':'+state.stage;
    if(previousStage.current&&previousStage.current!==stage)stageHeading.current?.focus();
    previousStage.current=stage;
  },[state?.phase,state?.stage]);
  useEffect(()=>{const timer=window.setInterval(()=>setClock(Date.now()),30000);return()=>window.clearInterval(timer);},[]);
  useEffect(()=>{let active=true;load().then(s=>{if(active)setState(s);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[load]);
  async function act(action:string) {
    if(!state||busy)return;
    setBusy(true);setError('');
    try {setState(await load({expected_revision:state.revision,action,selected,reason_selected:reason,guessed,model:state.question?.construction?model:undefined}));setSelected(undefined);setReason(undefined);setGuessed(false);setModel([]);}
    catch(e){setError(e instanceof Error?e.message:'Request failed');}
    finally{setBusy(false);}
  }
  return <main className="shell">
    <h1>{title}</h1>
    <p>Original SSC-style learning pilot. Not an authentic PYQ or an exam-readiness score.</p>
    {error&&<div role="alert"><p>{error}</p><button onClick={()=>window.location.reload()}>Reload saved journey</button></div>}
    {!state&&!error&&<p role="status">Loading your saved journey…</p>}
    {state&&<>
      <p ref={stageHeading} tabIndex={-1} role="status">Stage: {state.phase} · {state.stage}</p>
      {(state.phase==='teach'||state.phase==='repair')&&<section>
        <h2>{state.phase==='teach'?'Build the foundations':'Repair the mistake'}</h2>
        {state.phase==='repair'&&state.feedback&&<section aria-label="Question to revisit">
          <p>{state.feedback.stem}</p>
          {state.feedback.passage&&<article aria-label="Reading passage"><p>{state.feedback.passage}</p></article>}
          {state.feedback.figure&&<TeachingFigure figure={state.feedback.figure} labels={state.feedback.options}/>}
          {state.feedback.diagram&&<TeachingSceneView scene={state.feedback.diagram} label="Given diagram"/>}
        </section>}
        {state.feedback&&<p>{state.feedback.repair}</p>}
        {state.feedback?.construction_feedback&&<p>{state.feedback.construction_feedback}</p>}
        <p>{state.lesson.objective}</p>
        <ul>{state.lesson.prerequisites.map(x=><li key={x}>{x}</li>)}</ul>
        <h3>Worked example</h3><ol>{state.lesson.worked_example.map(x=><li key={x}>{x}</li>)}</ol>
        {state.lesson.illustrations?.map((scene,i)=><TeachingSceneView key={i} scene={scene} label={'Worked diagram '+(i+1)}/>)}
        <p>{state.lesson.shortcut}</p><p>{state.lesson.limit}</p>
        <button disabled={busy} onClick={()=>act(state.phase==='teach'?'start':'retry')}>{state.phase==='teach'?'Start diagnosis':'Try a fresh question'}</button>
      </section>}
      {(state.phase==='check'||state.phase==='justify')&&state.question&&<section>
        {state.question.passage&&<article aria-label="Reading passage"><p>{state.question.passage}</p></article>}
        {state.question.figure&&<TeachingFigure figure={state.question.figure} labels={state.question.options}/>}
        {state.question.diagram&&<TeachingSceneView scene={state.question.diagram} label="Given diagram"/>}
        {state.phase==='justify'&&<p>Your answer is saved and locked. Now justify it without changing your choice.</p>}
        <fieldset disabled={busy||state.phase==='justify'}><legend>{state.question.stem}</legend>
          {state.question.options.map((text,i)=><label key={i} style={{display:'block',padding:12}}>
            <input style={{width:'auto',marginRight:8}} type="radio" name="answer" value={i+1} checked={(state.pending_answer?.selected??selected)===i+1} onChange={()=>setSelected(i+1)}/> {text}
          </label>)}
        </fieldset>
        {state.question.reason_options&&<fieldset disabled={busy}><legend>{state.question.reason_prompt}</legend>
          {state.question.reason_options.map((text,i)=><label key={i} style={{display:'block',padding:12}}>
            <input style={{width:'auto',marginRight:8}} type="radio" name="reason" checked={reason===i+1} onChange={()=>setReason(i+1)}/> {text}
          </label>)}
        </fieldset>}
        {state.question.construction&&<fieldset disabled={busy}>
          <legend>Construct a counterexample</legend>
          <p>Add objects and select their category memberships. Every premise must remain true and the conclusion must be false. No listed objects means an empty population; an object with no categories belongs outside all named sets.</p>
          {model.map((members,index)=><fieldset key={index}>
            <legend>Object {index+1}</legend>
            {state.question!.construction!.terms.map(term=><label key={term} style={{display:'inline-block',padding:12}}>
              <input style={{width:'auto',marginRight:8}} type="checkbox" checked={members.includes(term)} onChange={e=>setModel(old=>old.map((row,i)=>i!==index?row:e.target.checked?[...row,term]:row.filter(t=>t!==term)))}/> {term}
            </label>)}
            <button type="button" onClick={()=>setModel(old=>old.filter((_,i)=>i!==index))}>Remove object {index+1}</button>
          </fieldset>)}
          <button type="button" disabled={busy||model.length>=8} onClick={()=>setModel(old=>[...old,[]])}>Add object</button>
          <p>{model.length} objects in your model. Only these objects exist.</p>
        </fieldset>}
        {(state.question.requires_reason||state.question.reason_options)&&<label><input style={{width:'auto',marginRight:8}} type="checkbox" disabled={busy||state.pending_answer?.guessed} checked={guessed||!!state.pending_answer?.guessed} onChange={e=>setGuessed(e.target.checked)}/> I guessed or used outside help</label>}
        {state.phase==='justify'?<button disabled={busy||reason===undefined} onClick={()=>act('justify')}>Check reasoning</button>:<button disabled={busy||selected===undefined||(!!state.question.reason_options&&reason===undefined)} onClick={()=>act('answer')}>{state.question.requires_reason?'Save answer':'Check answer'}</button>}
        {state.phase==='check'&&<button disabled={busy||state.assisted} onClick={()=>act('hint')}>Use a hint (assisted)</button>}
        {state.hint&&<p role="note">{state.hint}</p>}
      </section>}
      {state.phase==='feedback'&&state.feedback&&<section>
        <h2>{state.feedback.correct?'Correct':'Let’s examine the choices'}</h2>
        <p>{state.feedback.stem}</p>
        {state.feedback.passage&&<article aria-label="Reading passage"><p>{state.feedback.passage}</p></article>}
        {state.feedback.figure&&<TeachingFigure figure={state.feedback.figure} labels={state.feedback.options}/>}
        {state.feedback.diagram&&<TeachingSceneView scene={state.feedback.diagram} label="Given diagram"/>}
        <p>{state.feedback.independent?'Fresh, unassisted check recorded.':'This response is learning evidence, not an independent pass.'}</p>
        {state.feedback.reason_explanation&&<p>{state.feedback.reason_explanation}</p>}
        {state.feedback.construction_feedback&&<p>{state.feedback.construction_feedback}</p>}
        <h3>Understand all four options</h3>
        <ol>{state.feedback.options.map((option,i)=><li key={i}><strong>{option}{i+1===state.feedback!.correct_option?' — correct':''}</strong><p>{state.feedback!.explanations[i]}</p></li>)}</ol>
        <p>{state.feedback.repair}</p><button disabled={busy} onClick={()=>act('continue')}>Continue</button>
      </section>}
      {(state.phase==='waiting'||state.phase==='complete')&&<section>
        <h2>{state.phase==='complete'?'Pilot retention checks completed':'Spaced revision scheduled'}</h2>
        {state.due_at?<p>Next revision: {new Date(state.due_at+'Z').toLocaleString()}</p>:<p>The reviewed delayed checks for this objective are complete.</p>}
        <p>{state.evidence_label}</p>
        <button disabled={busy||!state.due_at||clock<Date.parse(state.due_at+'Z')} onClick={()=>act('revise')}>Start due revision</button>
      </section>}
    </>}
  </main>;
}
