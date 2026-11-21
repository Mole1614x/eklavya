"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Assessment = { id: string; title: string; description: string; instructions: string; assessment_type: string; duration_minutes: number; opens_at: string; closes_at: string; max_attempts: number; status: string; questions: Array<{ problem_slug: string; title: string; difficulty: string; points: number; languages: string[]; format: string }> };
type Attempt = { id: string; assessment_id: string; assessment_title: string; attempt_number: number; status: string; deadline_at: string; server_time: string; score: number | null; max_score: number | null; questions: Assessment["questions"]; answers: Array<{ problem_slug: string; answer: string; saved_at: string }> };
type Dataset = { id: string; title: string; description: string; category: string; difficulty: string; format: string; original_filename: string; size_bytes: number; status: string; version: number; download_allowed: boolean; column_info: Array<Record<string, unknown>>; profile: { rows?: number; columns?: number; missing_values?: number; duplicate_rows?: number; preview?: Array<Record<string, unknown>> }; transformations: Array<Record<string, unknown>>; owned_by_current_user: boolean };
type Evaluation = { valid: boolean; passed: boolean | null; result: unknown; feedback: string; supported_subset: string[] };
type MultiTool = { key: string; title: string; description: string; objective: string; technologies: string[]; progress: Record<string, boolean> };

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/advanced/${path}`, init);
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) throw new Error(data?.detail ?? `Request failed (${response.status})`);
  return data as T;
}

function fileBase64(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("The selected file could not be read"));
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] ?? "");
    reader.readAsDataURL(file);
  });
}

export function AdvancedPractice({ section }: { section: string }) {
  if (section === "assessments") return <Assessments />;
  if (section === "data-cleaning-lab") return <DataLab />;
  if (section === "excel-practice") return <ExpressionLab kind="excel" />;
  if (section === "tableau-practice") return <ExpressionLab kind="tableau" />;
  if (section === "linux-practice") return <LinuxPractice />;
  if (section === "multi-tool-challenges") return <MultiToolPractice />;
  return <DatasetLibrary />;
}

function Assessments() {
  const [items, setItems] = useState<Assessment[]>([]);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("Loading assigned assessments…");
  const [judge, setJudge] = useState<Record<string, string>>({});
  const [clock, setClock] = useState(Date.now());
  const load = useCallback(async () => {
    try { setItems(await api<Assessment[]>("assessments")); setMessage(""); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Assessments are unavailable"); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!attempt || attempt.status !== "IN_PROGRESS") return;
    const timer = window.setInterval(() => setClock(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [attempt]);
  const remaining = useMemo(() => attempt ? Math.max(0, Math.ceil((new Date(attempt.deadline_at).getTime() - clock) / 1000)) : 0, [attempt, clock]);
  useEffect(() => {
    if (attempt?.status === "IN_PROGRESS" && remaining === 0) void submit();
  }, [attempt?.id, attempt?.status, remaining]);

  async function start(id: string) {
    try {
      setMessage("Starting with the authoritative server clock…");
      const current = await api<Attempt>(`assessments/${id}/start`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      setAttempt(current); setDrafts(Object.fromEntries(current.answers.map((answer) => [answer.problem_slug, answer.answer]))); setMessage(""); setClock(Date.now());
    } catch (error) { setMessage(error instanceof Error ? error.message : "Assessment could not start"); }
  }
  async function save(problemSlug: string) {
    if (!attempt) return;
    try {
      setMessage("Autosaving…");
      const current = await api<Attempt>(`assessments/attempts/${attempt.id}/answers`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ problem_slug: problemSlug, answer: drafts[problemSlug] ?? "" }),
      });
      setAttempt(current); setMessage("Answer saved using the server deadline.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Autosave failed"); }
  }
  async function submit() {
    if (!attempt) return;
    try { setAttempt(await api<Attempt>(`assessments/attempts/${attempt.id}/submit`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })); setMessage("Assessment finalized."); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Submission failed"); }
  }
  async function runQuestion(problemSlug: string, language: string) {
    if (!attempt) return;
    try {
      setJudge((value) => ({ ...value, [problemSlug]: "Queued for the isolated judge…" }));
      const response = await api<{ id: string; status: string; verdict: string | null }>(`assessments/attempts/${attempt.id}/questions/${problemSlug}/submissions`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language, source_code: drafts[problemSlug] ?? "", mode: "SUBMIT" }),
      });
      for (let poll = 0; poll < 40; poll += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, Math.min(500 + poll * 100, 1800)));
        const currentResponse = await fetch(`/api/submissions/${response.id}`);
        if (!currentResponse.ok) break;
        const current = await currentResponse.json() as { status: string; verdict: string | null };
        setJudge((value) => ({ ...value, [problemSlug]: current.verdict ?? current.status }));
        if (["FINISHED", "SYSTEM_ERROR", "CANCELLED"].includes(current.status)) {
          setAttempt(await api<Attempt>(`assessments/attempts/${attempt.id}`)); return;
        }
      }
    } catch (error) { setJudge((value) => ({ ...value, [problemSlug]: error instanceof Error ? error.message : "Judge submission failed" })); }
  }

  if (attempt) return <section className="advanced-stack">
    <div className="card advanced-toolbar"><div><strong>{attempt.assessment_title}</strong><p>Attempt {attempt.attempt_number} · {attempt.status}</p></div><strong aria-live="polite">{attempt.status === "IN_PROGRESS" ? `${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, "0")} remaining` : attempt.score === null ? "Result pending release" : `${attempt.score} / ${attempt.max_score}`}</strong></div>
    {attempt.questions.map((question, index) => <article className="card advanced-editor" key={question.problem_slug}>
      <div className="section-heading"><div><h2>{index + 1}. {question.title}</h2><p>{question.difficulty} · {question.points} points</p></div><Link href={`/problems/${question.problem_slug}`}>Open practice problem</Link></div>
      <label>Your assessment answer<textarea disabled={attempt.status !== "IN_PROGRESS"} value={drafts[question.problem_slug] ?? ""} onChange={(event) => setDrafts((value) => ({ ...value, [question.problem_slug]: event.target.value }))} onBlur={() => void save(question.problem_slug)} /></label>
      {attempt.status === "IN_PROGRESS" && <div className="form-actions"><button className="button secondary" onClick={() => void save(question.problem_slug)}>Save answer</button>{question.languages.length > 0 && <button className="button" onClick={() => void runQuestion(question.problem_slug, question.languages[0])}>Submit to secure judge ({question.languages[0]})</button>}</div>}
      {judge[question.problem_slug] && <p role="status">{judge[question.problem_slug]}</p>}
    </article>)}
    {attempt.status === "IN_PROGRESS" && <button className="button" onClick={() => void submit()}>Submit assessment</button>}
    {message && <p role="status">{message}</p>}
  </section>;

  return <section className="advanced-stack">
    {message && <div className="card state" role="status">{message}</div>}
    {!message && items.length === 0 && <div className="card state"><h2>No assigned assessments</h2><p>Published assessments assigned by an administrator will appear here.</p></div>}
    <div className="skills-grid">{items.map((item) => <article className="card feature-card" key={item.id}><span className="pill">{item.assessment_type}</span><h2>{item.title}</h2><p>{item.description}</p><p>{item.duration_minutes} minutes · {item.questions.length} questions · up to {item.max_attempts} attempt(s)</p><button className="button" onClick={() => void start(item.id)}>Start or resume</button></article>)}</div>
  </section>;
}

function DataLab() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selected, setSelected] = useState<Dataset | null>(null);
  const [message, setMessage] = useState("Loading your private datasets…");
  const [technology, setTechnology] = useState("PANDAS");
  const [source, setSource] = useState("result = df.drop_duplicates()\n");
  const [runOutput, setRunOutput] = useState("");
  const load = useCallback(async (preferredId?: string) => { try { const values = await api<Dataset[]>("datasets/mine"); setDatasets(values); setSelected((current) => values.find((item) => item.id === preferredId) ?? values.find((item) => item.id === current?.id) ?? values[0] ?? null); setMessage(""); } catch (error) { setMessage(error instanceof Error ? error.message : "Data Lab is unavailable"); } }, []);
  useEffect(() => { void load(); }, [load]);
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const formElement = event.currentTarget; const form = new FormData(formElement); const file = form.get("file") as File;
    if (!file?.size) return;
    try {
      setMessage("Validating and profiling your private dataset…");
      const created = await api<Dataset>("datasets", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
        title: form.get("title"), description: form.get("description"), category: "Personal", difficulty: "Beginner",
        filename: file.name, content_type: file.type || "application/octet-stream", content_base64: await fileBase64(file),
      }) });
      formElement.reset(); await load(created.id); setMessage("Dataset uploaded. No user code was executed during preview.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Upload failed"); }
  }
  async function transform(operation: string) {
    if (!selected) return;
    try { setMessage("Applying bounded transformation…"); const updated = await api<Dataset>(`datasets/${selected.id}/transform`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ operation }) }); await load(updated.id); setMessage("Transformation preview updated."); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Transformation failed"); }
  }
  async function remove() {
    if (!selected) return;
    try { await api(`datasets/${selected.id}`, { method: "DELETE" }); setSelected(null); await load(); setMessage("Private dataset deleted."); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Deletion failed"); }
  }
  async function runPractice() {
    if (!selected) return;
    try {
      setRunOutput("Queued for isolated execution…");
      const run = await api<{ id: string }>(`datasets/${selected.id}/practice`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ technology, source_code: source }) });
      for (let poll = 0; poll < 40; poll += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, Math.min(500 + poll * 100, 1800)));
        const current = await api<{ status: string; output: string | null; execution_ms: number | null }>(`datasets/practice/${run.id}`);
        setRunOutput(current.status === "FINISHED" || current.status === "SYSTEM_ERROR" ? `${current.output ?? "No output"}${current.execution_ms !== null ? `\n${current.execution_ms} ms` : ""}` : `${current.status.toLowerCase()}…`);
        if (["FINISHED", "SYSTEM_ERROR"].includes(current.status)) return;
      }
      setRunOutput("The run is still processing and remains available to the server.");
    } catch (error) { setRunOutput(error instanceof Error ? error.message : "Practice run failed"); }
  }
  return <div className="advanced-two">
    <form className="card advanced-editor" onSubmit={upload}><h2>Upload private data</h2><label>Dataset title<input name="title" required /></label><label>Description<textarea name="description" /></label><label>CSV, XLSX, JSON, or Parquet<input name="file" type="file" accept=".csv,.xlsx,.json,.parquet" required /></label><button className="button">Upload and profile</button><p>Uploads are private by default, quota-limited, type-checked, and never executed as code.</p></form>
    <section className="advanced-stack">{message && <p role="status">{message}</p>}<div className="card advanced-editor"><h2>Your datasets</h2><select aria-label="Select dataset" value={selected?.id ?? ""} onChange={(event) => setSelected(datasets.find((item) => item.id === event.target.value) ?? null)}><option value="">Choose a dataset</option>{datasets.map((item) => <option key={item.id} value={item.id}>{item.title} v{item.version}</option>)}</select></div>
      {selected && <article className="card advanced-editor"><div className="section-heading"><div><h2>{selected.title}</h2><p>{selected.format} · {Math.ceil(selected.size_bytes / 1024)} KB</p></div><span className="pill">Private</span></div><div className="admin-metrics">{[["Rows", selected.profile.rows], ["Columns", selected.profile.columns], ["Missing", selected.profile.missing_values], ["Duplicates", selected.profile.duplicate_rows]].map(([label, value]) => <div key={String(label)}><small>{label}</small><strong>{String(value ?? 0)}</strong></div>)}</div><div className="form-actions"><button className="button secondary" onClick={() => void transform("drop_duplicates")}>Remove duplicates</button><a className="button secondary" href={`/api/advanced/datasets/${selected.id}/download`}>Download cleaned CSV</a><button className="button secondary" onClick={() => void remove()}>Delete</button></div><Preview rows={selected.profile.preview ?? []} /><h3>Free practice sandbox</h3><label>Technology<select value={technology} onChange={(event) => { const next = event.target.value; setTechnology(next); setSource(next === "SQL" ? "SELECT * FROM dataset LIMIT 20;" : next === "NUMPY" ? "result = np.asarray(df.select_dtypes(include='number'))\n" : "result = df.drop_duplicates()\n"); }}><option>PANDAS</option><option>NUMPY</option><option>SQL</option></select></label><label>Code or query<textarea className="expression-editor" value={source} onChange={(event) => setSource(event.target.value)} spellCheck={false} /></label><button className="button" onClick={() => void runPractice()}>Run in isolated sandbox</button>{runOutput && <pre role="status">{runOutput}</pre>}</article>}
    </section>
  </div>;
}

function Preview({ rows }: { rows: Array<Record<string, unknown>> }) {
  const columns = rows[0] ? Object.keys(rows[0]) : [];
  if (!rows.length) return <p>No preview rows.</p>;
  return <div className="advanced-table"><table><thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{rows.slice(0, 8).map((row, index) => <tr key={index}>{columns.map((column) => <td key={column}>{String(row[column] ?? "")}</td>)}</tr>)}</tbody></table></div>;
}

function ExpressionLab({ kind }: { kind: "excel" | "tableau" }) {
  const excel = kind === "excel";
  const [expression, setExpression] = useState(excel ? "=SUMIF(A2:A4,E2,B2:B4)" : "SUM([Profit]) / SUM([Sales])");
  const [result, setResult] = useState<Evaluation | null>(null);
  const [message, setMessage] = useState("");
  async function evaluate() {
    try {
      setMessage("Evaluating supported semantics…");
      const body = excel
        ? { expression, cells: { A2: "West", A3: "East", A4: "West", B2: 5, B3: 8, B4: 7, E2: "West" }, expected: 12 }
        : { expression, fields: ["Profit", "Sales"], rows: [{ Profit: 20, Sales: 100 }, { Profit: 30, Sales: 150 }], expected: 0.2 };
      setResult(await api<Evaluation>(`${kind}/evaluate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })); setMessage("");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Evaluation failed"); }
  }
  async function evaluateWorkbook(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const file = new FormData(event.currentTarget).get("workbook") as File;
    try { setResult(await api<Evaluation>("excel/evaluate-workbook", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ challenge_key: "regional-sales", filename: file.name, content_base64: await fileBase64(file), answer_cell: "F2" }) })); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Workbook evaluation failed"); }
  }
  return <div className="problem-layout"><section className="card statement"><h2>{excel ? "Regional sales" : "Overall profit ratio"}</h2><p>{excel ? "Total Sales in B2:B4 where Region in A2:A4 matches E2." : "Calculate total Profit divided by total Sales using aggregate functions."}</p><h3>Fixture</h3><pre>{excel ? "West  5\nEast  8\nWest  7\nE2 = West" : "Profit  Sales\n20      100\n30      150"}</pre><p>The grader implements a documented subset and reports unsupported functions explicitly. It does not claim full {excel ? "Microsoft Excel" : "Tableau"} compatibility.</p></section><section className="card advanced-editor"><label>{excel ? "Excel formula" : "Tableau expression"}<textarea className="expression-editor" value={expression} onChange={(event) => setExpression(event.target.value)} spellCheck={false} /></label><button className="button" onClick={() => void evaluate()}>Validate and submit</button>{excel && <form className="advanced-stack" onSubmit={evaluateWorkbook}><label>Or upload an XLSX solution (formula in F2)<input name="workbook" type="file" accept=".xlsx" required /></label><button className="button secondary">Evaluate workbook</button></form>}{message && <p role="status">{message}</p>}{result && <div className="judge-result" role="status"><strong>{result.valid ? result.passed ? "Accepted" : "Valid" : "Validation error"}</strong><span>{result.feedback}</span>{result.result !== null && <pre>{JSON.stringify(result.result, null, 2)}</pre>}<details><summary>Supported functions ({result.supported_subset.length})</summary><p>{result.supported_subset.join(", ")}</p></details></div>}</section></div>;
}

