"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Activity, ArrowUpRight, Award, CalendarDays, CheckCircle2, Code2, Flame, LogOut, Pencil, ShieldCheck, Target, Trophy, Zap } from "lucide-react";

type User = { email: string; username: string; role: string; email_verified: boolean; profile: { display_name?: string; bio?: string; timezone?: string } };
type Progress = { xp: number; solved_count: number; rank: string; stars: number; next_rank: string | null; next_rank_xp: number | null; accepted_submissions: number; submission_accuracy: number };
type Insights = { daily_activity: { day: string; count: number }[] };
type Achievement = { slug: string; name: string; description: string; earned_at: string | null };
type Submission = { id: string; problem_slug: string; language: string; mode: string; status: string; verdict: string | null; created_at: string };
type History = { streak: number };

function readableDate(value: string) {
  const date = Date.parse(value);
  return Number.isFinite(date) ? new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(date) : "—";
}

function ActivityHeatmap({ entries }: { entries: Insights["daily_activity"] }) {
  const days = useMemo(() => {
    const counts = new Map(entries.map(item => [item.day, item.count]));
    const today = new Date();
    const latest = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
    const start = new Date(latest);
    start.setUTCDate(start.getUTCDate() - 90);
    // Match calendar columns to Sunday through Saturday.
    start.setUTCDate(start.getUTCDate() - start.getUTCDay());
    return Array.from({ length: 98 }, (_, index) => {
      const date = new Date(start);
      date.setUTCDate(start.getUTCDate() + index);
      const key = date.toISOString().slice(0, 10);
      return { key, count: counts.get(key) ?? 0, future: date.getTime() > latest };
    });
  }, [entries]);

  return <div className="lp-heatmap-wrap">
    <div className="lp-heatmap" role="img" aria-label="Submission activity heatmap for the last 13 weeks">
      {days.map(day => <span key={day.key} title={`${day.key}: ${day.count} submissions`}
        className={`lp-day ${day.future ? "lp-day-future" : day.count === 0 ? "" : day.count === 1 ? "lp-day-1" : day.count < 4 ? "lp-day-2" : "lp-day-3"}`}/>)}
    </div>
    <div className="lp-heatmap-legend"><span>Less</span><i className="lp-day"/><i className="lp-day lp-day-1"/><i className="lp-day lp-day-2"/><i className="lp-day lp-day-3"/><span>More</span></div>
  </div>;
}

