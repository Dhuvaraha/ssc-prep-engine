import { useRef, useState } from "react";
import { EditorialRevision, fetchEditorialRevision, publishEditorialRevision, reviewEditorialRevision } from "../api";
import SecureImage from "./SecureImage";

const checks = [
  ["answer_verified", "I independently checked the answer"],
  ["all_options_checked", "I checked every option"],
  ["instruction_reviewed", "I checked the wording and explanation"],
  ["visual_reviewed", "I checked every visual, or confirmed there are none"],
] as const;

export default function EditorialRevisionPanel() {
  const [id, setId] = useState(() => new URLSearchParams(window.location.search).get("candidate") ?? "");
  const [revision, setRevision] = useState<EditorialRevision | null>(null);
  const [attestations, setAttestations] = useState<Record<string, boolean>>({});
  const [reference, setReference] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);
  async function run(action: "load" | "review" | "publish") {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setMessage("");
    try {
      const target = action === "load" ? id.trim() : revision?.candidate_id;
      if (!target) throw new Error("Enter a candidate reference");
      if (action === "load") {
        setRevision(null);
        setAttestations({});
        setReference("");
      }
      if (action === "review") await reviewEditorialRevision(target, {...attestations, reference});
      if (action === "publish") await publishEditorialRevision(target);
      setRevision(await fetchEditorialRevision(target));
      setMessage(action === "review" ? "Independent review recorded. Publication is separate." : action === "publish" ? "Reviewed correction published." : "Candidate loaded.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Revision request failed");
    } finally {
      setBusy(false);
      inFlight.current = false;
    }
  }
  return <section className="emptyCard" aria-label="Independent revision review">
    <h2>Independent revision review</h2>
    <p>Open the reference from the author. Review the complete before/after content before recording your checks.</p>
    <label>Candidate reference<input value={id} disabled={busy} onChange={event => { setId(event.target.value); setRevision(null); setAttestations({}); setReference(""); }} /></label>
    <button disabled={busy || !id.trim()} onClick={() => void run("load")}>Open candidate</button>
    {revision && <>
      <p>Loaded candidate: {revision.candidate_id}</p>
      <p>Reason: {revision.reason}</p>
      <p>{revision.published ? "Published" : revision.review_status === "reviewed" ? "Reviewed; awaiting publication" : "Draft; independent review required"}</p>
      <div style={{overflowX: "auto"}}><table>
        <caption>Complete question comparison</caption>
        <thead><tr><th scope="col">Field</th><th scope="col">Before</th><th scope="col">After</th></tr></thead>
        <tbody>{Object.keys(revision.before.question).map(field => <tr key={field}>
          <th scope="row">{field.replaceAll("_", " ")}</th>
          <td>{String(revision.before.question[field] ?? "—")}</td>
          <td>{String(revision.after.question[field] ?? "—")}</td>
        </tr>)}</tbody>
      </table></div>
      <details><summary>Complete option evidence</summary>
        <pre style={{whiteSpace: "pre-wrap", overflowWrap: "anywhere"}}>{JSON.stringify({before: revision.before.options, after: revision.after.options}, null, 2)}</pre>
      </details>
      {[revision.before, revision.after].map((version, index) => <section key={index} aria-label={index ? "Proposed visuals" : "Original visuals"}>
        {typeof version.question.question_image_url === "string" && <SecureImage candidateId={revision.candidate_id} src={version.question.question_image_url} alt={index ? "Proposed question visual" : "Original question visual"} />}
        {version.options.map(option => typeof option.image_url === "string" ? <SecureImage candidateId={revision.candidate_id} key={String(option.id)} src={option.image_url} alt={`${index ? "Proposed" : "Original"} option ${option.position}`} /> : null)}
      </section>)}
      <fieldset disabled={busy || revision.review_status === "reviewed"}>
        <legend>Independent checks</legend>
        {checks.map(([key, label]) => <label key={key} style={{display: "block"}}>
          <input type="checkbox" checked={attestations[key] === true} onChange={event => setAttestations(old => ({...old, [key]: event.target.checked}))} />{label}
        </label>)}
        <label>Review evidence reference<input value={reference} onChange={event => setReference(event.target.value)} /></label>
        <button disabled={!reference.trim() || !checks.every(([key]) => attestations[key])} onClick={() => void run("review")}>Record independent review</button>
      </fieldset>
      <button disabled={busy || revision.published || revision.review_status !== "reviewed" || !revision.publication_enabled} onClick={() => void run("publish")}>Publish reviewed correction</button>
      {!revision.publication_enabled && <p>Publication is disabled by the release gate.</p>}
    </>}
    <p role="status">{message}</p>
  </section>;
}
