import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { fetchCurrentUser } from "../api";
import { getToken } from "../auth";

const links = [
  ["/planner", "Today", "T"],
  ["/learn", "Learn", "L"],
  ["/practice?mode=mixed&limit=10", "Practice", "P"],
  ["/mocks", "Tests", "M"],
  ["/revision", "Revision", "R"],
  ["/analytics", "Analytics", "A"],
] as const;

const titles: Array<[RegExp, string, string]> = [
  [/^\/$/, "Dashboard", "Preparation overview"],
  [/^\/planner/, "Today", "Adaptive daily study plan"],
  [/^\/learn\/topic/, "Lesson", "Learn the concept and question patterns"],
  [/^\/learn/, "Learn", "Concepts, methods and shortcuts"],
  [/^\/practice/, "Practice", "Adaptive question intelligence"],
  [/^\/revision/, "Revision", "Spaced review and bookmarks"],
  [/^\/analytics/, "Analytics", "Accuracy, speed and mastery"],
  [/^\/settings/, "Profile", "Account and preparation settings"],
  [/^\/review/, "Content review", "Private admin workflow"],
];

export default function GlobalNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const hidden = location.pathname === "/login" || location.pathname === "/mocks";
  const authenticated = Boolean(getToken());
  const [profileName, setProfileName] = useState("");

  useEffect(() => {
    document.body.classList.toggle("hasAppSidebar", !hidden);
    return () => document.body.classList.remove("hasAppSidebar");
  }, [hidden]);

  useEffect(() => {
    if (!authenticated) {
      setProfileName("");
      return;
    }
    fetchCurrentUser()
      .then((user) => setProfileName(user.display_name?.trim() || user.email.split("@")[0] || "Profile"))
      .catch(() => setProfileName("Profile"));
  }, [authenticated, location.pathname]);

  const accountLabel = profileName || (authenticated ? "Profile" : "Sign in");
  const initials = useMemo(() => {
    if (!authenticated) return "?";
    const words = accountLabel.split(/\s+/).filter(Boolean);
    return (words.length > 1 ? words[0][0] + words[1][0] : accountLabel.slice(0, 2)).toUpperCase();
  }, [accountLabel, authenticated]);

  if (hidden) return null;

  const context = titles.find(([pattern]) => pattern.test(location.pathname));
  const title = context?.[1] ?? "SSC Prep Engine";
  const subtitle = context?.[2] ?? "SSC CGL preparation";
  const lessonRoute = location.pathname.startsWith("/learn/topic/");
  const profileActive = location.pathname.startsWith("/settings");

  return (
    <>
      <aside className="appSidebar" aria-label="Primary navigation">
        <Link className="sidebarBrand" to="/">
          <span>SSC</span>
          <div>
            <strong>Prep Engine</strong>
            <small>CGL Tier I</small>
          </div>
        </Link>

        <nav className="sidebarLinks">
          {links.map(([to, label, icon]) => {
            const path = to.split("?")[0];
            const active = location.pathname === path || (path !== "/" && location.pathname.startsWith(path));
            return (
              <Link
                aria-current={active ? "page" : undefined}
                className={active ? "sidebarLink sidebarLinkActive" : "sidebarLink"}
                key={to}
                to={to}
              >
                <i>{icon}</i><span>{label}</span>
              </Link>
            );
          })}
          {authenticated && (
            <Link
              aria-current={profileActive ? "page" : undefined}
              className={profileActive ? "sidebarLink sidebarLinkActive" : "sidebarLink"}
              to="/settings"
            >
              <i>U</i><span>Profile</span>
            </Link>
          )}
        </nav>

        <div className="sidebarAccount">
          <Link to={authenticated ? "/settings" : "/login"}>
            <span className="avatarDot">{initials}</span>
            <div>
              <strong>{authenticated ? accountLabel : "Sign in"}</strong>
              <small>{authenticated ? "Account & settings" : "Save your progress"}</small>
            </div>
          </Link>
        </div>
      </aside>

      <header className="appContextBar">
        <button className="contextBack" onClick={() => navigate(-1)} aria-label="Go back">←</button>
        <div>
          <strong>{title}</strong>
          <span>{subtitle}</span>
        </div>
        <div className="contextCrumb" aria-label="Breadcrumb">
          <Link to="/">SSC CGL</Link>
          <span>/</span>
          {lessonRoute && (
            <>
              <Link to="/learn">Learn</Link>
              <span>/</span>
            </>
          )}
          <b>{title}</b>
        </div>
        <Link
          className={profileActive ? "contextProfile contextProfileActive" : "contextProfile"}
          to={authenticated ? "/settings" : "/login"}
          aria-label={authenticated ? "Open profile" : "Sign in"}
          title={authenticated ? accountLabel : "Sign in"}
        >
          <span className="avatarDot">{initials}</span>
        </Link>
      </header>

      <nav className="mobileBottomNav" aria-label="Mobile navigation">
        {links.map(([to, label, icon]) => {
          const path = to.split("?")[0];
          const active = location.pathname === path || (path !== "/" && location.pathname.startsWith(path));
          return (
            <Link
              aria-current={active ? "page" : undefined}
              className={active ? "mobileNavActive" : ""}
              key={to}
              to={to}
            >
              <i>{icon}</i><span>{label}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
