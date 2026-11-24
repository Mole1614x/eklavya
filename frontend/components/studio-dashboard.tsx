"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Activity, ArrowRight, BookOpen, CalendarDays, Check, ChevronLeft, ChevronRight, Code2, Database, Flame, Layers3, LineChart, Network, Search, Sparkles, Target, Trophy, Zap } from "lucide-react";

type User = { username: string; profile?: { display_name?: string } };
type Progress = { xp: number; solved_count: number; submission_accuracy: number; rank: string; next_rank?: string | null; next_rank_xp?: number | null };
type Insights = { daily_activity: { day: string; count: number }[]; xp_growth: { day: string; amount: number }[]; solved_problems: { problem_slug: string; accepted_submissions: number }[] };
type Daily = { title: string; problem_slug: string };
type History = { streak: number };
type Path = { slug: string; title: string; description: string; problem_count: number };
type Submission = { id: string; problem_slug: string; language: string; verdict: string | null; created_at: string; mode: string };
type Catalogue = { target_total: number; published_catalog_total: number; subjects: { slug: string }[] };
type DashboardData = { user: User | null; progress: Progress | null; insights: Insights | null; daily: Daily | null; history: History | null; paths: Path[]; submissions: Submission[]; catalogue: Catalogue | null };

const featuredPaths = [
  { title: "Data Analyst", topics: "SQL · Pandas · Excel", icon: Database, href: "/vidya-paths", filters: ["sql", "pandas", "excel"] },
  { title: "Data Engineer", topics: "PySpark · Airflow · SQL", icon: Network, href: "/vidya-paths", filters: ["data", "spark", "big"] },
  { title: "ML Engineer", topics: "ML · DL · CV · LLM", icon: Sparkles, href: "/vidya-paths", filters: ["machine", "ml", "deep", "ai"] },
  { title: "Software Developer", topics: "DSA · Backend · System Design", icon: Code2, href: "/vidya-paths", filters: ["code", "dsa", "system"] },
];

const initial: DashboardData = { user: null, progress: null, insights: null, daily: null, history: null, paths: [], submissions: [], catalogue: null };

async function jsonOrNull<T>(url: string): Promise<T | null> {
  try { const response = await fetch(url); return response.ok ? await response.json() as T : null; } catch { return null; }
}

function atUTC(date: Date) { return date.toISOString().slice(0, 10); }
function formatActivityDate(date: string) { const d = new Date(date); return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString(undefined, { month: "short", day: "numeric" }); }

