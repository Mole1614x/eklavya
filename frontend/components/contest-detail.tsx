"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { Contest } from "./arena-data";

type Problem = { slug: string; title: string; difficulty: string; position: number; points: number };
type Detail = Contest & { problems: Problem[] };
type Standing = { position: number; username: string; display_name: string; score: number; solved: number; penalty_seconds: number };
type Participant = { registered: boolean; rating: number; submissions: number };

function duration(seconds: number) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remaining = seconds % 60;
  return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${remaining.toString().padStart(2, "0")}`;
}

export function ContestDetail({ slug }: { slug: string }) {
  const [contest, setContest] = useState<Detail | null>(null);
  const [participant, setParticipant] = useState<Participant | null>(null);
  const [standings, setStandings] = useState<Standing[]>([]);
  const [message, setMessage] = useState("");
  const [now, setNow] = useState(() => Date.now());

  const refresh = useCallback(async () => {
    const response = await fetch(`/api/contests/${encodeURIComponent(slug)}`);
    if (!response.ok) { setMessage("Contest not found."); return; }
    const detail: Detail = await response.json();
    setContest(detail);
    const [me, board] = await Promise.all([
      fetch(`/api/contests/${encodeURIComponent(slug)}/me`),
      fetch(`/api/contests/${encodeURIComponent(slug)}/leaderboard`),
    ]);
    if (me.ok) setParticipant(await me.json());
    if (board.ok) setStandings(await board.json());
  }, [slug]);

  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  async function register() {
    setMessage("");
    const response = await fetch(`/api/contests/${encodeURIComponent(slug)}/register`, { method: "POST" });
    if (!response.ok) { const data = await response.json(); setMessage(data.detail ?? "Registration failed."); return; }
    setMessage("Registration confirmed. See you in the Arena.");
    await refresh();
  }

  if (!contest) return <section className="card state" role="status">{message || "Loading contest…"}</section>;
  const target = contest.status === "UPCOMING" ? new Date(contest.starts_at).getTime() : new Date(contest.ends_at).getTime();
  const remaining = Math.max(0, Math.floor((target - now) / 1000));
  return <>
    <Link className="back-link" href="/arena">← Arena schedule</Link>
    <header className="page-header compact contest-hero">
      <div><p className="eyebrow">{contest.is_rated ? "Rated contest" : "Practice contest"}</p><h1>{contest.title}</h1><p>{contest.description}</p></div>
      <div className="contest-clock"><small>{contest.status === "UPCOMING" ? "STARTS IN" : contest.status === "ACTIVE" ? "ENDS IN" : "CONTEST ENDED"}</small><strong>{contest.status === "FINISHED" ? "Final" : duration(remaining)}</strong></div>
    </header>
    <section className="contest-actions card">
      <div><strong>{participant?.registered ? "Registered" : "Not registered"}</strong><p>{participant ? `${participant.rating} rating · ${participant.submissions} contest submissions` : "Sign in to register and see your rating."}</p></div>
      {contest.status === "UPCOMING" && !participant?.registered && <button className="button" onClick={() => void register()}>Register</button>}
    </section>
    {message && <p className="contest-message" role="status">{message}</p>}
    {contest.status === "UPCOMING" ? <section className="card state">Problems unlock when the contest begins. Registration closes at the start time.</section> : (
      <section><div className="section-heading contest-heading"><h2>Problems</h2><p>Wrong attempts add 20 minutes after a solve.</p></div><ol className="card contest-problems">{contest.problems.map((problem) => <li key={problem.slug}><strong>{String.fromCharCode(64 + problem.position)}</strong><span><b>{problem.title}</b><small>{problem.difficulty} · {problem.points} points</small></span><Link href={`/problems/${problem.slug}?contest=${encodeURIComponent(slug)}`}>Solve →</Link></li>)}</ol></section>
    )}
    <section><div className="section-heading contest-heading"><h2>Leaderboard</h2><p>Score, then penalty time.</p></div>{standings.length ? <ol className="card contest-board">{standings.map((row) => <li key={row.username}><strong>#{row.position}</strong><span><b>{row.display_name}</b><small>@{row.username}</small></span><span>{row.score} pts<small>{row.solved} solved · {Math.floor(row.penalty_seconds / 60)} min</small></span></li>)}</ol> : <div className="card state">No standings yet.</div>}</section>
  </>;
}
