"use client";

import { useEffect, useState } from "react";
import Editor, { loader } from "@monaco-editor/react";
import { Play, Send } from "lucide-react";
import type { ProblemDetail } from "@/lib/api";

loader.config({ paths: { vs: "/monaco/vs" } });

const languages: Record<string, string> = { python: "Python", java: "Java", c: "C", cpp: "C++", sql: "SQL" };

export function Workspace({ problem }: { problem: ProblemDetail }) {
  const [language, setLanguage] = useState(problem.starters[0]?.language ?? "");
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [tab, setTab] = useState("Test cases");
  const [status, setStatus] = useState("");
  const [editorUnavailable, setEditorUnavailable] = useState(false);
  const starter = problem.starters.find((entry) => entry.language === language)?.code ?? "";
  const code = drafts[language] ?? starter;
  const updateDraft = (value: string) => setDrafts((current) => ({ ...current, [language]: value }));

  useEffect(() => {
    if (!problem.starters.length) return;
    let active = true;
    const timer = window.setTimeout(() => { if (active) setEditorUnavailable(true); }, 12000);
    void loader.init().then(() => window.clearTimeout(timer), () => {
      window.clearTimeout(timer);
      if (active) setEditorUnavailable(true);
    });
    return () => { active = false; window.clearTimeout(timer); };
  }, [problem.starters.length]);

  function act(action: "Run" | "Submit") {
    setTab(action === "Run" ? "Output" : "Submissions");
    setStatus(action === "Run" ? "Execution is unavailable in Phase 1." : "Submissions are unavailable in Phase 1.");
  }

  return (
    <section className="card workspace" aria-label="Practice workspace">
      <div className="workspace-toolbar">
        {language ? <label>Language <select value={language} onChange={(event) => setLanguage(event.target.value)}>{problem.starters.map((entry) => <option key={entry.language} value={entry.language}>{languages[entry.language] ?? entry.language}</option>)}</select></label> : <strong>Your answer</strong>}
        <div><button className="button secondary" onClick={() => act("Run")}><Play size={15} /> Run</button><button className="button" onClick={() => act("Submit")}><Send size={15} /> Submit</button></div>
      </div>
      {language && !editorUnavailable
        ? <Editor height="360px" path={`${problem.slug}.${language}`} language={language} value={code} theme="vs-dark" loading={<p role="status">Loading editor…</p>} options={{ minimap: { enabled: false }, fontSize: 14, padding: { top: 14 }, ariaLabel: "Solution editor", scrollBeyondLastLine: false }} onMount={(editor) => editor.updateOptions({ tabFocusMode: true })} onChange={(value) => updateDraft(value ?? "")} />
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
          : <p role="status">{status || (tab === "Output" ? "Execution is unavailable in Phase 1." : "Submissions are unavailable in Phase 1.")}</p>}
      </div>
    </section>
  );
}
