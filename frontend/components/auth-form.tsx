"use client";

import { FormEvent, useState } from "react";
import { ArrowRight, AtSign, Eye, EyeOff, LockKeyhole, Mail, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";

type Mode = "login" | "register";

export function AuthForm() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  function switchMode(next: Mode) {
    setMode(next);
    setMessage("");
    setShowPassword(false);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
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

  return <section className="auth-card auth-access-card" aria-labelledby="auth-form-title">
    <div className="auth-card-topline"><span className="auth-card-logo"><LockKeyhole size={19}/></span><span>ACCOUNT ACCESS</span></div>
    <div className="auth-card-intro">
      <h2 id="auth-form-title">{mode === "login" ? "Welcome back." : "Start your journey."}</h2>
      <p>{mode === "login" ? "Sign in to continue your practice and pick up where you left off." : "Create your free account and start building your skills."}</p>
    </div>

    <div className="auth-tabs" role="tablist" aria-label="Account access">
      {(["login", "register"] as Mode[]).map(item =>
        <button key={item} id={`auth-tab-${item}`} type="button" role="tab" aria-selected={mode === item}
          aria-controls="auth-access-panel" onClick={() => switchMode(item)} disabled={pending}>
          {item === "login" ? "Sign in" : "Create account"}
        </button>
      )}
    </div>

    <div id="auth-access-panel" role="tabpanel" aria-labelledby={`auth-tab-${mode}`}>
      <form onSubmit={submit} className="auth-access-form">
        {mode === "register" && <>
          <div className="auth-form-field">
            <label htmlFor="auth-display-name">Display name</label>
            <div className="auth-input-shell"><UserRound size={17} aria-hidden="true"/><input id="auth-display-name" name="display_name" placeholder="How should we call you?" minLength={1} maxLength={80} required autoComplete="name"/></div>
          </div>
          <div className="auth-form-field">
            <label htmlFor="auth-username">Username</label>
            <div className="auth-input-shell"><AtSign size={17} aria-hidden="true"/><input id="auth-username" name="username" placeholder="Choose a username" pattern="[A-Za-z0-9_]+" minLength={3} maxLength={40} required autoComplete="username"/></div>
          </div>
          <div className="auth-form-field">
            <label htmlFor="auth-email">Email</label>
            <div className="auth-input-shell"><Mail size={17} aria-hidden="true"/><input id="auth-email" name="email" type="email" placeholder="you@example.com" required autoComplete="email"/></div>
          </div>
        </>}
        {mode === "login" && <div className="auth-form-field">
          <label htmlFor="auth-identity">Email or username</label>
          <div className="auth-input-shell"><Mail size={17} aria-hidden="true"/><input id="auth-identity" name="identity" placeholder="Enter your email or username" required autoComplete="username"/></div>
        </div>}

        <div className="auth-form-field">
          <label htmlFor="eklavya-auth-password">Password</label>
          <div className="auth-input-shell auth-password-shell">
            <LockKeyhole size={17} aria-hidden="true"/>
            <input id="eklavya-auth-password" name="password" placeholder={mode === "register" ? "Create a strong password" : "Enter your password"}
              type={showPassword ? "text" : "password"} minLength={mode === "register" ? 10 : 1} required
              autoComplete={mode === "register" ? "new-password" : "current-password"}
              aria-describedby={mode === "register" ? "auth-password-hint" : undefined}/>
            <button type="button" onClick={() => setShowPassword(value => !value)}
              aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword}>
              {showPassword ? <EyeOff size={18}/> : <Eye size={18}/>}
            </button>
          </div>
        </div>
        {mode === "register" && <p id="auth-password-hint" className="form-hint">At least 10 characters with uppercase, lowercase and numbers.</p>}
        {message && <p className="form-error auth-form-error" role="alert">{message}</p>}
        <button className="auth-submit" disabled={pending} type="submit">
          {pending ? "Please wait…" : mode === "login" ? "Sign in to workspace" : "Create account"}
          <ArrowRight size={18}/>
        </button>
      </form>
    </div>

    <p className="auth-form-footer">Build confidence with every challenge.</p>
  </section>;
}
