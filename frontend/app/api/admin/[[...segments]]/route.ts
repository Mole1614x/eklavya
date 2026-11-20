import { NextRequest, NextResponse } from "next/server";
import { applySession, authenticatedBackend } from "@/lib/auth-session";
import { rejectCrossSiteMutation } from "@/lib/request-security";

type Context = { params: Promise<{ segments?: string[] }> };
type Method = "GET" | "POST" | "PUT" | "PATCH";

async function proxy(request: NextRequest, context: Context, method: Method) {
  const rejected = rejectCrossSiteMutation(request);
  if (rejected) return rejected;
  const segments = (await context.params).segments ?? [];
  const path = `/admin/${segments.map(encodeURIComponent).join("/")}${request.nextUrl.search}`.replace(/\/$/, "");
  const headers: Record<string, string> = {};
  let body: string | undefined;
  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(await request.json());
  }
  const { upstream, session } = await authenticatedBackend(request, path, { method, headers, body });
  if (!upstream) {
    return applySession(
      NextResponse.json({ detail: "Administrator authentication is required" }, { status: 401 }),
      null,
      true,
    );
  }
  const contentType = upstream.headers.get("content-type") ?? "";
  let response: NextResponse;
  if (upstream.status === 204) {
    response = new NextResponse(null, { status: 204 });
  } else if (contentType.includes("application/json")) {
    response = NextResponse.json(await upstream.json(), { status: upstream.status });
  } else {
    response = new NextResponse(await upstream.arrayBuffer(), {
      status: upstream.status,
      headers: {
        "Content-Type": contentType || "application/octet-stream",
        ...(upstream.headers.get("content-disposition")
          ? { "Content-Disposition": upstream.headers.get("content-disposition")! }
          : {}),
      },
    });
  }
  return applySession(response, session, upstream.status === 401);
}

export function GET(request: NextRequest, context: Context) {
  return proxy(request, context, "GET");
}

export function POST(request: NextRequest, context: Context) {
  return proxy(request, context, "POST");
}

export function PUT(request: NextRequest, context: Context) {
  return proxy(request, context, "PUT");
}

export function PATCH(request: NextRequest, context: Context) {
  return proxy(request, context, "PATCH");
}
