const TOKEN_KEY = "ssc_prep_token";
export const SESSION_CHANGED = "ssc-session-changed";
let generation = 0;
let suspended = false;
let expiryTimer: ReturnType<typeof setTimeout> | undefined;
export function sessionSuspended(): boolean { return suspended; }
export function sessionGeneration(): number { return generation; }
export function resetSessionView(): void {
  generation += 1;
  window.speechSynthesis?.cancel();
  window.dispatchEvent(new Event(SESSION_CHANGED));
  scheduleExpiry();
}
function scheduleExpiry(): void {
  clearTimeout(expiryTimer);
  const token = getToken();
  if (!token) return;
  try {
    const exp = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).exp;
    if (typeof exp === "number") expiryTimer = setTimeout(() => {
      if (getToken() === token) clearToken();
    }, Math.min(2147483647, Math.max(0, exp * 1000 - Date.now())));
  } catch { /* Server rejects malformed tokens; never treat claims as grants. */ }
}
window.addEventListener("storage", (event) => {
  if (event.key === TOKEN_KEY || event.key === "ssc_scope_changed" || event.key === null) resetSessionView();
});
window.addEventListener("pagehide", () => { suspended = true; resetSessionView(); });
window.addEventListener("pageshow", () => { suspended = false; resetSessionView(); });
document.addEventListener("visibilitychange", () => { suspended = document.hidden; resetSessionView(); });
scheduleExpiry();
export function broadcastScopeChange(resetCurrentView = true): void {
  localStorage.setItem("ssc_scope_changed", String(Date.now()) + Math.random());
  if (resetCurrentView) resetSessionView();
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  resetSessionView();
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  resetSessionView();
}

export function isAuthenticated(): boolean {
  return Boolean(getToken());
}
