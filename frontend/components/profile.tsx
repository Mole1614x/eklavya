"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Activity, ArrowUpRight, Award, CalendarDays, CheckCircle2, Code2, Flame, LogOut, Pencil, ShieldCheck, Target, Trophy, Zap } from "lucide-react";

type User = { email: string; username: string; role: string; email_verified: boolean; profile: { display_name?: string; bio?: string; timezone?: string } };
type Progress = { xp: number; solved_count: number; rank: string; stars: number; next_rank: string | null; next_rank_xp: number | null; accepted_submissions: number; submission_accuracy: number };
type Insights = { daily_activity: { day: string; count: number }[]; solved_problems: { problem_slug: string; accepted_submissions: number }[] };
type Achievement = { slug: string; name: string; description: string; earned_at: string | null };
type Submission = { id: string; problem_slug: string; language: string; mode: string; status: string; verdict: string | null; created_at: string };
type History = { streak: number; completions: { date: string }[] };

function ActivityHeatmap({ entries }: { entries: Insights["daily_activity"] }) {
  const days = useMemo(() => {
    const counts = new Map(entries.map((item) => [item.day, item.count]));
    const today = new Date();
    const start = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
    start.setUTCDate(start.getUTCDate() - 83);
    const weekday = start.getUTCDay();
    start.setUTCDate(start.getUTCDate() - weekday);
    return Array.from({ length: 91 }, (_, index) => {
      const date = new Date(start);
      date.setUTCDate(start.getUTCDate() + index);
      const key = date.toISOString().slice(0, 10);
      return { date: key, count: counts.get(key) ?? 0, future: date.getTime() > Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()) };
    });
  }, [entries]);
  return <div className="lp-heatmap-wrap">
    <div className="lp-heatmap" role="img" aria-label={`Submission activity over the last 13 weeks, ${entries.reduce((sum, item) => sum + item.count, 0)} submissions in the available activity history`}>
      {days.map((day) => <span key={day.date} title={`${day.date}: ${day.count} submissions`} className={`lp-day ${day.future ? "lp-day-future" : day.count === 0 ? "" : day.count === 1 ? "lp-day-1" : day.count < 4 ? "lp-day-2" : "lp-day-3"}`} />)}
    </div>
    <div className="lp-heatmap-legend"><span>Less</span><i className="lp-day" /><i className="lp-day lp-day-1" /><i className="lp-day lp-day-2" /><i className="lp-day lp-day-3" /><span>More</span></div>
  </div>;
}

function niceDate(date: string) {
  const time = Date.parse(date);
  return Number.isFinite(time) ? new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(time) : "—";
}

