"use client";

import Link from "next/link";
import { CheckCircle2, Star, Target, Zap } from "lucide-react";
import { useEffect, useState } from "react";

type Dashboard = { xp: number; solved_count: number; rank: string; stars: number; next_rank: string | null; next_rank_xp: number | null; submission_accuracy: number };

export function LiveProgress() {
  const [data, setData] = useState<Dashboard | null | undefined>(undefined);
  useEffect(() => { void fetch("/api/gamification/dashboard").then(async (response) => setData(response.ok ? await response.json() : null)); }, []);
  if (data === undefined) return <section className="card state" role="status">Loading your verified progress…</section>;
  if (data === null) return <section className="card sign-in-progress"><div><h2>Save your real progress</h2><p>Sign in to earn verified XP, ranks, and achievements from accepted submissions.</p></div><Link className="button" href="/auth">Sign in</Link></section>;
  return <section className="live-progress"><article className="card stat"><span className="tile green"><CheckCircle2 size={19} /></span><div><p>Verified solves</p><strong>{data.solved_count}</strong></div></article><article className="card stat"><span className="tile purple"><Zap size={19} /></span><div><p>Total XP</p><strong>{data.xp}</strong></div></article><article className="card stat"><span className="tile orange"><Star size={19} /></span><div><p>{data.rank}</p><strong aria-label={`${data.stars} stars`}>{"★".repeat(data.stars)}</strong></div></article><article className="card stat"><span className="tile"><Target size={19} /></span><div><p>Accuracy</p><strong>{data.submission_accuracy}%</strong></div></article></section>;
}
