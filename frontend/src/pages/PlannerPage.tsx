import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  TodayPlan,
  fetchTodayPlan,
  rebuildTodayPlan,
  setPlannerConfig,
  updatePlannerTask,
} from "../api";
import { getToken } from "../auth";

const activityLinks: Record<string, string> = {
  learn: "/learn",
  practice: "/practice?mode=mixed&limit=10",
  mock: "/mocks",
  revision: "/revision",
  flashcards: "/revision",
};

function localDatePlusDays(days: number): string {
  const value = new Date();
  value.setDate(value.getDate() + days);
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export default function PlannerPage() {
  const [plan, setPlan] = useState<TodayPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [needsSetup, setNeedsSetup] = useState(false);
  const [examDate, setExamDate] = useState(() => localDatePlusDays(30));
  const [dailyMinutes, setDailyMinutes] = useState(240);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    if (!getToken()) {
      navigate("/login");
      return;
    }
    setLoading(true);
    fetchTodayPlan()
      .then((data) => {
        setPlan(data);
        setExamDate(data.target.exam_date);
        setDailyMinutes(data.target.daily_minutes);
        setNeedsSetup(false);
      })
      .catch((err) => {
        if (err instanceof Error && err.message.includes("Set an exam target")) {
          setNeedsSetup(true);
        } else {
          setError("Could not load today's plan.");
        }
      })
      .finally(() => setLoading(false));
  }, [navigate]);

  const progress = useMemo(() => {
    if (!plan || plan.progress.total_tasks === 0) return 0;
    return Math.round((plan.progress.completed_tasks / plan.progress.total_tasks) * 100);
  }, [plan]);

  async function saveConfig(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await setPlannerConfig(examDate, dailyMinutes);
      setPlan(data);
      setNeedsSetup(false);
    } catch {
      setError("Could not save planner settings.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleTask(taskId: number, completed: boolean) {
    if (!plan) return;
    setError("");
    try {
      await updatePlannerTask(taskId, completed);
      const minutes = plan.tasks.find((task) => task.id === taskId)?.target_minutes ?? 0;
      setPlan({
        ...plan,
        progress: {
          ...plan.progress,
          completed_tasks: plan.progress.completed_tasks + (completed ? 1 : -1),
          completed_minutes: plan.progress.completed_minutes + (completed ? minutes : -minutes),
        },
        tasks: plan.tasks.map((task) =>
          task.id === taskId ? {...task, status: completed ? "completed" : "pending"} : task
        ),
      });
    } catch {
      setError("Could not update that task. Your plan was not changed.");
    }
  }

  async function rebuild() {
    setBusy(true);
    setError("");
    try {
      setPlan(await rebuildTodayPlan());
    } catch {
      setError("Could not rebuild plan.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="plannerShell">
      <header className="topbar">
        <div>
          <p className="brand">Today's Preparation</p>
          <p className="muted">Concept first, then practice, timed testing and revision.</p>
        </div>
        <nav>
          <Link to="/analytics">Analytics</Link>
          <Link to="/">Dashboard</Link>
        </nav>
      </header>

      {loading && (
        <section className="plannerLoading" aria-label="Loading today's plan">
          <div className="plannerHero plannerHeroSkeleton">
            <div>
              <div className="skeletonBlock skeletonLine short" />
              <div className="skeletonBlock skeletonHeroTitle" />
              <div className="skeletonBlock skeletonLine" />
            </div>
            <div className="skeletonBlock skeletonCircle" />
          </div>
          <div className="plannerTaskList">
            {Array.from({length: 4}).map((_, index) => (
              <article className="plannerTask plannerTaskSkeleton" key={index}>
                <div className="skeletonBlock skeletonTaskCheck" />
                <div>
                  <div className="skeletonBlock skeletonLine short" />
                  <div className="skeletonBlock skeletonTaskTitle" />
                  <div className="skeletonBlock skeletonLine" />
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {!loading && (needsSetup || !plan) && (
        <section className="plannerSetup">
          <p className="eyebrow">Set your target</p>
          <h1>Tell the planner when the exam is.</h1>
          <form onSubmit={saveConfig} className="plannerSetupForm">
            <label>
              SSC CGL exam date
              <input type="date" min={localDatePlusDays(0)} value={examDate} onChange={(e) => setExamDate(e.target.value)} required />
            </label>
            <label>
              Study time available per day
              <select value={dailyMinutes} onChange={(e) => setDailyMinutes(Number(e.target.value))}>
                <option value={120}>2 hours</option>
                <option value={180}>3 hours</option>
                <option value={240}>4 hours</option>
                <option value={300}>5 hours</option>
                <option value={360}>6 hours</option>
                <option value={480}>8 hours</option>
              </select>
            </label>
            {error && <p className="errorText">{error}</p>}
            <button disabled={busy}>{busy ? "Building plan..." : "Generate my plan"}</button>
          </form>
        </section>
      )}

      {!loading && plan && !needsSetup && (
        <>
          <section className="plannerHero">
            <div>
              <p className="eyebrow">SSC CGL Tier I</p>
              <h1>{plan.target.days_left} calendar days</h1>
              <p className="plannerStudyDays">
                <strong>{plan.target.full_study_days}</strong> full study days available before exam day
              </p>
              <p>{plan.progress.planned_minutes} minutes planned today • {plan.target.daily_minutes} minute daily budget</p>
            </div>
            <div className="plannerProgress">
              <strong>{progress}%</strong>
              <span>{plan.progress.completed_tasks} / {plan.progress.total_tasks} tasks</span>
            </div>
          </section>

          {error && <section className="plannerInlineError">{error}</section>}

          <section className="plannerToolbar">
            <div className="plannerBar"><span style={{width: progress + "%"}} /></div>
            <button className="secondary" onClick={rebuild} disabled={busy}>Rebalance pending plan</button>
          </section>

          <section className="plannerTaskList">
            {plan.tasks.map((task, index) => {
              const completed = task.status === "completed";
              const practiceMode = task.title.startsWith("Guided practice") ? "guided" : "adaptive";
              const link = task.topic_id && (task.activity_type === "learn" || task.activity_type === "practice")
                ? task.activity_type === "learn"
                  ? "/learn/topic/" + task.topic_id
                  : "/practice?topic_id=" + task.topic_id + "&mode=" + practiceMode + "&limit=10"
                : activityLinks[task.activity_type] ?? "/";

              return (
                <article className={completed ? "plannerTask plannerTaskDone" : "plannerTask"} key={task.id}>
                  <button
                    className={completed ? "taskCheck taskChecked" : "taskCheck"}
                    aria-label={completed ? "Mark pending" : "Mark complete"}
                    onClick={() => void toggleTask(task.id, !completed)}
                  >
                    {completed ? "✓" : index + 1}
                  </button>
                  <div className="plannerTaskBody">
                    <div className="plannerTaskMeta">
                      <span>{task.activity_type}</span>
                      {task.subject_slug && <span>{task.subject_slug.replaceAll("-", " ")}</span>}
                      <span>{task.target_minutes} min</span>
                      {task.target_questions && <span>{task.target_questions} questions</span>}
                    </div>
                    <h2>{task.title}</h2>
                    <p className="plannerTaskReason"><strong>Why this?</strong> {task.reason}</p>
                    <p className="plannerTaskOutcome"><strong>Expected outcome:</strong> {task.expected_outcome}</p>
                  </div>
                  <Link className="taskOpen" to={link}>Open →</Link>
                </article>
              );
            })}
          </section>

          <section className="plannerSettings">
            <div>
              <strong>Plan settings</strong>
              <span>Exam: {new Date(plan.target.exam_date + "T00:00:00").toLocaleDateString()} • {plan.target.daily_minutes / 60}h/day</span>
            </div>
            <button className="secondary" onClick={() => setNeedsSetup(true)}>Change</button>
          </section>
        </>
      )}
    </main>
  );
}
