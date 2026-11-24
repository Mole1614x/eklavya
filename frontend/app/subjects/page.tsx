import Link from "next/link";
import { ArrowUpRight, BookOpen, ShieldCheck } from "lucide-react";
import { getSubjects } from "@/lib/api";

export const metadata = { title: "45 Subject Learning Catalogue" };

export default async function SubjectsPage() {
  const catalogue = await getSubjects();
  const active = catalogue.subjects.filter((s) => s.published_questions > 0).length;
  return <main className="subject-catalogue">
    <header className="page-header">
      <p className="section-kicker">EKLAVYA / PRACTICE TRACKS</p>
      <h1>Explore all 45 subjects</h1>
      <p>Discover working practice challenges while the larger subject question banks are developed and verified.</p>
    </header>
    <div className="subject-metrics" role="group" aria-label="Question bank coverage">
      <div className="card"><strong>{catalogue.subjects.length}</strong><span>Requested subjects</span></div>
      <div className="card"><strong>{active}</strong><span>Subjects with published checks</span></div>
      <div className="card"><strong>{catalogue.published_catalog_total}</strong><span>Available problems in total</span></div>
      <div className="card"><strong>{catalogue.target_total}</strong><span>Subject target (not completed)</span></div>
    </div>
    <p className="subject-catalogue-note"><ShieldCheck size={17}/>
      {catalogue.classification_note}
    </p>
    <div className="subject-card-grid">
      {catalogue.subjects.map((subject) => <article className="card subject-card" key={subject.slug}>
        <div className="subject-card-top"><BookOpen size={18} aria-hidden="true" />
          <span>SUBJECT {String(subject.id).padStart(2, "0")}</span>
        </div>
        <h2>{subject.name}</h2>
        <p>{subject.execution_status} · {subject.category}</p>
        <div className="subject-progress" role="meter" aria-label={`${subject.name} coverage`}
          aria-valuemin={0} aria-valuemax={subject.target} aria-valuenow={subject.published_questions}>
          <div style={{ width: `${Math.min(100, subject.published_questions / subject.target * 100)}%` }} />
        </div>
        <div className="subject-card-counts"><strong>{subject.published_questions} published in this track</strong>
          <span>Target {subject.target}</span></div>
        {subject.published_questions > 0
          ? <Link href={`/problems?topic=${encodeURIComponent(subject.name)}`}>
            Explore questions <ArrowUpRight size={16} />
          </Link>
          : <span className="subject-unavailable">No evaluated questions in this track yet</span>}
      </article>)}
    </div>
  </main>;
}
