import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import {
  PracticeQuestion,
  PracticeResult,
  TopicPackage,
  addQuestionToRevision,
  classifyPracticeMistake,
  fetchPracticeQuestions,
  fetchTopicPackage,
  submitPracticeAnswer,
  toggleBookmark,
} from "../api";
import { getToken } from "../auth";
import SecureImage from "../components/SecureImage";
import SpeakButton from "../components/SpeakButton";
import TeacherCoach from "../components/TeacherCoach";

const confidenceOptions = [
  {value: 3, label: "Sure"},
  {value: 2, label: "Unsure"},
  {value: 1, label: "Guess"},
];

const mistakeOptions = [
  ["concept", "Concept gap"],
  ["formula", "Forgot rule/formula"],
  ["calculation", "Calculation"],
  ["misread", "Misread question"],
  ["time_pressure", "Time pressure"],
  ["guess", "Risky guess"],
];

const practiceModes = [
  ["adaptive", "Adaptive", "Prioritises unseen, wrong, slow and low-confidence questions."],
  ["guided", "Guided", "Moves across question patterns from easier to harder."],
  ["topic", "Topic drill", "Rotates through the different patterns inside the selected topic."],
  ["pyq", "PYQ", "Prioritises previous-year and official-source questions."],
  ["mixed", "Mixed", "Rotates across topics for broader exam recall."],
  ["weak", "Weak topics", "Targets low-mastery topics and recent misses."],
  ["revision", "Revision drill", "Serves questions that are due from your revision queue."],
  ["speed", "Speed drill", "Prioritises questions with shorter target times."],
  ["ladder", "Difficulty ladder", "Cycles Easy → Medium → Hard."],
  ["timed", "Timed", "Per-question countdown using the expected exam time."],
] as const;

type Mode = typeof practiceModes[number][0];

