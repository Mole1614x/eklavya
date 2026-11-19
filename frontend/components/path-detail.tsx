"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type Detail = { slug: string; title: string; description: string; enrolled: boolean; completion_percentage: number; problems: { slug: string; title: string; position: number; milestone: string | null; completed: boolean }[] };

export function PathDetail({ slug }: { slug: string }) {
  const [detail, setDetail] = useState<Detail | null>(null);
  const [requiresAccount, setRequiresAccount] = useState(false);
  async function load() { const response = await fetch(`/api/learning/paths/${slug}`); if (response.status === 401) setRequiresAccount(true); else if (response.ok) setDetail(await response.json()); }
  useEffect(() => { void load(); }, [slug]);
  async function enroll() { const response = await fetch(`/api/learning/paths/${slug}/enroll`, { method: "POST" }); if (response.ok) await load(); }
  if (requiresAccount) return <section className="card state"><h1>Sign in to open this learning path</h1><Link className="button" href="/auth">Sign in</Link></section>;
  if (!detail) return <section className="card state" role="status">Loading path…</section>;
  return <><header className="page-header"><p className="eyebrow">Vidya Path</p><h1>{detail.title}</h1><p>{detail.description}</p>{detail.enrolled ? <span className="pill">{detail.completion_percentage}% complete</span> : <button className="button" onClick={() => void enroll()}>Enroll</button>}</header><ol className="card path-steps">{detail.problems.map((problem) => <li key={problem.slug} className={problem.completed ? "complete" : ""}><strong>{problem.position}</strong><span>{problem.title}{problem.milestone && <small>{problem.milestone}</small>}</span><Link href={`/problems/${problem.slug}`}>{problem.completed ? "Review" : "Practice"}</Link></li>)}</ol></>;
}
