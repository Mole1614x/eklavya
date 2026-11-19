"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export function CommunityData({ section }: { section: string }) {
  const action = section === "rankings" ? "leaderboard" : section === "badges" ? "achievements" : section === "progress-insights" ? "insights" : null;
  const [data, setData] = useState<unknown>(null);
  const [requiresAccount, setRequiresAccount] = useState(false);
  useEffect(() => {
    if (!action) return;
    void fetch(`/api/gamification/${action}`).then(async (response) => {
      if (response.status === 401) { setRequiresAccount(true); return; }
      if (response.ok) setData(await response.json());
    });
  }, [action]);
  if (!action) return null;
  if (requiresAccount) return <section className="card state"><p>Sign in to see your verified {section === "badges" ? "achievements" : "progress insights"}.</p><Link href="/auth" className="button">Sign in</Link></section>;
  if (!data) return <section className="card state" role="status">Loading verified data…</section>;
  if (section === "rankings") return <ol className="card leaderboard">{(data as Array<Record<string, string | number>>).map((row) => <li key={String(row.username)}><strong>#{row.position}</strong><span>{row.display_name}<small>@{row.username} · {row.rank}</small></span><b>{row.xp} XP</b></li>)}</ol>;
  if (section === "badges") return <ul className="skills-grid clean-list">{(data as Array<Record<string, string | number | null>>).map((badge) => <li className={`card feature-card ${badge.earned_at ? "earned" : "locked"}`} key={String(badge.slug)}><h2>{badge.name}</h2><p>{badge.description}</p><small>{badge.earned_at ? "Earned" : `${badge.xp_reward} XP reward`}</small></li>)}</ul>;
  const insights = data as { daily_activity: { day: string; count: number }[]; xp_growth: { day: string; amount: number }[] };
  return <div className="insight-grid"><section className="card insight-list"><h2>Daily activity</h2>{insights.daily_activity.length ? insights.daily_activity.map((item) => <div key={item.day}><span>{item.day}</span><strong>{item.count} submissions</strong></div>) : <p>Your submission activity will appear here.</p>}</section><section className="card insight-list"><h2>XP growth</h2>{insights.xp_growth.length ? insights.xp_growth.map((item) => <div key={item.day}><span>{item.day}</span><strong>+{item.amount} XP</strong></div>) : <p>Accepted first solves will appear here.</p>}</section></div>;
}
