import { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { getToken } from "../auth";
import { safeInternalPath } from "../session";

export default function RequireAuth({children}: {children: ReactNode}) {
  const location = useLocation();
  if (getToken()) return children;

  const next = safeInternalPath(
    location.pathname + location.search + location.hash,
  ) ?? "/";
  const params = new URLSearchParams({next});
  return <Navigate to={"/login?" + params.toString()} replace />;
}