export default function PracticePage() {
  const [params] = useSearchParams();
  const rawTopicId = Number(params.get("topic_id") ?? "0");
  const topicId = Number.isFinite(rawTopicId) && rawTopicId > 0 ? rawTopicId : undefined;
  const requestedMode = params.get("mode") ?? (topicId ? "adaptive" : "mixed");
  const validModes = practiceModes.map((item) => item[0]) as readonly string[];
  const mode = (validModes.includes(requestedMode) ? requestedMode : "adaptive") as Mode;
  const requestedLimit = Number(params.get("limit") ?? "10");
  const limit = Number.isFinite(requestedLimit) ? Math.min(30, Math.max(3, requestedLimit)) : 10;

  const [questions, setQuestions] = useState<PracticeQuestion[]>([]);
  const [topicPackage, setTopicPackage] = useState<TopicPackage | null>(null);
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [result, setResult] = useState<PracticeResult | null>(null);
  const [mistakeSaved, setMistakeSaved] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [actualSeconds, setActualSeconds] = useState(0);
  const [error, setError] = useState("");
  const [bookmarked, setBookmarked] = useState(false);
  const [usedHint, setUsedHint] = useState(false);
  const [revisionSaved, setRevisionSaved] = useState(false);
  const [outcomes, setOutcomes] = useState<Array<{correct: boolean; seconds: number}>>([]);
  const startedAt = useRef(Date.now());
  const timedOut = useRef(false);
  const navigate = useNavigate();

  const question = useMemo(() => questions[index] ?? null, [questions, index]);
  const targetSeconds = question?.expected_time_seconds ?? 45;
  const currentMode = practiceModes.find((item) => item[0] === mode);

  const coachPreview = useMemo(() => {
    if (!question || !topicPackage || question.topic_id !== topicPackage.topic.id) return null;
    const exact = topicPackage.archetypes.find((item) => item.slug === question.pattern_type) ?? null;
    const lesson = topicPackage.lessons[0] ?? null;
    const recognition = exact?.recognition_cues ?? null;
    const standardMethod = exact?.canonical_method ?? lesson?.concept ?? null;
    const fastMethod = exact?.shortcut_method ?? lesson?.shortcut ?? null;
    const commonTrap = exact?.common_trap ?? lesson?.common_traps ?? null;
    const hintSteps = [recognition, standardMethod, fastMethod].filter(
      (value): value is string => Boolean(value)
    );
    return {recognition, standardMethod, fastMethod, commonTrap, hintSteps};
  }, [question, topicPackage]);

  useEffect(() => {
    if (!getToken()) {
      navigate("/login");
      return;
    }

    setError("");
    setQuestions([]);
    setIndex(0);
    setOutcomes([]);
    if (topicId) {
      fetchTopicPackage(topicId).then(setTopicPackage).catch(() => setTopicPackage(null));
    } else {
      setTopicPackage(null);
    }
    fetchPracticeQuestions(topicId, limit, mode)
      .then((items) => {
        setQuestions(items);
        startedAt.current = Date.now();
        setElapsed(0);
        if (!items.length) setError("No verified questions matched this practice mode yet.");
      })
      .catch(() => setError("Could not load practice. Check your connection and try again."));
  }, [navigate, topicId, mode, limit]);

  useEffect(() => {
    if (!question || result) return;
    const timer = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt.current) / 1000));
    }, 250);
    return () => window.clearInterval(timer);
  }, [question, result]);

  useEffect(() => {
    if (mode !== "timed" || !question || result || timedOut.current) return;
    if (elapsed < targetSeconds) return;

    timedOut.current = true;
    setActualSeconds(targetSeconds);
    submitPracticeAnswer({
      question_id: question.id,
      selected_option: selected,
      time_seconds: targetSeconds,
      confidence: confidence ?? 1,
      used_hint: usedHint,
      mistake_type: "time_pressure",
    })
      .then((response) => {
        setResult(response);
        setOutcomes((items) => [...items, {correct: response.correct, seconds: targetSeconds}]);
      })
      .catch(() => setError("Could not submit the timed answer."));
  }, [mode, question, result, elapsed, targetSeconds, selected, confidence, usedHint]);

  async function submit() {
    if (!question || selected === null || confidence === null) return;
    const seconds = Math.max(1, (Date.now() - startedAt.current) / 1000);
    setActualSeconds(seconds);
    try {
      const response = await submitPracticeAnswer({
        question_id: question.id,
        selected_option: selected,
        time_seconds: seconds,
        confidence,
        used_hint: usedHint,
        mistake_type: confidence === 1 ? "guess" : null,
      });
      setResult(response);
      setOutcomes((items) => [...items, {correct: response.correct, seconds}]);
    } catch {
      setError("Could not submit this answer. Try again.");
    }
  }

  async function saveMistake(type: string) {
    if (!result) return;
    await classifyPracticeMistake(result.attempt_id, type);
    setMistakeSaved(type);
  }

  async function bookmarkCurrent() {
    if (!question) return;
    const response = await toggleBookmark(question.id);
    setBookmarked(response.bookmarked);
  }

  async function addToRevision() {
    if (!question) return;
    try {
      await addQuestionToRevision(question.id);
      setRevisionSaved(true);
    } catch {
      setError("Could not add this question to revision.");
    }
  }

  function next() {
    setIndex((value) => value + 1);
    setSelected(null);
    setConfidence(null);
    setResult(null);
    setMistakeSaved(null);
    setBookmarked(false);
    setUsedHint(false);
    setRevisionSaved(false);
    setElapsed(0);
    setActualSeconds(0);
    timedOut.current = false;
    startedAt.current = Date.now();
  }

  function modeUrl(nextMode: string) {
    const next = new URLSearchParams();
    if (topicId) next.set("topic_id", String(topicId));
    next.set("mode", nextMode);
    next.set("limit", String(limit));
    return "/practice?" + next.toString();
  }

  if (error && questions.length === 0) {
    return (
      <main className="lessonShell">
        <header className="lessonTopbar">
          <button className="textBackButton" onClick={() => navigate(-1)}>← Back</button>
          <Link to="/learn">Learn</Link>
        </header>
        <section className="emptyCard">
          <strong>{error}</strong>
          <div className="emptyActions">
            <button onClick={() => window.location.reload()}>Retry</button>
            <Link to="/learn">Choose a topic</Link>
          </div>
        </section>
      </main>
    );
  }

  if (index >= questions.length && questions.length > 0) {
    const correct = outcomes.filter((item) => item.correct).length;
    const accuracy = outcomes.length ? Math.round((correct / outcomes.length) * 100) : 0;
    const avgSeconds = outcomes.length
      ? Math.round(outcomes.reduce((sum, item) => sum + item.seconds, 0) / outcomes.length)
      : 0;
    return (
      <main className="lessonShell">
        <header className="lessonTopbar">
          <Link to="/practice?mode=mixed&limit=10">← Practice hub</Link>
          <Link to="/">Dashboard</Link>
        </header>
        <section className="practiceComplete">
          <p className="eyebrow">Practice set complete</p>
          <h1>{accuracy}% accuracy</h1>
          <div className="practiceSummaryGrid">
            <article><span>Correct</span><strong>{correct}/{outcomes.length}</strong></article>
            <article><span>Average time</span><strong>{avgSeconds}s</strong></article>
            <article><span>Mode</span><strong>{currentMode?.[1]}</strong></article>
          </div>
          <p>Your attempts are saved to mastery, analytics and the revision scheduler.</p>
          <div className="practiceCompleteActions">
            <Link className="primaryLink" to={modeUrl(mode)}>Another set</Link>
            <Link to="/revision">Review due items</Link>
            <Link to="/analytics">See analytics</Link>
          </div>
        </section>
      </main>
    );
  }

  if (!question) {
    return (
      <main className="lessonShell">
        <section className="emptyCard">Preparing {currentMode?.[1] ?? "practice"}…</section>
      </main>
    );
  }

  const remaining = Math.max(0, targetSeconds - elapsed);
  const selectedOption = question.options.find((option) => option.position === selected);
  const correctOption = result
    ? question.options.find((option) => option.position === result.correct_option)
    : null;
  const selectedLabel = selectedOption
    ? String.fromCharCode(64 + selectedOption.position) + ". " + (selectedOption.text ?? "Image option")
    : null;
  const correctLabel = correctOption
    ? String.fromCharCode(64 + correctOption.position) + ". " + (correctOption.text ?? "Image option")
    : null;

  return (
    <main className="practiceShell">
      <header className="practiceTopbar">
        <div>
          <button className="textBackButton" onClick={() => navigate(-1)}>← Back</button>
          <span>
            {topicPackage
              ? topicPackage.subject.name + " / " + topicPackage.topic.name
              : topicId
                ? "Topic practice"
                : "Mixed syllabus"}
          </span>
        </div>
        <span>Question {index + 1} / {questions.length}</span>
      </header>

      <section className="practiceModePanel">
        <div>
          <p className="eyebrow">
            {topicPackage ? topicPackage.subject.name + " • " + topicPackage.topic.name + " • " : ""}
            {currentMode?.[1]}
          </p>
          <p>{currentMode?.[2]}</p>
        </div>
        <div className="practiceModes">
          {practiceModes.map(([value, label]) => (
            <Link
              key={value}
              className={mode === value ? "modePill activeMode" : "modePill"}
              to={modeUrl(value)}
            >
              {label}
            </Link>
          ))}
        </div>
      </section>

      <article className="practiceCard">
        <div className="practiceQuestionToolbar">
          <div className="practiceMeta">
            {question.subtopic && <span>{question.subtopic}</span>}
            {question.pattern_type && <span>{question.pattern_type.replaceAll("-", " ")}</span>}
            <span>Difficulty {question.difficulty}</span>
            {question.expected_time_seconds && <span>Target {question.expected_time_seconds}s</span>}
            {question.year && <span>PYQ {question.year}</span>}
            <span className={mode === "timed" && remaining <= 10 ? "urgentTimer" : ""}>
              {mode === "timed" ? remaining + "s left" : elapsed + "s"}
            </span>
          </div>
          <button className={bookmarked ? "bookmarkButton activeBookmark" : "bookmarkButton"} onClick={() => void bookmarkCurrent()}>
            {bookmarked ? "★ Bookmarked" : "☆ Bookmark"}
          </button>
        </div>

        <h1>{question.question_text}</h1>
        <SpeakButton
          label="Read question"
          text={[
            question.question_text,
            ...question.options.map((option) => option.text ? String.fromCharCode(64 + option.position) + ". " + option.text : ""),
          ].filter(Boolean).join(". ")}
        />

        {question.question_image_url && (
          <SecureImage className="practiceQuestionImage" src={question.question_image_url} alt="Question visual" />
        )}

        <div className="practiceOptions">
          {question.options.map((option) => {
            const selectedClass = selected === option.position ? " practiceSelected" : "";
            const resultClass = result
              ? option.position === result.correct_option
                ? " practiceCorrect"
                : selected === option.position
                  ? " practiceWrong"
                  : ""
              : "";
            return (
              <button
                className={"practiceOption" + selectedClass + resultClass}
                key={option.position}
                disabled={Boolean(result)}
                onClick={() => setSelected(option.position)}
              >
                <strong>{String.fromCharCode(64 + option.position)}</strong>
                <span>{option.text ?? "See question image"}</span>
                {option.image_url && <SecureImage src={option.image_url} alt={"Option " + option.position} />}
              </button>
            );
          })}
        </div>

        {!result && (
          <>
            <TeacherCoach
              key={"before-" + question.id}
              title={question.subtopic || question.pattern_type || "this question"}
              context={question.question_text}
              explanation={coachPreview?.recognition}
              standardMethod={coachPreview?.standardMethod}
              fastMethod={coachPreview?.fastMethod}
              commonTrap={coachPreview?.commonTrap}
              hintSteps={coachPreview?.hintSteps ?? []}
              defaultOpen={mode === "guided"}
              lead="Try the question yourself first. If you are stuck, ask for Hint 1; I will reveal the method progressively instead of giving the answer immediately."
              onHintUsed={() => setUsedHint(true)}
            />
            {usedHint && <p className="hintUsedNote">Hint used — this attempt will be considered by mastery and revision.</p>}
            <div className="confidenceRow">
              <span>How confident are you?</span>
              <div>
                {confidenceOptions.map((item) => (
                  <button
                    key={item.value}
                    className={confidence === item.value ? "confidence activeConfidence" : "confidence"}
                    onClick={() => setConfidence(item.value)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
            <button className="submitAnswer" disabled={selected === null || confidence === null} onClick={() => void submit()}>
              Check answer
            </button>
          </>
        )}

        {result && (
          <section className={result.correct ? "answerPanel correctPanel" : "answerPanel wrongPanel"}>
            <p className="eyebrow">{result.correct ? "Correct" : mode === "timed" && timedOut.current ? "Time up" : "Needs review"}</p>
            <div className="answerAudit">
              <div>
                <span>Your answer</span>
                <strong>{selectedLabel ?? "Not answered"}</strong>
              </div>
              <div>
                <span>Correct answer</span>
                <strong>{correctLabel}</strong>
              </div>
              <div>
                <span>Time</span>
                <strong className={actualSeconds > targetSeconds * 1.25 ? "slowText" : ""}>
                  {Math.round(actualSeconds)}s / {targetSeconds}s target
                </strong>
              </div>
              <div>
                <span>Confidence calibration</span>
                <strong>
                  {confidence === 3 && !result.correct ? "Overconfident miss" :
                   confidence === 1 && result.correct ? "Correct guess — revise once" :
                   confidence === 3 && result.correct ? "Confident + correct" :
                   confidence === 2 ? "Uncertain — reinforce" : "Low-confidence attempt"}
                </strong>
              </div>
            </div>
            <div className="solutionTutor">
              <div className="solutionTutorHead">
                <div>
                  <span>Teacher review</span>
                  <h2>{result.correct ? "Confirm the method, not just the answer." : "Repair the method before the next question."}</h2>
                </div>
                {result.coaching?.archetype_exact && <small>Exact pattern match</small>}
              </div>

              {result.coaching?.pattern_name && (
                <section className="solutionStep solutionIdentity">
                  <span>What this tests</span>
                  <h3>{result.coaching.pattern_name}</h3>
                  {result.coaching.skill && <p>{result.coaching.skill}</p>}
                </section>
              )}

              {result.coaching?.recognition_cues && (
                <section className="solutionStep">
                  <span>1 • Recognise</span>
                  <h3>What clue should you notice?</h3>
                  <p>{result.coaching.recognition_cues}</p>
                </section>
              )}

              {result.coaching?.standard_method && (
                <section className="solutionStep">
                  <span>2 • Safe method</span>
                  <h3>How should you approach it?</h3>
                  <p>{result.coaching.standard_method}</p>
                </section>
              )}

              {result.explanation && (
                <section className="solutionStep solutionWorked">
                  <span>3 • This question</span>
                  <h3>Worked solution</h3>
                  <p>{result.explanation}</p>
                </section>
              )}

              {(result.coaching?.fast_method || result.fast_method) && (
                <section className="solutionStep solutionFast">
                  <span>4 • SSC-fast method</span>
                  <h3>Can this be done faster?</h3>
                  <p>{result.coaching?.fast_method ?? result.fast_method}</p>
                </section>
              )}

              {result.coaching?.difficulty_rule && (
                <section className="solutionStep">
                  <span>Difficulty cue</span>
                  <h3>At this level</h3>
                  <p>{result.coaching.difficulty_rule}</p>
                </section>
              )}

              {result.coaching?.common_trap && (
                <section className="solutionStep solutionTrap">
                  <span>5 • Marks trap</span>
                  <h3>What mistake should you avoid?</h3>
                  <p>{result.coaching.common_trap}</p>
                </section>
              )}

              {result.coaching?.worked_example && (
                <details className="relatedExample">
                  <summary>See a related worked example</summary>
                  <p>{result.coaching.worked_example}</p>
                </details>
              )}
            </div>

            <TeacherCoach
              key={"after-" + question.id}
              title={result.coaching?.pattern_name || question.subtopic || question.pattern_type || "this question"}
              context={[
                question.question_text,
                result.coaching?.recognition_cues ?? "",
                result.coaching?.standard_method ?? "",
              ].filter(Boolean).join(". ")}
              explanation={result.explanation}
              fastMethod={result.coaching?.fast_method ?? result.fast_method}
              commonTrap={result.coaching?.common_trap}
              standardMethod={result.coaching?.standard_method}
              examples={result.coaching?.worked_example ? [result.coaching.worked_example] : []}
              hintSteps={result.coaching?.hint_steps ?? []}
              correctAnswer={correctLabel}
              selectedAnswer={selectedLabel}
              defaultOpen={!result.correct}
              lead={
                result.correct
                  ? "Correct. Now make sure you can explain the recognition cue and method before moving on."
                  : "You missed this one. I will help you repair the recognition cue and method before the next question."
              }
              onNext={next}
            />

            {!result.correct && (
              <div className="mistakePicker">
                <span>What caused the miss?</span>
                <div>
                  {mistakeOptions.map(([value, label]) => (
                    <button
                      key={value}
                      className={mistakeSaved === value ? "mistakeChip activeMistake" : "mistakeChip"}
                      onClick={() => void saveMistake(value)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {result.mastery_score !== null && <p className="muted">Topic mastery: {Math.round(result.mastery_score)}%</p>}
            {(result.revision_scheduled || revisionSaved) && <p className="muted">This question is in your revision queue.</p>}
            <div className="answerActionRow">
              <button className="secondary" disabled={revisionSaved || result.revision_scheduled} onClick={() => void addToRevision()}>
                {revisionSaved || result.revision_scheduled ? "✓ In revision" : "+ Add to revision"}
              </button>
              <button onClick={next}>{index + 1 === questions.length ? "Finish set" : "Next question"}</button>
            </div>
          </section>
        )}
      </article>
    </main>
  );
}
