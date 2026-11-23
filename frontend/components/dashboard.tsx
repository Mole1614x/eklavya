import Link from "next/link";
import { ArrowRight, BookOpen, Code2, Sparkles, Terminal, Trophy, Zap } from "lucide-react";
import { modules } from "@/lib/navigation";
import { ModuleIcon } from "./icons";
import { PracticeChart } from "./practice-chart";
import { LiveProgress } from "./live-progress";
import { DashboardSchedule } from "./dashboard-schedule";

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
      <div className="hero-content">
        <p className="eyebrow"><span className="signal" /> {home ? "WELCOME TO EKLAVYA" : "YOUR LEARNING COMMAND CENTER"}</p>
        <h1>Build skills.<br/><em>Earn mastery.</em></h1>
        <p>Your space to practice code, explore data, train models and turn every challenge into progress.</p>
        <div className="hero-actions">
          <Link className="button" href="/problems"><Code2 size={17}/> Start practicing <ArrowRight size={16} /></Link>
          <Link className="button secondary" href={home ? "/dashboard" : "/vidya-paths"}>{home ? "Explore dashboard" : "Explore learning paths"}</Link>
        </div>
        <div className="hero-footnote"><span><Zap size={14}/> Learn by doing</span><span><Trophy size={14}/> Compete and grow</span></div>
      </div>
      <div className="hero-visual" aria-hidden="true">
        <div className="hero-code-window">
          <div className="hero-window-bar"><span/><span/><span/><small>practice.py</small></div>
          <div className="hero-code-lines"><p><span>01</span> <b>def</b> become_better(today):</p><p><span>02</span> &nbsp; practice = <i>True</i></p><p><span>03</span> &nbsp; <b>while</b> practice:</p><p><span>04</span> &nbsp; &nbsp; skills.level_up()</p><p><span>05</span> &nbsp; <b>return</b> <i>"mastery"</i></p></div>
          <div className="hero-run"><span className="signal"/> ALL SYSTEMS READY</div>
        </div>
        <div className="hero-orbit hero-orbit-one"/><div className="hero-orbit hero-orbit-two"/>
      </div>
    </section>
  );
}

export function Dashboard() {
  return (
    <>
      <header className="topbar"><span>Workspace <span className="crumb">/</span> <strong>My dashboard</strong></span><span className="topbar-status"><span className="signal"/> Ready to practice</span></header>
      <Hero />
      <section className="dashboard-section" aria-label="Verified learner statistics">
        <div className="section-heading"><div><p className="section-kicker">YOUR NUMBERS</p><h2>Progress at a glance</h2></div><Link href="/profile">View my profile <ArrowRight size={15}/></Link></div>
        <LiveProgress />
      </section>
      <div className="overview-grid">
        <PracticeChart />
        <div className="stack">
          <section className="card rank-card spotlight-card">
            <div className="section-heading"><div><p className="section-kicker">KEEP EXPLORING</p><h2>Your next milestone</h2></div><Sparkles size={22}/></div>
            <p>Every solved problem moves you closer to the next rank. Choose a track and keep your momentum.</p>
            <div className="milestone-actions"><Link href="/vidya-paths">Learning paths <ArrowRight size={15}/></Link><Link href="/leaderboard">Leaderboard <ArrowRight size={15}/></Link></div>
          </section>
          <DashboardSchedule />
        </div>
      </div>
      <section className="skills dashboard-section">
        <div className="section-heading"><div><p className="section-kicker">EXPLORE TRACKS</p><h2>Choose your practice area</h2></div><Link href="/problems">All challenges <ArrowRight size={15}/></Link></div>
        <SkillCards />
      </section>
      <div className="quick-links">
        <Link className="card quick-link" href="/vidya-paths"><BookOpen size={21}/><div><strong>Guided learning paths</strong><p>Learn concepts in the right order</p></div><ArrowRight size={17}/></Link>
        <Link className="card quick-link" href="/arena"><Trophy size={21}/><div><strong>Competitive arena</strong><p>Timed contests and rankings</p></div><ArrowRight size={17}/></Link>
        <Link className="card quick-link" href="/problems"><Terminal size={21}/><div><strong>Coding practice</strong><p>Sharpen your problem-solving</p></div><ArrowRight size={17}/></Link>
      </div>
    </>
  );
}
