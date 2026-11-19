import { NextRequest, NextResponse } from "next/server";
import { backend } from "@/lib/backend";

async function authorized(request: NextRequest, path: string, init: RequestInit = {}) {
  const access = request.cookies.get("eklavya_access")?.value;
  if (!access) return NextResponse.json({ detail: "Sign in to run or submit solutions." }, { status: 401 });
  const upstream = await backend(path, { ...init, headers: { ...init.headers, Authorization: `Bearer ${access}` } });
  const data = upstream.status === 204 ? null : await upstream.json();
  return data === null ? new NextResponse(null, { status: upstream.status }) : NextResponse.json(data, { status: upstream.status });
}

export async function GET(request: NextRequest, context: { params: Promise<{ segments?: string[] }> }) {
  const segments = (await context.params).segments ?? [];
  const path = segments.length ? `/submissions/${encodeURIComponent(segments[0])}` : `/submissions${request.nextUrl.search}`;
  return authorized(request, path);
}

export async function POST(request: NextRequest, context: { params: Promise<{ segments?: string[] }> }) {
  const segments = (await context.params).segments ?? [];
  if (segments[0] !== "problem" || !segments[1]) return NextResponse.json({ detail: "Problem is required" }, { status: 404 });
  return authorized(request, `/problems/${encodeURIComponent(segments[1])}/submissions`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(await request.json()),
  });
}
