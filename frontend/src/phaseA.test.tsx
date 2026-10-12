// @vitest-environment jsdom
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearToken, getToken, setToken, sessionGeneration, sessionSuspended } from "./auth";
import { fetchTopicPackage, purgeLegacyLessonCaches } from "./api";
import SecureImage from "./components/SecureImage";
import TeacherCoach from "./components/TeacherCoach";
import { fireEvent } from "@testing-library/react";

beforeEach(() => {
  localStorage.clear(); sessionStorage.clear(); setToken("synthetic-owner-a");
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.useRealTimers(); clearToken(); });

function response(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {status, headers: {"Content-Type":"application/json"}});
}

describe("SEC-06 private session isolation", () => {
  it("removes only legacy lesson/package keys from both persistent stores", () => {
    for (const storage of [localStorage, sessionStorage]) {
      storage.setItem("ssc_topic_package_v3_42", "PRIVATE_SENTINEL");
      storage.setItem("ssc_lesson_v2_4", "PRIVATE_SENTINEL");
      storage.setItem("ssc_voice_rate", "0.9");
    }
    purgeLegacyLessonCaches();
    for (const storage of [localStorage, sessionStorage]) {
      expect(storage.getItem("ssc_topic_package_v3_42")).toBeNull();
      expect(storage.getItem("ssc_lesson_v2_4")).toBeNull();
      expect(storage.getItem("ssc_voice_rate")).toBe("0.9");
    }
  });

  it("authenticates packages, bypasses browser cache and never persists them", async () => {
    const fetcher = vi.spyOn(window, "fetch").mockResolvedValue(response({private:"SYNTHETIC_PRIVATE"}));
    await fetchTopicPackage(42);
    expect(fetcher.mock.calls[0][1]?.cache).toBe("no-store");
    expect(fetcher.mock.calls[0][1]?.headers).toEqual({Authorization:"Bearer synthetic-owner-a"});
    expect(JSON.stringify({...sessionStorage})).not.toContain("SYNTHETIC_PRIVATE");
    expect(JSON.stringify({...localStorage})).not.toContain("SYNTHETIC_PRIVATE");
  });

  it.each(["logout", "switch", "cross-tab", "bfcache"])("discards stale package after %s", async (change) => {
    let resolve!: (response: Response) => void;
    vi.spyOn(window, "fetch").mockReturnValue(new Promise((done) => { resolve = done; }));
    const pending = fetchTopicPackage(42);
    const rejected = expect(pending).rejects.toThrow(/Session changed/);
    if (change === "logout") clearToken();
    if (change === "switch") setToken("synthetic-owner-b");
    if (change === "cross-tab") {
      localStorage.setItem("ssc_prep_token", "synthetic-owner-b");
      window.dispatchEvent(new StorageEvent("storage", {key:"ssc_prep_token"}));
    }
    if (change === "bfcache") window.dispatchEvent(new PageTransitionEvent("pageshow", {persisted:true}));
    resolve(response({private:"OLD_ACCOUNT_SENTINEL"}));
    await rejected;
  });

  it("a late 401 from account A cannot log out account B", async () => {
    let resolve!: (response: Response) => void;
    vi.spyOn(window, "fetch").mockReturnValue(new Promise((done) => { resolve = done; }));
    const pending = fetchTopicPackage(42);
    const rejected = expect(pending).rejects.toThrow();
    setToken("synthetic-owner-b");
    resolve(response({}, 401));
    await rejected;
    expect(getToken()).toBe("synthetic-owner-b");
  });

  it("clears a JWT on expiry even without another request", () => {
    vi.useFakeTimers();
    const token = "header." + btoa(JSON.stringify({exp: Math.floor(Date.now()/1000)+2})) + ".signature";
    setToken(token);
    vi.advanceTimersByTime(2100);
    expect(getToken()).toBeNull();
  });

  it("suspends private views for pagehide and revalidates on restore", () => {
    const old = sessionGeneration();
    window.dispatchEvent(new PageTransitionEvent("pagehide", {persisted:true}));
    expect(sessionSuspended()).toBe(true);
    window.dispatchEvent(new PageTransitionEvent("pageshow", {persisted:true}));
    expect(sessionSuspended()).toBe(false);
    expect(sessionGeneration()).toBeGreaterThan(old);
  });

  it("does not create an object URL for a late private image after account switch", async () => {
    let resolve!: (response: Response) => void;
    vi.spyOn(window, "fetch").mockReturnValue(new Promise((done) => { resolve = done; }));
    const createObjectURL = vi.fn();
    vi.stubGlobal("URL", Object.assign(URL, {createObjectURL, revokeObjectURL:vi.fn()}));
    render(<SecureImage src="private://synthetic.png" alt="private sample" />);
    setToken("synthetic-owner-b");
    await act(async () => resolve(new Response("synthetic bytes")));
    expect(createObjectURL).not.toHaveBeenCalled();
    expect(screen.queryByRole("img")).toBeNull();
  });
});

it("INT-07 practice coach obtains assistance through the server callback", async () => {
  const ask = vi.fn().mockResolvedValue("REVIEWED_ASSISTANCE");
  render(<TeacherCoach title="Synthetic" defaultOpen onAsk={ask} />);
  await act(async () => fireEvent.click(screen.getByRole("button", {name:"Compare methods"})));
  expect(ask).toHaveBeenCalledWith("Compare methods");
  expect(screen.getByText("REVIEWED_ASSISTANCE")).toBeTruthy();
});
