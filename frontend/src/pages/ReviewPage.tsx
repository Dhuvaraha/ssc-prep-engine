import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  ReviewQuestion,
  Topic,
  fetchReviewQuestions,
  fetchTopics,
  suggestReviewTopic,
  updateReviewQuestion,
} from "../api";
import { clearToken, getToken } from "../auth";

type TopicSuggestion = {
  topic_id: number | null;
  topic_slug: string | null;
  topic_name: string | null;
  confidence: number;
};

export default function ReviewPage() {
  const [questions, setQuestions] = useState<ReviewQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [topicId, setTopicId] = useState<number | null>(null);
  const [patternType, setPatternType] = useState("");
  const [subtopic, setSubtopic] = useState("");
  const [notes, setNotes] = useState("");
  const [suggestion, setSuggestion] = useState<TopicSuggestion | null>(null);
  const [status, setStatus] = useState("Loading...");
  const navigate = useNavigate();

  const question = useMemo(() => questions[index] ?? null, [questions, index]);

  useEffect(() => {
    if (!getToken()) {
      navigate("/login");
      return;
    }
    fetchReviewQuestions()
      .then((items) => {
        setQuestions(items);
        setStatus(items.length ? "" : "No review-required questions.");
      })
      .catch(() => {
        clearToken();
        navigate("/login");
      });
  }, [navigate]);

  useEffect(() => {
    if (!question) return;
    setTopicId(question.topic_id);
    setPatternType(question.pattern_type ?? "");
    setSubtopic(question.subtopic ?? "");
    setNotes(question.review_notes ?? "");
    setSuggestion(null);
    fetchTopics(question.subject_id).then(setTopics);
  }, [question]);

  async function getSuggestion() {
    if (!question) return;
    const result = await suggestReviewTopic(question.id) as TopicSuggestion;
    setSuggestion(result);
    if (result.topic_id) setTopicId(result.topic_id);
  }

  async function save(verification_status: "verified" | "rejected" | "review_required") {
    if (!question) return;
    await updateReviewQuestion(question.id, {
      topic_id: topicId,
      subtopic: subtopic || null,
      pattern_type: patternType || null,
      review_notes: notes || null,
      verification_status,
    });

    if (verification_status !== "review_required") {
      const next = questions.filter((q) => q.id !== question.id);
      setQuestions(next);
      setIndex((current) => Math.min(current, Math.max(next.length - 1, 0)));
    } else {
      setStatus("Saved.");
      window.setTimeout(() => setStatus(""), 1200);
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="brand">Content Review</p>
          <p className="muted">Only verified questions enter normal practice.</p>
        </div>
        <nav><Link to="/">Dashboard</Link></nav>
      </header>

      {!question ? (
        <section className="emptyCard">{status || "Review queue complete."}</section>
      ) : (
        <section className="reviewLayout">
          <article className="reviewQuestion">
            <div className="reviewMeta">
              <span>Queue {index + 1} / {questions.length}</span>
              <span>{question.year ?? "Year unknown"} {question.shift ? "• " + question.shift : ""}</span>
            </div>
            <h2>{question.question_text}</h2>
            {question.question_image_url && (
              <img className="questionImage" src={question.question_image_url} alt="Question visual" />
            )}
            <div className="optionList">
              {question.options.map((option) => (
                <div className={option.position === question.correct_option ? "option correctOption" : "option"} key={option.position}>
                  <strong>{String.fromCharCode(64 + option.position)}</strong>
                  <span>{option.text ?? "Image option"}</span>
                  {option.image_url && <img src={option.image_url} alt={"Option " + option.position} />}
                </div>
              ))}
            </div>
            {question.explanation && <div className="explanation"><strong>Explanation</strong><p>{question.explanation}</p></div>}
            <p className="sourceLine">Source: {question.source_type} • {question.source_reference ?? "No reference"}</p>
          </article>

          <aside className="reviewPanel">
            <p className="eyebrow">Verification</p>
            <button className="secondary fullWidth" onClick={getSuggestion}>Suggest topic</button>
            {suggestion && (
              <p className="suggestion">
                Suggestion: <strong>{suggestion.topic_name ?? "No confident match"}</strong>
                {suggestion.topic_name ? " • " + Math.round(suggestion.confidence * 100) + "%" : ""}
              </p>
            )}

            <label>
              Topic
              <select value={topicId ?? ""} onChange={(e) => setTopicId(e.target.value ? Number(e.target.value) : null)}>
                <option value="">Select topic</option>
                {topics.map((topic) => <option value={topic.id} key={topic.id}>{topic.name}</option>)}
              </select>
            </label>
            <label>
              Subtopic
              <input value={subtopic} onChange={(e) => setSubtopic(e.target.value)} />
            </label>
            <label>
              Pattern type
              <input value={patternType} onChange={(e) => setPatternType(e.target.value)} />
            </label>
            <label>
              Review notes
              <textarea rows={5} value={notes} onChange={(e) => setNotes(e.target.value)} />
            </label>

            <div className="reviewActions">
              <button onClick={() => save("verified")}>Verify</button>
              <button className="secondary" onClick={() => save("review_required")}>Save</button>
              <button className="danger" onClick={() => save("rejected")}>Reject</button>
            </div>
            {status && <p className="muted">{status}</p>}
          </aside>
        </section>
      )}
    </main>
  );
}
