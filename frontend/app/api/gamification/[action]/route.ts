import { NextRequest, NextResponse } from "next/server";
import { backend } from "@/lib/backend";

const publicActions = new Set(["ranks", "leaderboard"]);

export async function GET(request: NextRequest, context: { params: Promise<{ action: string }> }) {
  const { action } = await context.params;
  const access = request.cookies.get("eklavya_access")?.value;
  if (!publicActions.has(action) && !access) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  const upstream = await backend(`/gamification/${encodeURIComponent(action)}${request.nextUrl.search}`, {
    headers: access ? { Authorization: `Bearer ${access}` } : {},
  });
  return NextResponse.json(await upstream.json(), { status: upstream.status });
}
