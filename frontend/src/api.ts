import { clearToken } from "./auth";
import {
  SESSION_EXPIRED_EVENT,
  beginSessionExpiry,
} from "./session";

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("ssc_prep_token");
  return token ? { Authorization: "Bearer " + token } : {};
}

async function sessionFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const authenticatedRequest = headers.has("Authorization");
  const response = await window.fetch(input, init);

  if (response.status === 401 && authenticatedRequest) {
    clearToken();
    invalidatePrivateDataCache();
    const next = window.location.pathname + window.location.search + window.location.hash;
    if (beginSessionExpiry(next)) {
      window.dispatchEvent(
        new CustomEvent(SESSION_EXPIRED_EVENT, {detail: {next}}),
      );
    }
  }

  // A successful write makes snapshot APIs stale; never serve stale private
  // analytics, revision or planner state after a learner action.
  const method = (init.method ?? "GET").toUpperCase();
  if (response.ok && authenticatedRequest && method !== "GET" && method !== "HEAD") {
    invalidatePrivateDataCache();
  }

  return response;
}

// Authenticated snapshots stay in RAM only and never enter sessionStorage.
// Repeated visits within a short window reuse the same result, while writes,
// token changes and expiry invalidate every private snapshot.
const privateDataCache = new Map<string, CacheEnvelope<unknown>>();
const privateDataInflight = new Map<string, Promise<unknown>>();
let privateCacheOwner: string | null = null;

export function invalidatePrivateDataCache(): void {
  privateDataCache.clear();
  privateDataInflight.clear();
  privateCacheOwner = localStorage.getItem("ssc_prep_token");
}

function privateCacheSession(): string | null {
  const token = localStorage.getItem("ssc_prep_token");
  if (token !== privateCacheOwner) {
    privateDataCache.clear();
    privateDataInflight.clear();
    privateCacheOwner = token;
  }
  return token;
}

function fetchPrivateCachedJson<T>(key: string, url: string, ttlMs: number): Promise<T> {
  const owner = privateCacheSession();
  if (!owner) return Promise.reject(new Error("Sign in to load this page"));

  const cached = privateDataCache.get(key) as CacheEnvelope<T> | undefined;
  if (cached && cached.expires_at > Date.now()) return Promise.resolve(cached.value);

  const inflight = privateDataInflight.get(key) as Promise<T> | undefined;
  if (inflight) return inflight;

  const request = sessionFetch(url, {headers: authHeaders()})
    .then(async (response) => {
      if (!response.ok) {
        const error = await response.json().catch(() => null);
        throw new Error(error?.detail ?? "Failed to load study data");
      }
      const value = await response.json() as T;
      if (privateCacheSession() === owner) {
        privateDataCache.set(key, {value, expires_at: Date.now() + ttlMs});
      }
      return value;
    })
    .finally(() => {
      if (privateDataInflight.get(key) === request) privateDataInflight.delete(key);
    });
  privateDataInflight.set(key, request);
  return request;
}

type CacheEnvelope<T> = {
  value: T;
  expires_at: number;
};

const memoryCache = new Map<string, CacheEnvelope<unknown>>();
const inflightCache = new Map<string, Promise<unknown>>();

function requestCachedJson<T>(key: string, url: string, ttlMs: number): Promise<T> {
  const existing = inflightCache.get(key) as Promise<T> | undefined;
  if (existing) return existing;

  const request = sessionFetch(url)
    .then(async (response) => {
      if (!response.ok) throw new Error("Request failed");
      const value = await response.json() as T;
      const envelope: CacheEnvelope<T> = {value, expires_at: Date.now() + ttlMs};
      memoryCache.set(key, envelope as CacheEnvelope<unknown>);
      try {
        sessionStorage.setItem(key, JSON.stringify(envelope));
      } catch {
        // Cache is an optimisation; storage quota/private mode must not break navigation.
      }
      return value;
    })
    .finally(() => inflightCache.delete(key));

  inflightCache.set(key, request as Promise<unknown>);
  return request;
}

