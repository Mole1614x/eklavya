"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bell, ChevronDown, Command, LogOut, Search, UserRound } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";

type Account = {
  username: string;
  email?: string;
  profile?: { display_name?: string };
};

export function StudioHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const [account, setAccount] = useState<Account | null>(null);
  const [query, setQuery] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const menuRef = useRef<HTMLDivElement>(null);
  const accountButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    let active = true;
    setMenuOpen(false);
    void fetch("/api/auth/me", { cache: "no-store" })
      .then(async response => {
        if (active) setAccount(response.ok ? await response.json() as Account : null);
      })
      .catch(() => { if (active) setAccount(null); });
    return () => { active = false; };
  }, [pathname]);

  useEffect(() => {
    if (!menuOpen) return;
    const closeOutside = (event: PointerEvent) => {
      if (event.target instanceof Node && !menuRef.current?.contains(event.target)) {
        setMenuOpen(false);
      }
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        accountButtonRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [menuOpen]);

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (query.trim()) router.push(`/problems?q=${encodeURIComponent(query.trim())}`);
  }

  async function logout() {
    if (signingOut) return;
    setSigningOut(true);
    setLogoutError("");
    try {
      const response = await fetch("/api/auth/logout", { method: "POST" });
      if (!response.ok) throw new Error("Could not sign out. Please try again.");
      setAccount(null);
      setMenuOpen(false);
      router.replace("/auth");
      router.refresh();
    } catch (error) {
      setLogoutError(error instanceof Error ? error.message : "Could not sign out.");
    } finally {
      setSigningOut(false);
    }
  }

  const sections = [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/problems", label: "Practice" },
    { href: "/subjects", label: "Learn" },
    { href: "/assessments", label: "Assessments" },
    { href: "/vidya-paths", label: "Career Paths" },
    { href: "/arena", label: "Community" },
  ];
  const displayName = account?.profile?.display_name?.trim() || account?.username || "Guest";
  const initials = displayName.split(/\s+/).slice(0, 2).map(part => part[0]).join("").toUpperCase();

  return <header className="studio-header">
    <Link className="studio-header-brand" href="/dashboard" aria-label="EKLAVYA home">
      <span className="studio-brand-icon"><span>&lt;/&gt;</span></span><strong>EKLAVYA</strong>
    </Link>
    <nav className="studio-header-nav" aria-label="Primary navigation">
      {sections.map(item =>
        <Link key={item.href} href={item.href} className={pathname === item.href || pathname.startsWith(item.href + "/") ? "selected" : ""}>
          {item.label}
        </Link>
      )}
    </nav>
    <form className="studio-global-search" role="search" onSubmit={search}>
      <Search size={16}/>
      <input value={query} onChange={event => setQuery(event.target.value)} aria-label="Search questions and subjects" placeholder="Search subjects, topics, questions…"/>
      <kbd><Command size={12}/> K</kbd>
    </form>
    <div className="studio-header-actions">
      <Link href="/daily-sadhana" aria-label="Daily challenge"><Bell size={19}/></Link>
      {account ? <div className="studio-account-dropdown" ref={menuRef}>
        <button ref={accountButtonRef} type="button" className="studio-account-link studio-account-trigger"
          aria-label="Account menu" aria-haspopup="true" aria-controls="studio-account-menu"
          aria-expanded={menuOpen} onClick={() => { setLogoutError(""); setMenuOpen(open => !open); }}>
          <span className="studio-account-avatar">{initials}</span>
          <ChevronDown size={15} className={menuOpen ? "studio-chevron-open" : ""}/>
        </button>
        {menuOpen && <nav id="studio-account-menu" aria-label="Account options" className="studio-account-menu">
          <div className="studio-account-menu-heading">
            <strong>{displayName}</strong>
            <small>@{account.username}</small>
          </div>
          <Link href="/profile" onClick={() => setMenuOpen(false)}><UserRound size={17}/> My Profile</Link>
          <div className="studio-account-menu-divider"/>
          <button type="button" onClick={() => void logout()} disabled={signingOut}>
            <LogOut size={17}/>{signingOut ? "Logging out…" : "Log out"}
          </button>
          {logoutError && <p role="alert" className="studio-account-error">{logoutError}</p>}
        </nav>}
      </div> : <Link className="studio-account-link" href="/auth" aria-label="Sign in">
        <span className="studio-account-avatar">{initials}</span><ChevronDown size={15}/>
      </Link>}
    </div>
  </header>;
}