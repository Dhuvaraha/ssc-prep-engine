import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  AnalyticsSummary,
  User,
  changePassword,
  exportBackup,
  fetchAnalyticsSummary,
  fetchCurrentUser,
  fetchTodayPlan,
  setPlannerConfig,
  updateCurrentUser,
} from "../api";
import { clearToken, getToken } from "../auth";

function todayPlusDays(days: number): string {
  const value = new Date();
  value.setDate(value.getDate() + days);
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export default function SettingsPage() {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [examDate, setExamDate] = useState(todayPlusDays(8));
  const [dailyMinutes, setDailyMinutes] = useState(180);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [preferredLanguage, setPreferredLanguage] = useState(localStorage.getItem("ssc_preferred_language") ?? "english");
  const [voiceRate, setVoiceRate] = useState(Number(localStorage.getItem("ssc_voice_rate") ?? "0.94"));
  const [autoSpeak, setAutoSpeak] = useState(localStorage.getItem("ssc_auto_speak") === "true");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) {
      navigate("/login");
      return;
    }

    Promise.all([
      fetchCurrentUser(),
      fetchTodayPlan().catch(() => null),
      fetchAnalyticsSummary().catch(() => null),
    ])
      .then(([account, plan, stats]) => {
        setUser(account);
        setDisplayName(account.display_name ?? "");
        setAnalytics(stats);
        if (plan) {
          setExamDate(plan.target.exam_date);
          setDailyMinutes(plan.target.daily_minutes);
        }
      })
      .catch(() => setError("Could not load account settings."))
      .finally(() => setLoading(false));
  }, [navigate]);

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      const updated = await updateCurrentUser(displayName);
      setUser(updated);
      setDisplayName(updated.display_name ?? "");
      setMessage("Profile saved.");
    } catch {
      setError("Could not save profile.");
    }
  }

  async function saveStudyPlan(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      await setPlannerConfig(examDate, dailyMinutes);
      setMessage("Study target updated and today's plan rebuilt.");
    } catch {
      setError("Could not update study target.");
    }
  }

  function savePreferences(event: FormEvent) {
    event.preventDefault();
    localStorage.setItem("ssc_preferred_language", preferredLanguage);
    localStorage.setItem("ssc_voice_rate", String(voiceRate));
    localStorage.setItem("ssc_auto_speak", String(autoSpeak));
    setError("");
    setMessage("Learning and voice preferences saved on this device.");
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setMessage("Password changed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not change password.");
    }
  }

  async function saveBackup() {
    setError("");
    try {
      const blob = await exportBackup();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "ssc-prep-backup.json";
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Could not export backup.");
    }
  }

  function logout() {
    clearToken();
    navigate("/login");
  }

  if (loading) {
    return <main className="settingsShell"><section className="settingsCard"><p>Loading profile…</p></section></main>;
  }

  const readinessLabel = analytics?.overview.readiness != null
    ? analytics.overview.readiness + "%"
    : "Not assessed";
  const masteryLabel = analytics?.overview.practice_attempts
    ? analytics.overview.mastery + "%"
    : "—";

  return (
    <main className="settingsShell">
      {(message || error) && (
        <div className={error ? "settingsNotice settingsError" : "settingsNotice"}>
          {error || message}
        </div>
      )}

      <section className="profileHero">
        <div>
          <span className="profileAvatar">{(displayName || user?.email || "U").slice(0, 2).toUpperCase()}</span>
          <div>
            <p className="eyebrow">Learner profile</p>
            <h1>{displayName || "SSC aspirant"}</h1>
            <p>{user?.email}</p>
          </div>
        </div>
        <div className="profileStatStrip">
          <div><span>Streak</span><strong>{analytics?.overview.streak ?? 0}d</strong></div>
          <div><span>Practice</span><strong>{analytics?.overview.practice_attempts ?? 0}</strong></div>
          <div>
            <span>{analytics?.overview.readiness == null ? "Exam readiness" : "Provisional readiness"}</span>
            <strong>{readinessLabel}</strong>
          </div>
          <div>
            <span>{"Practised-topic mastery"}</span>
            <strong>{masteryLabel}</strong>
          </div>
        </div>
      </section>

      <div className="settingsGrid">
        <section className="settingsCard">
          <p className="eyebrow">Profile</p>
          <h2>Name & account</h2>
          <form className="settingsForm" onSubmit={saveProfile}>
            <label>
              Display name
              <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} maxLength={120} placeholder="Your name" />
            </label>
            <label>
              Email
              <input value={user?.email ?? ""} disabled />
            </label>
            <button type="submit">Save profile</button>
          </form>
        </section>

        <section className="settingsCard">
          <p className="eyebrow">Preparation target</p>
          <h2>Exam & daily hours</h2>
          <form className="settingsForm" onSubmit={saveStudyPlan}>
            <label>
              SSC CGL exam date
              <input type="date" min={todayPlusDays(0)} value={examDate} onChange={(event) => setExamDate(event.target.value)} required />
            </label>
            <label>
              Daily study minutes
              <input type="number" min={45} max={720} step={15} value={dailyMinutes} onChange={(event) => setDailyMinutes(Number(event.target.value))} required />
            </label>
            <button type="submit">Update plan</button>
          </form>
        </section>

        <section className="settingsCard">
          <p className="eyebrow">Learning preferences</p>
          <h2>Language & voice</h2>
          <form className="settingsForm" onSubmit={savePreferences}>
            <label>
              Preferred coach style
              <select value={preferredLanguage} onChange={(event) => setPreferredLanguage(event.target.value)}>
                <option value="english">English</option>
                <option value="tanglish">Tanglish prompts + English exam content</option>
              </select>
            </label>
            <label>
              Voice speed — {voiceRate.toFixed(2)}×
              <input type="range" min={0.75} max={1.2} step={0.05} value={voiceRate} onChange={(event) => setVoiceRate(Number(event.target.value))} />
            </label>
            <label className="settingsCheck">
              <input type="checkbox" checked={autoSpeak} onChange={(event) => setAutoSpeak(event.target.checked)} />
              Auto-read teacher responses when supported
            </label>
            <button type="submit">Save preferences</button>
          </form>
        </section>

        <section className="settingsCard">
          <p className="eyebrow">Security</p>
          <h2>Change password</h2>
          <form className="settingsForm" onSubmit={savePassword}>
            <label>Current password<input type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} autoComplete="current-password" required /></label>
            <label>New password<input type="password" minLength={8} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} autoComplete="new-password" required /></label>
            <label>Confirm new password<input type="password" minLength={8} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} autoComplete="new-password" required /></label>
            <button type="submit">Change password</button>
          </form>
        </section>

        <section className="settingsCard settingsWide">
          <div className="analyticsCardHead">
            <div>
              <p className="eyebrow">Mock history</p>
              <h2>Recent test performance</h2>
            </div>
            <Link to="/mocks">Take a test</Link>
          </div>
          {!analytics?.recent_mocks.length ? (
            <p className="muted">No submitted mocks yet.</p>
          ) : (
            <div className="profileMockHistory">
              {analytics.recent_mocks.slice(0, 6).map((mock) => (
                <div key={mock.attempt_id}>
                  <strong>{
                    mock.mode === "full"
                      ? "Full Tier-I simulation"
                      : mock.mode === "sectional"
                        ? "Section test"
                        : mock.mode === "mini"
                          ? "Quick Sprint"
                          : "Topic test"
                  }</strong>
                  <span>{mock.score} marks</span>
                  <small>{mock.correct} correct • {mock.incorrect} wrong • {mock.unattempted} skipped</small>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="settingsCard">
          <p className="eyebrow">Data</p>
          <h2>Backup</h2>
          <p className="muted">Export a portable JSON snapshot of your learning progress.</p>
          <div className="settingsActions"><button className="secondary" onClick={() => void saveBackup()}>Export backup</button></div>
        </section>

        <section className="settingsCard">
          <p className="eyebrow">Session</p>
          <h2>Account controls</h2>
          <div className="settingsActions">
            <Link className="secondaryLink" to="/analytics">View analytics</Link>
            <button className="danger" onClick={logout}>Log out</button>
          </div>
        </section>
      </div>
    </main>
  );
}
