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
  practice: "/learn",
  mock: "/mocks",
  revision: "/revision",
  flashcards: "/revision",
};

export default function PlannerPage() {
  const [plan, setPlan] = useState<TodayPlan | null>(null);
  const [needsSetup, setNeedsSetup] = useState(false);
  const [examDate, setExamDate] = useState("2026-10-15");
  const [dailyMinutes, setDailyMinutes] = useState(240);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    if (!getToken()) {
      navigate("/login");
      return;
    }
    fetchTodayPlan()
      .then((data) => {
        setPlan(data);
        setExamDate(data.target.exam_date);
        setDailyMinutes(data.target.daily_minutes);
      })
      .catch((err) => {
        if (err instanceof Error && err.message.includes("Set an exam target")) {
          setNeedsSetup(true);
        } else {
          setError("Could not load today's plan.");
        }
      });
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
    await updatePlannerTask(taskId, completed);
    setPlan({
      ...plan,
      progress: {
        ...plan.progress,
        completed_tasks: plan.progress.completed_tasks + (completed ? 1 : -1),
        completed_minutes:
          plan.progress.completed_minutes
          + (completed
            ? plan.tasks.find((task) => task.id === taskId)?.target_minutes ?? 0
            : -(plan.tasks.find((task) => task.id === taskId)?.target_minutes ?? 0)),
      },
      tasks: plan.tasks.map((task) =>
        task.id === taskId ? {...task, status: completed ? "completed" : "pending"} : task
      ),
    });
  }

  async function rebuild() {
    setBusy(true);
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
          <p className="muted">Your plan adapts to weak topics, revision due and days remaining.</p>
        </div>
        <nav>
          <Link to="/analytics">Analytics</Link>
          <Link to="/">Dashboard</Link>
        </nav>
      </header>

      {(needsSetup || !plan) && (
        <section className="plannerSetup">
          <p className="eyebrow">Set your target</p>
          <h1>Tell the planner when the exam is.</h1>
          <form onSubmit={saveConfig} className="plannerSetupForm">
            <label>
              SSC CGL exam date
              <input type="date" value={examDate} onChange={(e) => setExamDate(e.target.value)} required />
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

      {plan && !needsSetup && (
        <>
          <section className="plannerHero">
            <div>
              <p className="eyebrow">SSC CGL Tier I</p>
              <h1>{plan.target.days_left} days left</h1>
              <p>{plan.progress.planned_minutes} minutes planned today • {plan.target.daily_minutes} minute daily budget</p>
            </div>
            <div className="plannerProgress">
              <strong>{progress}%</strong>
              <span>{plan.progress.completed_tasks} / {plan.progress.total_tasks} tasks</span>
            </div>
          </section>

          <section className="plannerToolbar">
            <div className="plannerBar"><span style={{width: progress + "%"}} /></div>
            <button className="secondary" onClick={rebuild} disabled={busy}>Rebalance pending plan</button>
          </section>

          <section className="plannerTaskList">
            {plan.tasks.map((task, index) => {
              const completed = task.status === "completed";
              const link = task.topic_id && (task.activity_type === "learn" || task.activity_type === "practice")
                ? task.activity_type === "learn"
                  ? "/learn/topic/" + task.topic_id
                  : "/practice?topic_id=" + task.topic_id + "&mode=adaptive"
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
                      <span>{task.target_minutes} min</span>
                      {task.target_questions && <span>{task.target_questions} questions</span>}
                    </div>
                    <h2>{task.title}</h2>
                    <p className="plannerTaskReason"><strong>Why this?</strong> {task.reason}</p>
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
