import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { ContentTree, fetchContentTree } from "../api";

export default function LearnPage() {
  const [tree, setTree] = useState<ContentTree | null>(null);
  const [active, setActive] = useState("reasoning");
  const [query, setQuery] = useState("");
  const [priority, setPriority] = useState("all");
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
  const topics = useMemo(() => {
    const source = subject?.topics ?? [];
    const needle = query.trim().toLowerCase();
    return source.filter((topic) => {
      const matchesSearch = !needle || topic.name.toLowerCase().includes(needle) || topic.slug.includes(needle);
      const matchesPriority = priority === "all" || topic.priority === Number(priority);
      return matchesSearch && matchesPriority;
    });
  }, [subject, query, priority]);

  return (
    <main className="shell">
      <section className="learnHero">
        <div>
          <p className="eyebrow">SSC CGL • Core study bank</p>
          <h1>Build the pattern before chasing speed.</h1>
        </div>
        <div>
          <p>Every topic connects lesson → question patterns → quick check → guided practice → topic test.</p>
          {tree && (
            <p className="contentCountLine">
              <strong>{tree.totals?.lessons ?? 0}</strong> lessons • <strong>{tree.totals?.questions ?? 0}</strong> verified questions
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

          <section className="learnTools">
            <label>
              <span>Find a topic</span>
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search e.g. percentage, syllogism, spelling..." />
            </label>
            <label>
              <span>Priority</span>
              <select value={priority} onChange={(event) => setPriority(event.target.value)}>
                <option value="all">All priorities</option>
                <option value="5">High priority</option>
                <option value="4">Priority 4</option>
                <option value="3">Priority 3</option>
                <option value="2">Priority 2</option>
                <option value="1">Priority 1</option>
              </select>
            </label>
            <div className="learnToolSummary">
              <strong>{topics.length}</strong>
              <span>topics shown</span>
            </div>
          </section>

          {topics.length === 0 ? (
            <section className="emptyCard">No topics match this search or priority filter.</section>
          ) : (
            <section className="topicGrid">
              {topics.map((topic) => (
                <article className="topicCard" key={topic.id}>
                  <div className="topicCardTopline">
                    <span>Priority {topic.priority}</span>
                    <small>{topic.question_count} Q</small>
                  </div>
                  <h3>{topic.name}</h3>
                  <p>{topic.lesson_count ? "Lesson ready" : "Lesson pending"} • verified practice bank</p>
                  <div className="topicCardActions">
                    <Link className="secondaryLink" to={"/learn/topic/" + topic.id}>Study lesson</Link>
                    <Link className="primaryMiniLink" to={"/practice?topic_id=" + topic.id + "&mode=guided&limit=10"}>Practice</Link>
                    <Link className="topicTestLink" to={"/mocks?topic_id=" + topic.id}>Test</Link>
                  </div>
                </article>
              ))}
            </section>
          )}
        </>
      )}
    </main>
  );
}
