import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { TopicPackage, fetchTopicPackage } from "../api";
import SpeakButton from "../components/SpeakButton";
import TeacherCoach from "../components/TeacherCoach";

type TeachingBlock = {
  key: string;
  blockType: string;
  title: string;
  body: string;
  difficulty: number | null;
};

type TeachingStage = {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
  blockTypes: string[];
  blocks: TeachingBlock[];
};

const stageBlueprint = [
  {
    id: "understand",
    eyebrow: "Step 1",
    title: "Understand the idea",
    description: "Start with the minimum concept you need. Do not memorise a shortcut before the rule makes sense.",
    blockTypes: ["prerequisite", "concept"],
  },
  {
    id: "recognise",
    eyebrow: "Step 2",
    title: "Recognise the question",
    description: "Learn the cues that tell you which rule or pattern SSC is testing before you touch the options.",
    blockTypes: ["recognition"],
  },
  {
    id: "solve",
    eyebrow: "Step 3",
    title: "Solve it safely",
    description: "Use the standard method first. This is the method you should trust when the shortcut is not obvious.",
    blockTypes: ["formula", "method"],
  },
  {
    id: "speed",
    eyebrow: "Step 4",
    title: "Make it exam-fast",
    description: "Now compress the safe method into the smallest reliable shortcut or elimination rule.",
    blockTypes: ["shortcut"],
  },
  {
    id: "examples",
    eyebrow: "Step 5",
    title: "Watch the teacher solve",
    description: "See the same idea at easy, exam and harder variations. Notice what changes and what stays constant.",
    blockTypes: ["example_easy", "example_exam", "example_hard"],
  },
  {
    id: "traps",
    eyebrow: "Step 6",
    title: "Avoid the marks trap",
    description: "These are the mistakes that make a familiar question look harder or cost a negative mark.",
    blockTypes: ["trap"],
  },
  {
    id: "recall",
    eyebrow: "Step 7",
    title: "Lock it into memory",
    description: "Finish with a short recall rule, revision cue and practice target before moving to questions.",
    blockTypes: ["memory", "recall", "revision", "practice"],
  },
] as const;

const blockLabel: Record<string, string> = {
  prerequisite: "Before you start",
  concept: "Core concept",
  formula: "Formula / rule",
  recognition: "Recognition cue",
  method: "Standard method",
  shortcut: "Fast method",
  example_easy: "Easy walkthrough",
  example_exam: "SSC-level walkthrough",
  example_hard: "Hard variation",
  trap: "Common trap",
  recall: "Quick recall",
  memory: "Memory anchor",
  revision: "Revision rule",
  practice: "Practice target",
};

function fallbackBlocks(pkg: TopicPackage): TeachingBlock[] {
  return pkg.lessons.flatMap((lesson) => {
    const blocks: TeachingBlock[] = [
      {
        key: `${lesson.id}-concept`,
        blockType: "concept",
        title: "Core concept",
        body: lesson.concept,
        difficulty: null,
      },
    ];
    if (lesson.shortcut) {
      blocks.push({
        key: `${lesson.id}-shortcut`,
        blockType: "shortcut",
        title: "Fast method",
        body: lesson.shortcut,
        difficulty: null,
      });
    }
    if (lesson.worked_example) {
      blocks.push({
        key: `${lesson.id}-example`,
        blockType: "example_exam",
        title: "Worked example",
        body: lesson.worked_example,
        difficulty: 2,
      });
    }
    if (lesson.common_traps) {
      blocks.push({
        key: `${lesson.id}-trap`,
        blockType: "trap",
        title: "Common trap",
        body: lesson.common_traps,
        difficulty: null,
      });
    }
    if (lesson.memory_rule) {
      blocks.push({
        key: `${lesson.id}-memory`,
        blockType: "memory",
        title: "Remember",
        body: lesson.memory_rule,
        difficulty: null,
      });
    }
    return blocks;
  });
}

