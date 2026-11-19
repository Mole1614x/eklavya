import "server-only";

import { NextRequest, NextResponse } from "next/server";
import { backend } from "./backend";

export type SessionTokens = { access_token: string; refresh_token: string };

const secure = process.env.COOKIE_SECURE === "true";
const accessCookie = { httpOnly: true, secure, sameSite: "lax" as const, path: "/", maxAge: 15 * 60 };
// Every authenticated BFF route may need to rotate an expired access token.
const refreshCookie = { httpOnly: true, secure, sameSite: "strict" as const, path: "/api", maxAge: 30 * 24 * 60 * 60 };

export function setSession(response: NextResponse, tokens: SessionTokens) {
  response.cookies.set("eklavya_refresh", "", { ...refreshCookie, path: "/api/auth", maxAge: 0 });
  response.cookies.set("eklavya_access", tokens.access_token, accessCookie);
  response.cookies.set("eklavya_refresh", tokens.refresh_token, refreshCookie);
}

export function clearSession(response: NextResponse) {
  response.cookies.set("eklavya_access", "", { ...accessCookie, maxAge: 0 });
  response.cookies.set("eklavya_refresh", "", { ...refreshCookie, maxAge: 0 });
  response.cookies.set("eklavya_refresh", "", { ...refreshCookie, path: "/api/auth", maxAge: 0 });
}

function clientIp(request: NextRequest) {
  return request.headers.get("x-forwarded-for")?.split(",").at(-1)?.trim();
}

export async function apiJson(path: string, body: unknown, request: NextRequest, authorization?: string) {
  const forwardedFor = clientIp(request);
  return backend(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(authorization ? { Authorization: authorization } : {}),
      ...(forwardedFor ? { "X-Forwarded-For": forwardedFor } : {}),
    },
    body: JSON.stringify(body),
  });
}

async function rotateSession(request: NextRequest): Promise<SessionTokens | null> {
  const refresh = request.cookies.get("eklavya_refresh")?.value;
  if (!refresh) return null;
  const upstream = await apiJson("/auth/refresh", { refresh_token: refresh }, request);
  if (!upstream.ok) return null;
  return upstream.json() as Promise<SessionTokens>;
}

export async function authenticatedBackend(request: NextRequest, path: string, init: RequestInit = {}) {
  let access = request.cookies.get("eklavya_access")?.value;
  let session: SessionTokens | null = null;
  if (!access) {
    session = await rotateSession(request);
    access = session?.access_token;
  }
  if (!access) return { upstream: null, session: null };

  const invoke = (token: string) => backend(path, {
    ...init,
    headers: { ...init.headers, Authorization: `Bearer ${token}` },
  });
  let upstream = await invoke(access);
  if (upstream.status === 401 && session === null) {
    session = await rotateSession(request);
    if (session) upstream = await invoke(session.access_token);
  }
  return { upstream, session };
}

export function applySession(response: NextResponse, session: SessionTokens | null, unauthorized = false) {
  if (session) setSession(response, session);
  else if (unauthorized) clearSession(response);
  return response;
}
