import "server-only";

import { NextRequest, NextResponse } from "next/server";

const unsafeMethods = new Set(["POST", "PUT", "PATCH", "DELETE"]);

/**
 * SameSite cookies are the first CSRF boundary. This origin check is the
 * second boundary for browser mutations routed through the cookie-based BFF.
 * Requests without browser origin metadata remain usable by trusted CLI and
 * test clients; they still need valid HttpOnly session cookies.
 */
export function rejectCrossSiteMutation(request: NextRequest): NextResponse | null {
  if (!unsafeMethods.has(request.method)) return null;
  if (request.headers.get("sec-fetch-site") === "cross-site") {
    return NextResponse.json({ detail: "Cross-site request rejected" }, { status: 403 });
  }

  const origin = request.headers.get("origin");
  if (!origin) return null;
  const forwardedHost = request.headers.get("x-forwarded-host")?.split(",")[0]?.trim();
  const forwardedProtocol = request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim();
  const requestHost = forwardedHost || request.headers.get("host");
  const requestProtocol = forwardedProtocol || request.nextUrl.protocol.replace(":", "");
  try {
    const parsedOrigin = new URL(origin);
    if (!requestHost || parsedOrigin.host !== requestHost || parsedOrigin.protocol !== `${requestProtocol}:`) {
      return NextResponse.json({ detail: "Cross-site request rejected" }, { status: 403 });
    }
  } catch {
    return NextResponse.json({ detail: "Invalid request origin" }, { status: 403 });
  }
  return null;
}
