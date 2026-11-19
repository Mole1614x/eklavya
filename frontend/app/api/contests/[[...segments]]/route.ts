import { NextRequest, NextResponse } from "next/server";
import { backend } from "@/lib/backend";

type Context = { params: Promise<{ segments?: string[] }> };

async function proxy(request: NextRequest, context: Context, method: "GET" | "POST") {
  const segments = (await context.params).segments ?? [];
  const access = request.cookies.get("eklavya_access")?.value;
  const needsAuth = method === "POST" || segments.includes("me");
  if (needsAuth && !access) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  const headers: Record<string, string> = access ? { Authorization: `Bearer ${access}` } : {};
  let body: string | undefined;
  if (method === "POST" && request.headers.get("content-type")?.includes("application/json")) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(await request.json());
  }
  const path = `/contests/${segments.map(encodeURIComponent).join("/")}${request.nextUrl.search}`.replace(/\/$/, "");
  const upstream = await backend(path, { method, headers, body });
  if (upstream.status === 204) return new NextResponse(null, { status: 204 });
  return NextResponse.json(await upstream.json(), { status: upstream.status });
}

export function GET(request: NextRequest, context: Context) {
  return proxy(request, context, "GET");
}

export function POST(request: NextRequest, context: Context) {
  return proxy(request, context, "POST");
}
