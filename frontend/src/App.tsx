import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import AuthPage from "./pages/AuthPage";
import DashboardPage from "./pages/DashboardPage";
import LearnPage from "./pages/LearnPage";
import LessonPage from "./pages/LessonPage";
import MockPage from "./pages/MockPage";
import PracticePage from "./pages/PracticePage";
import ReviewPage from "./pages/ReviewPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/login" element={<AuthPage />} />
        <Route path="/learn" element={<LearnPage />} />
        <Route path="/learn/topic/:topicId" element={<LessonPage />} />
        <Route path="/practice" element={<PracticePage />} />
        <Route path="/mocks" element={<MockPage />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
