import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { ContentTree, fetchContentTree, prefetchTopicPackage } from "../api";

export default function LearnPage() {
  const [params] = useSearchParams();
  const requestedSubject = params.get("subject");
  const [tree, setTree] = useState<ContentTree | null>(null);
  const [active, setActive] = useState("reasoning");
  const [query, setQuery] = useState("");
  const [priority, setPriority] = useState("all");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchContentTree()
      .then((data) => {
        if (cancelled) return;
        setTree(data);
        const requestedExists = requestedSubject
          ? data.subjects.some((item) => item.slug === requestedSubject)
          : false;
        if (requestedExists && requestedSubject) {
          setActive(requestedSubject);
        } else if (data.subjects.length) {
          setActive(data.subjects[0].slug);
        }
      })
      .catch(() => {
        if (!cancelled) setError("Could not load learning content.");
      });
    return () => {
      cancelled = true;
    };
  }, [requestedSubject]);

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
              <strong>{tree.totals?.topics ?? 0}</strong> topics • <strong>{tree.totals?.lessons ?? 0}</strong> lessons
            </p>
          )}
        </div>
      </section>

      {error && <section className="emptyCard">{error}</section>}

      {!tree && !error && (
        <section className="learnLoading" aria-label="Loading learning topics">
          <div className="subjectTabs learnSkeletonTabs">
            {Array.from({length: 4}).map((_, index) => (
              <div className="skeletonBlock skeletonTab" key={index} />
            ))}
          </div>
          <div className="learnTools learnSkeletonTools">
            <div className="skeletonBlock skeletonInput" />
            <div className="skeletonBlock skeletonInput" />
            <div className="skeletonBlock skeletonSummary" />
          </div>
          <div className="topicGrid">
            {Array.from({length: 6}).map((_, index) => (
              <article className="topicCard skeletonCard" key={index}>
                <div className="skeletonBlock skeletonLine short" />
                <div className="skeletonBlock skeletonTitle" />
                <div className="skeletonBlock skeletonLine" />
                <div className="skeletonBlock skeletonButton" />
              </article>
            ))}
          </div>
        </section>
      )}

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
                <small>{item.topic_count} topics</small>
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
                <article
                  className="topicCard"
                  key={topic.id}
                  onMouseEnter={() => prefetchTopicPackage(topic.id)}
                  onFocus={() => prefetchTopicPackage(topic.id)}
                >
                  <div className="topicCardTopline">
                    <span>Priority {topic.priority}</span>
                    <small>{topic.lesson_count ? "Lesson ready" : "Lesson pending"}</small>
                  </div>
                  <h3>{topic.name}</h3>
                  <p>Concept lesson • verified practice bank • topic assessment</p>
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