function LinuxPractice() {
  const modules = ["Linux fundamentals", "Files and directories", "File permissions", "Text processing", "Process management", "Networking", "Disk monitoring", "Shell scripting", "Pipes and cron", "Linux for data engineering"];
  return <section className="advanced-stack"><div className="card advanced-editor"><h2>Disposable Linux sandbox</h2><p>Every Bash submission runs as UID 65534 in a fresh container with no network, a read-only root filesystem, dropped capabilities, bounded CPU/memory/PIDs/output, and deterministic fixtures.</p><Link className="button" href="/problems?category=linux">Browse Linux problems</Link></div><div className="skills-grid">{modules.map((module, index) => <article className="card feature-card" key={module}><span className="pill">Module {index + 1}</span><h2>{module}</h2></article>)}</div></section>;
}

function MultiToolPractice() {
  const [items, setItems] = useState<MultiTool[]>([]); const [technology, setTechnology] = useState("SQL"); const [answer, setAnswer] = useState("SELECT Region, SUM(Sales) FROM Orders GROUP BY Region;"); const [message, setMessage] = useState("Loading challenge…");
  const load = useCallback(async (clearMessage = true) => { try { setItems(await api<MultiTool[]>("multi-tool/challenges")); if (clearMessage) setMessage(""); } catch (error) { setMessage(error instanceof Error ? error.message : "Challenge unavailable"); } }, []);
  useEffect(() => { void load(); }, [load]);
  async function submit() { if (!items[0]) return; try { const result = await api<Evaluation>("multi-tool/submit", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ challenge_key: items[0].key, technology, answer }) }); setMessage(result.feedback); await load(false); } catch (error) { setMessage(error instanceof Error ? error.message : "Submission failed"); } }
  const challenge = items[0];
  return <div className="problem-layout"><section className="card statement"><h2>{challenge?.title ?? "Total sales by region"}</h2><p>{challenge?.description}</p><h3>Independent completion</h3><ul>{challenge?.technologies.map((item) => <li key={item}>{item}: {challenge.progress[item] ? "Completed" : "Not completed"}</li>)}</ul><p>Each grader preserves its tool&apos;s null, ordering, aggregation, and calculation-context semantics.</p></section><section className="card advanced-editor"><label>Technology<select value={technology} onChange={(event) => setTechnology(event.target.value)}>{["SQL", "PANDAS", "PYSPARK", "EXCEL", "TABLEAU"].map((item) => <option key={item}>{item}</option>)}</select></label><label>Solution<textarea className="expression-editor" value={answer} onChange={(event) => setAnswer(event.target.value)} /></label><button className="button" onClick={() => void submit()}>Submit approach</button>{message && <p role="status">{message}</p>}</section></div>;
}

function DatasetLibrary() {
  const [items, setItems] = useState<Dataset[]>([]); const [message, setMessage] = useState("Loading published datasets…");
  useEffect(() => { void api<Dataset[]>("datasets/library").then((values) => { setItems(values); setMessage(""); }).catch((error) => setMessage(error instanceof Error ? error.message : "Dataset library unavailable")); }, []);
  return <section className="advanced-stack">{message && <div className="card state" role="status">{message}</div>}<div className="skills-grid">{items.map((item) => <article className="card feature-card" key={item.id}><span className="pill">{item.category} · {item.difficulty}</span><h2>{item.title}</h2><p>{item.description}</p><p>{item.format} · version {item.version} · {item.profile.rows ?? 0} rows</p>{item.download_allowed && <a className="button secondary" href={`/api/advanced/datasets/${item.id}/download`}>Download</a>}</article>)}</div>{!message && !items.length && <div className="card state"><h2>No published datasets yet</h2><p>Administrators can publish synthetic or appropriately licensed datasets from Dataset Management.</p></div>}</section>;
}
