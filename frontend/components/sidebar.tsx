"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Award, BookOpen, Code2, Flame, Menu, Route, ShieldCheck, Target, Trophy, X } from "lucide-react";
import { useEffect, useState } from "react";
import { modules, advanced } from "@/lib/navigation";
import { ModuleIcon } from "./icons";

/** The header owns primary navigation on desktop.
 * The sidebar contains contextual practice shortcuts only, with primary links
 * repeated exclusively inside the mobile drawer where the header nav is hidden.
 */
const mobilePrimary = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/problems", label: "Practice" },
  { href: "/subjects", label: "Learn" },
  { href: "/assessments", label: "Assessments" },
  { href: "/vidya-paths", label: "Career Paths" },
  { href: "/arena", label: "Community" },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [administrator, setAdministrator] = useState(false);

  useEffect(() => {
    let active = true;
    setOpen(false);
    void fetch("/api/auth/me").then(async response => {
      if (active) setAdministrator(response.ok && (await response.json()).role === "admin");
    }).catch(() => { if (active) setAdministrator(false); });
    return () => { active = false; };
  }, [pathname]);

  const nav = (href: string, label: string, icon: React.ReactNode) => {
    const active = pathname === href || pathname.startsWith(href + "/");
    return (
      <Link key={href} href={href} className={active ? "nav-link active" : "nav-link"}
        aria-current={active ? "page" : undefined} onClick={() => setOpen(false)}>
        {icon}<span>{label}</span>
      </Link>
    );
  };

  return (
    <aside className="sidebar" aria-label="Learning sidebar">
      <div className="brand-row">
        <Link href="/" className="brand" onClick={() => setOpen(false)}>
          <span className="brand-mark" aria-hidden="true"><Code2 size={21} strokeWidth={2.4}/></span>
          <span>EKLAVYA<small>LEARN / PRACTICE / MASTER</small></span>
        </Link>
        <button type="button" className="menu-toggle" onClick={() => setOpen(value => !value)}
          aria-expanded={open} aria-controls="main-navigation" aria-label="Toggle navigation">
          {open ? <X size={22}/> : <Menu size={22}/>}
        </button>
      </div>
      <nav id="main-navigation" aria-label="Main navigation" className={open ? "nav-open" : ""}>
        <div className="sidebar-mobile-primary">
          <p className="nav-label">Navigate</p>
          {mobilePrimary.map(item => nav(item.href, item.label, <BookOpen size={17}/>))}
          <p className="nav-label">Practice workspace</p>
        </div>
        <p className="nav-label sidebar-desktop-label">Your workspace</p>
        {nav("/progress-insights", "Progress insights", <Activity size={18}/>)}
        {nav("/daily-sadhana", "Daily challenge", <Flame size={18}/>)}
        {nav("/rankings", "Rankings", <Trophy size={18}/>)}
        {nav("/badges", "Achievements", <Award size={18}/>)}
        <p className="nav-label">Practice tracks</p>
        {modules.map(item => (
          <div key={item.slug}>{nav(`/${item.slug}`, item.label, <ModuleIcon name={item.icon}/>)}</div>
        ))}
        <p className="nav-label">Specialized labs</p>
        {advanced.filter(item => item.slug !== "assessments").map(item => (
          <div key={item.slug}>{nav(`/${item.slug}`, item.label, <ModuleIcon name={item.icon}/>)}</div>
        ))}
        {administrator && <>
          <p className="nav-label">Administration</p>
          {nav("/admin", "Admin control center", <ShieldCheck size={18}/>)}
        </>}
      </nav>
      <div className="sidebar-footer">
        <span className="sidebar-footer-badge">CONSISTENT PRACTICE</span>
        <strong>Small wins. Serious skills.</strong>
        <p>Your learning tools are always one click away.</p>
      </div>
    </aside>
  );
}
