"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bell, ChevronDown, Command, Search, UserRound } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

export function StudioHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const [account, setAccount] = useState<{ username: string; profile?: { display_name?: string } } | null>(null);
  const [query, setQuery] = useState("");
  useEffect(() => {
    let mounted = true;
    void fetch("/api/auth/me").then(async r=>{if(r.ok&&mounted)setAccount(await r.json())}).catch(()=>undefined);
    return ()=>{mounted=false};
  }, [pathname]);
  function search(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if(query.trim()) router.push(`/problems?q=${encodeURIComponent(query.trim())}`);
  }
  const sections=[
    {href:"/dashboard",label:"Dashboard"},
    {href:"/problems",label:"Practice"},
    {href:"/subjects",label:"Learn"},
    {href:"/assessments",label:"Assessments"},
    {href:"/vidya-paths",label:"Career Paths"},
    {href:"/arena",label:"Community"},
  ];
  const initials=(account?.profile?.display_name||account?.username||"Guest").trim().split(/\s+/).slice(0,2).map(p=>p[0]).join("").toUpperCase();
  return <header className="studio-header">
    <Link className="studio-header-brand" href="/dashboard" aria-label="EKLAVYA home"><span className="studio-brand-icon"><span>&lt;/&gt;</span></span><strong>EKLAVYA</strong></Link>
    <nav className="studio-header-nav" aria-label="Primary navigation">{sections.map(item=><Link key={item.href} href={item.href} className={pathname===item.href||pathname.startsWith(item.href+"/")?"selected":""}>{item.label}</Link>)}</nav>
    <form className="studio-global-search" role="search" onSubmit={search}><Search size={16}/><input value={query} onChange={e=>setQuery(e.target.value)} aria-label="Search questions and subjects" placeholder="Search subjects, topics, questions…"/><kbd><Command size={12}/> K</kbd></form>
    <div className="studio-header-actions"><Link href="/daily-sadhana" aria-label="Daily challenge"><Bell size={19}/></Link><Link className="studio-account-link" href={account?"/profile":"/auth"} aria-label={account?"My profile":"Sign in"}><span className="studio-account-avatar">{initials}</span><ChevronDown size={15}/></Link></div>
  </header>;
}