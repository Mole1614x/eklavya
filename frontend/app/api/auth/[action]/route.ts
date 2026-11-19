import { NextRequest, NextResponse } from "next/server";
import { backend } from "@/lib/backend";

const secure = process.env.COOKIE_SECURE === "true";
const accessCookie = { httpOnly: true, secure, sameSite: "lax" as const, path: "/", maxAge: 15 * 60 };
const refreshCookie = { httpOnly: true, secure, sameSite: "strict" as const, path: "/api/auth", maxAge: 30 * 24 * 60 * 60 };

function setSession(response: NextResponse, tokens: { access_token: string; refresh_token: string }) {
  response.cookies.set("eklavya_access", tokens.access_token, accessCookie);
  response.cookies.set("eklavya_refresh", tokens.refresh_token, refreshCookie);
}

function clearSession(response: NextResponse) {
  response.cookies.set("eklavya_access", "", { ...accessCookie, maxAge: 0 });
  response.cookies.set("eklavya_refresh", "", { ...refreshCookie, maxAge: 0 });
}

function clientIp(request: NextRequest) {
  return request.headers.get("x-forwarded-for")?.split(",").at(-1)?.trim();
}

async function apiJson(path: string, body: unknown, request: NextRequest, authorization?: string) {
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

async function tokenResponse(upstream: Response) {
  const data = await upstream.json();
  if (!upstream.ok) return NextResponse.json(data, { status: upstream.status });
  const response = NextResponse.json({ authenticated: true });
  setSession(response, data);
  return response;
}

export async function POST(request: NextRequest, context: { params: Promise<{ action: string }> }) {
  const { action } = await context.params;
  if (action === "register" || action === "login") {
    return tokenResponse(await apiJson(`/auth/${action}`, await request.json(), request));
  }
  if (action === "logout") {
    const refresh = request.cookies.get("eklavya_refresh")?.value;
    if (refresh) await apiJson("/auth/logout", { refresh_token: refresh }, request);
    const response = NextResponse.json({ authenticated: false });
    clearSession(response);
    return response;
  }
  return NextResponse.json({ detail: "Unknown authentication action" }, { status: 404 });
}

async function refreshSession(request: NextRequest) {
  const refresh = request.cookies.get("eklavya_refresh")?.value;
  if (!refresh) return null;
  const upstream = await apiJson("/auth/refresh", { refresh_token: refresh }, request);
  if (!upstream.ok) return null;
  return upstream.json() as Promise<{ access_token: string; refresh_token: string }>;
}

export async function GET(request: NextRequest, context: { params: Promise<{ action: string }> }) {
  const { action } = await context.params;
  if (action !== "me") return NextResponse.json({ detail: "Unknown authentication action" }, { status: 404 });
  let access = request.cookies.get("eklavya_access")?.value;
  let session: { access_token: string; refresh_token: string } | null = null;
  let upstream = access ? await backend("/auth/me", { headers: { Authorization: `Bearer ${access}` } }) : null;
  if (!upstream || upstream.status === 401) {
    session = await refreshSession(request);
    if (session) {
      access = session.access_token;
      upstream = await backend("/auth/me", { headers: { Authorization: `Bearer ${access}` } });
    }
  }
  if (!upstream?.ok) {
    const response = NextResponse.json({ detail: "Authentication required" }, { status: 401 });
    clearSession(response);
    return response;
  }
  const response = NextResponse.json(await upstream.json());
  if (session) setSession(response, session);
  return response;
}

export async function PATCH(request: NextRequest, context: { params: Promise<{ action: string }> }) {
  const { action } = await context.params;
  if (action !== "me") return NextResponse.json({ detail: "Unknown authentication action" }, { status: 404 });
  const access = request.cookies.get("eklavya_access")?.value;
  if (!access) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  const upstream = await backend("/auth/me", {
    method: "PATCH", headers: { "Content-Type": "application/json", Authorization: `Bearer ${access}` },
    body: JSON.stringify(await request.json()),
  });
  return NextResponse.json(await upstream.json(), { status: upstream.status });
}
