import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { login, register } from "../api";
import { setToken } from "../auth";

export default function AuthPage() {
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
      navigate("/");
    } catch {
      setError(mode === "login" ? "Login failed." : "Registration failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="authShell">
      <section className="authCard">
        <Link className="backLink" to="/">← Back</Link>
        <p className="eyebrow">Private study account</p>
        <h1>{mode === "login" ? "Welcome back" : "Create your account"}</h1>
        <p className="muted">Your attempts, mastery and revision history stay tied to this account.</p>

        <form onSubmit={submit} className="formStack">
          {mode === "register" && (
            <label>
              Name
              <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
            </label>
          )}
          <label>
            Email
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>
            Password
            <input type="password" minLength={8} required value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          {error && <p className="errorText">{error}</p>}
          <button disabled={busy}>{busy ? "Please wait..." : mode === "login" ? "Login" : "Register"}</button>
        </form>

        <button
          className="textButton"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "Need an account? Register" : "Already registered? Login"}
        </button>
      </section>
    </main>
  );
}
