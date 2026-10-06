import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  AnalyticsSummary,
  ContentTree,
  exportBackup,
  fetchAnalyticsSummary,
  fetchContentTree,
  fetchRevisionQueue,
} from "../api";
import { clearToken, getToken } from "../auth";

const subjects = [
  ["reasoning", "Reasoning", "Pattern recognition, logic and speed"],
  ["general-awareness", "General Awareness", "Static GK, science and current recall"],
  ["quant", "Quantitative Aptitude", "Concepts, shortcuts and timed solving"],
  ["english", "English", "Grammar, vocabulary and comprehension"],
];

export default function DashboardPage() {
  const [tree, setTree] = useState<ContentTree | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [revisionDue, setRevisionDue] = useState(0);
  const authenticated = Boolean(getToken());
  const navigate = useNavigate();

  useEffect(() => {
    fetchContentTree().then(setTree).catch(() => undefined);

    if (authenticated) {
      fetchAnalyticsSummary().then(setAnalytics).catch(() => undefined);
      fetchRevisionQueue().then((items) => setRevisionDue(items.length)).catch(() => undefined);
    }
  }, [authenticated]);

  async function saveBackup() {
    if (!authenticated) {
      navigate("/login");
      return;
    }
    const blob = await exportBackup();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "ssc-prep-backup.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  function logout() {
    clearToken();
    navigate("/login");
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="brand">SSC Prep Engine</p>
          <p className="muted">CGL study system • lessons, drills, mocks and revision</p>
        </div>
        <nav>
          <Link to="/planner">Today</Link>
          <Link to="/learn">Learn</Link>
          <Link to="/revision">Revision</Link>
          <Link to="/analytics">Analytics</Link>
          <Link to="/mocks">Mock tests</Link>
          {authenticated ? (
            <>
              <button className="navButton" onClick={() => void saveBackup()}>Export backup</button>
              <button className="navButton" onClick={logout}>Logout</button>
            </>
          ) : (
            <Link to="/login">Login</Link>
          )}
        </nav>
      </header>

      <section className="hero">
        <p className="eyebrow">SSC CGL • Personal preparation engine</p>
        <h1>Study now. The content is ready.</h1>
        <p className="lead">
          Learn a topic, solve its drill set, take timed mocks, analyse mistakes and
          automatically revisit weak questions.
        </p>
        <div className="heroActions">
          <Link className="primaryLink" to={authenticated ? "/planner" : "/login"}>
            {authenticated ? "Open today's plan" : "Login and start"}
          </Link>
          <Link className="secondaryLink" to="/learn">Browse all lessons</Link>
          {authenticated && <Link className="secondaryLink" to="/mocks">Take a diagnostic mock</Link>}
        </div>
        {tree && (
          <p className="heroContentStatus">
            <strong>{tree.totals?.lessons ?? 0}</strong> lessons • <strong>{tree.totals?.questions ?? 0}</strong> verified practice questions • 4 exam sections
          </p>
        )}
      </section>

      <section className="metrics">
        <article>
          <span>Readiness</span>
          <strong>{analytics ? analytics.overview.readiness + "%" : "—"}</strong>
          <small>{analytics ? "Based on your practice + mocks" : "Starts after you practise"}</small>
        </article>
        <article>
          <span>Accuracy</span>
          <strong>{analytics ? analytics.overview.accuracy + "%" : "—"}</strong>
          <small>{analytics ? analytics.overview.practice_attempts + " practice attempts" : "Track correct / attempted"}</small>
        </article>
        <article>
          <span>Revision due</span>
          <strong>{authenticated ? revisionDue : "—"}</strong>
          <small>Wrong, slow & guessed questions</small>
        </article>
      </section>

      <section>
        <div className="sectionHeading">
          <div>
            <p className="eyebrow">CGL Tier I</p>
            <h2>Study by section</h2>
          </div>
          <p>Learn → Practice → Test → Analyse → Revise</p>
        </div>
        <div className="subjectGrid">
          {subjects.map(([slug, name, description]) => {
            const subject = tree?.subjects.find((item) => item.slug === slug);
            return (
              <article className="subjectCard" key={slug}>
                <span>Subject</span>
                <h3>{name}</h3>
                <p>{description}</p>
                {subject && (
                  <small>{subject.lesson_count} topics • {subject.question_count} questions</small>
                )}
                <Link className="secondaryLink" to="/learn">Study section</Link>
              </article>
            );
          })}
        </div>
      </section>

      <section className="quickStartGrid">
        <article>
          <p className="eyebrow">If you are starting from zero</p>
          <h3>Learn one topic first</h3>
          <p>Open a concise rule sheet, see a worked example, then immediately solve five questions.</p>
          <Link to="/learn">Start Learn mode →</Link>
        </article>
        <article>
          <p className="eyebrow">If you want an exam check</p>
          <h3>Take a 4-minute diagnostic</h3>
          <p>One question from each section gives the system an initial performance signal.</p>
          <Link to={authenticated ? "/mocks" : "/login"}>Open Mock Lab →</Link>
        </article>
        <article>
          <p className="eyebrow">If you made mistakes</p>
          <h3>Clear revision due</h3>
          <p>Wrong, slow and guessed questions return automatically on a spaced schedule.</p>
          <Link to={authenticated ? "/revision" : "/login"}>Open Revision Lab →</Link>
        </article>
      </section>
    </main>
  );
}
