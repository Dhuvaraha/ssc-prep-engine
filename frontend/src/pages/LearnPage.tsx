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
        <nav>
          <Link to="/planner">Today</Link>
          <Link to="/mocks">Mocks</Link>
          <Link to="/">Dashboard</Link>
        </nav>
      </header>

      <section className="learnHero">
        <div>
          <p className="eyebrow">SSC CGL • Core study bank</p>
          <h1>Build the pattern before chasing speed.</h1>
        </div>
        <div>
          <p>Every listed topic now has a concise lesson and a verified original drill set.</p>
          {tree && (
            <p className="contentCountLine">
              <strong>{tree.totals?.lessons ?? 0}</strong> lessons • <strong>{tree.totals?.questions ?? 0}</strong> practice questions
            </p>
          )}
        </div>
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
                <small>{item.question_count} Q</small>
              </button>
            ))}
          </div>

          <section className="topicGrid">
            {subject?.topics.map((topic) => (
              <article className="topicCard" key={topic.id}>
                <span>Topic</span>
                <h3>{topic.name}</h3>
                <p>{topic.lesson_count ? "Lesson ready" : "Lesson pending"} • {topic.question_count} verified questions</p>
                <div className="topicCardActions">
                  <Link className="secondaryLink" to={"/learn/topic/" + topic.id}>Study lesson</Link>
                  <Link className="primaryMiniLink" to={"/practice?topic_id=" + topic.id + "&mode=guided"}>Practice</Link>
                </div>
              </article>
            ))}
          </section>
        </>
      )}
    </main>
  );
}
