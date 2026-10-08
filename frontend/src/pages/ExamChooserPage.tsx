import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ExamCatalogEntry, fetchExamCatalog } from "../api";

const families = [
  {slug: "cgl", label: "SSC CGL", description: "Combined Graduate Level"},
  {slug: "je", label: "SSC JE", description: "Junior Engineer · Telecom track"},
] as const;

function ExamCard({exam}: {exam: ExamCatalogEntry}) {
  const ready = exam.status === "ready";
  const examLabel = exam.family === "cgl" ? "Tier" : "Paper";
  return (
    <article className="examChooserCard">
      <div className="examChooserCardTop">
        <span className="examChooserStage">{examLabel} {exam.stage.split("-")[1]}</span>
        <span className={ready ? "examChooserStatus examChooserReady" : "examChooserStatus"}>
          {ready ? "Ready to study" : "In development"}
        </span>
      </div>
      <h3>{exam.name}</h3>
      <p>{exam.subtitle}</p>
      <p className="examChooserMeta">
        {exam.total_questions} MCQs · {exam.duration_minutes} min
        {exam.extra_assessments.length > 0 && " · Separate typing assessment"}
      </p>
      <div className="examChooserActions">
        {ready ? (
          <Link className="examChooserPrimary" to="/">Continue preparation →</Link>
        ) : (
          <span className="examChooserDisabled" aria-label={exam.name + " not available yet"}>
            Course not published
          </span>
        )}
        <a href={exam.notice_url} target="_blank" rel="noopener noreferrer" className="examChooserNotice">
          Official notification ↗
        </a>
      </div>
    </article>
  );
}

export default function ExamChooserPage() {
  const [exams, setExams] = useState<ExamCatalogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchExamCatalog()
      .then((items) => { if (!cancelled) setExams(items); })
      .catch(() => { if (!cancelled) setError("Could not load the exam catalog. Your current CGL course is unchanged."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  return (
    <main className="examChooserShell">
      <header className="examChooserIntro">
        <p className="eyebrow">Your exam workspace</p>
        <h1>Choose what you're preparing for.</h1>
        <p>
          One preparation account for multiple SSC examinations. Each stage will
          have its own syllabus, tests and progress once its course is verified.
        </p>
        <Link className="examChooserBack" to="/">← Back to current study dashboard</Link>
      </header>
      {loading && <p className="examChooserFeedback" role="status">Loading available examinations…</p>}
      {!loading && error && <p className="examChooserFeedback" role="alert">{error}</p>}
      {!loading && !error && families.map((family) => {
        const items = exams.filter((exam) => exam.family === family.slug);
        return (
          <section className="examChooserFamily" key={family.slug} aria-label={family.label}>
            <div className="examChooserFamilyHeading">
              <h2>{family.label}</h2>
              <p>{family.description}</p>
            </div>
            <div className="examChooserGrid">
              {items.map((exam) => <ExamCard exam={exam} key={exam.slug} />)}
            </div>
          </section>
        );
      })}
      <p className="examChooserFootnote">
        Unpublished stages cannot be selected yet. Your existing SSC CGL Tier I
        lessons, mocks, revision and history stay exactly as they are. JE technical
        course content will be added only after it passes syllabus and question audits.
      </p>
    </main>
  );
}
