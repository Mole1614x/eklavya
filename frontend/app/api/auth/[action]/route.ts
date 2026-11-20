import { NextRequest, NextResponse } from "next/server";
import { apiJson, applySession, authenticatedBackend, clearSession, setSession } from "@/lib/auth-session";
import { rejectCrossSiteMutation } from "@/lib/request-security";

async function tokenResponse(upstream: Response) {
  const data = await upstream.json();
  if (!upstream.ok) return NextResponse.json(data, { status: upstream.status });
  const response = NextResponse.json({ authenticated: true });
  setSession(response, data);
  return response;
}

export async function POST(request: NextRequest, context: { params: Promise<{ action: string }> }) {
  const rejected = rejectCrossSiteMutation(request);
  if (rejected) return rejected;
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

export async function GET(request: NextRequest, context: { params: Promise<{ action: string }> }) {
  const { action } = await context.params;
  if (action !== "me") return NextResponse.json({ detail: "Unknown authentication action" }, { status: 404 });
  const { upstream, session } = await authenticatedBackend(request, "/auth/me");
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
  const rejected = rejectCrossSiteMutation(request);
  if (rejected) return rejected;
  const { action } = await context.params;
  if (action !== "me") return NextResponse.json({ detail: "Unknown authentication action" }, { status: 404 });
  const { upstream, session } = await authenticatedBackend(request, "/auth/me", {
    method: "PATCH", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(await request.json()),
  });
  if (!upstream) return applySession(NextResponse.json({ detail: "Authentication required" }, { status: 401 }), null, true);
  return applySession(NextResponse.json(await upstream.json(), { status: upstream.status }), session, upstream.status === 401);
}
