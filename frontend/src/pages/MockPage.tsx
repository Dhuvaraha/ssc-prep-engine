import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import {
  ActiveMock,
  MockQuestion,
  MockReview,
  MockSubmitResult,
  abandonMock,
  fetchActiveMock,
  fetchMockAttempt,
  fetchMockReview,
  fetchMockState,
  fetchTopicPackage,
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
  const [params] = useSearchParams();
  const topicIdParam = Number(params.get("topic_id") ?? "0");
  const topicId = Number.isFinite(topicIdParam) && topicIdParam > 0 ? topicIdParam : undefined;
  const [mode, setMode] = useState<"mini" | "full" | "sectional" | "topic">(topicId ? "topic" : "mini");
  const [topicName, setTopicName] = useState("");
  const [subject, setSubject] = useState("reasoning");
  const [attemptId, setAttemptId] = useState<number | null>(null);
  const [resumeInfo, setResumeInfo] = useState<ActiveMock | null>(null);
  const [questions, setQuestions] = useState<MockQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<number, LocalAnswer>>({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [running, setRunning] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<MockSubmitResult | null>(null);
  const [review, setReview] = useState<MockReview | null>(null);
  const questionOpenedAt = useRef(Date.now());
  const navigate = useNavigate();

  useEffect(() => {
    if (topicId) {
      setMode("topic");
      fetchTopicPackage(topicId).then((pkg) => setTopicName(pkg.topic.name)).catch(() => setTopicName("Topic test"));
    }
  }, [topicId]);

  useEffect(() => {
    if (!getToken()) {
      navigate("/login");
      return;
    }
    fetchActiveMock()
      .then((data) => setResumeInfo(data.attempt_id ? data : null))
      .catch(() => undefined);
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
      void finishMock(true);
    }
  }, [secondsLeft, running, attemptId, questions.length]);

  const current = questions[currentIndex] ?? null;
  const currentAnswer = current ? answers[current.question.id] : undefined;

  const sections = useMemo(
    () => Array.from(new Set(questions.map((item) => item.section_slug))),
    [questions],
  );

  async function begin() {
    if (resumeInfo?.attempt_id) {
      setError("Resume or discard the in-progress mock before starting another test.");
      return;
    }
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const data = await startMock(
        mode,
        mode === "sectional" ? subject : undefined,
        mode === "topic" ? topicId : undefined,
      );
      setAttemptId(data.attempt_id);
      setQuestions(data.questions);
      setAnswers({});
      setCurrentIndex(0);
      setSecondsLeft(data.duration_minutes * 60);
      setRunning(true);
      setResumeInfo(null);
      questionOpenedAt.current = Date.now();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start mock.");
    } finally {
      setBusy(false);
    }
  }

  async function resumeMock() {
    if (!resumeInfo?.attempt_id) return;
    setBusy(true);
    setError("");
    try {
      const [attempt, state] = await Promise.all([
        fetchMockAttempt(resumeInfo.attempt_id),
        fetchMockState(resumeInfo.attempt_id),
      ]);
      const restored: Record<number, LocalAnswer> = {};
      state.responses.forEach((item) => {
        restored[item.question_id] = {
          selected_option: item.selected_option,
          marked_for_review: item.marked_for_review,
          time_seconds: item.time_seconds,
        };
      });
      setAttemptId(attempt.attempt_id);
      setQuestions(attempt.questions);
      setAnswers(restored);
      setMode(attempt.mode as "mini" | "full" | "sectional" | "topic");
      if (resumeInfo.subject_slug) setSubject(resumeInfo.subject_slug);
      setCurrentIndex(0);
      setSecondsLeft(state.seconds_left);
      setRunning(true);
      questionOpenedAt.current = Date.now();
    } catch {
      setError("Could not resume the saved mock.");
    } finally {
      setBusy(false);
    }
  }

  async function discardActive() {
    if (!resumeInfo?.attempt_id) return;
    if (!window.confirm("Discard this in-progress mock? Saved answers in this attempt will be abandoned.")) return;
    setBusy(true);
    try {
      await abandonMock(resumeInfo.attempt_id);
      setResumeInfo(null);
      setError("");
    } catch {
      setError("Could not discard the in-progress mock.");
    } finally {
      setBusy(false);
    }
  }

  function elapsedForCurrent(): number {
    return Math.max(0, (Date.now() - questionOpenedAt.current) / 1000);
  }

  function localForCurrent(): LocalAnswer {
    if (!current) return {selected_option: null, marked_for_review: false, time_seconds: 0};
    return answers[current.question.id] ?? {
      selected_option: null,
      marked_for_review: false,
      time_seconds: 0,
    };
  }

  async function persistPatch(partial: Partial<LocalAnswer> = {}, extraTime = true) {
    if (!attemptId || !current) return;
    const previous = localForCurrent();
    const next = {
      ...previous,
      ...partial,
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
      await persistPatch();
    } catch {
      setError("Answer autosave failed. Try again.");
      return;
    }
    setCurrentIndex(index);
    questionOpenedAt.current = Date.now();
  }

  async function chooseOption(position: number | null) {
    try {
      await persistPatch({selected_option: position});
    } catch {
      setError("Answer autosave failed. Try again.");
    }
  }

  async function toggleReview() {
    try {
      await persistPatch({marked_for_review: !currentAnswer?.marked_for_review});
    } catch {
      setError("Review flag could not be saved.");
    }
  }

  async function saveAndNext() {
    try {
      await persistPatch();
      if (currentIndex < questions.length - 1) {
        setCurrentIndex((value) => value + 1);
        questionOpenedAt.current = Date.now();
      }
    } catch {
      setError("Answer save failed. Try again.");
    }
  }

  async function finishMock(force = false) {
    if (!attemptId || busy) return;
    if (!force && !window.confirm("Submit this test now? You cannot change answers after submission.")) return;
    setBusy(true);
    setError("");
    try {
      if (current) await persistPatch();
      const data = await submitMock(attemptId);
      setResult(data);
      setReview(await fetchMockReview(attemptId).catch(() => null));
      setRunning(false);
      setResumeInfo(null);
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
    const attemptRate = result.total_questions
      ? Math.round(((result.correct + result.incorrect) / result.total_questions) * 100)
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
            <article><span>Attempt rate</span><strong>{attemptRate}%</strong></article>
            {review && <article><span>Easy marks missed</span><strong>{review.easy_missed}</strong></article>}
            {review && <article><span>Slow questions</span><strong>{review.slow_questions}</strong></article>}
          </div>
          <p className="muted">Scoring uses the configured SSC CGL marking scheme, including negative marks.</p>

          {review && (
            <>
              <section className="mockSectionBreakdown">
                <p className="eyebrow">Section breakdown</p>
                <div>
                  {Object.entries(review.sections).map(([slug, stats]) => (
                    <article key={slug}>
                      <strong>{sectionLabels[slug] ?? slug}</strong>
                      <span>{stats.correct} correct • {stats.incorrect} wrong • {stats.unattempted} skipped</span>
                      <small>{Math.round(stats.time_seconds / 60)} min spent</small>
                    </article>
                  ))}
                </div>
              </section>

              <section className="mockQuestionReview">
                <p className="eyebrow">Question review</p>
                <h2>See exactly where marks leaked.</h2>
                {review.questions.map((item) => (
                  <details className={item.correct ? "mockReviewItem reviewCorrect" : "mockReviewItem reviewWrong"} key={item.question_id}>
                    <summary>
                      <span>Q{item.position}</span>
                      <strong>{item.correct ? "Correct" : item.selected_option ? "Wrong" : "Skipped"}</strong>
                      <small>{Math.round(item.time_seconds)}s{item.expected_time_seconds ? " / " + item.expected_time_seconds + "s target" : ""}</small>
                    </summary>
                    <div>
                      <p>{item.question_text}</p>
                      <p><strong>Your answer:</strong> {item.selected_option ? String.fromCharCode(64 + item.selected_option) : "Not answered"} • <strong>Correct:</strong> {String.fromCharCode(64 + item.correct_option)}</p>
                      {item.pattern_type && <p><strong>Pattern:</strong> {item.pattern_type.replaceAll("-", " ")}</p>}
                      {item.explanation && <p>{item.explanation}</p>}
                      {item.fast_method && <p><strong>Fast method:</strong> {item.fast_method}</p>}
                    </div>
                  </details>
                ))}
              </section>
            </>
          )}
          <div className="mockResultActions">
            <button onClick={() => {
              setResult(null);
              setAttemptId(null);
              setQuestions([]);
              setAnswers({});
              setReview(null);
            }}>Take another test</button>
            <Link to="/analytics">Analyse performance</Link>
            <Link to="/revision">Revision queue</Link>
            <Link to="/">Dashboard</Link>
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
            <p className="muted">Exam-style practice with autosave, review flags, resume and negative marking.</p>
          </div>
          <Link to="/">Dashboard</Link>
        </header>

        {resumeInfo?.attempt_id && (
          <section className="resumeMockCard">
            <div>
              <p className="eyebrow">In-progress test found</p>
              <h2>Resume where you stopped.</h2>
              <p>{resumeInfo.mode} test • {formatTime(resumeInfo.seconds_left ?? 0)} remaining</p>
            </div>
            <div>
              <button onClick={() => void resumeMock()} disabled={busy}>Resume test</button>
              <button className="secondary" onClick={() => void discardActive()} disabled={busy}>Discard</button>
            </div>
          </section>
        )}

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
            {topicId && (
              <button className={mode === "topic" ? "mockModeCard activeMockMode" : "mockModeCard"} onClick={() => setMode("topic")}>
                <strong>{topicName || "Topic test"}</strong>
                <span>Up to 20 questions • 20 minutes • focused test</span>
              </button>
            )}
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
          <button className="mockStartButton" onClick={() => void begin()} disabled={busy || Boolean(resumeInfo?.attempt_id)}>
            {busy ? "Preparing..." : resumeInfo?.attempt_id ? "Resume or discard current test first" : "Start test"}
          </button>
        </section>
      </main>
    );
  }

  const answeredCount = Object.values(answers).filter((item) => item.selected_option !== null).length;
  const reviewCount = Object.values(answers).filter((item) => item.marked_for_review).length;

  return (
    <main className="examShell">
      <header className="examHeader">
        <div>
          <strong>SSC CGL Tier I</strong>
          <span>{mode === "full" ? "Full mock" : mode === "sectional" ? "Sectional test" : mode === "topic" ? "Topic test" : "Mini mock"} • autosaved</span>
        </div>
        <div className={secondsLeft <= 60 ? "examTimer examTimerUrgent" : "examTimer"}>
          {formatTime(secondsLeft)}
        </div>
        <button className="finishButton" onClick={() => void finishMock(false)} disabled={busy}>Submit test</button>
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
                onClick={() => void chooseOption(option.position)}
              >
                <strong>{String.fromCharCode(64 + option.position)}</strong>
                <span>{option.text ?? "Image option"}</span>
                {option.image_url && <SecureImage src={option.image_url} alt={"Option " + option.position} />}
              </button>
            ))}
          </div>

          <div className="examQuestionActions">
            <button className="secondary" onClick={() => void chooseOption(null)}>Clear response</button>
            <button
              className={currentAnswer?.marked_for_review ? "reviewToggle activeReviewToggle" : "reviewToggle"}
              onClick={() => void toggleReview()}
            >
              {currentAnswer?.marked_for_review ? "Marked for review" : "Mark for review"}
            </button>
            <button onClick={() => void saveAndNext()}>{currentIndex === questions.length - 1 ? "Save response" : "Save & Next"}</button>
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
                answer?.selected_option !== null && answer?.selected_option !== undefined ? "paletteAnswered" : "",
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
            <span>Answered <strong>{answeredCount}</strong></span>
            <span>Review <strong>{reviewCount}</strong></span>
            <span>Remaining <strong>{questions.length - answeredCount}</strong></span>
          </div>
        </aside>
      </section>
    </main>
  );
}
