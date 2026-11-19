"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, LibraryBig, Menu, UserCircle, X } from "lucide-react";
import { useState } from "react";
import { modules, community } from "@/lib/navigation";
import { ModuleIcon } from "./icons";

export function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const nav = (href: string, label: string, icon: React.ReactNode, active = pathname === href) => (
    <Link href={href} className={active ? "nav-link active" : "nav-link"} aria-current={active ? "page" : undefined} onClick={() => setOpen(false)}>
      {icon}<span>{label}</span>
    </Link>
  );

  return (
    <aside className="sidebar">
      <div className="brand-row">
        <Link href="/" className="brand" onClick={() => setOpen(false)}>
          <img src="/mark.svg" width="34" height="34" alt="" />
          <span>EKLAVYA<small>Learn. Practice. Master.</small></span>
        </Link>
        <button className="menu-toggle" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="main-navigation" aria-label="Toggle navigation">
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>
      <nav id="main-navigation" aria-label="Main navigation" className={open ? "nav-open" : ""}>
        {nav("/dashboard", "Dashboard", <LayoutDashboard size={19} />)}
        {nav("/problems", "Problem Catalog", <LibraryBig size={19} />, pathname.startsWith("/problems"))}
        <p className="nav-label">Practice</p>
        {modules.map((item) => <div key={item.slug}>{nav(`/${item.slug}`, item.label, <ModuleIcon name={item.icon} />)}</div>)}
        <p className="nav-label">Community</p>
        {community.map((item) => <div key={item.slug}>{nav(`/${item.slug}`, item.label, <ModuleIcon name={item.icon} />)}</div>)}
        <p className="nav-label">Account</p>
        {nav("/profile", "Profile", <UserCircle size={19} />)}
      </nav>
    </aside>
  );
}