async function fetchCachedJson<T>(key: string, url: string, ttlMs: number): Promise<T> {
  const now = Date.now();
  const memory = memoryCache.get(key) as CacheEnvelope<T> | undefined;
  if (memory?.expires_at && memory.expires_at > now) return memory.value;

  let stale = memory;
  try {
    const raw = sessionStorage.getItem(key);
    if (raw) {
      const cached = JSON.parse(raw) as CacheEnvelope<T>;
      memoryCache.set(key, cached as CacheEnvelope<unknown>);
      if (cached.expires_at > now) return cached.value;
      stale = cached;
    }
  } catch {
    // Storage is optional. Keep any in-memory value and continue to the network.
  }

  if (stale) {
    // Immutable learner-navigation content can render stale immediately while a
    // background refresh keeps the next navigation fresh. Versioned cache keys
    // are bumped whenever the response contract/content shape changes.
    void requestCachedJson<T>(key, url, ttlMs).catch(() => undefined);
    return stale.value;
  }

  return requestCachedJson<T>(key, url, ttlMs);
}

export type User = {
  id: number;
  email: string;
  display_name: string | null;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type Topic = {
  id: number;
  subject_id: number;
  slug: string;
  name: string;
  priority: number;
};

export type ReviewQuestion = {
  id: number;
  subject_id: number;
  topic_id: number | null;
  subtopic: string | null;
  pattern_type: string | null;
  question_text: string;
  question_image_url: string | null;
  options: Array<{position: number; text: string | null; image_url: string | null}>;
  correct_option: number;
  explanation: string | null;
  fast_method: string | null;
  year: number | null;
  shift: string | null;
  source_type: string;
  source_reference: string | null;
  source_page: number | null;
  requires_visual_review: boolean;
  source_chosen_option: number | null;
  source_question_id: string | null;
  source_status: string | null;
  verification_status: string;
  review_notes: string | null;
};

export async function login(email: string, password: string): Promise<AuthResponse> {
  const response = await sessionFetch(API_BASE + "/auth/login", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({email, password}),
  });
  if (!response.ok) throw new Error("Login failed");
  return response.json();
}

export async function register(
  email: string,
  password: string,
  display_name?: string,
): Promise<AuthResponse> {
  const response = await sessionFetch(API_BASE + "/auth/register", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({email, password, display_name}),
  });
  if (!response.ok) throw new Error("Registration failed");
  return response.json();
}

export async function fetchCurrentUser(): Promise<User> {
  const response = await sessionFetch(API_BASE + "/auth/me", {headers: authHeaders()});
  if (!response.ok) throw new Error("Failed to load account");
  return response.json();
}

export async function updateCurrentUser(display_name: string): Promise<User> {
  const response = await sessionFetch(API_BASE + "/auth/me", {
    method: "PATCH",
    headers: {...authHeaders(), "Content-Type": "application/json"},
    body: JSON.stringify({display_name}),
  });
  if (!response.ok) throw new Error("Failed to update profile");
  return response.json();
}

export async function changePassword(current_password: string, new_password: string): Promise<void> {
  const response = await sessionFetch(API_BASE + "/auth/change-password", {
    method: "POST",
    headers: {...authHeaders(), "Content-Type": "application/json"},
    body: JSON.stringify({current_password, new_password}),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail ?? "Failed to change password");
  }
}

