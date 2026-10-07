import { useEffect, useMemo, useState } from "react";
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

  const maxTrendAttempts = useMemo(
    () => Math.max(1, ...(data?.trend.map((item) => item.attempts) ?? [1])),
    [data],
  );

  if (!data) {
    return (
      <main className="shell">
        {error ? (
          <section className="emptyCard">{error}</section>
        ) : (
          <section className="analyticsLoading" aria-label="Loading analytics">
            <div className="skeletonBlock analyticsHeroSkeleton" />
            <div className="analyticsMetricGrid">
              {Array.from({length: 4}).map((_, index) => (
                <div className="skeletonBlock analyticsMetricSkeleton" key={index} />
              ))}
            </div>
            <div className="skeletonBlock analyticsPanelSkeleton" />
          </section>
        )}
      </main>
    );
  }

  const errorEntries = Object.entries(data.errors.breakdown);
  const baselinePending = data.coach.evidence_level === "baseline";
  const established = data.coach.evidence_level === "established";

  return (
    <main className="shell">
      <section className="analyticsHero">
        <div>
          <p className="eyebrow">Exam readiness • {data.coach.evidence_level} evidence</p>
          <h1>{baselinePending ? "Baseline" : data.overview.readiness + "%"}</h1>
          <p>
            {baselinePending
              ? "Readiness is intentionally not treated as a real score until you create practice and timed-test evidence."
              : "Combined from practice accuracy, topic mastery, speed and mock accuracy. Treat it as provisional until your evidence becomes established."}
          </p>
          <div className="analyticsHeroLinks">
            <Link to={data.coach.primary_action.path}>{data.coach.primary_action.title}</Link>
            <Link to="/mocks">Open Mock Lab</Link>
          </div>
        </div>
        <div
          className={"readinessRing" + (baselinePending ? " readinessPending" : "")}
          aria-label={baselinePending ? "Readiness baseline pending" : "Readiness " + data.overview.readiness + "%"}
        >
          <strong>{baselinePending ? "—" : data.overview.readiness + "%"}</strong>
          <span>{baselinePending ? "baseline pending" : "ready"}</span>
        </div>
      </section>

      <section className="analyticsCoachCard">
        <div className="analyticsCoachLead">
          <span>Personal coach</span>
          <h2>{data.coach.headline}</h2>
          <p>{data.coach.summary}</p>
        </div>
        <div className="analyticsCoachActions">
          <Link to={data.coach.primary_action.path}>
            <span>Do this first</span>
            <strong>{data.coach.primary_action.title}</strong>
            <p>{data.coach.primary_action.reason}</p>
          </Link>
          <Link to={data.coach.secondary_action.path}>
            <span>Then</span>
            <strong>{data.coach.secondary_action.title}</strong>
            <p>{data.coach.secondary_action.reason}</p>
          </Link>
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
          <small>Within target time</small>
        </article>
        <article>
          <span>Topic mastery</span>
          <strong>{data.overview.mastery}%</strong>
          <small>Across practised topics</small>
        </article>
        <article>
          <span>Study streak</span>
          <strong>{data.overview.streak}</strong>
          <small>consecutive active days</small>
        </article>
      </section>

      <section className="analyticsCard analyticsTrendCard">
        <div className="analyticsCardHead">
          <div>
            <p className="eyebrow">Last 14 days</p>
            <h2>Practice trend</h2>
          </div>
          <span className="muted">Height = attempts • label = accuracy</span>
        </div>
        <div className="trendBars">
          {data.trend.map((item) => (
            <div className="trendDay" key={item.date} title={item.attempts + " attempts • " + item.accuracy + "% accuracy"}>
              <div className="trendBarTrack">
                <span style={{height: Math.max(4, (item.attempts / maxTrendAttempts) * 100) + "%"}} />
              </div>
              <strong>{item.attempts ? Math.round(item.accuracy) + "%" : "—"}</strong>
              <small>{new Date(item.date + "T00:00:00").toLocaleDateString(undefined, {weekday: "narrow"})}</small>
            </div>
          ))}
        </div>
      </section>

      <section className="analyticsSplit">
        <article className="analyticsCard">
          <div className="analyticsCardHead">
            <div>
              <p className="eyebrow">{established ? "Weakness map" : "Early topic signals"}</p>
              <h2>{established ? "Topics to fix next" : "Topics to sample before judging"}</h2>
            </div>
            <Link to={established ? "/practice?mode=weak&limit=10" : "/learn"}>
              {established ? "Weak drill" : "Guided lessons"}
            </Link>
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
                  <Link
                    className="analyticsRepairLink"
                    to={"/practice?topic_id=" + topic.topic_id + "&mode=" + (established ? "adaptive" : "guided") + "&limit=10"}
                  >
                    {established ? "Repair" : "Sample"}
                  </Link>
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

      <section className="analyticsSplit analyticsSecondSplit">
        <article className="analyticsCard">
          <p className="eyebrow">Subject performance</p>
          <h2>Where the section marks stand</h2>
          {data.subject_breakdown.length === 0 ? (
            <p className="muted">Subject analytics appears after practice.</p>
          ) : (
            <div className="subjectAnalyticsList">
              {data.subject_breakdown.map((item) => (
                <div key={item.subject_slug}>
                  <div>
                    <strong>{item.subject_name}</strong>
                    <span>{item.attempts} attempts • {item.avg_time_seconds}s avg</span>
                  </div>
                  <b>{item.accuracy}%</b>
                  <div className="subjectAccuracyTrack"><span style={{width: item.accuracy + "%"}} /></div>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="analyticsCard">
          <p className="eyebrow">Confidence calibration</p>
          <h2>Know when confidence is lying</h2>
          <div className="confidenceAnalyticsGrid">
            <div><span>Sure accuracy</span><strong>{data.confidence.sure_accuracy}%</strong></div>
            <div><span>Unsure accuracy</span><strong>{data.confidence.unsure_accuracy}%</strong></div>
            <div><span>Guess rate</span><strong>{data.confidence.guess_rate}%</strong></div>
            <div><span>Overconfident errors</span><strong>{data.confidence.overconfident_errors}</strong></div>
          </div>
        </article>
      </section>

      {data.next_actions.length > 0 && (
        <section className="analyticsCard nextActionsCard">
          <div className="analyticsCardHead">
            <div>
              <p className="eyebrow">Recommended next actions</p>
              <h2>What to do now</h2>
            </div>
            <Link to="/planner">Open today's plan</Link>
          </div>
          <div className="nextActionList">
            {data.next_actions.map((item, index) => (
              <article key={index}>
                <span>{index + 1}</span>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.reason}</p>
                </div>
                {item.topic_id ? (
                  <Link to={"/practice?topic_id=" + item.topic_id + "&mode=adaptive&limit=10"}>Start →</Link>
                ) : (
                  <Link to="/revision">Review →</Link>
                )}
              </article>
            ))}
          </div>
        </section>
      )}

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
                  <strong>{mock.mode === "full" ? "Full Tier-I simulation" : mock.mode === "sectional" ? "Section test" : mock.mode === "mini" ? "Quick Sprint" : "Topic test"}</strong>
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
