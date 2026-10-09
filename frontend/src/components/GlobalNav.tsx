import { useEffect, useState } from "react";
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

const mobileLinks = links.slice(0, 4);

const titles: Array<[RegExp, string, string]> = [
  [/^\/$/, "Dashboard", "Preparation overview"],
  [/^\/exams$/, "Examinations", "Your current course and upcoming SSC stages"],
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
  const [moreOpen, setMoreOpen] = useState(false);
  const moreActive = !mobileLinks.some(([to]) => location.pathname === to.split("?")[0]);

  useEffect(() => {
    setMoreOpen(false);
  }, [location.pathname, location.search]);

  useEffect(() => {
    if (!moreOpen) return;
    function onEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setMoreOpen(false);
    }
    window.addEventListener("keydown", onEscape);
    return () => window.removeEventListener("keydown", onEscape);
  }, [moreOpen]);

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
        <Link
          className={location.pathname === "/exams" ? "examSwitcherLink examSwitcherActive" : "examSwitcherLink"}
          to="/exams"
          aria-label="View exams and preparation stages"
        >
          <span>SSC CGL · Tier I</span>
          <span aria-hidden="true">Change ↗</span>
        </Link>

        <nav className="sidebarLinks">
          {links.map(([to, label, icon]) => {
            const path = to.split("?")[0];
            const active = location.pathname === path || (path !== "/" && location.pathname.startsWith(path));
            return (
              <Link
                className={active ? "sidebarLink sidebarLinkActive" : "sidebarLink"}
                aria-current={active ? "page" : undefined}
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
          <Link to="/exams">{location.pathname === "/exams" ? "All exams" : "SSC CGL · Tier I"}</Link>
          <span>/</span>
          <b>{title}</b>
        </div>
        <Link className="contextExamSwitcher" to={location.pathname === "/exams" ? "/" : "/exams"} aria-label={location.pathname === "/exams" ? "Return to current exam" : "Choose examination"}>
          {location.pathname === "/exams" ? "Current course ↗" : "Exams ↗"}
        </Link>
      </header>

      <nav className="mobileBottomNav" aria-label="Mobile navigation">
        {mobileLinks.map(([to, label, icon]) => {
          const path = to.split("?")[0];
          const active = location.pathname === path || location.pathname.startsWith(path + "/");
          return (
            <Link
              className={active ? "mobileNavActive" : ""}
              key={to}
              to={to}
              aria-current={active ? "page" : undefined}
              onTouchStart={() => prefetchStudyPage(path)}
              onFocus={() => prefetchStudyPage(path)}
            >
              <i aria-hidden="true">{icon}</i><span>{label}</span>
            </Link>
          );
        })}
        <button
          type="button"
          className={moreActive || moreOpen ? "mobileNavActive" : ""}
          aria-label="More navigation"
          aria-expanded={moreOpen}
          aria-controls="mobile-more-menu"
          onClick={() => setMoreOpen((open) => !open)}
        >
          <i aria-hidden="true">···</i><span>More</span>
        </button>
      </nav>
      <nav
        id="mobile-more-menu"
        className="mobileMoreMenu"
        aria-label="Additional navigation"
        hidden={!moreOpen}
      >
        <Link to="/">Dashboard</Link>
        <Link to="/revision" aria-current={location.pathname === "/revision" ? "page" : undefined}>Revision</Link>
        <Link to="/analytics" aria-current={location.pathname === "/analytics" ? "page" : undefined}>Analytics</Link>
        <Link to="/exams" aria-current={location.pathname === "/exams" ? "page" : undefined}>Choose exam</Link>
        <Link to={authenticated ? "/settings" : "/login"}>{authenticated ? "Profile & settings" : "Sign in"}</Link>
      </nav>
    </>
  );
}
