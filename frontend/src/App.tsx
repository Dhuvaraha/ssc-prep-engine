const subjects = [
  ["Reasoning", "Pattern recognition, logic and speed"],
  ["General Awareness", "Static GK, science and recall"],
  ["Quantitative Aptitude", "Concepts, shortcuts and timed solving"],
  ["English", "Grammar, vocabulary and comprehension"],
];

export default function App() {
  return (
    <main className="shell">
      <header className="hero">
        <p className="eyebrow">SSC CGL • Personal preparation engine</p>
        <h1>Know exactly what to study next.</h1>
        <p className="lead">
          Learn concepts, practise targeted questions, analyse mistakes and automatically
          revise weak areas.
        </p>
        <button>Start today's plan</button>
      </header>

      <section className="metrics">
        <article><span>Readiness</span><strong>—</strong><small>Starts after diagnostic</small></article>
        <article><span>Accuracy</span><strong>—</strong><small>Track correct / attempted</small></article>
        <article><span>Revision due</span><strong>0</strong><small>Wrong, slow & guessed</small></article>
      </section>

      <section>
        <div className="sectionHeading">
          <div>
            <p className="eyebrow">CGL Tier I</p>
            <h2>Preparation areas</h2>
          </div>
          <p>Learn → Practice → Test → Analyse → Revise</p>
        </div>
        <div className="subjectGrid">
          {subjects.map(([name, description]) => (
            <article className="subjectCard" key={name}>
              <span>Subject</span>
              <h3>{name}</h3>
              <p>{description}</p>
              <button className="secondary">Explore</button>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
