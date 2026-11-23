"use client";

import Link from "next/link";
import { StudentAccessManager, StudentAccessPicker, type StudentScope } from "./student-access";
import { FormEvent, useCallback, useEffect, useState } from "react";

type Section = "overview" | "assessments" | "problems" | "datasets" | "users" | "contests" | "paths" | "achievements" | "audit";
type Overview = Record<string, number | Array<{ day?: string; count?: number; username?: string; display_name?: string; created_at?: string }>>;
type Problem = { access_scope: StudentScope; assigned_count: number; slug: string; title: string; category: string; difficulty: string; format: string; topic: string; status: string; supported_languages: string[]; test_case_count: number; hidden_test_count: number };
type Dataset = { id: string; name: string; kind: string; version: number; original_filename: string; size_bytes: number; sha256: string; is_active: boolean; created_at: string };
type User = { id: number; username: string; email: string; display_name: string; role: string; is_active: boolean; created_at: string; last_login_at: string | null; submissions: number; accepted_submissions: number; system_errors: number };
type Contest = { access_scope: StudentScope; assigned_count: number; slug: string; title: string; starts_at: string; ends_at: string; is_rated: boolean; publication_status: string; registrations: number; submissions: number; problem_count: number };
type Path = { access_scope: StudentScope; assigned_count: number; slug: string; title: string; status: string; prerequisites: string[]; problem_count: number; enrollments: number };
type Achievement = { slug: string; name: string; description: string; criteria: Record<string, unknown>; xp_reward: number; awarded_count: number };
type Audit = { id: number; actor_username: string | null; action: string; target_type: string; target_id: string; details: Record<string, unknown>; ip_address: string | null; created_at: string };
type Ledger = { id: number; username: string; amount?: number; reason?: string; rank_slug?: string; created_at?: string; reached_at?: string };
type Assessment = { access_scope: StudentScope; assigned_user_ids: number[]; assigned_group_ids: string[]; id: string; title: string; assessment_type: string; duration_minutes: number; opens_at: string; closes_at: string; status: string; assigned_count: number; attempt_count: number; questions: Array<{ title: string; points: number }> };
type PracticeDataset = { access_scope: StudentScope; id: string; title: string; category: string; difficulty: string; format: string; version: number; status: string; size_bytes: number; profile: { rows?: number }; download_allowed: boolean };
type LearnerGroup = { id: string; name: string; user_ids: number[]; created_at: string };

const sections: Array<[Section, string]> = [
  ["overview", "Overview"], ["assessments", "Assessment Management"], ["problems", "Problems / Question Management"], ["datasets", "Datasets / Dataset Management"],
  ["users", "Users"], ["contests", "Contests"], ["paths", "Learning paths"],
  ["achievements", "Achievements & XP"], ["audit", "Audit log"],
];

const initialProblem = JSON.stringify({
  title: "", category: "foundations", difficulty: "Easy", format: "CODE", topic: "",
  tags: [], description: "", constraints: [], examples: [], choices: [], status: "DRAFT",
  access_scope: "ALL", assigned_user_ids: [],
  starters: [{ language: "python", code: "" }],
  test_cases: [{ input_data: "", expected_output: "", is_hidden: false, position: 0 }],
  evaluator: null,
}, null, 2);
const initialContest = JSON.stringify({
  title: "", description: "", starts_at: new Date(Date.now() + 86400000).toISOString(),
  ends_at: new Date(Date.now() + 90000000).toISOString(), is_rated: true,
  publication_status: "DRAFT", access_scope: "ALL", assigned_user_ids: [], problems: [{ problem_slug: "", points: 100 }],
}, null, 2);
const initialPath = JSON.stringify({ title: "", description: "", prerequisites: [], status: "DRAFT", access_scope: "ALL", assigned_user_ids: [], problems: [] }, null, 2);
const initialAchievement = JSON.stringify({ name: "", description: "", criteria: { solved: 1 }, xp_reward: 0 }, null, 2);
const initialAssessment = JSON.stringify({
  title: "Data Analyst Screening", description: "Role-specific technical assessment", instructions: "Complete every question before the server timer expires.",
  assessment_type: "MIXED", duration_minutes: 90,
  opens_at: new Date(Date.now() + 3600000).toISOString(), closes_at: new Date(Date.now() + 86400000).toISOString(),
  max_attempts: 1, penalty_percent: 0, release_results: false, status: "DRAFT", access_scope: "SELECTED", template_key: "data-analyst",
  questions: [{ problem_slug: "city-totals", points: 100 }], assigned_user_ids: [], assigned_group_ids: [],
}, null, 2);

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/admin/${path}`, init);
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) throw new Error(data?.detail ?? `Request failed (${response.status})`);
  return data as T;
}

async function advancedApi<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/advanced/admin/${path}`, init);
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) throw new Error(data?.detail ?? `Request failed (${response.status})`);
  return data as T;
}

