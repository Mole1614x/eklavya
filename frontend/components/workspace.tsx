"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import type { OnMount } from "@monaco-editor/react";
import { Play, Send } from "lucide-react";
import type { ProblemDetail } from "@/lib/api";

const Editor = dynamic(() => import("@monaco-editor/react").then((module) => module.default), {
  ssr: false, loading: () => <p role="status">Loading editor…</p>,
});

const languages: Record<string, string> = { python: "Python", java: "Java", c: "C", cpp: "C++", sql: "SQL", bash: "Bash", excel: "Excel formula", tableau: "Tableau expression" };
type Result = { id: string; status: string; verdict: string | null; output: string | null; passed_tests: number; total_tests: number; execution_ms: number | null };

export function Workspace({ problem, contestSlug }: { problem: ProblemDetail; contestSlug?: string }) {
  const [language, setLanguage] = useState(problem.starters[0]?.language ?? "");
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [tab, setTab] = useState("Test cases");
  const [status, setStatus] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [pending, setPending] = useState(false);
  const [editorUnavailable, setEditorUnavailable] = useState(false);
  const starter = problem.starters.find((entry) => entry.language === language)?.code ?? "";
  const code = drafts[language] ?? starter;
  const updateDraft = (value: string) => setDrafts((current) => ({ ...current, [language]: value }));

  useEffect(() => {
    if (!problem.starters.length) return;
    let active = true;
    const timer = window.setTimeout(() => { if (active) setEditorUnavailable(true); }, 12000);
    void import("@monaco-editor/react").then(({ loader }) => {
      loader.config({ paths: { vs: "/monaco/vs" } });
      return loader.init();
    }).then(() => window.clearTimeout(timer), () => {
      window.clearTimeout(timer);
      if (active) setEditorUnavailable(true);
    });
    return () => { active = false; window.clearTimeout(timer); };
  }, [problem.starters.length]);

  async function act(action: "Run" | "Submit") {
    setTab(action === "Run" ? "Output" : "Submissions");
    setPending(true); setResult(null); setStatus("Sending your solution to the judge…");
    const endpoint = action === "Submit" && contestSlug
      ? `/api/contests/${encodeURIComponent(contestSlug)}/problems/${encodeURIComponent(problem.slug)}/submissions`
      : `/api/submissions/problem/${problem.slug}`;
    const response = await fetch(endpoint, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ language: language || "answer", source_code: code, mode: action === "Run" ? "RUN" : "SUBMIT" }),
    });
    const created = await response.json();
    if (!response.ok) { setStatus(created.detail ?? "The submission could not be created."); setPending(false); return; }
    setResult(created); setStatus("Queued for evaluation…");
    for (let attempt = 0; attempt < 40; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, Math.min(500 + attempt * 100, 2000)));
      const poll = await fetch(`/api/submissions/${created.id}`);
      if (!poll.ok) break;
      const current: Result = await poll.json();
      setResult(current);
      setStatus(current.status === "RUNNING" ? "Running isolated tests…" : "Queued for evaluation…");
      if (["FINISHED", "SYSTEM_ERROR", "CANCELLED"].includes(current.status)) { setPending(false); setStatus(""); return; }
    }
    setPending(false); setStatus("The judge is still working. This result remains in your submission history.");
  }

  async function cancel() {
    if (!result) return;
    const response = await fetch(`/api/submissions/${result.id}/cancel`, { method: "POST" });
    const current = await response.json();
    if (!response.ok) { setStatus(current.detail ?? "This submission could not be cancelled."); return; }
    setResult(current); setStatus(current.status === "CANCELLED" ? "" : "Cancellation requested…");
    if (current.status === "CANCELLED") setPending(false);
  }

  const mountEditor: OnMount = (editor) => editor.updateOptions({ tabFocusMode: true });

  return (
    <section className="card workspace" aria-label="Practice workspace">
      {contestSlug && <div className="contest-workspace">Arena submission · Runs do not affect contest standings</div>}
      <div className="workspace-toolbar">
        {language ? <label>Language <select value={language} onChange={(event) => setLanguage(event.target.value)}>{problem.starters.map((entry) => <option key={entry.language} value={entry.language}>{languages[entry.language] ?? entry.language}</option>)}</select></label> : <strong>Your answer</strong>}
        <div><button className="button secondary" disabled={pending} onClick={() => void act("Run")}><Play size={15} /> Run</button><button className="button" disabled={pending} onClick={() => void act("Submit")}><Send size={15} /> Submit</button>{pending && result && <button className="button secondary" onClick={() => void cancel()}>Cancel</button>}</div>
      </div>
      {language && !editorUnavailable
        ? <Editor height="360px" path={`${problem.slug}.${language}`} language={language} value={code} theme="vs-dark" loading={<p role="status">Loading editor…</p>} options={{ minimap: { enabled: false }, fontSize: 14, padding: { top: 14 }, ariaLabel: "Solution editor", scrollBeyondLastLine: false }} onMount={mountEditor} onChange={(value) => updateDraft(value ?? "")} />
        : <div className="answer">{editorUnavailable && <p role="status">Monaco could not load. You can still draft your code below.</p>}{problem.format === "MULTIPLE_CHOICE" ? (
          <fieldset className="answer-options"><legend>Choose one answer</legend>{problem.choices.map((choice) => <label key={choice}><input type="radio" name="answer" value={choice} checked={code === choice} onChange={(event) => updateDraft(event.target.value)} />{choice}</label>)}</fieldset>
        ) : problem.format === "NUMERICAL" ? (
          <label className="numerical">Draft answer<input type="number" step="any" value={code} onChange={(event) => updateDraft(event.target.value)} /></label>
        ) : (
          <textarea aria-label="Solution editor" placeholder="Enter your code" value={code} onChange={(event) => updateDraft(event.target.value)} />
        )}</div>}
      <div className="workspace-tabs" role="group" aria-label="Workspace panels">{["Test cases", "Output", "Submissions"].map((name) => <button key={name} onClick={() => { setTab(name); setStatus(""); }} aria-pressed={tab === name}>{name}</button>)}</div>
      <div className="workspace-panel">
        {tab === "Test cases" ? problem.examples.map(({ input, output }, index) => <div key={index} className="example"><small>Sample {index + 1} · input</small><pre>{input}</pre><small>Expected output</small><pre>{output}</pre></div>)
          : <div role="status">{status && <p>{status}</p>}{result && <div className="judge-result"><strong>{result.verdict ?? result.status}</strong><span>{result.passed_tests} / {result.total_tests} tests{result.execution_ms !== null ? ` · ${result.execution_ms} ms` : ""}</span>{result.output && <pre>{result.output}</pre>}</div>}{!status && !result && <p>Sign in to run a solution or review your saved submission history.</p>}</div>}
      </div>
    </section>
  );
}
