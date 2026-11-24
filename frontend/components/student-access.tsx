"use client";

import { useEffect, useId, useState } from "react";

export type StudentScope = "ALL" | "SELECTED";
type Learner = { id: number; username: string; display_name: string };
type AccessInfo = { access_scope: StudentScope; assigned_user_ids: number[]; assigned_count: number; published: boolean };
type Preview = { current_scope: StudentScope; next_scope: StudentScope; currently_assigned: number; next_assigned: number; scope_change: boolean; may_remove_access: boolean; preserves_submissions: boolean };

export function StudentAccessPicker({
  scope, onScopeChange, selectedIds, onSelectedIdsChange,
}: {
  scope: StudentScope;
  onScopeChange: (value: StudentScope) => void;
  selectedIds: number[];
  onSelectedIdsChange: (values: number[]) => void;
}) {
  const controlId = useId();
  const [query, setQuery] = useState("");
  const [learners, setLearners] = useState<Learner[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    if (scope !== "SELECTED") return;
    const controller = new AbortController();
    void fetch(`/api/admin/students?q=${encodeURIComponent(query)}&limit=100`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Could not load eligible students");
        setLearners(await response.json() as Learner[]);
        setError("");
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Student lookup failed");
      });
    return () => controller.abort();
  }, [query, scope]);

  function toggle(id: number) {
    onSelectedIdsChange(selectedIds.includes(id) ? selectedIds.filter((value) => value !== id) : [...selectedIds, id]);
  }

  return <fieldset className="student-access" aria-label="Student access">
    <legend>Who can access this content?</legend>
    <label className="student-access-choice">
      <input type="radio" name={`access-scope-${controlId}`} checked={scope === "ALL"} onChange={() => onScopeChange("ALL")} />
      <span><strong>All Students</strong><small>All eligible learners, including future registrations. No manual assignment needed.</small></span>
    </label>
    <label className="student-access-choice">
      <input type="radio" name={`access-scope-${controlId}`} checked={scope === "SELECTED"} onChange={() => onScopeChange("SELECTED")} />
      <span><strong>Selected Students Only</strong><small>Only explicitly assigned eligible learners can access published content.</small></span>
    </label>
    {scope === "SELECTED" && <div className="student-access-selection">
      <label htmlFor={controlId}>Search registered learners</label>
      <input id={controlId} type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search username or email" />
      <p aria-live="polite">{selectedIds.length} selected {selectedIds.length === 1 ? "student" : "students"}</p>
      {error && <p role="alert" className="form-error">{error}</p>}
      <div className="student-access-results">
        {learners.map((learner) => <label key={learner.id} className="student-access-student">
          <input type="checkbox" checked={selectedIds.includes(learner.id)} onChange={() => toggle(learner.id)} />
          <span>{learner.display_name}<small>@{learner.username} · ID {learner.id}</small></span>
        </label>)}
        {learners.length === 0 && !error && <p>No eligible learners found.</p>}
      </div>
      {selectedIds.length > 0 && <div className="student-access-selected">
        {selectedIds.map((id) => <button type="button" key={id} onClick={() => toggle(id)} aria-label={`Remove student ${id}`}>Student #{id} ×</button>)}
      </div>}
      {selectedIds.length === 0 && <p className="form-error">Select at least one student before publishing.</p>}
    </div>}
    {scope === "ALL" && <p className="student-access-note">All eligible students will have access once this content is published.</p>}
  </fieldset>;
}

export function StudentAccessManager({
  kind, identifier, onSaved,
}: {
  kind: "problem" | "contest" | "path" | "assessment" | "dataset";
  identifier: string;
  onSaved?: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [original, setOriginal] = useState<AccessInfo | null>(null);
  const [scope, setScope] = useState<StudentScope>("ALL");
  const [students, setStudents] = useState<number[]>([]);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [message, setMessage] = useState("");

  async function openManager() {
    if (open) { setOpen(false); return; }
    setOpen(true); setMessage("Loading access settings…");
    try {
      const response = await fetch(`/api/admin/access/${kind}/${encodeURIComponent(identifier)}`);
      if (!response.ok) throw new Error("Could not load content access");
      const settings = await response.json() as AccessInfo;
      setOriginal(settings); setScope(settings.access_scope);
      setStudents(settings.assigned_user_ids); setPreview(null); setConfirmed(false); setMessage("");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Access settings unavailable"); }
  }
  function modifyScope(value: StudentScope) { setScope(value); setPreview(null); setConfirmed(false); }
  function modifyStudents(values: number[]) { setStudents(values); setPreview(null); setConfirmed(false); }
  async function previewChange() {
    setMessage("Checking impact…");
    try {
      const response = await fetch(`/api/admin/access/${kind}/${encodeURIComponent(identifier)}/preview`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ access_scope: scope, assigned_user_ids: students }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Preview failed");
      setPreview(result as Preview); setConfirmed(false); setMessage("");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Preview failed"); }
  }
  async function save() {
    if (!original || !preview) return;
    if (original.published && scope === "SELECTED" && students.length === 0 && original.assigned_count === 0) {
      setMessage("Select at least one learner before saving this scope."); return;
    }
    if (original.published && !confirmed && (preview.scope_change || preview.may_remove_access ||
        students.join(",") !== original.assigned_user_ids.join(","))) {
      setMessage("Confirm the access change before applying it."); return;
    }
    setMessage("Saving audience…");
    try {
      const response = await fetch(`/api/admin/access/${kind}/${encodeURIComponent(identifier)}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ access_scope: scope, assigned_user_ids: students,
          confirm_impact: confirmed, reason: "Changed through Student Access manager" }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Access update failed");
      setOriginal(result as AccessInfo); setPreview(null); setConfirmed(false);
      setMessage("Access updated. Existing student progress is preserved.");
      if (onSaved) await onSaved();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Update failed"); }
  }

  return <div className="access-manager">
    <button type="button" className="access-manager-toggle" onClick={() => void openManager()} aria-expanded={open}>{open ? "Close access" : "Manage access"}</button>
    {open && <div className="access-manager-panel">
      {original && <>
        <StudentAccessPicker scope={scope} onScopeChange={modifyScope} selectedIds={students} onSelectedIdsChange={modifyStudents}/>
        <button type="button" className="button secondary" onClick={() => void previewChange()}>Preview visibility change</button>
        {preview && <div className="access-impact" role="status">
          <strong>{preview.current_scope} → {preview.next_scope}</strong>
          <p>Assigned student records: {preview.currently_assigned} → {preview.next_assigned}. {preview.may_remove_access ? "Some students may lose future access." : "Review the new audience before applying."} Existing submissions and results are retained.</p>
          {original.published && <label><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)}/> I understand the impact on published content.</label>}
          <button type="button" className="button" onClick={() => void save()}>Apply access change</button>
        </div>}
      </>}
      {message && <p role="status">{message}</p>}
    </div>}
  </div>;
}
