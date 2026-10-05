import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import {
  PracticeQuestion,
  PracticeResult,
  fetchPracticeQuestions,
  submitPracticeAnswer,
} from "../api";
import { clearToken, getToken } from "../auth";
import SecureImage from "../components/SecureImage";

const confidenceOptions = [
  {value: 3, label: "Sure"},
  {value: 2, label: "Unsure"},
  {value: 1, label: "Guess"},
];

export default function PracticePage() {
  const [params] = useSearchParams();
  const topicId = Number(params.get("topic_id"));
  const [questions, setQuestions] = useState<PracticeQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [result, setResult] = useState<PracticeResult | null>(null);
  const [error, setError] = useState("");
  const startedAt = useRef(Date.now());
  const navigate = useNavigate();

  const question = useMemo(() => questions[index] ?? null, [questions, index]);

  useEffect(() => {
    if (!getToken()) {
      navigate("/login");
      return;
    }
    if (!Number.isFinite(topicId) || topicId <= 0) {
      setError("Choose a topic from Learn mode.");
      return;
    }

    fetchPracticeQuestions(topicId, 5)
      .then((items) => {
        setQuestions(items);
        startedAt.current = Date.now();
        if (!items.length) setError("No verified practice questions are ready for this topic yet.");
      })
      .catch(() => {
        clearToken();
        navigate("/login");
      });
  }, [navigate, topicId]);

  async function submit() {
    if (!question || selected === null || confidence === null) return;
    const seconds = Math.max(1, (Date.now() - startedAt.current) / 1000);
    const response = await submitPracticeAnswer({
      question_id: question.id,
      selected_option: selected,
      time_seconds: seconds,
      confidence,
      used_hint: false,
      mistake_type: confidence === 1 ? "guess" : null,
    });
    setResult(response);
  }

  function next() {
    setIndex((value) => value + 1);
    setSelected(null);
    setConfidence(null);
    setResult(null);
    startedAt.current = Date.now();
  }

  if (error) {
    return (
      <main className="lessonShell">
        <header className="lessonTopbar"><Link to="/learn">← Learn</Link><Link to="/">Dashboard</Link></header>
        <section className="emptyCard">{error}</section>
      </main>
    );
  }

  if (index >= questions.length) {
    return (
      <main className="lessonShell">
        <header className="lessonTopbar"><Link to="/learn">← Learn</Link><Link to="/">Dashboard</Link></header>
        <section className="practiceComplete">
          <p className="eyebrow">Guided practice complete</p>
          <h1>Good. Review the mistakes, not just the score.</h1>
          <p>Your attempts are already saved for mastery and revision.</p>
          <Link className="primaryLink" to="/learn">Choose next topic</Link>
        </section>
      </main>
    );
  }

  if (!question) {
    return (
      <main className="lessonShell">
        <section className="emptyCard">Loading practice…</section>
      </main>
    );
  }

  return (
    <main className="practiceShell">
      <header className="practiceTopbar">
        <Link to="/learn">← Learn</Link>
        <span>Question {index + 1} / {questions.length}</span>
      </header>

      <article className="practiceCard">
        <div className="practiceMeta">
          <span>Difficulty {question.difficulty}</span>
          {question.expected_time_seconds && <span>Target {question.expected_time_seconds}s</span>}
          {question.year && <span>PYQ {question.year}</span>}
        </div>

        <h1>{question.question_text}</h1>
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
            <button className="submitAnswer" disabled={selected === null || confidence === null} onClick={submit}>
              Check answer
            </button>
          </>
        )}

        {result && (
          <section className={result.correct ? "answerPanel correctPanel" : "answerPanel wrongPanel"}>
            <p className="eyebrow">{result.correct ? "Correct" : "Needs review"}</p>
            {!result.correct && <p>Correct option: {String.fromCharCode(64 + result.correct_option)}</p>}
            {result.explanation && <p>{result.explanation}</p>}
            {result.fast_method && <p><strong>Fast method:</strong> {result.fast_method}</p>}
            {result.mastery_score !== null && <p className="muted">Topic mastery: {Math.round(result.mastery_score)}%</p>}
            {result.revision_scheduled && <p className="muted">Added to your revision queue.</p>}
            <button onClick={next}>{index + 1 === questions.length ? "Finish" : "Next question"}</button>
          </section>
        )}
      </article>
    </main>
  );
}
