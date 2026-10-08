import { useEffect, useState } from "react";
import type { SolvedExample } from "../api";
import SecureImage from "./SecureImage";

type Props = {
  topicId: number;
  example: SolvedExample;
  recognitionCue?: string | null;
  commonTrap?: string | null;
};

const letter = (position: number) => String.fromCharCode(64 + position);

/**
 * A deliberately unscored teacher check.
 *
 * Unlike the official exam/mock and Practice API, this shows a published
 * worked example and does not persist or award readiness/mastery. The answer
 * and explanation are revealed only after the learner commits a choice.
 */
export default function TeacherGuidedCheck({topicId, example, recognitionCue, commonTrap}: Props) {
  const [selected, setSelected] = useState<number | null>(null);
  const [checked, setChecked] = useState(false);
  const [hintShown, setHintShown] = useState(false);
  const [showSolution, setShowSolution] = useState(false);

  useEffect(() => {
    setSelected(null);
    setChecked(false);
    setHintShown(false);
    setShowSolution(false);
  }, [topicId, example.id]);

  const correct = selected === example.correct_option;
  const hasOptions = example.options.length === 4
    && new Set(example.options.map((option) => option.position)).size === 4
    && example.options.some((option) => option.position === example.correct_option);
  if (!hasOptions) return null;

  const revealSolution = () => {
    setChecked(true);
    setShowSolution(true);
  };

  return (
    <section className="teacherGuidedCheck" aria-label="Try a verified example before the walkthrough">
      <header className="teacherGuidedHeader">
        <div>
          <p className="eyebrow">Teacher-led check · No exam marks</p>
          <h3>Your turn — choose before I explain.</h3>
          <p>Recognise the pattern and decide. The correct answer stays hidden until you check.</p>
        </div>
        <span className="teacherGuidedDifficulty">
          {example.difficulty === 1 ? "Foundation" : example.difficulty === 2 ? "Application" : "Challenge"}
        </span>
      </header>
      <div className="teacherGuidedQuestion">
        <p>{example.question_text}</p>
        {example.question_image_url && (
          <SecureImage
            className="verifiedExampleImage"
            src={example.question_image_url}
            alt="Question diagram"
          />
        )}
      </div>
      <div className="teacherGuidedOptions" role="group" aria-label="Choose your answer">
        {example.options.map((option) => {
          const chosen = selected === option.position;
          const actualCorrect = checked && option.position === example.correct_option;
          return (
            <button
              type="button"
              key={option.position}
              disabled={checked}
              className={[
                "teacherGuidedOption",
                chosen ? "teacherGuidedSelected" : "",
                actualCorrect ? "teacherGuidedCorrect" : "",
                checked && chosen && !correct ? "teacherGuidedIncorrect" : "",
              ].filter(Boolean).join(" ")}
              aria-pressed={chosen}
              onClick={() => setSelected(option.position)}
            >
              <span>{letter(option.position)}</span>
              {option.text && <span>{option.text}</span>}
              {option.image_url && (
                <SecureImage
                  className="verifiedExampleOptionImage"
                  src={option.image_url}
                  alt={"Option " + letter(option.position)}
                />
              )}
              {!option.text && !option.image_url && <span>Option {letter(option.position)}</span>}
            </button>
          );
        })}
      </div>
      {!checked && (
        <div className="teacherGuidedActions">
          <button type="button" onClick={revealSolution} disabled={selected === null}>Check my answer</button>
          <button type="button" className="secondary" onClick={() => setHintShown(true)} disabled={hintShown || !recognitionCue}>
            {hintShown ? "Hint shown" : "Get a recognition hint"}
          </button>
          <button type="button" className="teacherGuidedTextAction" onClick={() => setShowSolution(true)}>
            Show walkthrough instead
          </button>
        </div>
      )}
      {hintShown && !checked && recognitionCue && (
        <p className="teacherGuidedHint" role="status"><strong>First clue:</strong> {recognitionCue}</p>
      )}
      {showSolution && !checked && (
        <div className="teacherGuidedRevealWarning">
          <p>This is a worked teaching example, not a scored attempt.</p>
          <button type="button" onClick={revealSolution}>Reveal the verified walkthrough</button>
          <button type="button" className="secondary" onClick={() => setShowSolution(false)}>I want to try first</button>
        </div>
      )}
      {checked && (
        <div className="teacherGuidedFeedback" aria-live="polite">
          <strong>{selected === null ? "Walkthrough" : correct ? "Correct — now confirm the method." : "Not yet — compare your method with this one."}</strong>
          <p><strong>Answer {letter(example.correct_option)}.</strong> {example.options.find(option => option.position === example.correct_option)?.text ?? "See the highlighted option."}</p>
          {example.explanation
            ? <p>{example.explanation}</p>
            : <p>The bank has no published written derivation for this example. Review the concept before attempting an independent question.</p>}
          {example.fast_method && (
            <details><summary>See a faster method</summary><p>{example.fast_method}</p></details>
          )}
          {!correct && selected !== null && commonTrap && (
            <p><strong>Possible trap to check:</strong> {commonTrap}</p>
          )}
          <div className="teacherGuidedActions">
            <button type="button" onClick={() => {
              setSelected(null);
              setChecked(false);
              setHintShown(false);
              setShowSolution(false);
            }}>Try this example again</button>
            <a className="primaryLink" href={"/practice?topic_id=" + topicId + "&mode=path&limit=10"}>
              Try new independent questions →
            </a>
          </div>
          <small className="teacherGuidedCaveat">
            This demonstration does not change your mastery score. The Learning Path measures independent answers to new questions.
          </small>
        </div>
      )}
    </section>
  );
}
