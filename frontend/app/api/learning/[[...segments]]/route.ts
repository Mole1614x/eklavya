import { NextRequest, NextResponse } from "next/server";
import { backend } from "@/lib/backend";

export async function GET(request: NextRequest, context: { params: Promise<{ segments?: string[] }> }) {
  const segments = (await context.params).segments ?? [];
  const access = request.cookies.get("eklavya_access")?.value;
  const protectedRoute = segments.includes("history") || (segments[0] === "paths" && segments.length > 1);
  if (protectedRoute && !access) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  const upstream = await backend(`/learning/${segments.map(encodeURIComponent).join("/")}`, { headers: access ? { Authorization: `Bearer ${access}` } : {} });
  return NextResponse.json(await upstream.json(), { status: upstream.status });
}

export async function POST(request: NextRequest, context: { params: Promise<{ segments?: string[] }> }) {
  const segments = (await context.params).segments ?? [];
  const access = request.cookies.get("eklavya_access")?.value;
  if (!access) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  const upstream = await backend(`/learning/${segments.map(encodeURIComponent).join("/")}`, { method: "POST", headers: { Authorization: `Bearer ${access}` } });
  return upstream.status === 204 ? new NextResponse(null, { status: 204 }) : NextResponse.json(await upstream.json(), { status: upstream.status });
}
