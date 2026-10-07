import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import GlobalNav from "./components/GlobalNav";
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
      <GlobalNav />
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/login" element={<AuthPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/learn" element={<LearnPage />} />
        <Route path="/learn/topic/:topicId" element={<LessonPage />} />
        <Route path="/practice" element={<PracticePage />} />
        <Route path="/planner" element={<PlannerPage />} />
        <Route path="/mocks" element={<MockPage />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="/revision" element={<RevisionPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
