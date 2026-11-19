import Link from "next/link";
import { ArrowDownRight, ArrowRight, CheckCircle2, Flame, Star, Zap } from "lucide-react";
import { modules } from "@/lib/navigation";
import { ModuleIcon } from "./icons";
import { PracticeChart } from "./practice-chart";
import { LiveProgress } from "./live-progress";
import { DashboardSchedule } from "./dashboard-schedule";

const stats = [
  { label: "Problems solved", value: "24", icon: CheckCircle2, color: "green" },
  { label: "Current streak", value: "5 days", icon: Flame, color: "orange" },
  { label: "Total XP", value: "350 XP", icon: Zap, color: "purple" },
];

export function SkillCards() {
  return <div className="skills-grid">{modules.map((module) => (
    <Link className="card skill-card" href={`/${module.slug}`} key={module.slug}>
      <span className={`tile ${module.slug}`}><ModuleIcon name={module.icon} /></span>
      <div><h3>{module.label}</h3><p>{module.topics.slice(0, 2).join(" · ")}</p></div>
      <ArrowRight size={16} className="skill-arrow" />
    </Link>
  ))}</div>;
}

export function Hero({ home = false }: { home?: boolean }) {
  return (
    <section className="hero">
      <div className="target-art" aria-hidden="true"><span /><span /><span /><span /><i /><ArrowDownRight size={120} strokeWidth={0.8} /></div>
      <div className="hero-content">
        <p className="eyebrow"><span className="signal" /> {home ? "The practice platform" : "Your practice dashboard"}</p>
        <h1>Learn. Practice. <em>Master.</em></h1>
        <p>Sharpen your programming, data, and AI skills with hands-on challenges, one problem at a time.</p>
        <div className="hero-actions">
          <Link className="button" href="/problems">Explore problems <ArrowRight size={16} /></Link>
          <Link className="button secondary" href={home ? "/dashboard" : "/vidya-paths"}>{home ? "Open dashboard" : "View learning paths"}</Link>
        </div>
      </div>
    </section>
  );
}

export function Dashboard() {
  return (
    <>
      <header className="topbar"><span>Overview <span className="crumb">/</span> <strong>Dashboard</strong></span><span className="profile" aria-label="Demo profile">E</span></header>
      <Hero />
      <LiveProgress />
      <section className="stats-grid" aria-label="Demo practice statistics">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <article className="card stat" key={label}><span className={`tile ${color}`}><Icon size={19} /></span><div><p>{label}</p><strong>{value}</strong></div><span className="pill">Demo</span></article>
        ))}
      </section>
      <div className="overview-grid">
        <PracticeChart />
        <div className="stack">
          <section className="card rank-card">
            <div className="section-heading"><h2>Maharathi rank</h2><span className="pill">Demo</span></div>
            <div className="rank-name"><span className="tile orange"><Star size={23} fill="currentColor" /></span><div><strong>Shishya</strong><p>Next rank · Sadhak</p></div></div>
            <progress aria-label="XP towards Sadhak" value={350} max={500} /><p className="progress-caption"><span>350 / 500 XP</span><span>70%</span></p>
          </section>
          <DashboardSchedule />
        </div>
      </div>
      <section className="skills">
        <div className="section-heading"><h2>Explore practice areas</h2><Link href="/problems">View catalog <ArrowRight size={15} /></Link></div>
        <SkillCards />
      </section>
      <div className="skills-grid extra">
        <Link className="card skill-card" href="/vidya-paths"><div><h3>Learning paths</h3><p>Preview the Foundations path</p></div><ArrowRight size={16} /></Link>
        <Link className="card skill-card" href="/arena"><div><h3>Upcoming contests</h3><p>Register, compete, and build your rating</p></div><ArrowRight size={16} /></Link>
      </div>
    </>
  );
}
