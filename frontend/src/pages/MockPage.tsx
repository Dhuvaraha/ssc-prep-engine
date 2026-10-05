import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  MockQuestion,
  MockSubmitResult,
  saveMockResponse,
  startMock,
  submitMock,
} from "../api";
import { getToken } from "../auth";
import SecureImage from "../components/SecureImage";

type LocalAnswer = {
  selected_option: number | null;
  marked_for_review: boolean;
  time_seconds: number;
};

const sectionLabels: Record<string, string> = {
  reasoning: "Reasoning",
  "general-awareness": "General Awareness",
  quant: "Quantitative Aptitude",
  english: "English",
};

export default function MockPage() {
  const [mode, setMode] = useState<"mini" | "full" | "sectional">("mini");
  const [subject, setSubject] = useState("reasoning");
  const [attemptId, setAttemptId] = useState<number | null>(null);
  const [questions, setQuestions] = useState<MockQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<number, LocalAnswer>>({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [running, setRunning] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<MockSubmitResult | null>(null);
  const questionOpenedAt = useRef(Date.now());
  const navigate = useNavigate();

  useEffect(() => {
    if (!getToken()) navigate("/login");
  }, [navigate]);

  useEffect(() => {
    if (!running || secondsLeft <= 0) return;
    const timer = window.setInterval(() => {
      setSecondsLeft((value) => Math.max(0, value - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [running, secondsLeft]);

  useEffect(() => {
    if (running && secondsLeft === 0 && attemptId && questions.length) {
      void finishMock();
    }
  }, [secondsLeft, running, attemptId, questions.length]);

  const current = questions[currentIndex] ?? null;
  const currentAnswer = current ? answers[current.question.id] : undefined;

  const sections = useMemo(
    () => Array.from(new Set(questions.map((item) => item.section_slug))),
    [questions],
  );

  async function begin() {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const data = await startMock(mode, mode === "sectional" ? subject : undefined);
      setAttemptId(data.attempt_id);
      setQuestions(data.questions);
      setAnswers({});
      setCurrentIndex(0);
      setSecondsLeft(data.duration_minutes * 60);
      setRunning(true);
      questionOpenedAt.current = Date.now();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start mock.");
    } finally {
      setBusy(false);
    }
  }

  function elapsedForCurrent(): number {
    return Math.max(0, (Date.now() - questionOpenedAt.current) / 1000);
  }

  function updateLocal(partial: Partial<LocalAnswer>) {
    if (!current) return;
    const previous = answers[current.question.id] ?? {
      selected_option: null,
      marked_for_review: false,
      time_seconds: 0,
    };
    setAnswers((state) => ({
      ...state,
      [current.question.id]: {...previous, ...partial},
    }));
  }

  async function persistCurrent(extraTime = true) {
    if (!attemptId || !current) return;
    const previous = answers[current.question.id] ?? {
      selected_option: null,
      marked_for_review: false,
      time_seconds: 0,
    };
    const next = {
      ...previous,
      time_seconds: previous.time_seconds + (extraTime ? elapsedForCurrent() : 0),
    };
    setAnswers((state) => ({...state, [current.question.id]: next}));
    await saveMockResponse(attemptId, {
      question_id: current.question.id,
      selected_option: next.selected_option,
      marked_for_review: next.marked_for_review,
      time_seconds: next.time_seconds,
    });
    questionOpenedAt.current = Date.now();
  }

  async function goTo(index: number) {
    if (index === currentIndex) return;
    try {
      await persistCurrent();
    } catch {
      setError("Answer save failed. Try again.");
      return;
    }
    setCurrentIndex(index);
    questionOpenedAt.current = Date.now();
  }

  async function saveAndNext() {
    try {
      await persistCurrent();
      if (currentIndex < questions.length - 1) {
        setCurrentIndex((value) => value + 1);
        questionOpenedAt.current = Date.now();
      }
    } catch {
      setError("Answer save failed. Try again.");
    }
  }

  async function finishMock() {
    if (!attemptId || busy) return;
    setBusy(true);
    setError("");
    try {
      if (current) await persistCurrent();
      const data = await submitMock(attemptId);
      setResult(data);
      setRunning(false);
    } catch {
      setError("Could not submit mock.");
    } finally {
      setBusy(false);
    }
  }

  function jumpToSection(slug: string) {
    const index = questions.findIndex((item) => item.section_slug === slug);
    if (index >= 0) void goTo(index);
  }

  function formatTime(total: number) {
    const minutes = Math.floor(total / 60).toString().padStart(2, "0");
    const seconds = Math.floor(total % 60).toString().padStart(2, "0");
    return minutes + ":" + seconds;
  }

  if (result) {
    const accuracy = result.correct + result.incorrect
      ? Math.round((result.correct / (result.correct + result.incorrect)) * 100)
      : 0;
    return (
      <main className="mockShell">
        <section className="mockResult">
          <p className="eyebrow">Mock submitted</p>
          <h1>{result.score} marks</h1>
          <div className="mockResultGrid">
            <article><span>Correct</span><strong>{result.correct}</strong></article>
            <article><span>Incorrect</span><strong>{result.incorrect}</strong></article>
            <article><span>Unattempted</span><strong>{result.unattempted}</strong></article>
            <article><span>Accuracy</span><strong>{accuracy}%</strong></article>
          </div>
          <div className="mockResultActions">
            <button onClick={() => { setResult(null); setAttemptId(null); setQuestions([]); }}>Take another test</button>
            <Link to="/">Back to dashboard</Link>
          </div>
        </section>
      </main>
    );
  }

  if (!running || !current) {
    return (
      <main className="mockShell">
        <header className="mockLandingHeader">
          <div>
            <p className="brand">SSC Mock Lab</p>
            <p className="muted">Exam-style practice with timing, review flags and negative marking.</p>
          </div>
          <Link to="/">Dashboard</Link>
        </header>

        <section className="mockSetup">
          <p className="eyebrow">Choose test mode</p>
          <h1>Start an exam session.</h1>
          <div className="mockModeGrid">
            <button className={mode === "mini" ? "mockModeCard activeMockMode" : "mockModeCard"} onClick={() => setMode("mini")}>
              <strong>Mini mock</strong>
              <span>4 questions • 4 minutes • one from each section</span>
            </button>
            <button className={mode === "sectional" ? "mockModeCard activeMockMode" : "mockModeCard"} onClick={() => setMode("sectional")}>
              <strong>Sectional</strong>
              <span>25 questions • 15 minutes • one subject</span>
            </button>
            <button className={mode === "full" ? "mockModeCard activeMockMode" : "mockModeCard"} onClick={() => setMode("full")}>
              <strong>Full CGL Tier I</strong>
              <span>100 questions • 60 minutes • +2 / -0.5</span>
            </button>
          </div>

          {mode === "sectional" && (
            <label className="mockSubjectPicker">
              Subject
              <select value={subject} onChange={(e) => setSubject(e.target.value)}>
                <option value="reasoning">Reasoning</option>
                <option value="general-awareness">General Awareness</option>
                <option value="quant">Quantitative Aptitude</option>
                <option value="english">English</option>
              </select>
            </label>
          )}

          {error && <p className="errorText">{error}</p>}
          <button className="mockStartButton" onClick={begin} disabled={busy}>
            {busy ? "Preparing..." : "Start test"}
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="examShell">
      <header className="examHeader">
        <div>
          <strong>SSC CGL Tier I</strong>
          <span>{mode === "full" ? "Full mock" : mode === "sectional" ? "Sectional test" : "Mini mock"}</span>
        </div>
        <div className={secondsLeft <= 60 ? "examTimer examTimerUrgent" : "examTimer"}>
          {formatTime(secondsLeft)}
        </div>
        <button className="finishButton" onClick={finishMock} disabled={busy}>Submit test</button>
      </header>

      <div className="examSectionTabs">
        {sections.map((slug) => (
          <button
            key={slug}
            className={current.section_slug === slug ? "activeSectionTab" : ""}
            onClick={() => jumpToSection(slug)}
          >
            {sectionLabels[slug] ?? slug}
          </button>
        ))}
      </div>

      <section className="examLayout">
        <article className="examQuestionCard">
          <div className="examQuestionMeta">
            <span>Question {currentIndex + 1} of {questions.length}</span>
            <span>{sectionLabels[current.section_slug] ?? current.section_slug}</span>
          </div>
          <h1>{current.question.question_text}</h1>
          {current.question.question_image_url && (
            <SecureImage className="practiceQuestionImage" src={current.question.question_image_url} alt="Question visual" />
          )}

          <div className="practiceOptions">
            {current.question.options.map((option) => (
              <button
                key={option.position}
                className={currentAnswer?.selected_option === option.position ? "practiceOption practiceSelected" : "practiceOption"}
                onClick={() => updateLocal({selected_option: option.position})}
              >
                <strong>{String.fromCharCode(64 + option.position)}</strong>
                <span>{option.text ?? "Image option"}</span>
                {option.image_url && <SecureImage src={option.image_url} alt={"Option " + option.position} />}
              </button>
            ))}
          </div>

          <div className="examQuestionActions">
            <button className="secondary" onClick={() => updateLocal({selected_option: null})}>Clear response</button>
            <button
              className={currentAnswer?.marked_for_review ? "reviewToggle activeReviewToggle" : "reviewToggle"}
              onClick={() => updateLocal({marked_for_review: !currentAnswer?.marked_for_review})}
            >
              {currentAnswer?.marked_for_review ? "Marked for review" : "Mark for review"}
            </button>
            <button onClick={saveAndNext}>{currentIndex === questions.length - 1 ? "Save response" : "Save & Next"}</button>
          </div>
          {error && <p className="errorText">{error}</p>}
        </article>

        <aside className="examPalette">
          <div className="paletteLegend">
            <span><i className="legendDot answeredDot" /> Answered</span>
            <span><i className="legendDot reviewDot" /> Review</span>
            <span><i className="legendDot currentDot" /> Current</span>
          </div>
          <div className="questionPaletteGrid">
            {questions.map((item, index) => {
              const answer = answers[item.question.id];
              const classNames = [
                "paletteNumber",
                index === currentIndex ? "paletteCurrent" : "",
                answer?.selected_option ? "paletteAnswered" : "",
                answer?.marked_for_review ? "paletteReview" : "",
              ].filter(Boolean).join(" ");
              return (
                <button className={classNames} key={item.question.id} onClick={() => void goTo(index)}>
                  {index + 1}
                </button>
              );
            })}
          </div>
          <div className="paletteSummary">
            <span>Answered <strong>{Object.values(answers).filter((item) => item.selected_option).length}</strong></span>
            <span>Review <strong>{Object.values(answers).filter((item) => item.marked_for_review).length}</strong></span>
            <span>Remaining <strong>{questions.length - Object.values(answers).filter((item) => item.selected_option).length}</strong></span>
          </div>
        </aside>
      </section>
    </main>
  );
}
