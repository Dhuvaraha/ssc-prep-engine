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
  const [revisionDue, setRevisionDue] = useState<number | null>(null);
  const [backupError, setBackupError] = useState("");
  const [exporting, setExporting] = useState(false);
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
    if (exporting) return;
    setExporting(true);
    setBackupError("");
    try {
      const blob = await exportBackup();
      const url = URL.createObjectURL(blob);
      try {
        const link = document.createElement("a");
        link.href = url;
        link.download = "ssc-prep-backup.json";
        link.click();
      } finally {
        URL.revokeObjectURL(url);
      }
    } catch {
      setBackupError("Backup export failed. Your study data is unchanged; please try again.");
    } finally {
      setExporting(false);
    }
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
          {authenticated && <Link to="/settings">Settings</Link>}
          {authenticated ? (
            <>
              <button className="navButton" disabled={exporting} onClick={() => void saveBackup()}>{exporting ? "Exporting..." : "Export backup"}</button>
              <button className="navButton" onClick={logout}>Logout</button>
            </>
          ) : (
            <Link to="/login">Login</Link>
          )}
        </nav>
      </header>

      <section className="hero">
        <p className="eyebrow">SSC CGL • Personal preparation engine</p>
        <h1>
          {!authenticated
            ? "Build your SSC preparation, one topic at a time."
            : analytics?.coach.evidence_level === "baseline"
              ? "Discover your starting point."
              : analytics ? "Continue where you left off." : "Your study dashboard."}
        </h1>
        <p className="lead">
          {analytics?.coach.evidence_level === "baseline"
            ? "Take the 40-question starting diagnostic to sample all four subjects, then use your Learning Path for deeper topic practice. A diagnostic is not an exam readiness score."
            : "Learn a topic, practise its patterns, take a timed test and revisit mistakes. Your study plan adapts as you improve."}
        </p>
        <div className="heroActions">
          <Link className="primaryLink" to={authenticated ? "/planner" : "/login"}>
            {authenticated ? "Open today's plan" : "Login and start"}
          </Link>
          <Link className="secondaryLink" to="/learn">Browse all lessons</Link>
          {authenticated && <Link className="secondaryLink" to="/mocks?mode=diagnostic">Starting Diagnostic (40Q)</Link>}
        </div>
        {tree && (
          <p className="heroContentStatus">
            <strong>{tree.totals?.topics ?? 0}</strong> topics • <strong>{tree.totals?.lessons ?? 0}</strong> lessons • verified practice bank • 4 exam sections
          </p>
        )}
      </section>

      {backupError && <p className="errorText" role="alert">{backupError}</p>}

      <section className="metrics">
        <article>
          <span>Readiness</span>
          <strong>{analytics?.overview.readiness != null ? analytics.overview.readiness + "%" : "—"}</strong>
          <small>{analytics?.overview.readiness == null ? "Full-test readiness not assessed" : "Provisional — based on exam evidence"}</small>
        </article>
        <article>
          <span>Accuracy</span>
          <strong>{analytics && analytics.overview.practice_attempts > 0 ? analytics.overview.accuracy + "%" : "—"}</strong>
          <small>{analytics ? analytics.overview.practice_attempts + " practice attempts" : "Track correct / attempted"}</small>
        </article>
        <article>
          <span>Revision due</span>
          <strong>{authenticated ? (revisionDue ?? "—") : "—"}</strong>
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
                  <small>{subject.topic_count} topics • {subject.lesson_count} lessons</small>
                )}
                <Link className="secondaryLink" to={"/learn?subject=" + slug}>Study section</Link>
              </article>
            );
          })}
        </div>
      </section>

      <section className="quickStartGrid">
        <article>
          <p className="eyebrow">If you are starting from zero</p>
          <h3>Start your Learning Path</h3>
          <p>Choose a topic, learn the concept, then progress from Easy foundations to Medium application and Hard challenges as your independent answers improve.</p>
          <Link to="/learn">Choose a topic →</Link>
        </article>
        <article>
          <p className="eyebrow">If you want an exam check</p>
          <h3>Take the 40-question starting diagnostic</h3>
          <p>10 questions per subject with Easy, Medium and Hard samples. Results identify early learning signals, not overall exam readiness.</p>
          <Link to={authenticated ? "/mocks?mode=diagnostic" : "/login"}>Start diagnostic →</Link>
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
