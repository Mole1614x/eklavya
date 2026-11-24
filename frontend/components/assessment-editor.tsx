"use client";

import { FormEvent, useState } from "react";
import { StudentAccessPicker, type StudentScope } from "./student-access";

export type AssessmentDraft = {
  title: string;
  description: string;
  instructions: string;
  assessment_type: string;
  duration_minutes: number;
  opens_at: string;
  closes_at: string;
  max_attempts: number;
  penalty_percent: number;
  release_results: boolean;
  status: "DRAFT" | "PUBLISHED";
  access_scope: StudentScope;
  template_key: null;
  questions: Array<{ problem_slug: string; points: number }>;
  assigned_user_ids: number[];
  assigned_group_ids: string[];
};

type ProblemOption = { slug: string; title: string; status: string };
type GroupOption = { id: string; name: string; user_ids: number[] };
type Schedule = { opens_at: string; closes_at: string; duration_minutes: number };
type Status = "UPCOMING" | "AVAILABLE" | "CLOSED" | "DRAFT";

export function localDateTime(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function windowStatus(item: { status: string; opens_at: string; closes_at: string }, nowMs = Date.now()): Status {
  if (item.status !== "PUBLISHED") return "DRAFT";
  if (nowMs < new Date(item.opens_at).getTime()) return "UPCOMING";
  if (nowMs >= new Date(item.closes_at).getTime()) return "CLOSED";
  return "AVAILABLE";
}

export function AssessmentCreationForm({
  problems, groups, onCreate,
}: {
  problems: ProblemOption[];
  groups: GroupOption[];
  onCreate: (definition: AssessmentDraft) => Promise<void>;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState("CODING");
  const [duration, setDuration] = useState(60);
  const [scheduleMode, setScheduleMode] = useState<"NOW" | "LATER">("NOW");
  const [openLocal, setOpenLocal] = useState(() => localDateTime(new Date(Date.now() + 60 * 60_000)));
  const [closeLocal, setCloseLocal] = useState(() => localDateTime(new Date(Date.now() + 24 * 60 * 60_000)));
  const [scope, setScope] = useState<StudentScope>("ALL");
  const [students, setStudents] = useState<number[]>([]);
  const [groupIds, setGroupIds] = useState<string[]>([]);
  const [questionSlug, setQuestionSlug] = useState("");
  const [questions, setQuestions] = useState<string[]>([]);
  const [publish, setPublish] = useState(false);
  const [maxAttempts, setMaxAttempts] = useState(1);
  const [releaseResults, setReleaseResults] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const availableProblems = problems.filter((problem) => problem.status === "PUBLISHED");
  function addQuestion() {
    const slug = questionSlug.trim();
    if (!slug || questions.includes(slug)) return;
    setQuestions((current) => [...current, slug]);
    setQuestionSlug("");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    if (questions.length === 0) { setMessage("Choose at least one question from the question bank."); return; }
    if (publish && scope === "SELECTED" && !students.length && !groupIds.length) {
      setMessage("Select a student or an assignment group before publishing."); return;
    }
    const opens = scheduleMode === "NOW" ? new Date(Date.now() - 60_000) : new Date(openLocal);
    const closes = new Date(closeLocal);
    if (!Number.isFinite(opens.getTime()) || !Number.isFinite(closes.getTime()) || closes <= opens) {
      setMessage("Closing time must be after the opening time."); return;
    }
    setBusy(true);
    try {
      await onCreate({
        title: title.trim(), description: description.trim(),
        instructions: "Complete each question before your server-authoritative timer expires.",
        assessment_type: type, duration_minutes: duration, opens_at: opens.toISOString(),
        closes_at: closes.toISOString(), max_attempts: maxAttempts, penalty_percent: 0,
        release_results: releaseResults, status: publish ? "PUBLISHED" : "DRAFT",
        access_scope: scope, template_key: null,
        questions: questions.map((problem_slug) => ({ problem_slug, points: 100 })),
        assigned_user_ids: scope === "ALL" ? [] : students,
        assigned_group_ids: scope === "ALL" ? [] : groupIds,
      });
      setMessage(publish ? "Assessment published successfully." : "Assessment draft created successfully.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not create assessment");
    } finally {
      setBusy(false);
    }
  }

  return <form className="card admin-editor assessment-create-form" onSubmit={(event) => void submit(event)}>
    <div className="admin-editor-heading"><div>
      <span className="section-kicker">ASSESSMENT STUDIO</span>
      <h3>Create assessment</h3>
      <p>Choose questions, audience, and timing. No JSON editing required.</p>
    </div></div>

    <label>Assessment title<input required minLength={3} maxLength={160} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Python Fundamentals — Practice Test" /></label>
    <label>Description<textarea className="assessment-short-text" maxLength={1000} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="What should learners practice?" /></label>
    <div className="assessment-form-grid">
      <label>Assessment type<select value={type} onChange={(event) => setType(event.target.value)}>
        {["CODING","DSA","SQL","PANDAS","STATISTICS","DATA_ENGINEERING","EXCEL","TABLEAU","LINUX","MIXED"].map((item) => <option key={item}>{item}</option>)}
      </select></label>
      <label>Duration (minutes)<input type="number" min={1} max={480} required value={duration} onChange={(event) => setDuration(Number(event.target.value))}/></label>
    </div>

    <fieldset className="assessment-fieldset">
      <legend>Questions from the bank</legend>
      <div className="assessment-question-picker">
        <label>Choose a question<select aria-label="Question bank problem" value={questionSlug} onChange={(event) => setQuestionSlug(event.target.value)}>
          <option value="">Select a question</option>
          {availableProblems.map((problem) => <option key={problem.slug} value={problem.slug}>{problem.title} ({problem.slug})</option>)}
        </select></label>
        <button type="button" className="button secondary" disabled={!questionSlug} onClick={addQuestion}>Add question</button>
      </div>
      <label>Or enter a known problem slug<input aria-label="Manual problem slug" value={questionSlug} onChange={(event) => setQuestionSlug(event.target.value)} placeholder="e.g. parity-check"/></label>
      {questions.map((slug, index) => <div className="assessment-question-row" key={slug}>
        <span>{index + 1}. {availableProblems.find((problem) => problem.slug === slug)?.title ?? slug}</span>
        <button type="button" onClick={() => setQuestions((current) => current.filter((value) => value !== slug))} aria-label={`Remove question ${slug}`}>Remove</button>
      </div>)}
      <small>{questions.length} question{questions.length === 1 ? "" : "s"} selected · 100 points each</small>
    </fieldset>

    <fieldset className="assessment-fieldset">
      <legend>When should students be able to start?</legend>
      <label className="assessment-radio"><input type="radio" name="start-mode" checked={scheduleMode === "NOW"} onChange={() => setScheduleMode("NOW")}/> Available immediately after publication</label>
      <label className="assessment-radio"><input type="radio" name="start-mode" checked={scheduleMode === "LATER"} onChange={() => setScheduleMode("LATER")}/> Schedule for later</label>
      {scheduleMode === "LATER" && <label>Opens at (your local time)<input aria-label="Assessment opening date and time" type="datetime-local" required value={openLocal} onChange={(event) => setOpenLocal(event.target.value)}/></label>}
      <label>Closes at (your local time)<input aria-label="Assessment closing date and time" type="datetime-local" required value={closeLocal} onChange={(event) => setCloseLocal(event.target.value)}/></label>
      <small>The assessment becomes available only when it is published and within its open/close window. Attempts still obey time and attempt limits.</small>
    </fieldset>

    <StudentAccessPicker scope={scope} onScopeChange={setScope} selectedIds={students} onSelectedIdsChange={setStudents} />
    {scope === "SELECTED" && groups.length > 0 && <fieldset className="assessment-fieldset">
      <legend>Or assign learner groups</legend>
      {groups.map((group) => <label className="assessment-radio" key={group.id}>
        <input type="checkbox" checked={groupIds.includes(group.id)} onChange={(event) => setGroupIds((current) => event.target.checked ? [...current, group.id] : current.filter((value) => value !== group.id))}/>
        {group.name} ({group.user_ids.length} members)
      </label>)}
    </fieldset>}

    <details className="assessment-extra"><summary>Advanced settings</summary>
      <div className="assessment-form-grid">
        <label>Maximum attempts<input type="number" min={1} max={20} required value={maxAttempts} onChange={(event) => setMaxAttempts(Number(event.target.value))}/></label>
        <label className="assessment-radio"><input type="checkbox" checked={releaseResults} onChange={(event) => setReleaseResults(event.target.checked)}/> Release results</label>
      </div>
    </details>

    <label className="assessment-radio assessment-publish-option"><input type="checkbox" checked={publish} onChange={(event) => setPublish(event.target.checked)}/> Publish immediately after creating</label>
    {message && <p role="status" className="assessment-message">{message}</p>}
    <button className="button" type="submit" disabled={busy}>{busy ? "Saving assessment…" : publish ? "Create and publish assessment" : "Save assessment draft"}</button>
  </form>;
}

export function AssessmentScheduleEditor({
  assessment, onSaved,
}: {
  assessment: { id: string; opens_at: string; closes_at: string; duration_minutes: number; attempt_count: number };
  onSaved: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [start, setStart] = useState(() => localDateTime(new Date(assessment.opens_at)));
  const [end, setEnd] = useState(() => localDateTime(new Date(assessment.closes_at)));
  const [duration, setDuration] = useState(assessment.duration_minutes);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const a = new Date(start);
    const b = new Date(end);
    if (!Number.isFinite(a.getTime()) || !Number.isFinite(b.getTime()) || b <= a) {
      setMessage("Closing time must be after opening time."); return;
    }
    setBusy(true); setMessage("");
    try {
      const response = await fetch(`/api/advanced/admin/assessments/${assessment.id}/schedule`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ opens_at: a.toISOString(), closes_at: b.toISOString(),
          duration_minutes: duration, reason: "Schedule corrected in Admin Control Center" }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Could not update schedule.");
      await onSaved();
      setMessage("Schedule saved successfully."); setOpen(false);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Schedule update failed"); }
    finally { setBusy(false); }
  }

  return <div className="assessment-schedule-editor">
    <button type="button" onClick={() => setOpen((current) => !current)} disabled={assessment.attempt_count > 0} aria-expanded={open}>
      Edit schedule
    </button>
    {assessment.attempt_count > 0 && <small>Locked after the first attempt</small>}
    {open && <form onSubmit={(event) => void save(event)} className="assessment-schedule-fields">
      <label>Opens at (local)<input type="datetime-local" aria-label="Edit opening time" value={start} onChange={(event) => setStart(event.target.value)} required/></label>
      <label>Closes at (local)<input type="datetime-local" aria-label="Edit closing time" value={end} onChange={(event) => setEnd(event.target.value)} required/></label>
      <label>Duration in minutes<input type="number" min={1} max={480} value={duration} onChange={(event) => setDuration(Number(event.target.value))} required/></label>
      <button className="button" type="submit" disabled={busy}>{busy ? "Saving…" : "Save schedule"}</button>
    </form>}
    {message && <p role="status">{message}</p>}
  </div>;
}