export function ProfilePanel() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [insights, setInsights] = useState<Insights | null>(null);
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [history, setHistory] = useState<History | null>(null);
  const [editing, setEditing] = useState(false);
  const [status, setStatus] = useState("Loading profile…");

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const res = await fetch("/api/auth/me", { cache: "no-store" });
        if (res.status === 401) { router.replace("/auth"); return; }
        if (!res.ok) throw new Error("Profile is temporarily unavailable.");
        const current = await res.json() as User;
        if (!alive) return;
        setUser(current);
        setStatus("");
        const routes = [
          "/api/gamification/dashboard", "/api/gamification/insights",
          "/api/gamification/achievements", "/api/submissions?limit=25",
          "/api/learning/daily/history"
        ];
        const results = await Promise.allSettled(routes.map(async url => {
          const response = await fetch(url, { cache: "no-store" });
          if (!response.ok) throw new Error(url);
          return response.json() as Promise<unknown>;
        }));
        if (!alive) return;
        if (results[0].status === "fulfilled") setProgress(results[0].value as Progress);
        if (results[1].status === "fulfilled") setInsights(results[1].value as Insights);
        if (results[2].status === "fulfilled") setAchievements(results[2].value as Achievement[]);
        if (results[3].status === "fulfilled") setSubmissions(results[3].value as Submission[]);
        if (results[4].status === "fulfilled") setHistory(results[4].value as History);
      } catch (error) {
        if (alive) setStatus(error instanceof Error ? error.message : "Unable to load your profile.");
      }
    })();
    return () => { alive = false; };
  }, [router]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("Saving…");
    try {
      const payload = Object.fromEntries(new FormData(event.currentTarget));
      const response = await fetch("/api/auth/me", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      if (!response.ok) throw new Error("Profile could not be saved.");
      setUser(await response.json() as User);
      setEditing(false);
      setStatus("Profile saved.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "Profile could not be saved."); }
  }

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.replace("/auth");
    router.refresh();
  }

  if (!user) return <div className="card state" role="status">{status}</div>;

  const displayName = user.profile?.display_name?.trim() || user.username;
  const initials = displayName.split(/\s+/).slice(0,2).map(part => part[0] || "").join("").toUpperCase();
  const earned = achievements.filter(item => Boolean(item.earned_at));
  const submitted = submissions.filter(item => item.mode === "SUBMIT");
  const accuracy = Math.max(0, Math.min(100, progress?.submission_accuracy ?? 0));
  const totalActivity = (insights?.daily_activity ?? []).reduce((sum, item) => sum + item.count, 0);
  const xpToNext = progress?.next_rank_xp == null ? null : Math.max(0, progress.next_rank_xp - progress.xp);

  return <div className="lp-profile" data-profile-design="studio-glass-v2">
    <header className="lp-glass lp-hero">
      <div className="lp-hero-orb" aria-hidden="true"/>
      <div className="lp-avatar" aria-hidden="true">{initials}</div>
      <div className="lp-hero-info">
        <p className="lp-eyebrow">EKLAVYA / DEVELOPER PROFILE</p>
        <h1>{displayName}</h1>
        <p className="lp-handle">@{user.username} <span className="lp-hero-separator">·</span> {progress?.rank ?? "Learning member"}</p>
        <p className="lp-hero-bio">{user.profile?.bio?.trim() || "Practice consistently. Build mastery. Track every milestone."}</p>
      </div>
      <div className="lp-hero-actions">
        <Link href="/problems" className="lp-practice-link">Solve problems <ArrowUpRight size={16}/></Link>
        <button type="button" className="lp-edit-button" onClick={() => setEditing(value => !value)} aria-expanded={editing}><Pencil size={15}/> {editing ? "Close editor" : "Edit profile"}</button>
      </div>
    </header>

    <div className="lp-profile-layout">
      <aside className="lp-sidebar" aria-label="Profile details">
        <section className="lp-glass lp-identity">
          <div className="lp-section-title"><ShieldCheck size={17}/><h2>About</h2></div>
          <div className="lp-account-details">
            <div><span>Account</span><strong>{user.email_verified ? "Verified" : "Verification pending"}</strong></div>
            <div><span>Role</span><strong>{user.role}</strong></div>
            <div><span>Email</span><strong className="lp-email">{user.email}</strong></div>
            <div><span>Timezone</span><strong>{user.profile?.timezone || "UTC"}</strong></div>
          </div>
          {user.role === "admin" && <Link className="lp-text-link" href="/admin">Open administration <ArrowUpRight size={14}/></Link>}
        </section>

        <section className="lp-glass lp-rank-card">
          <div className="lp-section-title"><Trophy size={17}/><h2>Your rank</h2></div>
          <div className="lp-rank-summary"><strong>{progress?.rank ?? "—"}</strong><span>{progress?.stars ?? "—"} stars</span></div>
          <p>{progress ? `${progress.xp.toLocaleString()} XP earned` : "Complete challenges to build your rank."}</p>
          {progress?.next_rank_xp != null && <>
            <progress value={progress.xp} max={Math.max(progress.next_rank_xp,1)} aria-label="Rank progress"/>
            <small>{xpToNext?.toLocaleString()} XP to {progress.next_rank}</small>
          </>}
        </section>

        <section className="lp-glass lp-accuracy-card">
          <div className="lp-section-title"><Target size={17}/><h2>Submission accuracy</h2></div>
          <div className="lp-accuracy-body">
            <div className="lp-ring" style={{ background: `conic-gradient(#97bdf7 ${accuracy}%, #364454 0)` }} aria-label={progress ? `${accuracy}% accepted submissions` : "Accuracy unavailable"}>
              <div><strong>{progress ? `${accuracy}%` : "—"}</strong><small>Acceptance</small></div>
            </div>
            <div className="lp-accuracy-description"><strong>{progress?.accepted_submissions.toLocaleString() ?? "—"}</strong><span>Accepted submissions</span><small>Only verified judge results count towards your progress.</small></div>
          </div>
        </section>

        {editing && <section className="lp-glass lp-form-card">
          <h2>Edit profile</h2>
          <form onSubmit={save}>
            <label>Display name<input name="display_name" defaultValue={user.profile?.display_name ?? ""} required maxLength={100}/></label>
            <label>Bio<textarea name="bio" defaultValue={user.profile?.bio ?? ""} maxLength={280}/></label>
            <label>Timezone<input name="timezone" defaultValue={user.profile?.timezone ?? "UTC"}/></label>
            <button className="button" type="submit">Save profile</button>
          </form>
        </section>}
        <button type="button" className="lp-signout" onClick={logout}><LogOut size={16}/> Sign out</button>
      </aside>

      <div className="lp-content">
        <section className="lp-stats" aria-label="Your coding statistics">
          <article className="lp-glass lp-stat"><CheckCircle2 size={21}/><span>Problems solved</span><strong>{progress?.solved_count.toLocaleString() ?? "—"}</strong><small>Unique verified solutions</small></article>
          <article className="lp-glass lp-stat"><Zap size={21}/><span>Experience points</span><strong>{progress?.xp.toLocaleString() ?? "—"}</strong><small>Earned through practice</small></article>
          <article className="lp-glass lp-stat"><Flame size={21}/><span>Daily streak</span><strong>{history?.streak ?? "—"}</strong><small>Consecutive challenge days</small></article>
          <article className="lp-glass lp-stat"><Award size={21}/><span>Badges unlocked</span><strong>{earned.length}</strong><small>Achievements earned</small></article>
        </section>

        <section className="lp-glass lp-activity">
          <div className="lp-section-heading">
            <div><div className="lp-section-title"><CalendarDays size={19}/><h2>Submission activity</h2></div><p>Daily contributions across the last 13 weeks</p></div>
            <span className="lp-activity-total">{insights ? totalActivity.toLocaleString() : "—"} submissions</span>
          </div>
          <ActivityHeatmap entries={insights?.daily_activity ?? []}/>
        </section>

        <div className="lp-bottom-grid">
          <section className="lp-glass lp-recent">
            <div className="lp-section-heading"><div className="lp-section-title"><Activity size={18}/><h2>Recent submissions</h2></div><Link href="/problems" className="lp-text-link">Practice <ArrowUpRight size={14}/></Link></div>
            {submitted.length ? <div className="lp-submission-list">{submitted.slice(0,7).map(item =>
              <Link key={item.id} href={`/problems/${encodeURIComponent(item.problem_slug)}`} className="lp-submission">
                <span className={item.verdict === "ACCEPTED" ? "lp-verdict-pass" : "lp-verdict-other"}>{item.verdict === "ACCEPTED" ? <CheckCircle2 size={18}/> : <Code2 size={18}/>}</span>
                <span className="lp-submission-info"><strong>{item.problem_slug.replaceAll("-"," ")}</strong><small>{item.language} · {readableDate(item.created_at)}</small></span>
                <span className={item.verdict === "ACCEPTED" ? "lp-pass" : "lp-muted"}>{item.verdict === "ACCEPTED" ? "Accepted" : item.verdict ?? item.status}</span>
              </Link>)}</div>
              : <div className="lp-empty"><Code2 size={25}/><p>Your submissions will appear here after your first challenge.</p><Link href="/problems">Explore problems <ArrowUpRight size={14}/></Link></div>}
          </section>

          <section className="lp-glass lp-achievements">
            <div className="lp-section-heading"><div className="lp-section-title"><Award size={18}/><h2>Achievements</h2></div><span className="lp-subtle">{earned.length} unlocked</span></div>
            {earned.length ? <div className="lp-badges">{earned.slice(0,6).map(item =>
              <div className="lp-badge" key={item.slug} title={item.description}><span><Award size={20}/></span><strong>{item.name}</strong><small>{readableDate(item.earned_at!)}</small></div>)}</div>
              : <div className="lp-empty"><Trophy size={25}/><p>Your badges will appear here as you practice and complete milestones.</p></div>}
          </section>
        </div>
        {status && <p className="lp-status" role="status">{status}</p>}
      </div>
    </div>
  </div>;
}
