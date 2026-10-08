import { FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { login, register } from "../api";
import { setToken } from "../auth";
import {
  consumeAuthReturnPath,
  resetSessionExpiryState,
  safeInternalPath,
} from "../session";

// Account creation is opt-in: the backend disables public registration in production.
// An unset Vite env var must never display an unusable Register form.
const registrationEnabled = import.meta.env.VITE_REGISTRATION_ENABLED === "true";

export default function AuthPage() {
  const [params] = useSearchParams();
  const expired = params.get("expired") === "1";
  const requestedReturn = safeInternalPath(params.get("next"));
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = mode === "login"
        ? await login(email, password)
        : await register(email, password, displayName || undefined);
      setToken(response.access_token);
      resetSessionExpiryState();
      const returnTo = consumeAuthReturnPath(requestedReturn);
      navigate(returnTo, {replace: true});
    } catch (cause) {
      const networkFailure = cause instanceof TypeError;
      setError(networkFailure
        ? "Cannot reach the study server right now. Check your connection and retry."
        : mode === "login"
          ? "Login failed. Check your email and password."
          : "Registration failed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="authShell">
      <section className="authCard">
        <Link className="backLink" to={requestedReturn ?? "/"}>← Back</Link>
        <p className="eyebrow">Private study account</p>
        <h1>{mode === "login" ? "Welcome back" : "Create your account"}</h1>
        <p className="muted">Your attempts, mastery and revision history stay tied to this account.</p>

        {expired && (
          <div className="sessionExpiredNotice" role="status">
            <strong>Your study session expired.</strong>
            <span>Sign in again and we’ll return you to the same screen. Saved progress stays intact.</span>
          </div>
        )}

        <form onSubmit={submit} className="formStack">
          {mode === "register" && (
            <label>
              Name
              <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
            </label>
          )}
          <label>
            Email
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label>
            Password
            <input
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              minLength={8}
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error && <p className="errorText">{error}</p>}
          <button disabled={busy}>
            {busy ? "Signing in…" : mode === "login" ? "Login" : "Register"}
          </button>
        </form>

        {(registrationEnabled || mode === "register") && (
          <button
            className="textButton"
            onClick={() => {
              setError("");
              setMode(mode === "login" ? "register" : "login");
            }}
          >
            {mode === "login" ? "Need an account? Register" : "Already registered? Login"}
          </button>
        )}
      </section>
    </main>
  );
}
