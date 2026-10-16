// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import EditorialRevisionPanel from "./EditorialRevisionPanel";
import * as api from "../api";
vi.mock("../api", () => ({fetchEditorialRevision: vi.fn(), reviewEditorialRevision: vi.fn(), publishEditorialRevision: vi.fn()}));
afterEach(() => { cleanup(); vi.resetAllMocks(); });
const revision: api.EditorialRevision = {
  candidate_id: "candidate-1", author_id: 1, reason: "Clarify explanation", review_status: "pending_independent_review",
  published: false, publication_enabled: false,
  before: {question: {question_text: "Original", explanation: "Before"}, options: []},
  after: {question: {question_text: "Original", explanation: "After"}, options: []},
};
async function open() {
  render(<EditorialRevisionPanel />);
  fireEvent.change(screen.getByLabelText("Candidate reference"), {target: {value: "candidate-1"}});
  fireEvent.click(screen.getByText("Open candidate"));
  await screen.findByText("Candidate loaded.");
}
it("shows before/after and requires explicit independent checks; publication stays gated", async () => {
  vi.mocked(api.fetchEditorialRevision).mockResolvedValue(revision);
  await open();
  expect(screen.getByRole("cell", {name: /^After$/})).toBeTruthy();
  const review = screen.getByRole("button", {name: "Record independent review"}) as HTMLButtonElement;
  expect(review.disabled).toBe(true);
  expect((screen.getByText("Publish reviewed correction") as HTMLButtonElement).disabled).toBe(true);
  for (const box of screen.getAllByRole("checkbox")) fireEvent.click(box);
  fireEvent.change(screen.getByLabelText("Review evidence reference"), {target: {value: "Independent evidence"}});
  fireEvent.click(review);
  await waitFor(() => expect(api.reviewEditorialRevision).toHaveBeenCalledWith("candidate-1", {
    answer_verified: true, all_options_checked: true, instruction_reviewed: true, visual_reviewed: true, reference: "Independent evidence",
  }));
  expect(api.publishEditorialRevision).not.toHaveBeenCalled();
});
it("clears the old candidate and checks when opening a different reference", async () => {
  vi.mocked(api.fetchEditorialRevision).mockResolvedValue(revision);
  await open();
  fireEvent.click(screen.getAllByRole("checkbox")[0]);
  fireEvent.change(screen.getByLabelText("Candidate reference"), {target: {value: "candidate-2"}});
  expect(screen.queryByText("Complete question comparison")).toBeNull();
  expect(screen.queryByRole("checkbox")).toBeNull();
});
it("shows server conflicts without claiming publication succeeded", async () => {
  vi.mocked(api.fetchEditorialRevision).mockResolvedValue({...revision, review_status: "reviewed", publication_enabled: true});
  vi.mocked(api.publishEditorialRevision).mockRejectedValue(new Error("STALE_REVISION"));
  await open();
  fireEvent.click(screen.getByText("Publish reviewed correction"));
  await screen.findByText("STALE_REVISION");
  expect(screen.queryByText("Reviewed correction published.")).toBeNull();
});
