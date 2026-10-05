import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { AnalyticsSummary, fetchAnalyticsSummary } from "../api";
import { getToken } from "../auth";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    if (!getToken()) {
      navigate("/login");
      return;
    }
    fetchAnalyticsSummary()
      .then(setData)
      .catch(() => setError("Could not load analytics."));
  }, [navigate]);

  if (!data) {
    return (
      <main className="shell">
        <header className="topbar">
          <div>
            <p className="brand">Performance Analytics</p>
            <p className="muted">Accuracy, speed, mastery and mock performance.</p>
          </div>
          <Link to="/">Dashboard</Link>
        </header>
        <section className="emptyCard">{error || "Loading analytics..."}</section>
      </main>
    );
  }

  const errorEntries = Object.entries(data.errors.breakdown);

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="brand">Performance Analytics</p>
          <p className="muted">See where marks are being gained and lost.</p>
        </div>
        <nav>
          <Link to="/practice">Practice</Link>
          <Link to="/mocks">Mocks</Link>
          <Link to="/">Dashboard</Link>
        </nav>
      </header>

      <section className="analyticsHero">
        <div>
          <p className="eyebrow">Exam readiness</p>
          <h1>{data.overview.readiness}%</h1>
          <p>
            Combined from practice accuracy, topic mastery, speed and mock accuracy.
            This becomes more meaningful as you complete more sessions.
          </p>
        </div>
        <div className="readinessRing" aria-label={"Readiness " + data.overview.readiness + "%"}>
          <strong>{data.overview.readiness}%</strong>
          <span>ready</span>
        </div>
      </section>

      <section className="analyticsMetricGrid">
        <article>
          <span>Practice accuracy</span>
          <strong>{data.overview.accuracy}%</strong>
          <small>{data.overview.practice_attempts} attempts</small>
        </article>
        <article>
          <span>Speed score</span>
          <strong>{data.overview.speed_score}%</strong>
          <small>Within topic target time</small>
        </article>
        <article>
          <span>Topic mastery</span>
          <strong>{data.overview.mastery}%</strong>
          <small>Across practised topics</small>
        </article>
        <article>
          <span>Mock attempt rate</span>
          <strong>{data.overview.mock_attempt_rate}%</strong>
          <small>Questions attempted in mocks</small>
        </article>
      </section>

      <section className="analyticsSplit">
        <article className="analyticsCard">
          <div className="analyticsCardHead">
            <div>
              <p className="eyebrow">Weakness map</p>
              <h2>Topics to fix next</h2>
            </div>
            <Link to="/learn">Open Learn</Link>
          </div>

          {data.weak_topics.length === 0 ? (
            <p className="muted">Practice some topic questions to build your weakness map.</p>
          ) : (
            <div className="topicAnalyticsList">
              {data.weak_topics.map((topic) => (
                <div className="topicAnalyticsRow" key={topic.topic_id}>
                  <div>
                    <strong>{topic.topic_name}</strong>
                    <span>{topic.attempts} attempts • {topic.avg_time_seconds}s avg</span>
                  </div>
                  <div className="topicAnalyticsScores">
                    <span>Accuracy <strong>{topic.accuracy}%</strong></span>
                    <span>Mastery <strong>{topic.mastery}%</strong></span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="analyticsCard">
          <p className="eyebrow">Score leakage</p>
          <h2>Fix avoidable errors</h2>
          <div className="scoreLeakage">
            <strong>+{data.errors.potential_score_gain}</strong>
            <span>potential marks from avoidable errors</span>
          </div>
          {errorEntries.length === 0 ? (
            <p className="muted">Classify wrong practice answers to see error patterns.</p>
          ) : (
            <div className="errorBreakdown">
              {errorEntries.map(([name, count]) => (
                <div key={name}>
                  <span>{name.replaceAll("_", " ")}</span>
                  <strong>{count}</strong>
                </div>
              ))}
            </div>
          )}
        </article>
      </section>

      <section className="analyticsCard recentMocksCard">
        <div className="analyticsCardHead">
          <div>
            <p className="eyebrow">Recent tests</p>
            <h2>Mock performance</h2>
          </div>
          <Link to="/mocks">Take a mock</Link>
        </div>

        {data.recent_mocks.length === 0 ? (
          <p className="muted">No submitted mocks yet.</p>
        ) : (
          <div className="recentMockList">
            {data.recent_mocks.map((mock) => (
              <div className="recentMockRow" key={mock.attempt_id}>
                <div>
                  <strong>{mock.mode === "full" ? "Full mock" : mock.mode === "sectional" ? "Sectional test" : "Mini mock"}</strong>
                  <span>{mock.submitted_at ? new Date(mock.submitted_at).toLocaleDateString() : ""}</span>
                </div>
                <strong>{mock.score} marks</strong>
                <span>{mock.correct} correct • {mock.incorrect} wrong • {mock.unattempted} skipped</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
