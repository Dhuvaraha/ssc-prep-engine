import { Link, useLocation } from "react-router-dom";
import { getToken } from "../auth";

const links = [
  ["/planner", "Today"],
  ["/learn", "Learn"],
  ["/practice?mode=mixed&limit=10", "Practice"],
  ["/revision", "Revision"],
  ["/mocks", "Mocks"],
  ["/analytics", "Analytics"],
];

export default function GlobalNav() {
  const location = useLocation();
  if (location.pathname === "/login" || location.pathname === "/mocks") return null;

  return (
    <div className="globalNavWrap">
      <nav className="globalNav" aria-label="Primary">
        <Link className="globalBrand" to="/">SSC Prep Engine</Link>
        <div className="globalNavLinks">
          {links.map(([to, label]) => (
            <Link
              key={to}
              className={location.pathname === to.split("?")[0] ? "globalNavActive" : ""}
              to={to}
            >
              {label}
            </Link>
          ))}
        </div>
        <Link className="globalAccount" to={getToken() ? "/settings" : "/login"}>
          {getToken() ? "Profile" : "Login"}
        </Link>
      </nav>
    </div>
  );
}
