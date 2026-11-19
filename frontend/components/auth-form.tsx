"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

type Mode = "login" | "register";

export function AuthForm() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setMessage("");
    const data = Object.fromEntries(new FormData(event.currentTarget));
    const response = await fetch(`/api/auth/${mode}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
    });
    if (response.ok) {
      router.push("/profile");
      router.refresh();
      return;
    }
    const error = await response.json();
    setMessage(typeof error.detail === "string" ? error.detail : "Please check the highlighted information.");
    setPending(false);
  }

  return (
    <section className="card auth-card">
      <div className="auth-tabs" role="tablist" aria-label="Account access">
        {(["login", "register"] as Mode[]).map((item) => <button key={item} role="tab" aria-selected={mode === item} onClick={() => { setMode(item); setMessage(""); }}>{item === "login" ? "Sign in" : "Create account"}</button>)}
      </div>
      <form onSubmit={submit}>
        {mode === "register" && <><label>Display name<input name="display_name" minLength={1} maxLength={80} required autoComplete="name" /></label><label>Username<input name="username" pattern="[A-Za-z0-9_]+" minLength={3} maxLength={40} required autoComplete="username" /></label><label>Email<input name="email" type="email" required autoComplete="email" /></label></>}
        {mode === "login" && <label>Email or username<input name="identity" required autoComplete="username" /></label>}
        <label>Password<input name="password" type="password" minLength={mode === "register" ? 10 : 1} required autoComplete={mode === "register" ? "new-password" : "current-password"} /></label>
        {mode === "register" && <p className="form-hint">Use at least 10 characters with upper-case, lower-case, and numeric characters.</p>}
        {message && <p className="form-error" role="alert">{message}</p>}
        <button className="button" disabled={pending}>{pending ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</button>
      </form>
    </section>
  );
}
