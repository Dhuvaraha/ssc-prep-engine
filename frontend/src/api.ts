export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("ssc_prep_token");
  return token ? { Authorization: "Bearer " + token } : {};
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
  const response = await fetch(API_BASE + "/auth/login", {
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
  const response = await fetch(API_BASE + "/auth/register", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({email, password, display_name}),
  });
  if (!response.ok) throw new Error("Registration failed");
  return response.json();
}

export async function fetchTopics(subjectId: number): Promise<Topic[]> {
  const response = await fetch(API_BASE + "/content/topics?subject_id=" + subjectId, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error("Failed to load topics");
  return response.json();
}

export async function fetchReviewQuestions(): Promise<ReviewQuestion[]> {
  const response = await fetch(API_BASE + "/review/questions", {headers: authHeaders()});
  if (!response.ok) throw new Error("Failed to load review queue");
  return response.json();
}

export async function suggestReviewTopic(questionId: number) {
  const response = await fetch(API_BASE + "/review/questions/" + questionId + "/suggest-topic", {
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
  const response = await fetch(API_BASE + "/review/questions/" + questionId, {
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
  const response = await fetch(API_BASE + "/review/stats", {headers: authHeaders()});
  if (!response.ok) throw new Error("Failed to load review stats");
  return response.json();
}


export type ContentTree = {
  exam: {id: number; slug: string; name: string};
  subjects: Array<{
    id: number;
    slug: string;
    name: string;
    topics: Array<{id: number; slug: string; name: string; priority: number}>;
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
  const response = await fetch(API_BASE + "/content/tree?exam_slug=ssc-cgl-tier-1");
  if (!response.ok) throw new Error("Failed to load content tree");
  return response.json();
}

export async function fetchTopicLessons(topicId: number): Promise<Lesson[]> {
  const response = await fetch(API_BASE + "/learn/topics/" + topicId + "/lessons");
  if (!response.ok) throw new Error("Failed to load lessons");
  return response.json();
}


export type PracticeQuestion = {
  id: number;
  topic_id: number | null;
  question_text: string;
  question_image_url: string | null;
  difficulty: number;
  expected_time_seconds: number | null;
  year: number | null;
  shift: string | null;
  options: Array<{position: number; text: string | null; image_url: string | null}>;
};

export type PracticeResult = {
  attempt_id: number;
  correct: boolean;
  correct_option: number;
  explanation: string | null;
  fast_method: string | null;
  mastery_score: number | null;
  revision_scheduled: boolean;
};

export async function fetchPracticeQuestions(topicId: number, limit = 5, mode = "adaptive"): Promise<PracticeQuestion[]> {
  const response = await fetch(
    API_BASE + "/practice/questions?topic_id=" + topicId + "&limit=" + limit + "&mode=" + mode,
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
  const response = await fetch(API_BASE + "/practice/submit", {
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
  const response = await fetch(API_BASE + "/practice/attempts/" + attemptId + "/mistake", {
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
  mode: "mini" | "full" | "sectional",
  subject_slug?: string,
): Promise<MockStartResponse> {
  const response = await fetch(API_BASE + "/mocks/start", {
    method: "POST",
    headers: {...authHeaders(), "Content-Type": "application/json"},
    body: JSON.stringify({mode, subject_slug: subject_slug ?? null}),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail ?? "Failed to start mock");
  }
  return response.json();
}

export async function fetchMockState(attemptId: number): Promise<MockStateResponse> {
  const response = await fetch(API_BASE + "/mocks/" + attemptId + "/state", {
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
  const response = await fetch(API_BASE + "/mocks/" + attemptId + "/response", {
    method: "PATCH",
    headers: {...authHeaders(), "Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("Failed to save mock response");
}

export async function submitMock(attemptId: number): Promise<MockSubmitResult> {
  const response = await fetch(API_BASE + "/mocks/" + attemptId + "/submit", {
    method: "POST",
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error("Failed to submit mock");
  return response.json();
}