export function ProfilePanel() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [insights, setInsights] = useState<Insights | null>(null);
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [history, setHistory] = useState<History | null>(null);
  const [status, setStatus] = useState("Loading profile…");
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const response = await fetch("/api/auth/me");
        if (response.status === 401) { router.replace("/auth"); return; }
        if (!response.ok) throw new Error("Profile is temporarily unavailable.");
        const current = await response.json() as User;
        if (!alive) return;
        setUser(current);
        setStatus("");
        const endpoints = [
          "/api/gamification/dashboard",
          "/api/gamification/insights",
          "/api/gamification/achievements",
          "/api/submissions?limit=12",
          "/api/learning/daily/history",
        ];
        const result = await Promise.allSettled(endpoints.map(async (url) => {
          const res = await fetch(url);
          if (!res.ok) throw new Error("Could not load " + url);
          return res.json() as Promise<unknown>;
        }));
        if (!alive) return;
        if (result[0].status === "fulfilled") setProgress(result[0].value as Progress);
        if (result[1].status === "fulfilled") setInsights(result[1].value as Insights);
        if (result[2].status === "fulfilled") setAchievements(result[2].value as Achievement[]);
        if (result[3].status === "fulfilled") setSubmissions(result[3].value as Submission[]);
        if (result[4].status === "fulfilled") setHistory(result[4].value as History);
      } catch (error) {
        if (alive) setStatus(error instanceof Error ? error.message : "Unable to load profile.");
      }
    })();
    return () => { alive = false; };
  }, [router]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("Saving…");
    try {
      const response = await fetch("/api/auth/me", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))) });
      if (!response.ok) throw new Error("Profile could not be saved.");
      setUser(await response.json() as User);
      setStatus("Profile saved.");
      setEditing(false);
    } catch (error) { setStatus(error instanceof Error ? error.message : "Profile could not be saved."); }
  }

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.replace("/auth"); router.refresh();
  }

  if (!user) return <div className="card state" role="status">{status}</div>;
  const earned = achievements.filter((item) => item.earned_at);
  const submitted = submissions.filter((item) => item.mode === "SUBMIT");
  return <div className="lp-profile">
    <aside className="lp-sidebar">
      <section className="lp-glass lp-identity">
        <div className="lp-avatar" aria-hidden="true">{(user.profile.display_name || user.username).trim().slice(0, 2).toUpperCase()}</div>
        <h2>{user.profile.display_name || user.username}</h2>
        <p className="lp-handle">@{user.username}</p>
        <p className="lp-bio">{user.profile.bio || "Your coding journey starts here. Add a short bio to introduce yourself."}</p>
        <div className="lp-identity-meta"><span><ShieldCheck size={15} /> {user.email_verified ? "Verified account" : "Verification pending"}</span><span><Code2 size={15} /> {user.role}</span></div>
        <button type="button" className="lp-edit-button" onClick={() => setEditing((value) => !value)}><Pencil size={15} /> {editing ? "Close editor" : "Edit profile"}</button>
        {user.role === "admin" && <Link className="lp-text-link" href="/admin">Open administration <ArrowUpRight size={14} /></Link>}
      </section>
      <section className="lp-glass lp-rank-card">
        <div className="lp-section-title"><Trophy size={17} /><h3>Current rank</h3></div>
        <strong>{progress?.rank ?? "Not available"}</strong>
        <p>{progress ? `${progress.stars} stars · ${progress.xp.toLocaleString()} XP` : "Earn XP by completing challenges."}</p>
        {progress?.next_rank_xp != null && <><progress value={progress.xp} max={Math.max(progress.next_rank_xp, 1)} /><small>Next: {progress.next_rank} · {Math.max(0, progress.next_rank_xp - progress.xp).toLocaleString()} XP to go</small></>}
      </section>
      {editing && <section className="lp-glass lp-form-card">
        <h3>Edit profile</h3>
        <form onSubmit={save}>
          <label>Display name<input name="display_name" defaultValue={user.profile.display_name} required /></label>
          <label>Bio<textarea name="bio" maxLength={280} defaultValue={user.profile.bio} /></label>
          <label>Timezone<input name="timezone" defaultValue={user.profile.timezone ?? "UTC"} /></label>
          <button className="button" type="submit">Save profile</button>
        </form>
      </section>}
      <button type="button" className="lp-signout" onClick={logout}><LogOut size={16} /> Sign out</button>
    </aside>

    <main className="lp-content">
      <header className="lp-header"><div><p className="lp-eyebrow">YOUR LEARNING IDENTITY</p><h1>My Profile</h1><p>All your practice and growth, in one place.</p></div><Link href="/problems" className="lp-practice-link">Practice now <ArrowUpRight size={16}/></Link></header>
      <section className="lp-stats" aria-label="Your coding statistics">
        <article className="lp-glass lp-stat"><CheckCircle2 size={20}/><span>Problems solved</span><strong>{progress?.solved_count.toLocaleString() ?? "—"}</strong><small>Verified unique solves</small></article>
        <article className="lp-glass lp-stat"><Target size={20}/><span>Submission accuracy</span><strong>{progress ? `${progress.submission_accuracy}%` : "—"}</strong><small>Accepted / finished attempts</small></article>
        <article className="lp-glass lp-stat"><Zap size={20}/><span>Total XP</span><strong>{progress?.xp.toLocaleString() ?? "—"}</strong><small>Earned through practice</small></article>
        <article className="lp-glass lp-stat"><Flame size={20}/><span>Daily challenge streak</span><strong>{history?.streak ?? "—"}</strong><small>Consecutive completions</small></article>
      </section>

      <section className="lp-glass lp-activity">
        <div className="lp-section-heading"><div><div className="lp-section-title"><CalendarDays size={18}/><h3>Submission activity</h3></div><p>Last 13 weeks · UTC dates</p></div><span className="lp-subtle">{insights ? `${insights.daily_activity.reduce((n, item) => n + item.count, 0)} recorded submissions in available history` : "Activity unavailable"}</span></div>
        <ActivityHeatmap entries={insights?.daily_activity ?? []}/>
      </section>

      <div className="lp-bottom-grid">
        <section className="lp-glass lp-recent">
          <div className="lp-section-heading"><div className="lp-section-title"><Activity size={18}/><h3>Recent submissions</h3></div><Link href="/problems" className="lp-text-link">Explore problems <ArrowUpRight size={14}/></Link></div>
          {submitted.length ? <div className="lp-submission-list">{submitted.slice(0, 7).map((item) => <Link key={item.id} href={`/problems/${encodeURIComponent(item.problem_slug)}`} className="lp-submission"><span className={item.verdict === "ACCEPTED" ? "lp-verdict-pass" : "lp-verdict-other"}>{item.verdict === "ACCEPTED" ? <CheckCircle2 size={18}/> : <Code2 size={18}/>}</span><span className="lp-submission-info"><strong>{item.problem_slug.replaceAll("-", " ")}</strong><small>{item.language} · {niceDate(item.created_at)}</small></span><span className={item.verdict === "ACCEPTED" ? "lp-pass" : "lp-muted"}>{item.verdict === "ACCEPTED" ? "Accepted" : item.verdict ?? item.status}</span></Link>)}</div> : <p className="lp-empty">No submissions yet. Solve your first challenge to start building your profile.</p>}
        </section>
        <section className="lp-glass lp-achievements">
          <div className="lp-section-heading"><div className="lp-section-title"><Award size={18}/><h3>Achievements</h3></div><span className="lp-subtle">{earned.length} unlocked</span></div>
          {earned.length ? <div className="lp-badges">{earned.slice(0, 6).map((item) => <div key={item.slug} className="lp-badge" title={item.description}><span><Award size={20}/></span><strong>{item.name}</strong><small>{niceDate(item.earned_at!)}</small></div>)}</div> : <p className="lp-empty">Your first achievement will appear here after you earn it.</p>}
        </section>
      </div>
      {status && <p className="lp-status" role="status">{status}</p>}
    </main>
  </div>;
}