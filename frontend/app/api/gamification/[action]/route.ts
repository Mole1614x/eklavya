import { NextRequest, NextResponse } from "next/server";
import { backend } from "@/lib/backend";
import { applySession, authenticatedBackend } from "@/lib/auth-session";

const publicActions = new Set(["ranks", "leaderboard"]);

export async function GET(request: NextRequest, context: { params: Promise<{ action: string }> }) {
  const { action } = await context.params;
  const access = request.cookies.get("eklavya_access")?.value;
  const path = `/gamification/${encodeURIComponent(action)}${request.nextUrl.search}`;
  if (publicActions.has(action) && !access) {
    const upstream = await backend(path);
    return NextResponse.json(await upstream.json(), { status: upstream.status });
  }
  const { upstream, session } = await authenticatedBackend(request, path);
  if (!upstream) return applySession(NextResponse.json({ detail: "Authentication required" }, { status: 401 }), null, true);
  return applySession(NextResponse.json(await upstream.json(), { status: upstream.status }), session, upstream.status === 401);
}
