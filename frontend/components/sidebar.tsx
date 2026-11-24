"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowUpRight, BookOpen, Code2, LayoutDashboard, LibraryBig, Menu, ShieldCheck, UserCircle, X } from "lucide-react";
import { useEffect, useState } from "react";
import { modules, community, advanced } from "@/lib/navigation";
import { ModuleIcon } from "./icons";

export function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [administrator, setAdministrator] = useState(false);
  useEffect(() => {
    let active = true;
    setAdministrator(false);
    void fetch("/api/auth/me").then(async (response) => {
      if (active && response.ok) setAdministrator((await response.json()).role === "admin");
    }).catch(() => undefined);
    return () => { active = false; };
  }, [pathname]);

  const nav = (href: string, label: string, icon: React.ReactNode, active = pathname === href) => (
    <Link href={href} className={active ? "nav-link active" : "nav-link"} aria-current={active ? "page" : undefined} onClick={() => setOpen(false)}>
      {icon}<span>{label}</span>
    </Link>
  );

  return (
    <aside className="sidebar">
      <div className="brand-row">
        <Link href="/" className="brand" onClick={() => setOpen(false)}>
          <span className="brand-mark" aria-hidden="true"><Code2 size={21} strokeWidth={2.4}/></span>
          <span>EKLAVYA<small>LEARN / PRACTICE / MASTER</small></span>
        </Link>
        <button className="menu-toggle" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="main-navigation" aria-label="Toggle navigation">
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>
      <nav id="main-navigation" aria-label="Main navigation" className={open ? "nav-open" : ""}>
        <p className="nav-label">Workspace</p>
        {nav("/dashboard", "My dashboard", <LayoutDashboard size={18} />)}
        {nav("/problems", "Problem library", <LibraryBig size={18} />, pathname.startsWith("/problems"))}
        {nav("/subjects", "All 45 subjects", <BookOpen size={18} />, pathname.startsWith("/subjects"))}
        {administrator && nav("/admin", "Admin control center", <ShieldCheck size={18} />, pathname.startsWith("/admin"))}
        <p className="nav-label">Practice tracks</p>
        {modules.map((item) => <div key={item.slug}>{nav(`/${item.slug}`, item.label, <ModuleIcon name={item.icon} />)}</div>)}
        <p className="nav-label">Advanced labs</p>
        {advanced.map((item) => <div key={item.slug}>{nav(`/${item.slug}`, item.label, <ModuleIcon name={item.icon} />)}</div>)}
        <p className="nav-label">Community</p>
        {community.map((item) => <div key={item.slug}>{nav(`/${item.slug}`, item.label, <ModuleIcon name={item.icon} />)}</div>)}
        <p className="nav-label">Account</p>
        {nav("/profile", "My profile", <UserCircle size={18} />)}
      </nav>
      <div className="sidebar-footer">
        <span className="sidebar-footer-badge">YOUR NEXT CHALLENGE</span>
        <strong>Build your streak.</strong>
        <p>Small wins. Serious skills.</p>
        <Link href="/daily-sadhana" onClick={() => setOpen(false)}>Daily Sadhana <ArrowUpRight size={15}/></Link>
      </div>
    </aside>
  );
}
