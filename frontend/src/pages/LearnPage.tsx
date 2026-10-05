import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ContentTree, fetchContentTree } from "../api";

export default function LearnPage() {
  const [tree, setTree] = useState<ContentTree | null>(null);
  const [active, setActive] = useState("reasoning");
  const [error, setError] = useState("");

  useEffect(() => {
    fetchContentTree()
      .then((data) => {
        setTree(data);
        if (data.subjects.length) setActive(data.subjects[0].slug);
      })
      .catch(() => setError("Could not load learning content."));
  }, []);

  const subject = tree?.subjects.find((item) => item.slug === active);

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="brand">Learn</p>
          <p className="muted">Concept → shortcut → example → practice</p>
        </div>
        <nav><Link to="/">Dashboard</Link></nav>
      </header>

      <section className="learnHero">
        <div>
          <p className="eyebrow">SSC CGL</p>
          <h1>Build the pattern before chasing speed.</h1>
        </div>
        <p>Start from a topic, learn the core rule and move straight into guided practice.</p>
      </section>

      {error && <section className="emptyCard">{error}</section>}

      {tree && (
        <>
          <div className="subjectTabs">
            {tree.subjects.map((item) => (
              <button
                key={item.slug}
                className={active === item.slug ? "tab activeTab" : "tab"}
                onClick={() => setActive(item.slug)}
              >
                {item.name}
              </button>
            ))}
          </div>

          <section className="topicGrid">
            {subject?.topics.map((topic) => (
              <Link className="topicCard" to={"/learn/topic/" + topic.id} key={topic.id}>
                <span>Topic</span>
                <h3>{topic.name}</h3>
                <p>Learn the rule, shortcut and worked example.</p>
                <strong>Open lesson →</strong>
              </Link>
            ))}
          </section>
        </>
      )}
    </main>
  );
}
