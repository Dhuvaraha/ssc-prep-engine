import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import {
  ActiveMock,
  DiagnosticBaseline,
  MockQuestion,
  MockReview,
  MockStateResponse,
  MockSubmitResult,
  abandonMock,
  fetchDiagnosticBaseline,
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

const fullSectionOrder = ["reasoning", "general-awareness", "quant", "english"];
const fullSectionSeconds = 15 * 60;

export default function MockPage() {
  const [params] = useSearchParams();
  const topicIdParam = Number(params.get("topic_id") ?? "0");
  const topicId = Number.isFinite(topicIdParam) && topicIdParam > 0 ? topicIdParam : undefined;
  const [mode, setMode] = useState<"mini" | "full" | "sectional" | "topic" | "diagnostic">(
    topicId ? "topic" : params.get("mode") === "diagnostic" ? "diagnostic" : "mini"
  );
  const [topicName, setTopicName] = useState("");
  const [subject, setSubject] = useState("reasoning");
  const [attemptId, setAttemptId] = useState<number | null>(null);
  const [resumeInfo, setResumeInfo] = useState<ActiveMock | null>(null);
  const [checkingActive, setCheckingActive] = useState(true);
  const [questions, setQuestions] = useState<MockQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<number, LocalAnswer>>({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [activeSectionSlug, setActiveSectionSlug] = useState<string | null>(null);
  const [sectionIndex, setSectionIndex] = useState<number | null>(null);
  const [sectionSecondsLeft, setSectionSecondsLeft] = useState<number | null>(null);
  const [running, setRunning] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [result, setResult] = useState<MockSubmitResult | null>(null);
  const [review, setReview] = useState<MockReview | null>(null);
  const [diagnosticProfile, setDiagnosticProfile] = useState<DiagnosticBaseline | null>(null);
  const questionOpenedAt = useRef(Date.now());
  const boundarySyncing = useRef(false);
  const pendingAnswerSave = useRef<Promise<void> | null>(null);
  const [savingAnswer, setSavingAnswer] = useState(false);
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
    let cancelled = false;
    setCheckingActive(true);
    fetchActiveMock()
      .then((data) => { if (!cancelled) setResumeInfo(data.attempt_id ? data : null); })
      .catch(() => {
        if (!cancelled) setError("Could not check for an in-progress test. Starting again will still protect your saved attempt.");
      })
      .finally(() => { if (!cancelled) setCheckingActive(false); });
    return () => { cancelled = true; };
  }, [navigate]);

  useEffect(() => {
    if (!running || secondsLeft <= 0) return;
    const timer = window.setInterval(() => {
      setSecondsLeft((value) => Math.max(0, value - 1));
      if (mode === "full") {
        setSectionSecondsLeft((value) => value === null ? null : Math.max(0, value - 1));
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [running, secondsLeft, mode]);

  useEffect(() => {
    if (running && secondsLeft === 0 && attemptId && questions.length) {
      void finishMock(true);
    }
  }, [secondsLeft, running, attemptId, questions.length]);

  useEffect(() => {
    if (
      mode === "full"
      && running
      && attemptId
      && secondsLeft > 0
      && sectionSecondsLeft === 0
      && !boundarySyncing.current
    ) {
      void syncFullSectionBoundary();
    }
  }, [mode, running, attemptId, secondsLeft, sectionSecondsLeft]);

  useEffect(() => {
    if (!running || !attemptId) return;
    function onVisibilityChange() {
      if (document.visibilityState === "visible") {
        void syncServerTiming();
      }
    }
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => document.removeEventListener("visibilitychange", onVisibilityChange);
  }, [running, attemptId, mode, questions]);

  useEffect(() => {
    if (!running || !attemptId) return;

    function onBeforeUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
      event.returnValue = "";
    }

    function onReconnect() {
      void syncServerTiming();
    }

    window.addEventListener("beforeunload", onBeforeUnload);
    window.addEventListener("online", onReconnect);
    return () => {
      window.removeEventListener("beforeunload", onBeforeUnload);
      window.removeEventListener("online", onReconnect);
    };
  }, [running, attemptId, mode, questions]);

  const current = questions[currentIndex] ?? null;
  const currentAnswer = current ? answers[current.question.id] : undefined;

  const sections = useMemo(
    () => Array.from(new Set(questions.map((item) => item.section_slug))),
    [questions],
  );

  const visiblePalette = useMemo(
    () => questions
      .map((item, index) => ({item, index}))
      .filter(({item}) => mode !== "full" || item.section_slug === activeSectionSlug),
    [questions, mode, activeSectionSlug],
  );

  const currentSectionQuestionNumber = useMemo(() => {
    if (!current || mode !== "full") return currentIndex + 1;
    const inSection = visiblePalette.findIndex(({index}) => index === currentIndex);
    return inSection >= 0 ? inSection + 1 : 1;
  }, [current, mode, currentIndex, visiblePalette]);

  function applyTimingState(state: MockStateResponse) {
    setSecondsLeft(state.seconds_left);
    if (mode === "full") {
      setActiveSectionSlug(state.active_section_slug);
      setSectionIndex(state.section_index);
      setSectionSecondsLeft(state.section_seconds_left);
      if (state.active_section_slug) {
        const first = questions.findIndex((item) => item.section_slug === state.active_section_slug);
        const currentStillValid = questions[currentIndex]?.section_slug === state.active_section_slug;
        if (!currentStillValid && first >= 0) {
          setCurrentIndex(first);
          questionOpenedAt.current = Date.now();
        }
      }
    }
  }

  async function syncServerTiming() {
    if (!attemptId) return;
    try {
      const state = await fetchMockState(attemptId);
      applyTimingState(state);
      if (state.seconds_left <= 0) {
        await finishMock(true);
      }
    } catch {
      // A clock sync is best-effort; answer saves remain server-enforced.
    }
  }

  async function syncFullSectionBoundary() {
    if (!attemptId || mode !== "full" || boundarySyncing.current) return;
    boundarySyncing.current = true;
    const previousSection = activeSectionSlug;
    try {
      const state = await fetchMockState(attemptId);
      setSecondsLeft(state.seconds_left);
      setActiveSectionSlug(state.active_section_slug);
      setSectionIndex(state.section_index);
      setSectionSecondsLeft(state.section_seconds_left);

      if (state.seconds_left <= 0 || !state.active_section_slug) {
        await finishMock(true);
        return;
      }

      const nextIndex = questions.findIndex((item) => item.section_slug === state.active_section_slug);
      if (nextIndex >= 0) {
        setCurrentIndex(nextIndex);
        questionOpenedAt.current = Date.now();
      }
      if (previousSection && previousSection !== state.active_section_slug) {
        setNotice(
          `Time completed for ${sectionLabels[previousSection] ?? previousSection}. ${sectionLabels[state.active_section_slug] ?? state.active_section_slug} is now active.`
        );
        setError("");
      }
    } catch {
      setError("Could not sync the section timer. Your saved answers are safe; retry in a moment.");
    } finally {
      boundarySyncing.current = false;
    }
  }

  async function begin() {
    if (checkingActive) {
      setError("Checking your saved test. Please wait a moment.");
      return;
    }
    if (resumeInfo?.attempt_id) {
      setError("Resume or discard the in-progress test before starting another.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    setResult(null);
    setDiagnosticProfile(null);
    try {
      const data = await startMock(
        mode,
        mode === "sectional" ? subject : undefined,
        mode === "topic" ? topicId : undefined,
      );
      if (data.resumed_existing) {
        // Another tab or a delayed active-attempt check can race with Start.
        // Never initialise an existing attempt as a fresh zero-answer test.
        const current = await fetchActiveMock().catch(() => null);
        setResumeInfo(current?.attempt_id ? current : {attempt_id: data.attempt_id, mode: data.mode});
        setError("An in-progress test already exists. Resume it to restore your saved answers and timer.");
        return;
      }
      setAttemptId(data.attempt_id);
      setQuestions(data.questions);
      setAnswers({});
      setSecondsLeft(data.duration_minutes * 60);
      if (mode === "full") {
        setActiveSectionSlug(fullSectionOrder[0]);
        setSectionIndex(0);
        setSectionSecondsLeft(fullSectionSeconds);
      } else {
        setActiveSectionSlug(null);
        setSectionIndex(null);
        setSectionSecondsLeft(null);
      }
      setCurrentIndex(0);
      setRunning(true);
      setResumeInfo(null);
      questionOpenedAt.current = Date.now();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start test.");
    } finally {
      setBusy(false);
    }
  }

  async function resumeMock() {
    if (!resumeInfo?.attempt_id) return;
    setBusy(true);
    setError("");
    setNotice("");
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
      const resumedMode = attempt.mode as "mini" | "full" | "sectional" | "topic" | "diagnostic";
      setAttemptId(attempt.attempt_id);
      setQuestions(attempt.questions);
      setAnswers(restored);
      setMode(resumedMode);
      if (resumeInfo.subject_slug) setSubject(resumeInfo.subject_slug);
      setSecondsLeft(state.seconds_left);
      setActiveSectionSlug(state.active_section_slug);
      setSectionIndex(state.section_index);
      setSectionSecondsLeft(state.section_seconds_left);
      const firstIndex = resumedMode === "full" && state.active_section_slug
        ? attempt.questions.findIndex((item) => item.section_slug === state.active_section_slug)
        : 0;
      setCurrentIndex(Math.max(0, firstIndex));
      setRunning(true);
      questionOpenedAt.current = Date.now();
    } catch {
      setError("Could not resume the saved test.");
    } finally {
      setBusy(false);
    }
  }

  async function discardActive() {
    if (!resumeInfo?.attempt_id) return;
    if (!window.confirm("Discard this in-progress test? Saved answers in this attempt will be abandoned.")) return;
    setBusy(true);
    try {
      await abandonMock(resumeInfo.attempt_id);
      setResumeInfo(null);
      setError("");
    } catch {
      setError("Could not discard the in-progress test.");
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
    if (pendingAnswerSave.current) {
      throw new Error("Your previous answer is still saving. Please try again.");
    }
    const questionId = current.question.id;
    const previous = localForCurrent();
    const next = {
      ...previous,
      ...partial,
      time_seconds: previous.time_seconds + (extraTime ? elapsedForCurrent() : 0),
    };
    // A question is visually selected immediately, but navigation and further
    // edits are disabled until the backend acknowledges the save.
    setAnswers((state) => ({...state, [questionId]: next}));
    const pending = saveMockResponse(attemptId, {
      question_id: questionId,
      selected_option: next.selected_option,
      marked_for_review: next.marked_for_review,
      time_seconds: next.time_seconds,
    });
    pendingAnswerSave.current = pending;
    setSavingAnswer(true);
    try {
      await pending;
      questionOpenedAt.current = Date.now();
    } catch (error) {
      // Do not keep displaying an unsaved choice as if it persisted.
      setAnswers((state) => ({...state, [questionId]: previous}));
      throw error;
    } finally {
      pendingAnswerSave.current = null;
      setSavingAnswer(false);
    }
  }

  async function goTo(index: number) {
    if (index === currentIndex) return;
    const target = questions[index];
    if (!target) return;
    if (mode === "full" && target.section_slug !== activeSectionSlug) {
      setNotice("Other sections are locked by the SSC sectional timer.");
      return;
    }
    try {
      await persistPatch();
      setCurrentIndex(index);
      questionOpenedAt.current = Date.now();
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Answer autosave failed. Try again.");
      if (mode === "full") void syncServerTiming();
    }
  }

  async function chooseOption(position: number | null) {
    try {
      await persistPatch({selected_option: position});
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Answer autosave failed. Try again.");
      if (mode === "full") void syncServerTiming();
    }
  }

  async function toggleReview() {
    try {
      await persistPatch({marked_for_review: !currentAnswer?.marked_for_review});
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Review flag could not be saved.");
      if (mode === "full") void syncServerTiming();
    }
  }

  async function saveAndNext() {
    try {
      await persistPatch();
      if (mode === "full") {
        const position = visiblePalette.findIndex(({index}) => index === currentIndex);
        const next = visiblePalette[position + 1];
        if (next) {
          setCurrentIndex(next.index);
          questionOpenedAt.current = Date.now();
        } else {
          setNotice("You reached the end of this section. Review any question in this section until the 15-minute timer completes.");
        }
      } else if (currentIndex < questions.length - 1) {
        setCurrentIndex((value) => value + 1);
        questionOpenedAt.current = Date.now();
      }
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Answer save failed. Try again.");
      if (mode === "full") void syncServerTiming();
    }
  }

  async function finishMock(force = false) {
    if (!attemptId || busy) return;
    if (!force && !window.confirm("Submit this test now? You cannot change answers after submission.")) return;
    setBusy(true);
    setError("");
    try {
      if (pendingAnswerSave.current) {
        try {
          await pendingAnswerSave.current;
        } catch (err) {
          if (!force) throw err;
        }
      } else if (current) {
        try {
          await persistPatch();
        } catch (err) {
          if (!force) throw err;
        }
      }
      const data = await submitMock(attemptId);
      setResult(data);
      setReview(await fetchMockReview(attemptId).catch(() => null));
      if (mode === "diagnostic") {
        setDiagnosticProfile(await fetchDiagnosticBaseline().catch(() => null));
      }
      setRunning(false);
      setResumeInfo(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit test.");
      if (mode === "full") void syncServerTiming();
    } finally {
      setBusy(false);
    }
  }

  function jumpToSection(slug: string) {
    if (mode === "full" && slug !== activeSectionSlug) {
      setNotice("Sections unlock automatically every 15 minutes in the official simulation.");
      return;
    }
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
          <p className="eyebrow">{mode === "diagnostic" ? "Starting diagnostic submitted" : "Test submitted"}</p>
          <h1>{mode === "diagnostic" ? "Your starting profile" : result.score + " marks"}</h1>
          {mode === "diagnostic" && (
            <div className="diagnosticResultNote" role="status">
              <strong>Exam readiness: Not assessed</strong>
              <p>These 40 questions are a sampled starting check, not a prediction of your SSC exam score. Untested topics are unknown, not weak.</p>
              {diagnosticProfile?.baseline && (
                <p>
                  First baseline: {diagnosticProfile.baseline.attempted_questions}/40 attempted ·
                  {diagnosticProfile.baseline.attempted_topics}/{diagnosticProfile.baseline.total_topics} topics tried ·
                  {diagnosticProfile.baseline.evidence_label === "limited_sample" ? "Limited sample" : "Initial sample"}
                </p>
              )}
            </div>
          )}
          <div className="mockResultGrid">
            <article><span>Correct</span><strong>{result.correct}</strong></article>
            <article><span>Incorrect</span><strong>{result.incorrect}</strong></article>
            <article><span>Unattempted</span><strong>{result.unattempted}</strong></article>
            <article><span>Accuracy</span><strong>{accuracy}%</strong></article>
            <article><span>Attempt rate</span><strong>{attemptRate}%</strong></article>
            {review && <article><span>Easy marks missed</span><strong>{review.easy_missed}</strong></article>}
            {review && <article><span>Slow questions</span><strong>{review.slow_questions}</strong></article>}
          </div>
          <p className="muted">
            {mode === "diagnostic"
              ? "Diagnostic sample marks use the familiar +2 / −0.50 rule only for feedback. They are not official full-exam marks or exam readiness."
              : "Scoring uses +2 for a correct answer and −0.50 for a wrong answer."}
          </p>

          {review && (
            <>
              <section className="mockSectionBreakdown">
                <p className="eyebrow">Section breakdown</p>
                <div>
                  {Object.entries(review.sections).map(([slug, stats]) => (
                    <article key={slug}>
                      <strong>{sectionLabels[slug] ?? slug}</strong>
                      <span>{stats.correct} correct • {stats.incorrect} wrong • {stats.unattempted} skipped</span>
                      <small>{stats.score} marks • {stats.accuracy}% accuracy • {Math.round(stats.time_seconds / 60)} min active solving</small>
                    </article>
                  ))}
                </div>
              </section>

              {review.weak_patterns.length > 0 && (
                <section className="mockWeakPatterns">
                  <p className="eyebrow">Weak question patterns</p>
                  <div>
                    {review.weak_patterns.map((item) => (
                      <span key={item.pattern}>{item.pattern.replaceAll("-", " ")} <strong>{item.missed} missed</strong></span>
                    ))}
                  </div>
                </section>
              )}

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
              setNotice("");
              setError("");
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
            <p className="muted">Starting diagnostic, practice tests and the official-format SSC CGL Tier-I simulation.</p>
          </div>
          <Link to="/">Dashboard</Link>
        </header>

        {resumeInfo?.attempt_id && (
          <section className="resumeMockCard">
            <div>
              <p className="eyebrow">In-progress test found</p>
              <h2>Resume where you stopped.</h2>
              <p>
                {resumeInfo.mode === "full" ? "Full Tier-I Simulation" : resumeInfo.mode} • {formatTime(resumeInfo.seconds_left ?? 0)} total remaining
                {resumeInfo.mode === "full" && resumeInfo.active_section_slug && (
                  <> • {sectionLabels[resumeInfo.active_section_slug]} {formatTime(resumeInfo.section_seconds_left ?? 0)}</>
                )}
              </p>
            </div>
            <div>
              <button onClick={() => void resumeMock()} disabled={busy}>Resume test</button>
              <button className="secondary" onClick={() => void discardActive()} disabled={busy}>Discard</button>
            </div>
          </section>
        )}

        <section className="mockSetup">
          <p className="eyebrow">Choose test mode</p>
          <h1>Train in the format you need.</h1>
          <div className="mockModeGrid">
            <button className={mode === "mini" ? "mockModeCard activeMockMode" : "mockModeCard"} onClick={() => setMode("mini")}>
              <strong>Quick Sprint</strong>
              <span>4 questions • 4 minutes • one from each section • warm-up only</span>
            </button>
            {!topicId && (
              <button className={mode === "diagnostic" ? "mockModeCard activeMockMode" : "mockModeCard"} onClick={() => setMode("diagnostic")}>
                <strong>Starting Diagnostic</strong>
                <span>40 questions · 24 minutes · 10 per subject · 3 Easy / 5 Medium / 2 Hard in each</span>
                <small>Find your initial learning gaps. This does not certify overall readiness.</small>
              </button>
            )}
            <button className={mode === "sectional" ? "mockModeCard activeMockMode" : "mockModeCard"} onClick={() => setMode("sectional")}>
              <strong>Section Test</strong>
              <span>25 questions • 15 minutes • one SSC section</span>
            </button>
            <button className={mode === "full" ? "mockModeCard activeMockMode" : "mockModeCard"} onClick={() => setMode("full")}>
              <strong>Full Tier-I Simulation</strong>
              <span>100 questions • 60 minutes • 25Q × 4 • strict 15-minute sectional timers • +2 / −0.50</span>
            </button>
            {topicId && (
              <button className={mode === "topic" ? "mockModeCard activeMockMode" : "mockModeCard"} onClick={() => setMode("topic")}>
                <strong>{topicName || "Topic Test"}</strong>
                <span>Up to 20 questions • 20 minutes • focused assessment</span>
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

          {mode === "full" && (
            <div className="officialSimulationNote">
              <strong>Strict simulation</strong>
              <span>Each section stays active for exactly 15 minutes. Previous and future sections remain locked. The test moves forward automatically.</span>
            </div>
          )}

          {error && <p className="errorText">{error}</p>}
          <button className="mockStartButton" onClick={() => void begin()} disabled={busy || checkingActive || Boolean(resumeInfo?.attempt_id)}>
            {checkingActive ? "Checking saved tests..." : busy ? "Preparing..." : resumeInfo?.attempt_id ? "Resume or discard current test first" : "Start test"}
          </button>
        </section>
      </main>
    );
  }

  const paletteAnswers = visiblePalette.map(({item}) => answers[item.question.id]);
  const answeredCount = paletteAnswers.filter((item) => item?.selected_option !== null && item?.selected_option !== undefined).length;
  const reviewCount = paletteAnswers.filter((item) => item?.marked_for_review).length;
  const canSubmitFull = mode !== "full" || sectionIndex === fullSectionOrder.length - 1 || secondsLeft === 0;

  return (
    <main className="examShell">
      <header className="examHeader">
        <div>
          <strong>SSC CGL Tier I</strong>
          <span>
            {mode === "full" ? "Full Tier-I Simulation" : mode === "sectional" ? "Section Test" : mode === "topic" ? "Topic Test" : "Quick Sprint"} • {savingAnswer ? "Saving answer..." : "Answers saved"}
          </span>
        </div>
        {mode === "full" ? (
          <div className="examTimerStack">
            <div className={(sectionSecondsLeft ?? 0) <= 60 ? "examTimer examTimerUrgent" : "examTimer"}>
              <small>{activeSectionSlug ? sectionLabels[activeSectionSlug] : "Section"}</small>
              <strong>{formatTime(sectionSecondsLeft ?? 0)}</strong>
            </div>
            <span>Total {formatTime(secondsLeft)}</span>
          </div>
        ) : (
          <div className={secondsLeft <= 60 ? "examTimer examTimerUrgent" : "examTimer"}>
            {formatTime(secondsLeft)}
          </div>
        )}
        <button
          className="finishButton"
          onClick={() => void finishMock(false)}
          disabled={busy || savingAnswer || !canSubmitFull}
          title={!canSubmitFull ? "Available in the final 15-minute section" : undefined}
        >
          {mode === "full" && !canSubmitFull ? "Submit in final section" : "Submit test"}
        </button>
      </header>

      <div className="examSectionTabs">
        {sections.map((slug) => {
          const locked = mode === "full" && slug !== activeSectionSlug;
          const orderIndex = fullSectionOrder.indexOf(slug);
          const completed = mode === "full" && sectionIndex !== null && orderIndex < sectionIndex;
          return (
            <button
              key={slug}
              className={[
                current.section_slug === slug ? "activeSectionTab" : "",
                locked ? "lockedSectionTab" : "",
                completed ? "completedSectionTab" : "",
              ].filter(Boolean).join(" ")}
              onClick={() => jumpToSection(slug)}
              disabled={locked || savingAnswer}
            >
              {sectionLabels[slug] ?? slug}
              {mode === "full" && locked ? completed ? " ✓" : " 🔒" : ""}
            </button>
          );
        })}
      </div>

      {notice && <div className="examNotice">{notice}</div>}

      <section className="examLayout">
        <article className="examQuestionCard">
          <div className="examQuestionMeta">
            <span>
              {mode === "full"
                ? `Question ${currentSectionQuestionNumber} of ${visiblePalette.length} in this section`
                : `Question ${currentIndex + 1} of ${questions.length}`}
            </span>
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
                disabled={savingAnswer || busy}
                onClick={() => void chooseOption(option.position)}
              >
                <strong>{String.fromCharCode(64 + option.position)}</strong>
                <span>{option.text ?? "Image option"}</span>
                {option.image_url && <SecureImage src={option.image_url} alt={"Option " + option.position} />}
              </button>
            ))}
          </div>

          <div className="examQuestionActions">
            <button className="secondary" disabled={savingAnswer || busy} onClick={() => void chooseOption(null)}>Clear response</button>
            <button
              className={currentAnswer?.marked_for_review ? "reviewToggle activeReviewToggle" : "reviewToggle"}
              disabled={savingAnswer || busy}
              onClick={() => void toggleReview()}
            >
              {currentAnswer?.marked_for_review ? "Marked for review" : "Mark for review"}
            </button>
            <button disabled={savingAnswer || busy} onClick={() => void saveAndNext()}>
              {mode === "full" && currentSectionQuestionNumber === visiblePalette.length
                ? "Save response"
                : currentIndex === questions.length - 1
                  ? "Save response"
                  : "Save & Next"}
            </button>
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
            {visiblePalette.map(({item, index}, localIndex) => {
              const answer = answers[item.question.id];
              const classNames = [
                "paletteNumber",
                index === currentIndex ? "paletteCurrent" : "",
                answer?.selected_option !== null && answer?.selected_option !== undefined ? "paletteAnswered" : "",
                answer?.marked_for_review ? "paletteReview" : "",
              ].filter(Boolean).join(" ");
              return (
                <button className={classNames} key={item.question.id} disabled={savingAnswer || busy} onClick={() => void goTo(index)}>
                  {mode === "full" ? localIndex + 1 : index + 1}
                </button>
              );
            })}
          </div>
          <div className="paletteSummary">
            <span>Answered <strong>{answeredCount}</strong></span>
            <span>Review <strong>{reviewCount}</strong></span>
            <span>Remaining <strong>{visiblePalette.length - answeredCount}</strong></span>
          </div>
          {mode === "full" && (
            <p className="sectionLockHelp">Only the active 25-question section is available during its 15-minute window.</p>
          )}
        </aside>
      </section>
    </main>
  );
}
