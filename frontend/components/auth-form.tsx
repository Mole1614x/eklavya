"use client";

import { FormEvent, useState } from "react";
import { ArrowRight, Eye, EyeOff, LockKeyhole } from "lucide-react";
import { useRouter } from "next/navigation";

type Mode = "login" | "register";

export function AuthForm() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setMessage("");
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const response = await fetch(`/api/auth/${mode}`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
      });
      if (response.ok) {
        const current = await fetch("/api/auth/me", { cache: "no-store" });
        const user = current.ok ? await current.json() as { role?: string } : null;
        router.push(user?.role === "admin" ? "/admin" : "/dashboard");
        router.refresh();
        return;
      }
      const error = await response.json();
      setMessage(typeof error.detail === "string" ? error.detail : "Please check the information and try again.");
    } catch {
      setMessage("Could not connect to EKLAVYA. Check your connection and try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="card auth-card">
      <div className="auth-welcome"><span className="auth-lock"><LockKeyhole size={18}/></span><div><strong>Welcome to your workspace</strong><p>One account for practice, progress and your role-based dashboard.</p></div></div>
      <div className="auth-tabs" role="tablist" aria-label="Account access">
        {(["login", "register"] as Mode[]).map((item) => <button key={item} role="tab" aria-selected={mode === item} onClick={() => { setMode(item); setMessage(""); }}>{item === "login" ? "Sign in" : "Create account"}</button>)}
      </div>
      <form onSubmit={submit}>
        {mode === "register" && <><label>Display name<input name="display_name" minLength={1} maxLength={80} required autoComplete="name" /></label><label>Username<input name="username" pattern="[A-Za-z0-9_]+" minLength={3} maxLength={40} required autoComplete="username" /></label><label>Email<input name="email" type="email" required autoComplete="email" /></label></>}
        {mode === "login" && <label>Email or username<input name="identity" required autoComplete="username" /></label>}
        <label>Password<div className="password-field"><input name="password" type={showPassword ? "text" : "password"} minLength={mode === "register" ? 10 : 1} required autoComplete={mode === "register" ? "new-password" : "current-password"} /><button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword}>{showPassword ? <EyeOff size={18}/> : <Eye size={18}/>}</button></div></label>
        {mode === "register" && <p className="form-hint">Use at least 10 characters with upper-case, lower-case, and numeric characters.</p>}
        {message && <p className="form-error" role="alert">{message}</p>}
        <button className="button" disabled={pending}>{pending ? "Please wait…" : mode === "login" ? "Sign in to workspace" : "Create account"} <ArrowRight size={16}/></button>
      </form>
    </section>
  );
}
