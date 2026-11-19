import "server-only";

export const backendUrl = process.env.API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export async function backend(path: string, init: RequestInit = {}) {
  return fetch(`${backendUrl}${path}`, { ...init, cache: "no-store", signal: AbortSignal.timeout(8000) });
}
