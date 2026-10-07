import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { SESSION_EXPIRED_EVENT, safeInternalPath } from "../session";

type SessionExpiredDetail = {
  next?: string;
};

export default function SessionExpiryGuard() {
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    function handleExpired(event: Event) {
      if (location.pathname === "/login") return;
      const detail = (event as CustomEvent<SessionExpiredDetail>).detail;
      const next = safeInternalPath(detail?.next)
        ?? location.pathname + location.search + location.hash;
      const params = new URLSearchParams({expired: "1", next});
      navigate("/login?" + params.toString(), {replace: true});
    }

    window.addEventListener(SESSION_EXPIRED_EVENT, handleExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, handleExpired);
  }, [location.hash, location.pathname, location.search, navigate]);

  return null;
}
