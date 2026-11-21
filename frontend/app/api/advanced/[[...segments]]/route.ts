import { NextRequest, NextResponse } from "next/server";
import { applySession, authenticatedBackend } from "@/lib/auth-session";
import { rejectCrossSiteMutation } from "@/lib/request-security";

type Context = { params: Promise<{ segments?: string[] }> };
type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

async function proxy(request: NextRequest, context: Context, method: Method) {
  if (method !== "GET") {
    const rejected = rejectCrossSiteMutation(request);
    if (rejected) return rejected;
  }
  const segments = (await context.params).segments ?? [];
  const path = `/advanced/${segments.map(encodeURIComponent).join("/")}${request.nextUrl.search}`.replace(/\/$/, "");
  const headers: Record<string, string> = {};
  let body: string | undefined;
  if (!["GET", "DELETE"].includes(method)) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(await request.json());
  }
  const { upstream, session } = await authenticatedBackend(request, path, { method, headers, body });
  if (!upstream) return applySession(NextResponse.json({ detail: "Authentication required" }, { status: 401 }), null, true);
  const contentType = upstream.headers.get("content-type") ?? "";
  const response = upstream.status === 204
    ? new NextResponse(null, { status: 204 })
    : contentType.includes("application/json")
      ? NextResponse.json(await upstream.json(), { status: upstream.status })
      : new NextResponse(await upstream.arrayBuffer(), {
          status: upstream.status,
          headers: {
            "Content-Type": contentType || "application/octet-stream",
            ...(upstream.headers.get("content-disposition") ? { "Content-Disposition": upstream.headers.get("content-disposition")! } : {}),
          },
        });
  return applySession(response, session, upstream.status === 401);
}

export function GET(request: NextRequest, context: Context) { return proxy(request, context, "GET"); }
export function POST(request: NextRequest, context: Context) { return proxy(request, context, "POST"); }
export function PUT(request: NextRequest, context: Context) { return proxy(request, context, "PUT"); }
export function PATCH(request: NextRequest, context: Context) { return proxy(request, context, "PATCH"); }
export function DELETE(request: NextRequest, context: Context) { return proxy(request, context, "DELETE"); }
