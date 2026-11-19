import "server-only";

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
  const base = process.env.API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
  const response = await fetch(base + path, { cache: "no-store", signal: AbortSignal.timeout(5000) });
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
