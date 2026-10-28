export type Point = {x:number;y:number};
export type TeachingScene = {description:string;polygons:Point[][];dots:Point[];lines:Point[][]};
export type TeachingFigureData = {stem:TeachingScene;options:TeachingScene[]};

export function TeachingSceneView({scene,label}:{scene:TeachingScene;label:string}) {
  const points=(values:Point[])=>values.map(p=>`${p.x},${-p.y}`).join(' ');
  return <figure><figcaption>{label}</figcaption>
    <svg viewBox="-105 -105 210 210" role="img" aria-label={scene.description} style={{width:'100%',maxWidth:240,height:'auto',background:'white'}}>
      {scene.polygons.map((shape,i)=><polygon key={'shape'+i} points={points(shape)} fill="#d7eafa" stroke="#173a5e" strokeWidth="3"/>)}
      {scene.lines.map((line,i)=><polyline key={'line'+i} points={points(line)} fill="none" stroke="#555" strokeWidth="1.5"/>)}
      {scene.dots.map((p,i)=><circle key={'dot'+i} cx={p.x} cy={-p.y} r="4" fill="#111"/>)}
    </svg>
  </figure>;
}

export default function TeachingFigure({figure}:{figure:TeachingFigureData}) {
  return <section aria-label="Question figures"><TeachingSceneView scene={figure.stem} label="Given figure"/>
    <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(130px,1fr))',gap:8}}>
      {figure.options.map((scene,i)=><TeachingSceneView key={i} scene={scene} label={'Option '+(i+1)}/>)}
    </div>
  </section>;
}
