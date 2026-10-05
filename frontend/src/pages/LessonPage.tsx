import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Lesson, fetchTopicLessons } from "../api";

export default function LessonPage() {
  const { topicId } = useParams();
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!topicId) return;
    fetchTopicLessons(Number(topicId))
      .then(setLessons)
      .catch(() => setError("Lesson is not ready for this topic yet."));
  }, [topicId]);

  return (
    <main className="lessonShell">
      <header className="lessonTopbar">
        <Link to="/learn">← All topics</Link>
        <Link to="/">Dashboard</Link>
      </header>

      {error && <section className="emptyCard">{error}</section>}

      {!error && lessons.length === 0 && (
        <section className="emptyCard">This topic is queued for lesson creation.</section>
      )}

      {lessons.map((lesson) => (
        <article className="lessonArticle" key={lesson.id}>
          <p className="eyebrow">{lesson.estimated_minutes} min lesson</p>
          <h1>{lesson.title}</h1>
          <p className="lessonIntro">{lesson.intro}</p>

          <section className="lessonBlock">
            <span>Core concept</span>
            <p>{lesson.concept}</p>
          </section>

          {lesson.shortcut && (
            <section className="lessonBlock emphasis">
              <span>Fast method</span>
              <p>{lesson.shortcut}</p>
            </section>
          )}

          {lesson.worked_example && (
            <section className="lessonBlock">
              <span>Worked example</span>
              <p>{lesson.worked_example}</p>
            </section>
          )}

          {lesson.memory_rule && (
            <section className="memoryRule">
              <span>Remember</span>
              <strong>{lesson.memory_rule}</strong>
            </section>
          )}

          {lesson.common_traps && (
            <section className="lessonBlock warningBlock">
              <span>Common trap</span>
              <p>{lesson.common_traps}</p>
            </section>
          )}

          <div className="lessonActions">
            <Link className="primaryLink" to={"/practice?topic_id=" + lesson.topic_id}>Start guided practice</Link>
            <Link to="/learn">Choose another topic</Link>
          </div>
        </article>
      ))}
    </main>
  );
}
