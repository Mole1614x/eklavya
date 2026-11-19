"use client";

import Link from "next/link";
import { ArrowRight, Flame, Trophy } from "lucide-react";
import { useEffect, useState } from "react";
import type { Contest } from "./arena-data";

type Daily = { problem_slug: string; title: string; difficulty: string; xp_reward: number };

export function DashboardSchedule() {
  const [daily, setDaily] = useState<Daily | null>(null);
  const [contest, setContest] = useState<Contest | null>(null);
  useEffect(() => {
    void Promise.all([
      fetch("/api/learning/daily").then((response) => response.ok ? response.json() as Promise<Daily> : null),
      fetch("/api/contests").then((response) => response.ok ? response.json() as Promise<Contest[]> : []),
    ]).then(([dailyChallenge, contests]) => {
      setDaily(dailyChallenge);
      setContest(contests.find((item) => item.status !== "FINISHED") ?? contests[0] ?? null);
    });
  }, []);
  return <>
    <section className="card daily-card">
      <div className="section-heading"><h2><Flame size={17} /> Daily Sadhana</h2><span className="pill">Live</span></div>
      <p>{daily ? `${daily.title} · ${daily.difficulty} · ${daily.xp_reward} bonus XP` : "Today’s challenge is loading."}</p>
      <Link href={daily ? `/problems/${daily.problem_slug}` : "/daily-sadhana"}>Open daily challenge <ArrowRight size={15} /></Link>
    </section>
    <section className="card daily-card">
      <div className="section-heading"><h2><Trophy size={17} /> Eklavya Arena</h2><span className="pill">{contest?.status ?? "Schedule"}</span></div>
      <p>{contest ? `${contest.title} · ${new Date(contest.starts_at).toLocaleString()}` : "The next contest will be announced soon."}</p>
      <Link href={contest ? `/arena/${contest.slug}` : "/arena"}>View contest <ArrowRight size={15} /></Link>
    </section>
  </>;
}