export async function fetchTopics(subjectId: number): Promise<Topic[]> {
  const response = await sessionFetch(API_BASE + "/content/topics?subject_id=" + subjectId, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error("Failed to load topics");
  return response.json();
}

export async function fetchReviewQuestions(): Promise<ReviewQuestion[]> {
  const response = await sessionFetch(API_BASE + "/review/questions", {headers: authHeaders()});
  if (!response.ok) throw new Error("Failed to load review queue");
  return response.json();
}

export async function suggestReviewTopic(questionId: number) {
  const response = await sessionFetch(API_BASE + "/review/questions/" + questionId + "/suggest-topic", {
    method: "POST",
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error("Failed to suggest topic");
  return response.json();
}

export async function updateReviewQuestion(
  questionId: number,
  payload: {
    topic_id: number | null;
    correct_option: number | null;
    subtopic: string | null;
    pattern_type: string | null;
    review_notes: string | null;
    verification_status: string;
  },
) {
  const response = await sessionFetch(API_BASE + "/review/questions/" + questionId, {
    method: "PATCH",
    headers: {...authHeaders(), "Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("Failed to update review question");
  return response.json();
}


export type ReviewStats = {
  by_status: Record<string, number>;
  visual_pending: number;
};

export async function fetchReviewStats(): Promise<ReviewStats> {
  const response = await sessionFetch(API_BASE + "/review/stats", {headers: authHeaders()});
  if (!response.ok) throw new Error("Failed to load review stats");
  return response.json();
}


export type ContentTree = {
  exam: {id: number; slug: string; name: string};
  totals?: {lessons: number; topics: number};
  subjects: Array<{
    id: number;
    slug: string;
    name: string;
    lesson_count: number;
    topic_count: number;
    topics: Array<{
      id: number;
      slug: string;
      name: string;
      priority: number;
      lesson_count: number;
    }>;
  }>;
};

export type Lesson = {
  id: number;
  topic_id: number;
  title: string;
  intro: string;
  concept: string;
  shortcut: string | null;
  worked_example: string | null;
  memory_rule: string | null;
  common_traps: string | null;
  estimated_minutes: number;
};

export async function fetchContentTree(): Promise<ContentTree> {
  return fetchCachedJson<ContentTree>(
    "ssc_content_tree_v2",
    API_BASE + "/content/tree?exam_slug=ssc-cgl-tier-1",
    30 * 60 * 1000,
  );
}

export async function fetchTopicLessons(topicId: number): Promise<Lesson[]> {
  const response = await sessionFetch(API_BASE + "/learn/topics/" + topicId + "/lessons");
  if (!response.ok) throw new Error("Failed to load lessons");
  return response.json();
}


export type PracticeQuestion = {
  id: number;
  topic_id: number | null;
  subtopic: string | null;
  pattern_type: string | null;
  question_text: string;
  question_image_url: string | null;
  difficulty: number;
  expected_time_seconds: number | null;
  year: number | null;
  shift: string | null;
  options: Array<{position: number; text: string | null; image_url: string | null}>;
};

export type PracticeCoaching = {
  pattern_name: string | null;
  skill: string | null;
  recognition_cues: string | null;
  standard_method: string | null;
  fast_method: string | null;
  common_trap: string | null;
  difficulty_rule: string | null;
  worked_example: string | null;
  hint_steps: string[];
  archetype_exact: boolean;
};

export type PracticeResult = {
  attempt_id: number;
  correct: boolean;
  correct_option: number;
  explanation: string | null;
  fast_method: string | null;
  mastery_score: number | null;
  revision_scheduled: boolean;
  coaching: PracticeCoaching | null;
};

export async function fetchPracticeQuestions(
  topicId: number | undefined,
  limit = 5,
  mode = "adaptive",
  similarTo?: number,
): Promise<PracticeQuestion[]> {
  const params = new URLSearchParams({limit: String(limit), mode});
  if (topicId) params.set("topic_id", String(topicId));
  if (similarTo) params.set("similar_to", String(similarTo));
  const response = await sessionFetch(
    API_BASE + "/practice/questions?" + params.toString(),
    {headers: authHeaders()},
  );
  if (!response.ok) throw new Error("Failed to load practice questions");
  return response.json();
}

export async function submitPracticeAnswer(payload: {
  question_id: number;
  selected_option: number | null;
  time_seconds: number;
  confidence: number | null;
  used_hint: boolean;
  mistake_type: string | null;
}): Promise<PracticeResult> {
  const response = await sessionFetch(API_BASE + "/practice/submit", {
    method: "POST",
    headers: {...authHeaders(), "Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("Failed to submit practice answer");
  return response.json();
}


export async function classifyPracticeMistake(
  attemptId: number,
  mistakeType: string,
): Promise<void> {
  const response = await sessionFetch(API_BASE + "/practice/attempts/" + attemptId + "/mistake", {
    method: "PATCH",
    headers: {...authHeaders(), "Content-Type": "application/json"},
    body: JSON.stringify({mistake_type: mistakeType}),
  });
  if (!response.ok) throw new Error("Failed to classify mistake");
}


export type MockQuestion = {
  position: number;
  section_slug: string;
  question: PracticeQuestion;
};

export type MockStartResponse = {
  attempt_id: number;
  mode: string;
  duration_minutes: number;
  questions: MockQuestion[];
};

export type MockStateResponse = {
  attempt_id: number;
  status: string;
  started_at: string;
  duration_minutes: number;
  seconds_left: number;
  active_section_slug: string | null;
  section_index: number | null;
  section_seconds_left: number | null;
  section_duration_seconds: number | null;
  responses: Array<{
    question_id: number;
    selected_option: number | null;
    marked_for_review: boolean;
    time_seconds: number;
  }>;
};

export type MockSubmitResult = {
  attempt_id: number;
  score: number;
  correct: number;
  incorrect: number;
  unattempted: number;
  total_questions: number;
};

export async function startMock(
  mode: "mini" | "full" | "sectional" | "topic",
  subject_slug?: string,
  topic_id?: number,
): Promise<MockStartResponse> {
  const response = await sessionFetch(API_BASE + "/mocks/start", {
    method: "POST",
    headers: {...authHeaders(), "Content-Type": "application/json"},
    body: JSON.stringify({mode, subject_slug: subject_slug ?? null, topic_id: topic_id ?? null}),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail ?? "Failed to start mock");
  }
  return response.json();
}

export type ActiveMock = {
  attempt_id: number | null;
  mode?: string;
  subject_slug?: string | null;
  seconds_left?: number;
  active_section_slug?: string | null;
  section_index?: number | null;
  section_seconds_left?: number | null;
  section_duration_seconds?: number | null;
};

export async function fetchActiveMock(): Promise<ActiveMock> {
  const response = await sessionFetch(API_BASE + "/mocks/active/current", {headers: authHeaders()});
  if (!response.ok) throw new Error("Failed to load active mock");
  return response.json();
}

export async function fetchMockAttempt(attemptId: number): Promise<MockStartResponse> {
  const response = await sessionFetch(API_BASE + "/mocks/" + attemptId, {headers: authHeaders()});
  if (!response.ok) throw new Error("Failed to load mock");
  return response.json();
}

export async function abandonMock(attemptId: number): Promise<void> {
  const response = await sessionFetch(API_BASE + "/mocks/" + attemptId, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error("Failed to abandon mock");
}


export async function fetchMockState(attemptId: number): Promise<MockStateResponse> {
  const response = await sessionFetch(API_BASE + "/mocks/" + attemptId + "/state", {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error("Failed to load mock state");
  return response.json();
}

export async function saveMockResponse(
  attemptId: number,
  payload: {
    question_id: number;
    selected_option: number | null;
    marked_for_review: boolean;
    time_seconds: number;
  },
): Promise<void> {
  const response = await sessionFetch(API_BASE + "/mocks/" + attemptId + "/response", {
    method: "PATCH",
    headers: {...authHeaders(), "Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail ?? "Failed to save mock response");
  }
}

export type MockReview = {
  attempt_id: number;
  sections: Record<string, {
    correct: number;
    incorrect: number;
    unattempted: number;
    time_seconds: number;
    score: number;
    accuracy: number;
  }>;
  easy_missed: number;
  slow_questions: number;
  weak_patterns: Array<{pattern: string; missed: number}>;
  questions: Array<{
    position: number;
    section_slug: string;
    question_id: number;
    question_text: string;
    selected_option: number | null;
    correct_option: number;
    correct: boolean;
    marked_for_review: boolean;
    time_seconds: number;
    expected_time_seconds: number | null;
    difficulty: number;
    pattern_type: string | null;
    explanation: string | null;
    fast_method: string | null;
  }>;
};

export async function fetchMockReview(attemptId: number): Promise<MockReview> {
  const response = await sessionFetch(API_BASE + "/mocks/" + attemptId + "/review", {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error("Failed to load mock review");
  return response.json();
}


export async function submitMock(attemptId: number): Promise<MockSubmitResult> {
  const response = await sessionFetch(API_BASE + "/mocks/" + attemptId + "/submit", {
    method: "POST",
    headers: authHeaders(),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail ?? "Failed to submit mock");
  }
  return response.json();
}


export type AnalyticsSummary = {
  overview: {
    practice_attempts: number;
    accuracy: number;
    speed_score: number;
    mastery: number;
    mock_accuracy: number;
    mock_attempt_rate: number;
    readiness: number;
    streak: number;
  };
  errors: {
    breakdown: Record<string, number>;
    avoidable_errors: number;
    potential_score_gain: number;
  };
  confidence: {
    sure_accuracy: number;
    unsure_accuracy: number;
    guess_accuracy: number;
    guess_rate: number;
    overconfident_errors: number;
  };
  learning_curve: {
    first_attempts: number;
    first_attempt_accuracy: number;
    repeat_attempts: number;
    repeat_attempt_accuracy: number;
    repeat_gain: number;
    slow_attempts: number;
    time_over_target_seconds: number;
  };
  subject_breakdown: Array<{
    subject_slug: string;
    subject_name: string;
    attempts: number;
    accuracy: number;
    avg_time_seconds: number;
  }>;
  trend: Array<{
    date: string;
    attempts: number;
    accuracy: number;
    avg_time_seconds: number;
  }>;
  next_actions: Array<{
    type: string;
    title: string;
    reason: string;
    topic_id: number | null;
  }>;
  weak_topics: Array<{
    topic_id: number;
    topic_name: string;
    attempts: number;
    accuracy: number;
    avg_time_seconds: number;
    mastery: number;
  }>;
  recent_mocks: Array<{
    attempt_id: number;
    mode: string;
    score: number;
    correct: number;
    incorrect: number;
    unattempted: number;
    submitted_at: string | null;
  }>;
  coach: {
    evidence_level: "baseline" | "developing" | "established";
    headline: string;
    summary: string;
    primary_action: {
      title: string;
      reason: string;
      path: string;
    };
    secondary_action: {
      title: string;
      reason: string;
      path: string;
    };
  };
};

export async function fetchAnalyticsSummary(): Promise<AnalyticsSummary> {
  return fetchPrivateCachedJson<AnalyticsSummary>(
    "analytics_summary",
    API_BASE + "/analytics/summary",
    45_000,
  );
}


export type RevisionQuestion = {
  id: number;
  topic_id: number | null;
  question_text: string;
  question_image_url: string | null;
  correct_option: number | null;
  explanation: string | null;
  fast_method: string | null;
  options: Array<{position: number; text: string | null; image_url: string | null}>;
};

export type RevisionItem = {
  id: number;
  reason: string;
  successful_reviews: number;
  next_review_at: string;
  question: RevisionQuestion;
};

export type FlashcardItem = {
  id: number;
  topic_id: number | null;
  front: string;
  back: string;
  related_fact: string | null;
  card_type: string;
  successful_reviews: number;
};

export type BookmarkItem = {
  bookmark_id: number;
  question: RevisionQuestion;
};

export async function fetchRevisionQueue(reason?: string): Promise<RevisionItem[]> {
  const suffix = reason ? "?reason=" + encodeURIComponent(reason) : "";
  return fetchPrivateCachedJson<RevisionItem[]>(
    "revision_queue_" + (reason ?? "all"),
    API_BASE + "/revision/queue" + suffix,
    20_000,
  );
}

export async function reviewRevisionItem(itemId: number, success: boolean): Promise<void> {
  const response = await sessionFetch(API_BASE + "/revision/items/" + itemId + "/review?success=" + success, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error("Failed to update revision item");
}

export async function addQuestionToRevision(questionId: number): Promise<{added: boolean; item_id: number; reason: string}> {
  const response = await sessionFetch(API_BASE + "/revision/questions/" + questionId + "/add", {
    method: "POST",
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error("Failed to add question to revision");
  return response.json();
}


export async function toggleBookmark(questionId: number): Promise<{bookmarked: boolean}> {
  const response = await sessionFetch(API_BASE + "/revision/bookmarks/" + questionId, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error("Failed to update bookmark");
  return response.json();
}

export async function fetchBookmarks(): Promise<BookmarkItem[]> {
  return fetchPrivateCachedJson<BookmarkItem[]>(
    "revision_bookmarks",
    API_BASE + "/revision/bookmarks",
    20_000,
  );
}

export async function fetchDueFlashcards(): Promise<FlashcardItem[]> {
  return fetchPrivateCachedJson<FlashcardItem[]>(
    "revision_flashcards",
    API_BASE + "/revision/flashcards/due",
    20_000,
  );
}

export async function reviewFlashcard(flashcardId: number, success: boolean): Promise<void> {
  const response = await sessionFetch(API_BASE + "/revision/flashcards/" + flashcardId + "/review?success=" + success, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error("Failed to update flashcard");
}


export type PlannerTask = {
  id: number;
  activity_type: string;
  subject_slug: string | null;
  topic_id: number | null;
  title: string;
  target_minutes: number;
  target_questions: number | null;
  priority: number;
  status: string;
  reason: string;
  expected_outcome: string;
};

export type TodayPlan = {
  target: {
    exam_id: number;
    exam_date: string;
    daily_minutes: number;
    days_left: number;
    full_study_days: number;
  };
  progress: {
    completed_minutes: number;
    planned_minutes: number;
    completed_tasks: number;
    total_tasks: number;
  };
  tasks: PlannerTask[];
};

export async function fetchTodayPlan(): Promise<TodayPlan> {
  return fetchPrivateCachedJson<TodayPlan>(
    "planner_today",
    API_BASE + "/planner/today",
    20_000,
  );
}

export async function setPlannerConfig(
  examDate: string,
  dailyMinutes: number,
): Promise<TodayPlan> {
  const response = await sessionFetch(API_BASE + "/planner/config", {
    method: "PUT",
    headers: {...authHeaders(), "Content-Type": "application/json"},
    body: JSON.stringify({
      exam_slug: "ssc-cgl-tier-1",
      exam_date: examDate,
      daily_minutes: dailyMinutes,
    }),
  });
  if (!response.ok) throw new Error("Failed to save planner settings");
  return response.json();
}

export async function rebuildTodayPlan(): Promise<TodayPlan> {
  const response = await sessionFetch(API_BASE + "/planner/today/rebuild", {
    method: "POST",
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error("Failed to rebuild plan");
  return response.json();
}

export async function updatePlannerTask(taskId: number, completed: boolean): Promise<void> {
  const response = await sessionFetch(API_BASE + "/planner/tasks/" + taskId + "?completed=" + completed, {
    method: "PATCH",
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error("Failed to update task");
}


export async function exportBackup(): Promise<Blob> {
  const response = await sessionFetch(API_BASE + "/backup/export", {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error("Failed to export backup");
  const data = await response.json();
  return new Blob([JSON.stringify(data, null, 2)], {type: "application/json"});
}


export type LessonBlock = {
  id: number;
  lesson_id: number;
  block_type: string;
  title: string;
  body: string;
  difficulty: number | null;
  sort_order: number;
};

export type QuestionArchetype = {
  id: number;
  topic_id: number;
  slug: string;
  name: string;
  skill: string;
  recognition_cues: string;
  canonical_method: string;
  shortcut_method: string | null;
  common_trap: string | null;
  easy_rule: string | null;
  medium_rule: string | null;
  hard_rule: string | null;
  expected_time_seconds: number;
  source_notes: string | null;
};

export type SolvedExample = {
  id: number;
  pattern_type: string | null;
  question_text: string;
  question_image_url: string | null;
  difficulty: number;
  expected_time_seconds: number | null;
  year: number | null;
  shift: string | null;
  correct_option: number;
  explanation: string | null;
  fast_method: string | null;
  options: Array<{position: number; text: string | null; image_url: string | null}>;
};

export type TopicPackage = {
  subject: {id: number; slug: string; name: string};
  topic: {id: number; slug: string; name: string; priority: number};
  lessons: Array<Lesson & {blocks: LessonBlock[]}>;
  archetypes: QuestionArchetype[];
  solved_examples: SolvedExample[];
};

export async function fetchTopicPackage(topicId: number): Promise<TopicPackage> {
  return fetchCachedJson<TopicPackage>(
    "ssc_topic_package_v3_" + topicId,
    API_BASE + "/learn/topics/" + topicId + "/package",
    30 * 60 * 1000,
  );
}

export function prefetchTopicPackage(topicId: number): void {
  void fetchTopicPackage(topicId).catch(() => undefined);
}
