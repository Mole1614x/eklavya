import { NextRequest, NextResponse } from "next/server";
import { backend } from "@/lib/backend";
import { applySession, authenticatedBackend } from "@/lib/auth-session";
import { rejectCrossSiteMutation } from "@/lib/request-security";

type Context = { params: Promise<{ segments?: string[] }> };

async function proxy(request: NextRequest, context: Context, method: "GET" | "POST") {
  const rejected = rejectCrossSiteMutation(request);
  if (rejected) return rejected;
  const segments = (await context.params).segments ?? [];
  const access = request.cookies.get("eklavya_access")?.value;
  const needsAuth = method === "POST" || segments.includes("me");
  const headers: Record<string, string> = {};
  let body: string | undefined;
  if (method === "POST" && request.headers.get("content-type")?.includes("application/json")) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(await request.json());
  }
  const path = `/contests/${segments.map(encodeURIComponent).join("/")}${request.nextUrl.search}`.replace(/\/$/, "");
  if (!needsAuth && !access) {
    const upstream = await backend(path, { method, headers, body });
    return upstream.status === 204 ? new NextResponse(null, { status: 204 }) : NextResponse.json(await upstream.json(), { status: upstream.status });
  }
  const { upstream, session } = await authenticatedBackend(request, path, { method, headers, body });
  if (!upstream) return applySession(NextResponse.json({ detail: "Authentication required" }, { status: 401 }), null, true);
  const response = upstream.status === 204 ? new NextResponse(null, { status: 204 }) : NextResponse.json(await upstream.json(), { status: upstream.status });
  return applySession(response, session, upstream.status === 401);
}

export function GET(request: NextRequest, context: Context) {
  return proxy(request, context, "GET");
}

export function POST(request: NextRequest, context: Context) {
  return proxy(request, context, "POST");
}