export function StudioDashboard() {
  const [data, setData] = useState<DashboardData>(initial);
  const [loading, setLoading] = useState(true);
  const [monthOffset, setMonthOffset] = useState(0);

  useEffect(() => {
    let alive = true;
    void Promise.all([
      jsonOrNull<User>("/api/auth/me"),
      jsonOrNull<Progress>("/api/gamification/dashboard"),
      jsonOrNull<Insights>("/api/gamification/insights"),
      jsonOrNull<Daily>("/api/learning/daily"),
      jsonOrNull<History>("/api/learning/daily/history"),
      jsonOrNull<Path[]>("/api/learning/paths"),
      jsonOrNull<Submission[]>("/api/submissions?limit=15"),
      jsonOrNull<Catalogue>("/api/catalog-summary"),
    ]).then(([user, progress, insights, daily, history, paths, submissions, catalogue]) => {
      if (alive) {
        setData({ user, progress, insights, daily, history, paths: paths ?? [], submissions: submissions ?? [], catalogue });
        setLoading(false);
      }
    });
    return () => { alive = false; };
  }, []);

  const today = new Date();
  const recent = useMemo(() => {
    const counts = new Map((data.insights?.daily_activity ?? []).map(({ day, count }) => [day, count]));
    return Array.from({ length: 7 }, (_, index) => {
      const d = new Date(); d.setUTCDate(d.getUTCDate() - (6 - index));
      return { day: d.toLocaleDateString("en-US", { weekday: "short", timeZone: "UTC" }), active: (counts.get(atUTC(d)) ?? 0) > 0, date: atUTC(d) };
    });
  }, [data.insights]);
  const calendarMonth = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth() + monthOffset, 1));
  const monthName = calendarMonth.toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });
  const monthDays = new Date(Date.UTC(calendarMonth.getUTCFullYear(), calendarMonth.getUTCMonth() + 1, 0)).getUTCDate();
  const firstWeekday = (calendarMonth.getUTCDay() + 6) % 7;
  const activityMap = new Map((data.insights?.daily_activity ?? []).map(({ day, count }) => [day, count]));
  const solved = data.progress?.solved_count ?? 0;
  const attempted = data.insights?.daily_activity.reduce((sum, entry) => sum + entry.count, 0) ?? 0;
  const progressPct = data.progress?.submission_accuracy ?? 0;
  const displayName = data.user?.profile?.display_name?.trim()?.split(" ")[0] || data.user?.username || "learner";

  return <div className="studio-dashboard">
    <div className="studio-main-col">
      <section className="studio-welcome">
        <div className="studio-landscape" aria-hidden="true"><span/><span/><span/><span/></div>
        <p className="studio-hello">👋 Hi {data.user ? displayName : "there"},</p>
        <h1>Continue your learning journey</h1>
        <p>Practice, learn, and master in-demand technical skills.</p>
      </section>

      <section className="studio-stats" aria-label="Learning overview">
        {[
          { label: "Subjects", value: data.catalogue?.subjects.length ?? 45, icon: Layers3 },
          { label: "Questions", value: data.catalogue?.published_catalog_total ?? "—", icon: Code2 },
          { label: "Verified solves", value: data.progress?.solved_count ?? (loading ? "…" : "—"), icon: LineChart },
          { label: "Daily streak", value: data.history?.streak ?? (loading ? "…" : "—"), icon: Flame },
        ].map((item) => <article className="studio-card studio-stat" key={item.label}>
          <span className="studio-icon-circle"><item.icon size={22}/></span>
          <span><strong>{typeof item.value === "number" ? item.value.toLocaleString() : item.value}</strong><small>{item.label}</small></span>
        </article>)}
      </section>

      <section className="studio-card studio-continue">
        <div className="studio-heading"><h2><BookOpen size={17}/> Continue Practicing</h2><Link href="/problems" aria-label="Browse all problems"><ArrowRight size={19}/></Link></div>
        <div className="studio-continue-body">
          <span className="studio-python-icon"><Code2 size={28}/></span>
          <div className="studio-continue-details">
            <h3>{data.daily?.title ?? "Explore your next coding challenge"}</h3>
            <p>{data.daily ? "Today's daily challenge · Practise at your own pace" : "Python · SQL · DSA · Data Science"}</p>
            <div className="studio-progress-row"><div className="studio-bar"><span style={{ width: `${Math.min(100, Math.max(0, progressPct))}%` }}/></div><strong>{data.progress ? `${progressPct}% accuracy` : "Start solving"}</strong></div>
          </div>
          <Link className="studio-cta" href={data.daily ? `/problems/${data.daily.problem_slug}` : "/problems"}>Continue <ArrowRight size={17}/></Link>
        </div>
      </section>

      <section className="studio-card studio-paths">
        <div className="studio-heading"><h2><Layers3 size={18}/> Your Learning Paths</h2><Link href="/vidya-paths">View All <ArrowRight size={15}/></Link></div>
        <div className="studio-path-grid">
          {featuredPaths.map(({ title, topics, icon: Icon, href, filters }) => {
            const related = data.paths.filter(path => filters.some(tag => (path.title + " " + path.slug).toLowerCase().includes(tag)));
            return <Link href={related[0] ? `/paths/${related[0].slug}` : href} className="studio-path" key={title}>
              <Icon size={22}/><strong>{title}</strong><small>{topics}</small>
              <div className="studio-path-bottom"><span className="studio-mini-bar"><i style={{width: related.length ? "100%" : "0%"}}/></span><span>{related.length ? `${related.length} paths` : "Explore"}</span></div>
            </Link>;
          })}
        </div>
      </section>

      <section className="studio-insights">
        <article className="studio-card studio-mastery">
          <div className="studio-heading"><h2><Target size={18}/> Subject Mastery</h2></div>
          {data.progress ? <div className="studio-mastery-body"><div className="studio-ring" style={{background:`conic-gradient(#9fc4fa ${Math.min(progressPct,100)}%, #374254 0)`}}><span><strong>{progressPct}%</strong><small>Accuracy</small></span></div>
            <div className="studio-mastery-legend"><p><i className="studio-dot-blue"/>Verified solves <b>{solved}</b></p><p><i className="studio-dot-gray"/>XP earned <b>{data.progress.xp.toLocaleString()}</b></p><p><i className="studio-dot-light"/>Rank <b>{data.progress.rank}</b></p></div></div>
            : <p className="studio-placeholder">Sign in to see your verified skill analytics. <Link href="/auth">Sign in</Link></p>}
        </article>
        <article className="studio-card studio-performance">
          <div className="studio-heading"><h2><LineChart size={18}/> Performance Overview</h2><span>Last 7 Days</span></div>
          <div className="studio-chart" role="img" aria-label="Submission counts for the last seven days">
            <div className="studio-chart-bars">{recent.map((day) => {
              const count = activityMap.get(day.date) ?? 0;
              return <div key={day.date} className="studio-chart-column"><div className="studio-chart-pillar" style={{height:`${Math.max(5,Math.min(100,(count / Math.max(1,...recent.map(d=>activityMap.get(d.date)??0)))*100))}%`}} title={`${count} submissions`}/><span>{day.day}</span></div>;
            })}</div>
          </div>
          {!data.user && <p className="studio-chart-note">Sign in to record your practice activity.</p>}
        </article>
      </section>
      <section className="studio-footer-links"><Link href="/subjects">Explore all subjects <ArrowRight size={15}/></Link><Link href="/assessments">Take an assessment <ArrowRight size={15}/></Link><Link href="/profile">View your profile <ArrowRight size={15}/></Link></section>
    </div>

    <aside className="studio-right-col" aria-label="Your activity">
      <section className="studio-card studio-streak">
        <div className="studio-streak-heading"><Flame size={31}/><div><h2>{data.history?.streak ?? "—"} Day Streak</h2><p>{data.user ? "Your daily challenge completion streak." : "Sign in to start your streak."}</p></div></div>
        <div className="studio-streak-days">{recent.map(({date,day,active})=><div key={date}><span className={active?"active":""}>{active?<Check size={13}/>:null}</span><small>{day}</small></div>)}</div>
      </section>
      <section className="studio-card studio-goal">
        <div className="studio-goal-title"><Target size={20}/><strong>Weekly Goal</strong><small>{recent.filter(x=>x.active).length} / 5 days</small></div>
        <div className="studio-bar"><span style={{width:`${Math.min(100,recent.filter(x=>x.active).length / 5 * 100)}%`}}/></div>
      </section>
      <section className="studio-card studio-calendar">
        <div className="studio-heading"><h2><CalendarDays size={18}/> Your Activity</h2><div className="studio-month-controls"><button aria-label="Previous month" onClick={()=>setMonthOffset(m=>Math.max(m-12,-1))}><ChevronLeft size={16}/></button><span>{monthName}</span><button aria-label="Next month" onClick={()=>setMonthOffset(m=>Math.min(0,m+1))} disabled={monthOffset===0}><ChevronRight size={16}/></button></div></div>
        <div className="studio-calendar-grid">{["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map(d=><span className="studio-weekday" key={d}>{d}</span>)}
          {Array.from({length:firstWeekday},(_,i)=><span key={`blank-${i}`} />)}
          {Array.from({length:monthDays},(_,i)=>{const date=i+1;const key=`${calendarMonth.getUTCFullYear()}-${String(calendarMonth.getUTCMonth()+1).padStart(2,"0")}-${String(date).padStart(2,"0")}`;const count=activityMap.get(key)??0;return <span key={key} className={count?"studio-cal-active":""} title={`${key} · ${count} submissions`}>{date}</span>})}
        </div>
      </section>
      <section className="studio-card studio-recent">
        <div className="studio-heading"><h2><Activity size={18}/> Recent Activity</h2><Link href="/profile">View All <ArrowRight size={14}/></Link></div>
        {data.submissions.length ? <div className="studio-recent-list">{data.submissions.slice(0,4).map(item=><Link href={`/problems/${item.problem_slug}`} key={item.id}>
          <span className={item.verdict==="ACCEPTED"?"studio-recent-ok":"studio-recent-neutral"}>{item.verdict==="ACCEPTED"?<Check size={18}/>:<Code2 size={16}/>}</span>
          <span><strong>{item.problem_slug.replaceAll("-"," ")}</strong><small>{item.language} · {item.verdict??"In progress"}</small></span><time>{formatActivityDate(item.created_at)}</time>
        </Link>)}</div>:<p className="studio-empty">{loading?"Loading activity…":"Your completed challenges and submissions will appear here."}</p>}
      </section>
      <section className="studio-card studio-daily">
        <div className="studio-heading"><h2><Zap size={18}/> Daily Challenge</h2></div>
        <p>{data.daily?.title??"Explore today's coding challenge"}</p><Link href={data.daily?`/problems/${data.daily.problem_slug}`:"/daily-sadhana"}>Start challenge <ArrowRight size={15}/></Link>
      </section>
    </aside>
  </div>;
}
