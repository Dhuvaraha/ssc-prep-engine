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
