import { NextRequest, NextResponse } from "next/server";
import { applySession, authenticatedBackend } from "@/lib/auth-session";

async function authorized(request: NextRequest, path: string, init: RequestInit = {}) {
  const { upstream, session } = await authenticatedBackend(request, path, init);
  if (!upstream) return applySession(NextResponse.json({ detail: "Sign in to run or submit solutions." }, { status: 401 }), null, true);
  const data = upstream.status === 204 ? null : await upstream.json();
  const response = data === null ? new NextResponse(null, { status: upstream.status }) : NextResponse.json(data, { status: upstream.status });
  return applySession(response, session, upstream.status === 401);
}

export async function GET(request: NextRequest, context: { params: Promise<{ segments?: string[] }> }) {
  const segments = (await context.params).segments ?? [];
  const path = segments.length ? `/submissions/${encodeURIComponent(segments[0])}` : `/submissions${request.nextUrl.search}`;
  return authorized(request, path);
}

export async function POST(request: NextRequest, context: { params: Promise<{ segments?: string[] }> }) {
  const segments = (await context.params).segments ?? [];
  if (segments[0] && segments[1] === "cancel") {
    return authorized(request, `/submissions/${encodeURIComponent(segments[0])}/cancel`, { method: "POST" });
  }
  if (segments[0] !== "problem" || !segments[1]) return NextResponse.json({ detail: "Problem is required" }, { status: 404 });
  return authorized(request, `/problems/${encodeURIComponent(segments[1])}/submissions`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(await request.json()),
  });
}
