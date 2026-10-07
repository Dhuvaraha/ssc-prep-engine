import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import AppErrorBoundary from "./components/AppErrorBoundary";
import GlobalNav from "./components/GlobalNav";
import OfflineBanner from "./components/OfflineBanner";
import RequireAuth from "./components/RequireAuth";
import SessionExpiryGuard from "./components/SessionExpiryGuard";
import AnalyticsPage from "./pages/AnalyticsPage";
import AuthPage from "./pages/AuthPage";
import DashboardPage from "./pages/DashboardPage";
import LearnPage from "./pages/LearnPage";
import LessonPage from "./pages/LessonPage";
import MockPage from "./pages/MockPage";
import PracticePage from "./pages/PracticePage";
import PlannerPage from "./pages/PlannerPage";
import ReviewPage from "./pages/ReviewPage";
import RevisionPage from "./pages/RevisionPage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <BrowserRouter>
      <SessionExpiryGuard />
      <GlobalNav />
      <OfflineBanner />
      <AppErrorBoundary>
        <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/login" element={<AuthPage />} />
        <Route path="/analytics" element={<RequireAuth><AnalyticsPage /></RequireAuth>} />
        <Route path="/learn" element={<LearnPage />} />
        <Route path="/learn/topic/:topicId" element={<LessonPage />} />
        <Route path="/practice" element={<RequireAuth><PracticePage /></RequireAuth>} />
        <Route path="/planner" element={<RequireAuth><PlannerPage /></RequireAuth>} />
        <Route path="/mocks" element={<RequireAuth><MockPage /></RequireAuth>} />
        <Route path="/review" element={<RequireAuth><ReviewPage /></RequireAuth>} />
        <Route path="/revision" element={<RequireAuth><RevisionPage /></RequireAuth>} />
        <Route path="/settings" element={<RequireAuth><SettingsPage /></RequireAuth>} />
        <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppErrorBoundary>
    </BrowserRouter>
  );
}
