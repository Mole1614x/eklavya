"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

type User = { email: string; username: string; role: string; email_verified: boolean; profile: { display_name?: string; bio?: string; timezone?: string } };

export function ProfilePanel() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState("Loading profile…");

  useEffect(() => { void fetch("/api/auth/me").then(async (response) => {
    if (response.status === 401) { router.replace("/auth"); return; }
    setUser(await response.json()); setStatus("");
  }); }, [router]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("Saving…");
    const response = await fetch("/api/auth/me", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))) });
    if (response.ok) { setUser(await response.json()); setStatus("Profile saved."); }
    else setStatus("Profile could not be saved.");
  }

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.replace("/auth"); router.refresh();
  }

  if (!user) return <div className="card state" role="status">{status}</div>;
  return <section className="card profile-card"><div className="section-heading"><div><h2>{user.profile.display_name}</h2><p>@{user.username} · {user.email}</p></div><span className="pill">{user.email_verified ? "Verified" : "Verification pending"}</span></div>{user.role === "admin" && <p><Link className="button secondary" href="/admin">Open administration</Link></p>}<form onSubmit={save}><label>Display name<input name="display_name" defaultValue={user.profile.display_name} required /></label><label>Bio<textarea name="bio" maxLength={280} defaultValue={user.profile.bio} /></label><label>Timezone<input name="timezone" defaultValue={user.profile.timezone ?? "UTC"} /></label><div className="form-actions"><button className="button">Save profile</button><button className="button secondary" type="button" onClick={logout}>Sign out</button></div>{status && <p role="status">{status}</p>}</form></section>;
}
