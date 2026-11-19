"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type Daily = { date: string; timezone: string; problem_slug: string; title: string; difficulty: string; xp_reward: number };
type Path = { slug: string; title: string; description: string; prerequisites: string[]; problem_count: number };

export function LearningData({ section }: { section: "daily-sadhana" | "vidya-paths" }) {
  const [data, setData] = useState<Daily | Path[] | null>(null);
  useEffect(() => { void fetch(section === "daily-sadhana" ? "/api/learning/daily" : "/api/learning/paths").then(async (response) => { if (response.ok) setData(await response.json()); }); }, [section]);
  if (!data) return <section className="card state" role="status">Loading the learning schedule…</section>;
  if (section === "daily-sadhana") {
    const daily = data as Daily;
    return <section className="card daily-live"><div><span className="pill">{daily.date} · {daily.timezone}</span><h2>{daily.title}</h2><p>{daily.difficulty} · {daily.xp_reward} bonus XP after a verified solve</p></div><Link className="button" href={`/problems/${daily.problem_slug}`}>Open challenge</Link></section>;
  }
  return <ul className="path-grid clean-list">{(data as Path[]).map((path) => <li className="card path-card" key={path.slug}><div><h2>{path.title}</h2><p>{path.description}</p><small>{path.problem_count} assignments{path.prerequisites.length ? ` · Requires ${path.prerequisites.join(", ")}` : ""}</small></div><Link className="button secondary" href={`/paths/${path.slug}`}>View path</Link></li>)}</ul>;
}
