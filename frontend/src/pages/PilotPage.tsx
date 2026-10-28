import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import TeachingJourney from '../components/TeachingJourney';
import { pilotCatalog, objectiveJourney, type PilotObjective, type JourneyAction } from '../api';

export function ObjectivePage() {
  const { objectiveId = '' } = useParams();
  const load=useCallback((action?:JourneyAction)=>objectiveJourney(objectiveId,action),[objectiveId]);
  return <TeachingJourney key={objectiveId} title={'Teaching objective '+objectiveId} load={load}/>;
}

export default function PilotPage() {
  const [objectives,setObjectives]=useState<PilotObjective[]>([]);
  const [error,setError]=useState('');
  useEffect(()=>{let active=true;pilotCatalog().then(items=>{if(active)setObjectives(items);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[]);
  return <main className="shell"><h1>Teaching pilot: choose a foundation</h1>
    <p>Objectives are separate from exam readiness. Work at your own pace; unavailable content has not passed release checks.</p>
    {error&&<p role="alert">{error}</p>}
    {!objectives.length&&!error&&<p role="status">Loading objectives…</p>}
    {Array.from(new Set(objectives.map(o=>o.topic))).map(topic=><section key={topic}><h2>{topic}</h2><ul>
      {objectives.filter(o=>o.topic===topic).map(o=><li key={o.objective_id}>{o.available
        ?<Link to={'/learn/pilot/'+o.objective_id}>{o.objective_id}: {o.title}</Link>
        :<span>{o.objective_id}: {o.title} — awaiting reviewed release</span>}</li>)}
    </ul></section>)}
  </main>;
}
