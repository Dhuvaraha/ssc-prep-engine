import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { TopicPackage, fetchTopicPackage } from "../api";
import SpeakButton from "../components/SpeakButton";
import TeacherCoach from "../components/TeacherCoach";

const blockLabel: Record<string, string> = {
  prerequisite: "Before you start",
  concept: "Core concept",
  formula: "Formula / rule",
  recognition: "How to recognise it",
  method: "Standard method",
  shortcut: "Fast method",
  example_easy: "Easy example",
  example_exam: "Exam-level example",
  example_hard: "Hard variation",
  trap: "Common trap",
  recall: "Quick recall",
  memory: "Memory anchor",
  revision: "Revision rule",
  practice: "Practice target",
};

export default function LessonPage() {
  const { topicId } = useParams();
  const navigate = useNavigate();
  const [pkg, setPkg] = useState<TopicPackage | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!topicId) return;
    fetchTopicPackage(Number(topicId))
      .then(setPkg)
      .catch(() => setError("Could not load this topic."));
  }, [topicId]);

  const speakText = useMemo(() => {
    if (!pkg) return "";
    return pkg.lessons
      .flatMap((lesson) => [
        lesson.title,
        lesson.intro,
        ...(lesson.blocks.length
          ? lesson.blocks.flatMap((block) => [block.title, block.body])
          : [
              lesson.concept,
              lesson.shortcut ?? "",
              lesson.worked_example ?? "",
              lesson.memory_rule ?? "",
              lesson.common_traps ?? "",
            ]),
      ])
      .filter(Boolean)
      .join(". ");
  }, [pkg]);

  return (
    <main className="lessonShell">
      <header className="lessonTopbar">
        <div className="lessonNavGroup">
          <button className="textBackButton" onClick={() => navigate(-1)}>← Back</button>
          <span>/</span>
          <Link to="/learn">Learn</Link>
          {pkg && <><span>/</span><strong>{pkg.topic.name}</strong></>}
        </div>
        <nav>
          <Link to="/planner">Today</Link>
          <Link to="/revision">Revision</Link>
          <Link to="/">Dashboard</Link>
        </nav>
      </header>

      {error && <section className="emptyCard">{error}</section>}
      {!error && !pkg && <section className="emptyCard">Loading lesson...</section>}

      {pkg && (
        <>
          <section className="topicLessonHero">
            <div>
              <p className="eyebrow">SSC CGL • {pkg.topic.priority >= 5 ? "High priority" : "Topic lesson"}</p>
              <h1>{pkg.topic.name}</h1>
              <p>
                Learn the pattern, see the method, compare the shortcut and then solve the same skill at multiple difficulty levels.
              </p>
            </div>
            <div className="topicLessonActions">
              <SpeakButton label="Read lesson" text={speakText} />
              <Link className="secondaryLink" to={"/practice?topic_id=" + pkg.topic.id + "&mode=guided&limit=3"}>
                3-question quick check
              </Link>
              <Link className="primaryLink" to={"/practice?topic_id=" + pkg.topic.id + "&mode=guided&limit=10"}>
                Start guided practice
              </Link>
            </div>
          </section>

          {pkg.lessons.map((lesson) => (
            <article className="lessonArticle" key={lesson.id}>
              <div className="lessonArticleHead">
                <div>
                  <p className="eyebrow">{lesson.estimated_minutes} min lesson</p>
                  <h2>{lesson.title}</h2>
                  <p className="lessonIntro">{lesson.intro}</p>
                </div>
              </div>

              {lesson.blocks.length > 0 ? (
                <div className="lessonBlockStack">
                  {lesson.blocks.map((block) => (
                    <section
                      className={
                        block.block_type === "shortcut"
                          ? "lessonBlock emphasis"
                          : block.block_type === "trap"
                            ? "lessonBlock warningBlock"
                            : "lessonBlock"
                      }
                      key={block.id}
                    >
                      <span>{blockLabel[block.block_type] ?? block.title}</span>
                      <h3>{block.title}</h3>
                      <p>{block.body}</p>
                    </section>
                  ))}
                </div>
              ) : (
                <div className="lessonBlockStack">
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
                </div>
              )}
            </article>
          ))}

          <TeacherCoach
            title={pkg.topic.name}
            context={pkg.lessons.map((lesson) => lesson.concept).join(". ")}
            explanation={pkg.lessons[0]?.worked_example ?? pkg.lessons[0]?.concept}
            fastMethod={pkg.lessons[0]?.shortcut}
            commonTrap={pkg.lessons[0]?.common_traps}
          />

          <section className="archetypeSection">
            <div className="sectionHeading">
              <div>
                <p className="eyebrow">Question patterns</p>
                <h2>Know what SSC can change.</h2>
              </div>
              <p>Same concept, different surface form.</p>
            </div>

            {pkg.archetypes.length === 0 ? (
              <div className="emptyCard">
                Pattern library for this topic is being expanded. The lesson and practice bank are still available.
              </div>
            ) : (
              <div className="archetypeGrid">
                {pkg.archetypes.map((item) => (
                  <article className="archetypeCard" key={item.id}>
                    <div className="archetypeMeta">
                      <span>{item.expected_time_seconds}s target</span>
                    </div>
                    <h3>{item.name}</h3>
                    <p><strong>Skill:</strong> {item.skill}</p>
                    <p><strong>Recognition:</strong> {item.recognition_cues}</p>
                    <div className="archetypeMethod">
                      <span>Method</span>
                      <p>{item.canonical_method}</p>
                    </div>
                    {item.shortcut_method && (
                      <div className="archetypeShortcut">
                        <span>Shortcut</span>
                        <p>{item.shortcut_method}</p>
                      </div>
                    )}
                    {item.common_trap && (
                      <p className="archetypeTrap"><strong>Trap:</strong> {item.common_trap}</p>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="lessonBottomActions">
            <button className="secondary" onClick={() => navigate(-1)}>← Back</button>
            <Link to="/learn">Choose another topic</Link>
            <Link className="primaryLink" to={"/practice?topic_id=" + pkg.topic.id + "&mode=guided&limit=10"}>
              Practice this topic →
            </Link>
          </section>
        </>
      )}
    </main>
  );
}