export default function LessonPage() {
  const { topicId } = useParams();
  const navigate = useNavigate();
  const [pkg, setPkg] = useState<TopicPackage | null>(null);
  const [error, setError] = useState("");
  const [activeStageIndex, setActiveStageIndex] = useState(0);
  const [activePatternIndex, setActivePatternIndex] = useState(0);

  useEffect(() => {
    if (!topicId) return;
    let cancelled = false;
    setError("");
    setPkg(null);
    fetchTopicPackage(Number(topicId))
      .then((data) => {
        if (cancelled) return;
        setPkg(data);
        setActiveStageIndex(0);
        setActivePatternIndex(0);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load this topic.");
      });
    return () => {
      cancelled = true;
    };
  }, [topicId]);

  const allBlocks = useMemo<TeachingBlock[]>(() => {
    if (!pkg) return [];
    const seeded = pkg.lessons.flatMap((lesson) =>
      lesson.blocks.map((block) => ({
        key: String(block.id),
        blockType: block.block_type,
        title: block.title,
        body: block.body,
        difficulty: block.difficulty,
      }))
    );
    return seeded.length ? seeded : fallbackBlocks(pkg);
  }, [pkg]);

  const stages = useMemo<TeachingStage[]>(() => {
    return stageBlueprint
      .map((blueprint) => ({
        ...blueprint,
        blockTypes: [...blueprint.blockTypes],
        blocks: allBlocks.filter((block) => blueprint.blockTypes.includes(block.blockType as never)),
      }))
      .filter((stage) => stage.blocks.length > 0);
  }, [allBlocks]);

  const activeStage = stages[activeStageIndex] ?? stages[0] ?? null;
  const activePattern = pkg?.archetypes[activePatternIndex] ?? null;
  const estimatedMinutes = pkg?.lessons.reduce((sum, lesson) => sum + lesson.estimated_minutes, 0) ?? 0;
  const progress = stages.length ? Math.round(((activeStageIndex + 1) / stages.length) * 100) : 0;

  const examples = useMemo(
    () => allBlocks
      .filter((block) => block.blockType.startsWith("example"))
      .map((block) => block.body),
    [allBlocks],
  );

  const shortcuts = useMemo(
    () => allBlocks.filter((block) => block.blockType === "shortcut").map((block) => block.body),
    [allBlocks],
  );

  const traps = useMemo(
    () => allBlocks.filter((block) => block.blockType === "trap").map((block) => block.body),
    [allBlocks],
  );

  const methods = useMemo(
    () => allBlocks
      .filter((block) => block.blockType === "method" || block.blockType === "formula")
      .map((block) => block.body),
    [allBlocks],
  );

  const speakText = useMemo(() => {
    if (!pkg) return "";
    return [
      pkg.topic.name,
      ...stages.flatMap((stage) => [
        stage.title,
        ...stage.blocks.flatMap((block) => [block.title, block.body]),
      ]),
    ].filter(Boolean).join(". ");
  }, [pkg, stages]);

  const teacherLead = activeStage
    ? `We are on “${activeStage.title}”. ${activeStage.description} ${activeStage.blocks[0]?.body ?? ""}`
    : null;

  const teacherHints = activeStage?.blocks.map((block) => block.body).slice(0, 3) ?? [];

  return (
    <main className="lessonShell teacherLessonShell">
      <header className="lessonTopbar">
        <div className="lessonNavGroup">
          <button className="textBackButton" onClick={() => navigate(-1)}>← Back</button>
          <span>/</span>
          <Link to="/learn">Learn</Link>
          {pkg && (
            <>
              <span>/</span>
              <span>{pkg.subject.name}</span>
              <span>/</span>
              <strong>{pkg.topic.name}</strong>
            </>
          )}
        </div>
        <nav>
          <Link to="/planner">Today</Link>
          <Link to="/revision">Revision</Link>
          <Link to="/">Dashboard</Link>
        </nav>
      </header>

      {error && <section className="emptyCard">{error}</section>}

      {!error && !pkg && (
        <section className="lessonLoadingSkeleton" aria-label="Loading lesson">
          <div className="skeletonBlock skeletonLine short" />
          <div className="skeletonBlock lessonHeroSkeletonTitle" />
          <div className="skeletonBlock skeletonLine" />
          <div className="lessonClassroomSkeleton">
            <div className="skeletonBlock lessonRailSkeleton" />
            <div className="skeletonBlock lessonBoardSkeleton" />
          </div>
        </section>
      )}

      {pkg && activeStage && (
        <>
          <section className="topicLessonHero teacherLessonHero">
            <div>
              <p className="eyebrow">SSC CGL • {pkg.subject.name} • {pkg.topic.priority >= 5 ? "High priority" : "Topic lesson"}</p>
              <h1>{pkg.topic.name}</h1>
              <p>
                By the end of this lesson, you should be able to recognise the pattern, apply a safe method,
                use the faster SSC approach and avoid the common trap before you practise independently.
              </p>
              <div className="lessonHeroMeta">
                <span>{estimatedMinutes} min guided lesson</span>
                <span>{stages.length} teaching steps</span>
                <span>{pkg.archetypes.length} question patterns</span>
              </div>
            </div>
            <div className="topicLessonActions">
              <SpeakButton label="Read lesson aloud" text={speakText} />
              <Link className="primaryLink" to={"/practice?topic_id=" + pkg.topic.id + "&mode=guided&limit=10"}>
                Start guided practice
              </Link>
              <Link className="secondaryLink" to={"/practice?topic_id=" + pkg.topic.id + "&mode=guided&limit=3"}>
                3-question quick check
              </Link>
            </div>
          </section>

          <section className="lessonProgressHeader">
            <div>
              <span>Lesson progress</span>
              <strong>{progress}%</strong>
            </div>
            <div className="lessonProgressTrack">
              <span style={{width: progress + "%"}} />
            </div>
          </section>

          <section className="teacherClassroom">
            <aside className="lessonStageRail">
              <p className="eyebrow">Class plan</p>
              {stages.map((stage, index) => (
                <button
                  key={stage.id}
                  className={index === activeStageIndex ? "lessonStageButton activeLessonStage" : "lessonStageButton"}
                  onClick={() => setActiveStageIndex(index)}
                >
                  <span>{index + 1}</span>
                  <div>
                    <small>{stage.eyebrow}</small>
                    <strong>{stage.title}</strong>
                  </div>
                  {index < activeStageIndex && <b>✓</b>}
                </button>
              ))}
              <div className="lessonRailActions">
                <Link to={"/practice?topic_id=" + pkg.topic.id + "&mode=guided&limit=3"}>Quick check →</Link>
                <Link to={"/mocks?topic_id=" + pkg.topic.id}>Topic test →</Link>
              </div>
            </aside>

            <div className="teacherBoard">
              <header className="teacherBoardHeader">
                <div>
                  <p className="eyebrow">{activeStage.eyebrow} of {stages.length}</p>
                  <h2>{activeStage.title}</h2>
                  <p>{activeStage.description}</p>
                </div>
                <span className="teacherBoardBadge">{activeStage.blocks.length} key point{activeStage.blocks.length === 1 ? "" : "s"}</span>
              </header>

              <div className="teacherBlockList">
                {activeStage.blocks.map((block, index) => {
                  const example = block.blockType.startsWith("example");
                  const trap = block.blockType === "trap";
                  const shortcut = block.blockType === "shortcut";
                  return (
                    <article
                      className={[
                        "teacherBlock",
                        example ? "teacherExampleBlock" : "",
                        trap ? "teacherTrapBlock" : "",
                        shortcut ? "teacherShortcutBlock" : "",
                      ].filter(Boolean).join(" ")}
                      key={block.key}
                    >
                      <div className="teacherBlockNumber">{index + 1}</div>
                      <div>
                        <span className="teacherBlockLabel">{blockLabel[block.blockType] ?? block.title}</span>
                        <h3>{block.title}</h3>
                        <p>{block.body}</p>
                        {example && (
                          <small className="teacherPrompt">Teacher cue: identify the rule first, then compare the steps with the answer.</small>
                        )}
                      </div>
                    </article>
                  );
                })}
              </div>

              <TeacherCoach
                title={pkg.topic.name}
                context={activeStage.blocks.map((block) => block.body).join(". ")}
                explanation={activeStage.blocks[0]?.body}
                fastMethod={shortcuts[0]}
                commonTrap={traps[0]}
                standardMethod={methods[0] ?? pkg.archetypes[0]?.canonical_method}
                examples={examples}
                defaultOpen
                lead={teacherLead}
                hintSteps={teacherHints}
              />

              <footer className="teacherBoardNav">
                <button
                  className="secondary"
                  disabled={activeStageIndex === 0}
                  onClick={() => setActiveStageIndex((value) => Math.max(0, value - 1))}
                >
                  ← Previous step
                </button>
                {activeStageIndex < stages.length - 1 ? (
                  <button onClick={() => setActiveStageIndex((value) => Math.min(stages.length - 1, value + 1))}>
                    Next teaching step →
                  </button>
                ) : (
                  <Link className="primaryLink" to={"/practice?topic_id=" + pkg.topic.id + "&mode=guided&limit=3"}>
                    Check understanding →
                  </Link>
                )}
              </footer>
            </div>
          </section>

          <section className="patternStudio">
            <div className="sectionHeading">
              <div>
                <p className="eyebrow">Pattern studio</p>
                <h2>See how SSC changes the surface.</h2>
              </div>
              <p>Choose one pattern at a time. Recognition first, method second, shortcut last.</p>
            </div>

            {pkg.archetypes.length === 0 ? (
              <div className="emptyCard">
                Pattern library for this topic is being expanded. The guided lesson and practice bank are available.
              </div>
            ) : (
              <div className="patternStudioLayout">
                <div className="patternSelector" role="tablist" aria-label="Question patterns">
                  {pkg.archetypes.map((item, index) => (
                    <button
                      key={item.id}
                      className={index === activePatternIndex ? "patternSelectorButton activePatternSelector" : "patternSelectorButton"}
                      onClick={() => setActivePatternIndex(index)}
                    >
                      <span>{index + 1}</span>
                      <div>
                        <strong>{item.name}</strong>
                        <small>{item.expected_time_seconds}s target</small>
                      </div>
                    </button>
                  ))}
                </div>

                {activePattern && (
                  <article className="patternTeachingCard">
                    <div className="patternTeachingHead">
                      <div>
                        <p className="eyebrow">Pattern {activePatternIndex + 1} of {pkg.archetypes.length}</p>
                        <h3>{activePattern.name}</h3>
                      </div>
                      <span>{activePattern.expected_time_seconds}s target</span>
                    </div>
                    <section>
                      <span>What skill is this?</span>
                      <p>{activePattern.skill}</p>
                    </section>
                    <section>
                      <span>How do I recognise it?</span>
                      <p>{activePattern.recognition_cues}</p>
                    </section>
                    <section className="patternMethodPanel">
                      <span>Safe method</span>
                      <p>{activePattern.canonical_method}</p>
                    </section>
                    {activePattern.shortcut_method && (
                      <section className="patternShortcutPanel">
                        <span>SSC-fast method</span>
                        <p>{activePattern.shortcut_method}</p>
                      </section>
                    )}
                    {activePattern.common_trap && (
                      <section className="patternTrapPanel">
                        <span>Do not lose marks here</span>
                        <p>{activePattern.common_trap}</p>
                      </section>
                    )}
                    <div className="patternLevelGrid">
                      {activePattern.easy_rule && <div><span>Easy</span><p>{activePattern.easy_rule}</p></div>}
                      {activePattern.medium_rule && <div><span>Medium</span><p>{activePattern.medium_rule}</p></div>}
                      {activePattern.hard_rule && <div><span>Hard</span><p>{activePattern.hard_rule}</p></div>}
                    </div>
                    <Link className="primaryLink" to={"/practice?topic_id=" + pkg.topic.id + "&mode=guided&limit=10"}>
                      Practise this topic →
                    </Link>
                  </article>
                )}
              </div>
            )}
          </section>

          <section className="lessonFinishCard">
            <div>
              <p className="eyebrow">Lesson complete</p>
              <h2>Do not stop at reading.</h2>
              <p>Use a 3-question check to prove recall, then move into guided practice. Reading alone does not raise mastery.</p>
            </div>
            <div>
              <Link className="secondaryLink" to="/learn">Choose another topic</Link>
              <Link className="secondaryLink" to={"/mocks?topic_id=" + pkg.topic.id}>Topic test</Link>
              <Link className="primaryLink" to={"/practice?topic_id=" + pkg.topic.id + "&mode=guided&limit=3"}>
                Take quick check →
              </Link>
            </div>
          </section>
        </>
      )}
    </main>
  );
}
