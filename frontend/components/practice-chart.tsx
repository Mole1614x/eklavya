"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Analytics = {
  totals: { questions_attempted: number; questions_solved: number; accuracy: number; assessments_completed: number };
  subjects: Array<{ subject: string; attempted: number; solved: number; accuracy: number }>;
  daily: Array<{ day: string; attempted: number; solved: number }>;
  weak_topics: string[];
};

const demoActivity = [
  { day: "Mon", solved: 2 }, { day: "Tue", solved: 4 }, { day: "Wed", solved: 3 },
  { day: "Thu", solved: 6 }, { day: "Fri", solved: 4 }, { day: "Sat", solved: 5 }, { day: "Sun", solved: 2 },
];

export function PracticeChart({ verified = false }: { verified?: boolean }) {
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "account" | "error">("loading");
  useEffect(() => {
    if (!verified) return;
    const controller = new AbortController();
    void fetch("/api/advanced/analytics", { signal: controller.signal }).then(async (response) => {
      if (response.status === 401) { setState("account"); return; }
      if (!response.ok) { setState("error"); return; }
      setAnalytics(await response.json() as Analytics); setState("ready");
    }).catch((error: unknown) => { if (!(error instanceof DOMException && error.name === "AbortError")) setState("error"); });
    return () => controller.abort();
  }, [verified]);
  if (!verified) return <section className="card chart-card"><div className="section-heading"><div><h2>Practice activity</h2><p>Problems solved this week</p></div><span className="pill">Demo data</span></div><div className="chart" aria-label={demoActivity.map(({ day, solved }) => `${day} ${solved}`).join(", ")} role="img"><ResponsiveContainer width="100%" height="100%" minWidth={0}><BarChart data={demoActivity} margin={{ top: 12, right: 8, left: -20, bottom: 0 }}><XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: "#a4adc6", fontSize: 12 }} dy={8} /><YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: "#a4adc6", fontSize: 12 }} /><Tooltip cursor={{ fill: "#202941" }} contentStyle={{ background: "#151c2f", border: "1px solid #303952", borderRadius: 8 }} /><Bar name="Solved" dataKey="solved" fill="#F5A623" radius={[5, 5, 0, 0]} maxBarSize={34} /></BarChart></ResponsiveContainer></div></section>;
  if (state === "loading") return <section className="card state" role="status">Loading verified skill analytics…</section>;
  if (state === "account") return <section className="card state"><p>Sign in to see your verified skill analytics.</p><Link href="/auth" className="button">Sign in</Link></section>;
  if (state === "error" || !analytics) return <section className="card state" role="alert">Skill analytics are temporarily unavailable.</section>;
  const activity = analytics.daily.slice(-14).map((item) => ({ ...item, day: item.day.slice(5) }));
  return (
    <div className="advanced-stack">
      <section className="card"><div className="section-heading"><div><h2>Verified progress</h2><p>Calculated from your submitted solutions and finalized assessments.</p></div><span className="pill">Live data</span></div><div className="admin-metrics">{[
        ["Attempted", analytics.totals.questions_attempted], ["Solved", analytics.totals.questions_solved],
        ["Accuracy", `${analytics.totals.accuracy}%`], ["Assessments", analytics.totals.assessments_completed],
      ].map(([label, value]) => <div key={String(label)}><small>{label}</small><strong>{value}</strong></div>)}</div></section>
      <div className="insight-grid">
        <section className="card chart-card">
          <div className="section-heading"><div><h2>Recent activity</h2><p>Latest 14 active days</p></div></div>
          {activity.length ? <div className="chart" aria-label={activity.map(({ day, solved }) => `${day} ${solved} solved`).join(", ")} role="img"><ResponsiveContainer width="100%" height="100%" minWidth={0}><BarChart data={activity} margin={{ top: 12, right: 8, left: -20, bottom: 0 }}><XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: "#a4adc6", fontSize: 12 }} dy={8} /><YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: "#a4adc6", fontSize: 12 }} /><Tooltip cursor={{ fill: "#202941" }} contentStyle={{ background: "#151c2f", border: "1px solid #303952", borderRadius: 8 }} /><Bar name="Solved" dataKey="solved" fill="#F5A623" radius={[5, 5, 0, 0]} maxBarSize={34} /></BarChart></ResponsiveContainer></div> : <p>Your submitted practice activity will appear here.</p>}
        </section>
        <section className="card insight-list"><h2>Subject mastery</h2>{analytics.subjects.length ? analytics.subjects.map((item) => <div key={item.subject}><span>{item.subject}<small>{item.solved} of {item.attempted} solved</small></span><strong>{item.accuracy}%</strong></div>) : <p>Complete problems to build your subject profile.</p>}{analytics.weak_topics.length > 0 && <p><strong>Focus next:</strong> {analytics.weak_topics.join(", ")}</p>}</section>
      </div>
    </div>
  );
}
