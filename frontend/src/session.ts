export const SESSION_EXPIRED_EVENT = "ssc-session-expired";

const RETURN_PATH_KEY = "ssc_auth_return_path";
let expiryRedirectPending = false;

export function safeInternalPath(value: string | null | undefined): string | null {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return null;
  if (value.startsWith("/login")) return null;
  return value;
}

export function rememberAuthReturnPath(value: string): string {
  const safe = safeInternalPath(value) ?? "/";
  try {
    sessionStorage.setItem(RETURN_PATH_KEY, safe);
  } catch {
    // Private browsing/storage restrictions must not block session recovery.
  }
  return safe;
}

export function consumeAuthReturnPath(preferred?: string | null): string {
  let stored: string | null = null;
  try {
    stored = sessionStorage.getItem(RETURN_PATH_KEY);
    sessionStorage.removeItem(RETURN_PATH_KEY);
  } catch {
    stored = null;
  }
  return safeInternalPath(preferred) ?? safeInternalPath(stored) ?? "/";
}

export function beginSessionExpiry(returnPath: string): boolean {
  if (expiryRedirectPending) return false;
  expiryRedirectPending = true;
  rememberAuthReturnPath(returnPath);
  return true;
}

export function resetSessionExpiryState(): void {
  expiryRedirectPending = false;
}