function formatDate(value: string | null | undefined) {
  return value ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "Never";
}

function fileBase64(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("The selected file could not be read"));
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] ?? "");
    reader.readAsDataURL(file);
  });
}

function JsonEditor({ title, initial, endpoint, onSaved }: { title: string; initial: string; endpoint: string; onSaved: () => Promise<void> }) {
  const [message, setMessage] = useState("");
  const [scope, setScope] = useState<StudentScope>("ALL");
  const [students, setStudents] = useState<number[]>([]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const slug = String(form.get("slug") ?? "").trim();
    try {
      setMessage("Saving…");
      const definition = JSON.parse(String(form.get("definition")));
      definition.access_scope = scope;
      definition.assigned_user_ids = students;
      if (definition.status === "PUBLISHED" || definition.publication_status === "PUBLISHED") {
        if (scope === "SELECTED" && students.length === 0) throw new Error("Select at least one student before publishing.");
      }
      await api(`${endpoint}/${encodeURIComponent(slug)}`, {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(definition),
      });
      setMessage("Saved and audited.");
      await onSaved();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Save failed"); }
  }
  return <form className="card admin-editor" onSubmit={submit}>
    <h3>{title}</h3>
    <label>Slug<input name="slug" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" /></label>
    <StudentAccessPicker scope={scope} onScopeChange={setScope} selectedIds={students} onSelectedIdsChange={setStudents}/>
    <label>Validated definition<textarea name="definition" defaultValue={initial} required spellCheck={false} /></label>
    <div className="form-actions"><button className="button">Save</button><span role="status">{message}</span></div>
  </form>;
}

export function AdminConsole() {
  const [section, setSection] = useState<Section>("overview");
  const [status, setStatus] = useState("Validating administrator session…");
  const [denied, setDenied] = useState(false);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [contests, setContests] = useState<Contest[]>([]);
  const [paths, setPaths] = useState<Path[]>([]);
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [audits, setAudits] = useState<Audit[]>([]);
  const [xp, setXp] = useState<Ledger[]>([]);
  const [ranks, setRanks] = useState<Ledger[]>([]);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [assessmentScope, setAssessmentScope] = useState<StudentScope>("SELECTED");
  const [assessmentStudents, setAssessmentStudents] = useState<number[]>([]);
  const [datasetScope, setDatasetScope] = useState<StudentScope>("ALL");
  const [datasetStudents, setDatasetStudents] = useState<number[]>([]);
  const [accessFilter, setAccessFilter] = useState<"ALL" | "SELECTED" | "ANY">("ANY");
  const [assessmentAnalytics, setAssessmentAnalytics] = useState<Record<string, unknown> | null>(null);
  const [practiceDatasets, setPracticeDatasets] = useState<PracticeDataset[]>([]);
  const [groups, setGroups] = useState<LearnerGroup[]>([]);
  const [contestReview, setContestReview] = useState<{ slug: string; registrations: unknown[]; standings: unknown[]; submissions: unknown[] } | null>(null);

  const load = useCallback(async () => {
    const results = await Promise.all([
      api<Overview>("overview"), api<Problem[]>("problems?limit=100"), api<Dataset[]>("datasets?limit=100"),
      api<User[]>("users?limit=100"), api<Contest[]>("contests"), api<Path[]>("paths"),
      api<Achievement[]>("achievements"), api<Audit[]>("audit-logs?limit=100"),
      api<Ledger[]>("xp-transactions?limit=100"), api<Ledger[]>("rank-history?limit=100"),
      advancedApi<Assessment[]>("assessments?limit=100"),
      advancedApi<PracticeDataset[]>("datasets"),
      advancedApi<LearnerGroup[]>("groups"),
    ]);
    setOverview(results[0]); setProblems(results[1]); setDatasets(results[2]); setUsers(results[3]);
    setContests(results[4]); setPaths(results[5]); setAchievements(results[6]); setAudits(results[7]);
    setXp(results[8]); setRanks(results[9]); setAssessments(results[10]); setPracticeDatasets(results[11]); setGroups(results[12]);
  }, []);

  useEffect(() => {
    void fetch("/api/auth/me").then(async (response) => {
      if (!response.ok) throw new Error("Sign in before opening administration.");
      const user = await response.json();
      if (user.role !== "admin") throw new Error("This area is restricted to administrators.");
      await load();
      setStatus("");
    }).catch((error) => { setDenied(true); setStatus(error instanceof Error ? error.message : "Access denied"); });
  }, [load]);

  async function act(path: string, body: unknown, message: string) {
    try {
      setStatus("Applying change…");
      await api(path, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      await load(); setStatus(message);
    } catch (error) { setStatus(error instanceof Error ? error.message : "Change failed"); }
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const file = form.get("file") as File;
    if (!file?.size) return;
    const content = await fileBase64(file);
    try {
      setStatus("Validating and uploading dataset…");
      await api("datasets", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
        name: form.get("name"), kind: form.get("kind"), filename: file.name,
        content_type: file.type || "application/octet-stream", content_base64: content,
      }) });
      await load(); formElement.reset(); setStatus("Dataset uploaded to private storage.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "Upload failed"); }
  }

  async function searchUsers(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = String(new FormData(event.currentTarget).get("q") ?? "");
    try { setUsers(await api<User[]>(`users?q=${encodeURIComponent(query)}&limit=100`)); }
    catch (error) { setStatus(error instanceof Error ? error.message : "Search failed"); }
  }

  async function reviewContest(slug: string) {
    try {
      setStatus("Loading contest operations…");
      const [registrations, standings, submissions] = await Promise.all([
        api<unknown[]>(`contests/${slug}/registrations`), api<unknown[]>(`contests/${slug}/standings`),
        api<unknown[]>(`contests/${slug}/submissions`),
      ]);
      setContestReview({ slug, registrations, standings, submissions }); setStatus("");
    } catch (error) { setStatus(error instanceof Error ? error.message : "Contest review failed"); }
  }

  async function recoverJudge() {
    try {
      setStatus("Recovering stale judge leases…");
      const result = await api<{ recovered: number; cancelled: number; failed_to_enqueue: number }>("judge/recover-stuck", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      await load();
      setStatus(`Recovered ${result.recovered}; cancelled ${result.cancelled}; enqueue failures ${result.failed_to_enqueue}.`);
    } catch (error) { setStatus(error instanceof Error ? error.message : "Recovery failed"); }
  }

  async function createAssessment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      setStatus("Validating assessment definition…");
      const definition = JSON.parse(String(new FormData(event.currentTarget).get("definition")));
      definition.access_scope = assessmentScope;
      definition.assigned_user_ids = assessmentStudents;
      if (definition.status === "PUBLISHED" && assessmentScope === "SELECTED" && assessmentStudents.length === 0 && !definition.assigned_group_ids?.length) throw new Error("Select at least one student before publishing.");
      await advancedApi("assessments", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(definition) });
      await load(); setStatus("Assessment created and audited.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "Assessment creation failed"); }
  }

  async function setAssessmentStatus(id: string, next: string) {
    try {
      setStatus("Updating assessment publication status…");
      await advancedApi(`assessments/${id}/status`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: next, reason: "Changed from admin control center" }) });
      await load(); setStatus("Assessment status updated.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "Assessment update failed"); }
  }

  async function reviewAssessment(id: string) {
    try { setAssessmentAnalytics(await advancedApi<Record<string, unknown>>(`assessments/${id}/analytics`)); }
    catch (error) { setStatus(error instanceof Error ? error.message : "Assessment analytics failed"); }
  }

  async function publishPracticeDataset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const formElement = event.currentTarget; const form = new FormData(formElement); const file = form.get("file") as File;
    try {
      setStatus("Validating and publishing practice dataset…");
      if (datasetScope === "SELECTED" && datasetStudents.length === 0) throw new Error("Select at least one student before publishing.");
      const response = await fetch("/api/advanced/datasets", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
        title: form.get("title"), description: form.get("description"), category: form.get("category"), difficulty: form.get("difficulty"),
        filename: file.name, content_type: file.type || "application/octet-stream", content_base64: await fileBase64(file), publish: true,
        access_scope: datasetScope, assigned_user_ids: datasetStudents,
      }) });
      const result = await response.json(); if (!response.ok) throw new Error(result.detail ?? "Publish failed");
      formElement.reset(); await load(); setStatus("Practice dataset published to the library.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "Dataset publishing failed"); }
  }

  async function createGroup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const formElement = event.currentTarget; const form = new FormData(formElement);
    try {
      const userIds = String(form.get("user_ids") ?? "").split(",").map((value) => value.trim()).filter(Boolean).map(Number);
      if (userIds.some((value) => !Number.isInteger(value) || value < 1)) throw new Error("Member IDs must be comma-separated positive integers");
      await advancedApi("groups", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: form.get("name"), user_ids: userIds }) });
      formElement.reset(); await load(); setStatus("Learner group created and audited.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "Group creation failed"); }
  }

  if (denied) return <section className="card state" role="alert"><h1>Administration unavailable</h1><p>{status}</p><Link className="button" href="/profile">Return to profile</Link></section>;
  if (!overview) return <section className="card state" role="status">{status}</section>;

  const trend = overview.submission_trend as Array<{ day: string; count: number }>;
  const maxTrend = Math.max(1, ...trend.map((item) => item.count));
  return <>
    <header className="page-header compact"><p className="eyebrow">Operations</p><h1>Admin control center</h1><p>Manage platform content and review authoritative activity. Every mutation is validated and audited by the API.</p></header>
    <div className="admin-tabs" role="tablist" aria-label="Administration sections">{sections.map(([key, label]) => <button key={key} role="tab" aria-selected={section === key} onClick={() => setSection(key)}>{label}</button>)}</div>
    {status && <p className="admin-notice" role="status">{status}</p>}

    {section === "overview" && <div className="admin-stack">
      <section className="admin-metrics">{[
        ["Users", overview.total_users], ["Active users", overview.active_users], ["Problems", overview.total_problems],
        ["Submissions", overview.total_submissions], ["Accepted", overview.accepted_submissions], ["Failed", overview.failed_submissions],
        ["Active contests", overview.active_contests], ["Judge queue", Number(overview.queued_submissions) + Number(overview.running_submissions)],
        ["Stuck tasks", overview.stuck_submissions], ["Cancelled", overview.cancelled_submissions],
      ].map(([label, value]) => <article className="card admin-metric" key={String(label)}><p>{String(label)}</p><strong>{Number(value)}</strong></article>)}</section>
      {Number(overview.stuck_submissions) > 0 && <button className="button" onClick={() => void recoverJudge()}>Recover stale judge tasks</button>}
      <section className="card admin-chart"><div className="section-heading"><div><h2>Platform activity</h2><p>Verified submission volume over the latest active days</p></div></div><div className="activity-bars">{trend.map((item) => <div key={item.day}><span style={{ height: `${Math.max(6, item.count / maxTrend * 100)}%` }} title={`${item.day}: ${item.count}`} /><small>{item.day.slice(5)}</small></div>)}</div></section>
      <section className="card admin-table"><h2>Recent registrations</h2><table><thead><tr><th>User</th><th>Display name</th><th>Registered</th></tr></thead><tbody>{(overview.recent_registrations as Array<{ username: string; display_name: string; created_at: string }>).map((item) => <tr key={item.username}><td>@{item.username}</td><td>{item.display_name}</td><td>{formatDate(item.created_at)}</td></tr>)}</tbody></table></section>
    </div>}

    {section === "problems" && <div className="admin-two"><JsonEditor title="Create or replace a problem" initial={initialProblem} endpoint="problems" onSaved={load} /><section className="card admin-table"><h2>Problem lifecycle</h2><label className="admin-access-filter">Audience <select value={accessFilter} onChange={(event) => setAccessFilter(event.target.value as "ALL" | "SELECTED" | "ANY")}><option value="ANY">Any</option><option value="ALL">All students</option><option value="SELECTED">Selected only</option></select></label><table><thead><tr><th>Problem</th><th>Format</th><th>Tests</th><th>Status</th><th>Actions</th></tr></thead><tbody>{problems.filter((item) => accessFilter === "ANY" || item.access_scope === accessFilter).map((item) => <tr key={item.slug}><td><strong>{item.title}</strong><small>{item.slug} · {item.difficulty}</small></td><td>{item.format}<small>{item.supported_languages.join(", ") || "Evaluator"}</small></td><td>{item.test_case_count}<small>{item.hidden_test_count} hidden</small></td><td><span className="pill">{item.status}</span><small>{item.access_scope === "ALL" ? "All students" : `${item.assigned_count} selected`}</small></td><td className="row-actions">{item.status === "PUBLISHED" && <Link href={`/problems/${item.slug}`}>Preview</Link>}<button onClick={() => void act(`problems/${item.slug}/status`, { status: item.status === "PUBLISHED" ? "UNPUBLISHED" : "PUBLISHED", reason: "Changed from admin control center" }, "Problem status updated.")}>{item.status === "PUBLISHED" ? "Unpublish" : "Publish"}</button><button onClick={() => void act(`problems/${item.slug}/status`, { status: "ARCHIVED", reason: "Archived from admin control center" }, "Problem archived.")}>Archive</button><StudentAccessManager kind="problem" identifier={item.slug} onSaved={load}/></td></tr>)}</tbody></table></section></div>}

    {section === "assessments" && <div className="admin-two"><form className="card admin-editor" onSubmit={createAssessment}><h3>Create from question bank or template</h3><StudentAccessPicker scope={assessmentScope} onScopeChange={setAssessmentScope} selectedIds={assessmentStudents} onSelectedIdsChange={setAssessmentStudents}/><label>Validated assessment definition<textarea name="definition" defaultValue={initialAssessment} required spellCheck={false} /></label><button className="button">Create assessment</button><p>Use learner user IDs in assigned_user_ids. SELECTED assessments require at least one student or group; ALL can publish without assignments.</p></form><section className="card admin-table"><h2>Assessments and results</h2><table><thead><tr><th>Assessment</th><th>Window</th><th>Participation</th><th>Actions</th></tr></thead><tbody>{assessments.map((item) => <tr key={item.id}><td><strong>{item.title}</strong><small>{item.assessment_type} · {item.duration_minutes} minutes · {item.status}</small></td><td>{formatDate(item.opens_at)}<small>Closes {formatDate(item.closes_at)}</small></td><td>{item.access_scope === "ALL" ? "All eligible students" : `${item.assigned_count} assigned`}<small>{item.attempt_count} attempts · {item.questions.length} questions</small></td><td className="row-actions"><button onClick={() => void reviewAssessment(item.id)}>Results</button><a href={`/api/advanced/admin/assessments/${item.id}/export?format=csv`}>CSV</a><a href={`/api/advanced/admin/assessments/${item.id}/export?format=xlsx`}>XLSX</a><button onClick={() => void setAssessmentStatus(item.id, item.status === "PUBLISHED" ? "UNPUBLISHED" : "PUBLISHED")}>{item.status === "PUBLISHED" ? "Unpublish" : "Publish"}</button><StudentAccessManager kind="assessment" identifier={item.id} onSaved={load}/></td></tr>)}</tbody></table>{assessmentAnalytics && <div className="admin-review"><h3>Assessment analytics</h3><pre>{JSON.stringify(assessmentAnalytics, null, 2)}</pre></div>}</section></div>}
    {section === "assessments" && <div className="admin-two"><form className="card admin-editor" onSubmit={createGroup}><h3>Create learner group</h3><label>Group name<input name="name" required /></label><label>Member user IDs<input name="user_ids" placeholder="2, 5, 8" /></label><button className="button">Create group</button></form><section className="card admin-table"><h2>Assignment groups</h2><table><thead><tr><th>Group</th><th>Members</th><th>Identifier</th></tr></thead><tbody>{groups.map((group) => <tr key={group.id}><td><strong>{group.name}</strong><small>{formatDate(group.created_at)}</small></td><td>{group.user_ids.length}<small>{group.user_ids.join(", ") || "No members"}</small></td><td><code>{group.id}</code></td></tr>)}</tbody></table></section></div>}

    {section === "datasets" && <div className="admin-two"><form className="card admin-editor" onSubmit={upload}><h3>Upload private evaluation data</h3><label>Dataset name<input name="name" required /></label><label>Evaluator<select name="kind"><option>SQL</option><option>PANDAS</option><option>NUMPY</option><option>STATISTICS</option><option>PYSPARK</option><option>MACHINE_LEARNING</option></select></label><label>CSV, JSON, or Parquet<input name="file" type="file" accept=".csv,.json,.parquet" required /></label><button className="button">Validate and upload</button></form><section className="card admin-table"><h2>Versioned datasets</h2><table><thead><tr><th>Dataset</th><th>Size</th><th>Integrity</th><th>Action</th></tr></thead><tbody>{datasets.map((item) => <tr key={item.id}><td><strong>{item.name} v{item.version}</strong><small>{item.kind} · {item.original_filename}</small></td><td>{Math.ceil(item.size_bytes / 1024)} KB</td><td><code>{item.sha256.slice(0, 12)}…</code><small>{item.is_active ? "Active" : "Disabled"}</small></td><td className="row-actions"><a href={`/api/admin/datasets/${item.id}/download`}>Download</a><button onClick={() => void act(`datasets/${item.id}`, { is_active: !item.is_active, reason: "Changed from admin control center" }, "Dataset status updated.")}>{item.is_active ? "Disable" : "Activate"}</button></td></tr>)}</tbody></table></section></div>}
    {section === "datasets" && <div className="admin-two"><form className="card admin-editor" onSubmit={publishPracticeDataset}><h3>Publish to Dataset Library</h3><StudentAccessPicker scope={datasetScope} onScopeChange={setDatasetScope} selectedIds={datasetStudents} onSelectedIdsChange={setDatasetStudents}/><label>Title<input name="title" required /></label><label>Description<textarea name="description" required /></label><label>Category<select name="category">{["Retail", "Banking", "E-commerce", "Healthcare", "Sales", "HR Analytics", "Finance", "Logistics"].map((item) => <option key={item}>{item}</option>)}</select></label><label>Difficulty<select name="difficulty"><option>Beginner</option><option>Easy</option><option>Medium</option><option>Hard</option></select></label><label>CSV, XLSX, JSON, or Parquet<input name="file" type="file" accept=".csv,.xlsx,.json,.parquet" required /></label><button className="button">Validate and publish</button></form><section className="card admin-table"><h2>Published practice library</h2><table><thead><tr><th>Dataset</th><th>Profile</th><th>Status</th></tr></thead><tbody>{practiceDatasets.map((item) => <tr key={item.id}><td><strong>{item.title} v{item.version}</strong><small>{item.category} · {item.difficulty}</small></td><td>{item.profile.rows ?? 0} rows<small>{item.format} · {Math.ceil(item.size_bytes / 1024)} KB</small></td><td><span className="pill">{item.status}</span><small>{item.access_scope === "ALL" ? "All students" : `${item.assigned_count} selected`}</small><StudentAccessManager kind="path" identifier={item.slug} onSaved={load}/></td></tr>)}</tbody></table></section></div>}

    {section === "users" && <section className="card admin-table"><div className="section-heading"><h2>User and suspicious-activity review</h2><form className="admin-search" onSubmit={searchUsers}><input name="q" aria-label="Search users" placeholder="Username, email, or display name" /><button className="button">Search</button></form></div><table><thead><tr><th>User</th><th>Activity</th><th>Account</th><th>Action</th></tr></thead><tbody>{users.map((item) => <tr key={item.id}><td><strong>{item.display_name}</strong><small>@{item.username} · {item.email}</small></td><td>{item.accepted_submissions}/{item.submissions} accepted<small>{item.system_errors} system errors · last login {formatDate(item.last_login_at)}</small></td><td><span className="pill">{item.role} · {item.is_active ? "active" : "suspended"}</span></td><td><button onClick={() => void act(`users/${item.id}/status`, { is_active: !item.is_active, reason: "Account review from admin control center" }, "Account status updated.")}>{item.is_active ? "Suspend" : "Reactivate"}</button></td></tr>)}</tbody></table></section>}

    {section === "contests" && <div className="admin-two"><JsonEditor title="Create or edit a contest" initial={initialContest} endpoint="contests" onSaved={load} /><section className="card admin-table"><h2>Contest operations</h2><label className="admin-access-filter">Audience <select value={accessFilter} onChange={(event) => setAccessFilter(event.target.value as "ALL" | "SELECTED" | "ANY")}><option value="ANY">Any</option><option value="ALL">All students</option><option value="SELECTED">Selected only</option></select></label><table><thead><tr><th>Contest</th><th>Schedule</th><th>Participation</th><th>Actions</th></tr></thead><tbody>{contests.filter((item) => accessFilter === "ANY" || item.access_scope === accessFilter).map((item) => <tr key={item.slug}><td><strong>{item.title}</strong><small>{item.slug} · {item.publication_status} · {item.access_scope === "ALL" ? "All students" : `${item.assigned_count} selected`}</small></td><td>{formatDate(item.starts_at)}<small>Ends {formatDate(item.ends_at)}</small></td><td>{item.registrations} registered<small>{item.submissions} submissions · {item.problem_count} problems</small></td><td className="row-actions"><button onClick={() => void reviewContest(item.slug)}>Review</button>{item.publication_status !== "FINALIZED" && <button onClick={() => void act(`contests/${item.slug}/status`, { status: item.publication_status === "PUBLISHED" ? "CANCELLED" : "PUBLISHED", reason: "Changed from admin control center" }, "Contest status updated.")}>{item.publication_status === "PUBLISHED" ? "Cancel" : "Publish"}</button>}<StudentAccessManager kind="contest" identifier={item.slug} onSaved={load}/></td></tr>)}</tbody></table>{contestReview && <div className="admin-review"><h3>{contestReview.slug} review</h3><details open><summary>Registrations ({contestReview.registrations.length})</summary><pre>{JSON.stringify(contestReview.registrations, null, 2)}</pre></details><details><summary>Standings ({contestReview.standings.length})</summary><pre>{JSON.stringify(contestReview.standings, null, 2)}</pre></details><details><summary>Submissions ({contestReview.submissions.length})</summary><pre>{JSON.stringify(contestReview.submissions, null, 2)}</pre></details></div>}</section></div>}

    {section === "paths" && <div className="admin-two"><JsonEditor title="Create or edit a learning path" initial={initialPath} endpoint="paths" onSaved={load} /><section className="card admin-table"><h2>Published learning plans</h2><label className="admin-access-filter">Audience <select value={accessFilter} onChange={(event) => setAccessFilter(event.target.value as "ALL" | "SELECTED" | "ANY")}><option value="ANY">Any</option><option value="ALL">All students</option><option value="SELECTED">Selected only</option></select></label><table><thead><tr><th>Path</th><th>Structure</th><th>Status</th></tr></thead><tbody>{paths.filter((item) => accessFilter === "ANY" || item.access_scope === accessFilter).map((item) => <tr key={item.slug}><td><strong>{item.title}</strong><small>{item.slug}</small></td><td>{item.problem_count} problems<small>{item.prerequisites.length} prerequisites · {item.enrollments} enrollments</small></td><td><span className="pill">{item.status}</span><small>{item.access_scope === "ALL" ? "All students" : "Selected only"}</small><StudentAccessManager kind="dataset" identifier={item.id} onSaved={load}/></td></tr>)}</tbody></table></section></div>}

    {section === "achievements" && <div className="admin-two"><JsonEditor title="Create or edit an achievement" initial={initialAchievement} endpoint="achievements" onSaved={load} /><div className="admin-stack"><section className="card admin-table"><h2>Badge definitions</h2><table><tbody>{achievements.map((item) => <tr key={item.slug}><td><strong>{item.name}</strong><small>{item.slug} · {JSON.stringify(item.criteria)}</small></td><td>{item.xp_reward} XP<small>{item.awarded_count} awards</small></td></tr>)}</tbody></table></section><section className="card admin-table"><h2>Read-only XP ledger</h2><table><tbody>{xp.slice(0, 20).map((item) => <tr key={item.id}><td>@{item.username}<small>{item.reason}</small></td><td>{item.amount} XP</td></tr>)}</tbody></table></section><section className="card admin-table"><h2>Ranking progression</h2><table><tbody>{ranks.slice(0, 20).map((item) => <tr key={item.id}><td>@{item.username}</td><td>{item.rank_slug}<small>{formatDate(item.reached_at)}</small></td></tr>)}</tbody></table></section></div></div>}

    {section === "audit" && <section className="card admin-table"><h2>Administrative action history</h2><table><thead><tr><th>When</th><th>Actor</th><th>Action</th><th>Target</th><th>Context</th></tr></thead><tbody>{audits.map((item) => <tr key={item.id}><td>{formatDate(item.created_at)}</td><td>{item.actor_username ?? "system"}<small>{item.ip_address ?? "IP unavailable"}</small></td><td>{item.action}</td><td>{item.target_type}<small>{item.target_id}</small></td><td><code>{JSON.stringify(item.details)}</code></td></tr>)}</tbody></table></section>}
  </>;
}
