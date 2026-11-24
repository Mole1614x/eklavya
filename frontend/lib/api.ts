import "server-only";
import { cookies } from "next/headers";
import { backend } from "./backend";

export type Problem = {
  slug: string;
  title: string;
  category: string;
  difficulty: string;
  format: string;
  topic: string;
  tags: string[];
};

export type ProblemDetail = Problem & {
  description: string;
  constraints: string[];
  examples: { input: string; output: string }[];
  starters: { language: string; code: string }[];
  choices: string[];
};

export type Catalog = { items: Problem[]; total: number; topics: string[] };

async function request<T>(path: string): Promise<T | null> {
  const access = (await cookies()).get("eklavya_access")?.value;
  let response = await backend(path, access ? { headers: { Authorization: `Bearer ${access}` } } : {});
  // An expired access token must never expose selected content; fall back to public data.
  if (response.status === 401 && access) response = await backend(path);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error("The problem catalog is unavailable.");
  return response.json() as Promise<T>;
}

export async function getCatalog(filters: Record<string, string> = {}) {
  const catalog = await request<Catalog>(`/problems?${new URLSearchParams(filters)}`);
  if (!catalog) throw new Error("The problem catalog is unavailable.");
  return catalog;
}

export function getProblem(slug: string) {
  return request<ProblemDetail>(`/problems/${encodeURIComponent(slug)}`);
}

export type ProblemNavigation = {
  previous: string | null;
  next: string | null;
  position: number;
  total: number;
};

/** Context-aware neighbors in the same title/slug order as the problem catalog. */
export function getProblemNavigation(slug: string, filters: Record<string, string> = {}) {
  const query = new URLSearchParams(filters);
  return request<ProblemNavigation>(
    `/problems/${encodeURIComponent(slug)}/navigation${query.size ? `?${query}` : ""}`
  );
}

export type SubjectCoverage = {
  id: number; slug: string; name: string; target: number; category: string;
  published_questions: number; remaining_to_target: number; execution_status: string;
};
export type SubjectCatalog = {
  subjects: SubjectCoverage[];
  target_total: number;
  classified_published: number;
  published_catalog_total: number;
  classification_note: string;
};

export async function getSubjects() {
  const response = await request<SubjectCatalog>("/subjects");
  if (!response) throw new Error("The subject catalogue is unavailable.");
  return response;
}
