import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  User,
  changePassword,
  exportBackup,
  fetchCurrentUser,
  fetchTodayPlan,
  setPlannerConfig,
  updateCurrentUser,
} from "../api";
import { clearToken, getToken } from "../auth";

function todayPlusDays(days: number): string {
  const value = new Date();
  value.setDate(value.getDate() + days);
  return value.toISOString().slice(0, 10);
}

export default function SettingsPage() {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [examDate, setExamDate] = useState(todayPlusDays(8));
  const [dailyMinutes, setDailyMinutes] = useState(180);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
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
    ])
      .then(([account, plan]) => {
        setUser(account);
        setDisplayName(account.display_name ?? "");
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
    return (
      <main className="settingsShell">
        <section className="settingsCard"><p>Loading settings…</p></section>
      </main>
    );
  }

  return (
    <main className="settingsShell">
      <header className="topbar">
        <div>
          <p className="brand">Settings</p>
          <p className="muted">Account, exam target and data controls.</p>
        </div>
        <nav>
          <Link to="/">Dashboard</Link>
          <Link to="/planner">Today</Link>
          <Link to="/learn">Learn</Link>
        </nav>
      </header>

      {(message || error) && (
        <div className={error ? "settingsNotice settingsError" : "settingsNotice"}>
          {error || message}
        </div>
      )}

      <div className="settingsGrid">
        <section className="settingsCard">
          <p className="eyebrow">Profile</p>
          <h1>Your account</h1>
          <p className="muted">{user?.email}</p>
          <form className="settingsForm" onSubmit={saveProfile}>
            <label>
              Display name
              <input
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                maxLength={120}
                placeholder="Your name"
              />
            </label>
            <button type="submit">Save profile</button>
          </form>
        </section>

        <section className="settingsCard">
          <p className="eyebrow">Preparation target</p>
          <h2>Daily plan</h2>
          <form className="settingsForm" onSubmit={saveStudyPlan}>
            <label>
              CGL exam date
              <input
                type="date"
                value={examDate}
                onChange={(event) => setExamDate(event.target.value)}
                required
              />
            </label>
            <label>
              Daily study minutes
              <input
                type="number"
                min={45}
                max={720}
                step={15}
                value={dailyMinutes}
                onChange={(event) => setDailyMinutes(Number(event.target.value))}
                required
              />
            </label>
            <button type="submit">Update plan</button>
          </form>
        </section>

        <section className="settingsCard">
          <p className="eyebrow">Security</p>
          <h2>Change password</h2>
          <form className="settingsForm" onSubmit={savePassword}>
            <label>
              Current password
              <input
                type="password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                autoComplete="current-password"
                required
              />
            </label>
            <label>
              New password
              <input
                type="password"
                minLength={8}
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                autoComplete="new-password"
                required
              />
            </label>
            <label>
              Confirm new password
              <input
                type="password"
                minLength={8}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                autoComplete="new-password"
                required
              />
            </label>
            <button type="submit">Change password</button>
          </form>
        </section>

        <section className="settingsCard">
          <p className="eyebrow">Data & session</p>
          <h2>Controls</h2>
          <p className="muted">Keep a portable JSON backup of your attempts, mastery and revision data.</p>
          <div className="settingsActions">
            <button className="secondary" onClick={() => void saveBackup()}>Export backup</button>
            <button className="danger" onClick={logout}>Log out</button>
          </div>
        </section>
      </div>
    </main>
  );
}
