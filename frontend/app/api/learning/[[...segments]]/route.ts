import { NextRequest, NextResponse } from "next/server";
import { backend } from "@/lib/backend";
import { applySession, authenticatedBackend } from "@/lib/auth-session";
import { rejectCrossSiteMutation } from "@/lib/request-security";

export async function GET(request: NextRequest, context: { params: Promise<{ segments?: string[] }> }) {
  const segments = (await context.params).segments ?? [];
  const access = request.cookies.get("eklavya_access")?.value;
  const protectedRoute = segments.includes("history") || (segments[0] === "paths" && segments.length > 1);
  const path = `/learning/${segments.map(encodeURIComponent).join("/")}`;
  if (!protectedRoute && !access) {
    const upstream = await backend(path);
    return NextResponse.json(await upstream.json(), { status: upstream.status });
  }
  const { upstream, session } = await authenticatedBackend(request, path);
  if (!upstream) return applySession(NextResponse.json({ detail: "Authentication required" }, { status: 401 }), null, true);
  return applySession(NextResponse.json(await upstream.json(), { status: upstream.status }), session, upstream.status === 401);
}

export async function POST(request: NextRequest, context: { params: Promise<{ segments?: string[] }> }) {
  const rejected = rejectCrossSiteMutation(request);
  if (rejected) return rejected;
  const segments = (await context.params).segments ?? [];
  const { upstream, session } = await authenticatedBackend(request, `/learning/${segments.map(encodeURIComponent).join("/")}`, { method: "POST" });
  if (!upstream) return applySession(NextResponse.json({ detail: "Authentication required" }, { status: 401 }), null, true);
  const response = upstream.status === 204 ? new NextResponse(null, { status: 204 }) : NextResponse.json(await upstream.json(), { status: upstream.status });
  return applySession(response, session, upstream.status === 401);
}
