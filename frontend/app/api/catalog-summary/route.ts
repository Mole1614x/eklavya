import { NextResponse } from "next/server";
import { backend } from "@/lib/backend";

export async function GET() {
  try {
    const response = await backend("/subjects");
    if (!response.ok) return NextResponse.json({ detail: "Catalogue unavailable" }, { status: response.status });
    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ detail: "Catalogue temporarily unavailable" }, { status: 503 });
  }
}
