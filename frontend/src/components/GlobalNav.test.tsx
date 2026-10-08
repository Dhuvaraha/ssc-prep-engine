// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

vi.mock("../api", () => ({
  fetchContentTree: vi.fn().mockResolvedValue({}),
  prefetchStudyPage: vi.fn(),
}));
vi.mock("../auth", () => ({ getToken: () => "test-token" }));

import GlobalNav from "./GlobalNav";

afterEach(() => {
  cleanup();
  document.body.classList.remove("hasAppSidebar");
});

function mount(path = "/planner") {
  render(<MemoryRouter initialEntries={[path]}><GlobalNav /></MemoryRouter>);
}

describe("responsive primary navigation", () => {
  it("keeps five readable mobile destinations and an accessible More menu", () => {
    mount();
    const mobile = screen.getByRole("navigation", {name: "Mobile navigation"});
    expect(mobile.querySelectorAll("a")).toHaveLength(4);
    expect(within(mobile).getByRole("button", {name: "More navigation"}).getAttribute("aria-expanded")).toBe("false");
    const menu = document.getElementById("mobile-more-menu")!;
    expect(menu.hasAttribute("hidden")).toBe(true);

    fireEvent.click(within(mobile).getByRole("button", {name: "More navigation"}));
    expect(menu.hasAttribute("hidden")).toBe(false);
    expect(within(menu).getByRole("link", {name: "Revision"}).getAttribute("href")).toBe("/revision");
    expect(within(menu).getByRole("link", {name: "Analytics"}).getAttribute("href")).toBe("/analytics");
    expect(within(menu).getByRole("link", {name: "Choose exam"}).getAttribute("href")).toBe("/exams");
  });

  it("closes More on Escape and after navigation, and keeps active route semantics", () => {
    mount("/analytics");
    const mobile = screen.getByRole("navigation", {name: "Mobile navigation"});
    const moreButton = within(mobile).getByRole("button", {name: "More navigation"});
    fireEvent.click(moreButton);
    const menu = screen.getByRole("navigation", {name: "Additional navigation"});
    expect(within(menu).getByRole("link", {name: "Analytics"}).getAttribute("aria-current")).toBe("page");
    fireEvent.keyDown(window, {key: "Escape"});
    expect(menu.hasAttribute("hidden")).toBe(true);
    fireEvent.click(moreButton);
    fireEvent.click(within(menu).getByRole("link", {name: "Revision"}));
    expect(menu.hasAttribute("hidden")).toBe(true);
    expect(menu.querySelector('a[href="/revision"]')?.getAttribute("aria-current")).toBe("page");
  });

  it("does not show the application navigation over an active test", () => {
    mount("/mocks");
    expect(screen.queryByRole("navigation", {name: "Mobile navigation"})).toBeNull();
    expect(screen.queryByRole("navigation", {name: "Additional navigation", hidden: true})).toBeNull();
    expect(document.body.classList.contains("hasAppSidebar")).toBe(false);
  });
});
