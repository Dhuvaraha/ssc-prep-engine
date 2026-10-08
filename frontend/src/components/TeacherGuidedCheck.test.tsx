// @vitest-environment jsdom
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { SolvedExample } from "../api";
import TeacherGuidedCheck from "./TeacherGuidedCheck";

afterEach(cleanup);

const example: SolvedExample = {
  id: 123,
  pattern_type: "test-pattern",
  question_text: "A learner's sample verified question?",
  question_image_url: null,
  difficulty: 1,
  expected_time_seconds: 40,
  year: null,
  shift: null,
  correct_option: 3,
  explanation: "VERIFIED_WORKED_EXPLANATION for teaching this sample.",
  fast_method: "VERIFIED_FAST_METHOD",
  options: [
    {position: 1, text: "First candidate", image_url: null},
    {position: 2, text: "Second candidate", image_url: null},
    {position: 3, text: "Correct candidate", image_url: null},
    {position: 4, text: "Fourth candidate", image_url: null},
  ],
};

function mount(props = {}) {
  return render(
    <MemoryRouter>
      <TeacherGuidedCheck
        topicId={99}
        example={example}
        recognitionCue="Notice the governing pattern before calculating."
        commonTrap="Do not confuse the values."
        {...props}
      />
    </MemoryRouter>,
  );
}

describe("Teacher guided check", () => {
  it("hides both verified answer feedback and explanation until the learner checks", () => {
    mount();
    expect(screen.getByText(example.question_text)).toBeTruthy();
    expect(screen.queryByText(example.explanation as string)).toBeNull();
    expect(screen.queryByText(/Answer C/)).toBeNull();
    expect(screen.getByRole("button", {name: "Check my answer"}).hasAttribute("disabled")).toBe(true);

    fireEvent.click(screen.getByRole("button", {name: /First candidate/}));
    fireEvent.click(screen.getByRole("button", {name: "Check my answer"}));
    expect(screen.getByText(/Not yet/)).toBeTruthy();
    expect(screen.getByText(example.explanation as string)).toBeTruthy();
    expect(screen.getByText(/Answer C/)).toBeTruthy();
    expect(screen.getByText(/Possible trap to check/)).toBeTruthy();
    expect(screen.getByRole("link", {name: /Try new independent questions/}).getAttribute("href"))
      .toBe("/practice?topic_id=99&mode=path&limit=10");
  });

  it("does not treat an explicitly revealed walkthrough as a scored incorrect response", () => {
    mount();
    fireEvent.click(screen.getByRole("button", {name: /First candidate/}));
    fireEvent.click(screen.getByRole("button", {name: "Show walkthrough instead"}));
    expect(screen.queryByText(example.explanation as string)).toBeNull();
    fireEvent.click(screen.getByRole("button", {name: "Reveal the verified walkthrough"}));
    expect(screen.getByText("Walkthrough")).toBeTruthy();
    expect(screen.queryByText(/Not yet/)).toBeNull();
    expect(screen.getByText(example.explanation as string)).toBeTruthy();
  });

  it("supports a recognition hint without automatically revealing answer or awarding mastery", () => {
    mount();
    fireEvent.click(screen.getByRole("button", {name: "Get a recognition hint"}));
    expect(screen.getByText(/Notice the governing pattern/)).toBeTruthy();
    expect(screen.queryByText(example.explanation as string)).toBeNull();
    fireEvent.click(screen.getByRole("button", {name: /Correct candidate/}));
    fireEvent.click(screen.getByRole("button", {name: "Check my answer"}));
    expect(screen.getByText(/Correct — now confirm/)).toBeTruthy();
    expect(screen.getByText(/does not change your mastery score/)).toBeTruthy();
  });

  it("resets answer state when the teacher changes to a new verified example", () => {
    const {rerender} = mount();
    fireEvent.click(screen.getByRole("button", {name: /First candidate/}));
    fireEvent.click(screen.getByRole("button", {name: "Check my answer"}));
    expect(screen.getByText(example.explanation as string)).toBeTruthy();

    rerender(
      <MemoryRouter>
        <TeacherGuidedCheck
          topicId={100}
          example={{...example, id: 124, question_text: "A new topic question?"}}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText("A new topic question?")).toBeTruthy();
    expect(screen.queryByText(example.explanation as string)).toBeNull();
  });
});
