import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  BookmarkItem,
  FlashcardItem,
  RevisionItem,
  fetchBookmarks,
  fetchDueFlashcards,
  fetchRevisionQueue,
  reviewFlashcard,
  reviewRevisionItem,
} from "../api";
import { getToken } from "../auth";
import SecureImage from "../components/SecureImage";

type Tab = "due" | "flashcards" | "bookmarks";

const reasonOptions = [
  ["", "All due"],
  ["wrong", "Wrong"],
  ["slow", "Slow"],
  ["guess", "Guessed"],
  ["calculation", "Calculation"],
  ["misread", "Misread"],
  ["time_pressure", "Time pressure"],
];

export default function RevisionPage() {
  const [tab, setTab] = useState<Tab>("due");
  const [reason, setReason] = useState("");
  const [items, setItems] = useState<RevisionItem[]>([]);
  const [flashcards, setFlashcards] = useState<FlashcardItem[]>([]);
  const [bookmarks, setBookmarks] = useState<BookmarkItem[]>([]);
  const [showAnswer, setShowAnswer] = useState(false);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    if (!getToken()) {
      navigate("/login");
      return;
    }
    void load();
  }, [navigate, tab, reason]);

  async function load() {
    setError("");
    setIndex(0);
    setShowAnswer(false);
    try {
      if (tab === "due") setItems(await fetchRevisionQueue(reason || undefined));
      if (tab === "flashcards") setFlashcards(await fetchDueFlashcards());
      if (tab === "bookmarks") setBookmarks(await fetchBookmarks());
    } catch {
      setError("Could not load revision data.");
    }
  }

  const dueItem = useMemo(() => items[index] ?? null, [items, index]);
  const card = useMemo(() => flashcards[index] ?? null, [flashcards, index]);
  const bookmark = useMemo(() => bookmarks[index] ?? null, [bookmarks, index]);

  async function gradeRevision(success: boolean) {
    if (!dueItem) return;
    await reviewRevisionItem(dueItem.id, success);
    const next = items.filter((item) => item.id !== dueItem.id);
    setItems(next);
    setIndex((value) => Math.min(value, Math.max(next.length - 1, 0)));
    setShowAnswer(false);
  }

  async function gradeCard(success: boolean) {
    if (!card) return;
    await reviewFlashcard(card.id, success);
    const next = flashcards.filter((item) => item.id !== card.id);
    setFlashcards(next);
    setIndex((value) => Math.min(value, Math.max(next.length - 1, 0)));
    setShowAnswer(false);
  }

  function nextBookmark() {
    if (!bookmarks.length) return;
    setIndex((value) => (value + 1) % bookmarks.length);
    setShowAnswer(false);
  }

  return (
    <main className="revisionShell">
      <header className="topbar">
        <div>
          <p className="brand">Revision Lab</p>
          <p className="muted">Wrong, slow, guessed and memory items return when they are due.</p>
        </div>
        <nav>
          <Link to="/analytics">Analytics</Link>
          <Link to="/">Dashboard</Link>
        </nav>
      </header>

      <div className="revisionTabs">
        <button className={tab === "due" ? "activeRevisionTab" : ""} onClick={() => setTab("due")}>Due questions</button>
        <button className={tab === "flashcards" ? "activeRevisionTab" : ""} onClick={() => setTab("flashcards")}>Flashcards</button>
        <button className={tab === "bookmarks" ? "activeRevisionTab" : ""} onClick={() => setTab("bookmarks")}>Bookmarks</button>
      </div>

      {tab === "due" && (
        <div className="revisionFilters">
          {reasonOptions.map(([value, label]) => (
            <button
              key={value || "all"}
              className={reason === value ? "activeFilter" : ""}
              onClick={() => setReason(value)}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {error && <section className="emptyCard">{error}</section>}

      {!error && tab === "due" && !dueItem && (
        <section className="revisionEmpty">
          <p className="eyebrow">Queue clear</p>
          <h1>No revision due right now.</h1>
          <p>Wrong, slow and low-confidence questions will automatically return here.</p>
          <Link className="primaryLink" to="/practice">Go to practice</Link>
        </section>
      )}

      {!error && tab === "due" && dueItem && (
        <section className="revisionCard">
          <div className="revisionMeta">
            <span>{dueItem.reason.replaceAll("_", " ")}</span>
            <span>{index + 1} / {items.length}</span>
          </div>
          <h1>{dueItem.question.question_text}</h1>
          {dueItem.question.question_image_url && (
            <SecureImage className="practiceQuestionImage" src={dueItem.question.question_image_url} alt="Question visual" />
          )}
          <div className="revisionOptions">
            {dueItem.question.options.map((option) => (
              <div key={option.position} className={showAnswer && option.position === dueItem.question.correct_option ? "revisionOption revisionAnswer" : "revisionOption"}>
                <strong>{String.fromCharCode(64 + option.position)}</strong>
                <span>{option.text ?? "Image option"}</span>
                {option.image_url && <SecureImage src={option.image_url} alt={"Option " + option.position} />}
              </div>
            ))}
          </div>

          {!showAnswer ? (
            <button className="revisionReveal" onClick={() => setShowAnswer(true)}>Reveal answer</button>
          ) : (
            <>
              <div className="revisionExplanation">
                {dueItem.question.explanation && <p>{dueItem.question.explanation}</p>}
                {dueItem.question.fast_method && <p><strong>Fast method:</strong> {dueItem.question.fast_method}</p>}
              </div>
              <div className="revisionGradeRow">
                <button className="danger" onClick={() => void gradeRevision(false)}>Again tomorrow</button>
                <button onClick={() => void gradeRevision(true)}>I remembered</button>
              </div>
            </>
          )}
        </section>
      )}

      {!error && tab === "flashcards" && !card && (
        <section className="revisionEmpty">
          <p className="eyebrow">Flashcards clear</p>
          <h1>No cards due right now.</h1>
          <p>Reviewed cards return on a spaced schedule.</p>
        </section>
      )}

      {!error && tab === "flashcards" && card && (
        <section className="flashcardShell">
          <div className="revisionMeta">
            <span>{card.card_type}</span>
            <span>{index + 1} / {flashcards.length}</span>
          </div>
          <div className="flashcardFace">
            <p className="eyebrow">Recall</p>
            <h1>{card.front}</h1>
            {showAnswer && (
              <div className="flashcardBack">
                <strong>{card.back}</strong>
                {card.related_fact && <p>{card.related_fact}</p>}
              </div>
            )}
          </div>
          {!showAnswer ? (
            <button className="revisionReveal" onClick={() => setShowAnswer(true)}>Show answer</button>
          ) : (
            <div className="revisionGradeRow">
              <button className="danger" onClick={() => void gradeCard(false)}>Forgot</button>
              <button onClick={() => void gradeCard(true)}>Remembered</button>
            </div>
          )}
        </section>
      )}

      {!error && tab === "bookmarks" && !bookmark && (
        <section className="revisionEmpty">
          <p className="eyebrow">Bookmarks</p>
          <h1>No bookmarked questions yet.</h1>
          <p>Bookmark useful questions during practice and review them here.</p>
        </section>
      )}

      {!error && tab === "bookmarks" && bookmark && (
        <section className="revisionCard">
          <div className="revisionMeta">
            <span>Bookmarked</span>
            <span>{index + 1} / {bookmarks.length}</span>
          </div>
          <h1>{bookmark.question.question_text}</h1>
          <div className="revisionOptions">
            {bookmark.question.options.map((option) => (
              <div key={option.position} className={showAnswer && option.position === bookmark.question.correct_option ? "revisionOption revisionAnswer" : "revisionOption"}>
                <strong>{String.fromCharCode(64 + option.position)}</strong>
                <span>{option.text ?? "Image option"}</span>
              </div>
            ))}
          </div>
          <div className="bookmarkActions">
            <button className="secondary" onClick={() => setShowAnswer((value) => !value)}>{showAnswer ? "Hide answer" : "Show answer"}</button>
            <button onClick={nextBookmark}>Next bookmark</button>
          </div>
          {showAnswer && bookmark.question.explanation && <p className="revisionExplanation">{bookmark.question.explanation}</p>}
        </section>
      )}
    </main>
  );
}
