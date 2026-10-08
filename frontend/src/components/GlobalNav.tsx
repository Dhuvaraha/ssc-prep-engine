import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";

import { fetchContentTree, prefetchStudyPage } from "../api";
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
  const hidden = location.pathname === "/login" || location.pathname === "/mocks";
  const authenticated = Boolean(getToken());

  useEffect(() => {
    document.body.classList.toggle("hasAppSidebar", !hidden);
    return () => document.body.classList.remove("hasAppSidebar");
  }, [hidden]);

  useEffect(() => {
    if (hidden) return;
    void fetchContentTree().catch(() => undefined);
  }, [hidden]);

  if (hidden) return null;

  const context = titles.find(([pattern]) => pattern.test(location.pathname));
  const title = context?.[1] ?? "SSC Prep Engine";
  const subtitle = context?.[2] ?? "SSC CGL preparation";
  const parentPath = location.pathname.startsWith("/learn/topic/") ? "/learn" : "/";

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
                className={active ? "sidebarLink sidebarLinkActive" : "sidebarLink"}
                key={to}
                to={to}
                onPointerEnter={() => prefetchStudyPage(path)}
                onFocus={() => prefetchStudyPage(path)}
                onTouchStart={() => prefetchStudyPage(path)}
              >
                <i>{icon}</i><span>{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="sidebarAccount">
          <Link to={authenticated ? "/settings" : "/login"}>
            <span className="avatarDot">{authenticated ? "DP" : "?"}</span>
            <div>
              <strong>{authenticated ? "Profile & settings" : "Sign in"}</strong>
              <small>{authenticated ? "Exam target & voice" : "Save your progress"}</small>
            </div>
          </Link>
        </div>
      </aside>

      <header className="appContextBar">
        {location.pathname !== "/" && (
          <Link className="contextBack" to={parentPath} aria-label={parentPath === "/learn" ? "Back to lessons" : "Back to dashboard"}>←</Link>
        )}
        <div>
          <strong>{title}</strong>
          <span>{subtitle}</span>
        </div>
        <div className="contextCrumb">
          <Link to="/">SSC CGL</Link>
          <span>/</span>
          <b>{title}</b>
        </div>
      </header>

      <nav className="mobileBottomNav" aria-label="Mobile navigation">
        {links.map(([to, label, icon]) => {
          const path = to.split("?")[0];
          const active = location.pathname === path || (path !== "/" && location.pathname.startsWith(path));
          return (
            <Link
              className={active ? "mobileNavActive" : ""}
              key={to}
              to={to}
              onTouchStart={() => prefetchStudyPage(path)}
              onFocus={() => prefetchStudyPage(path)}
            >
              <i>{icon}</i><span>{label}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
