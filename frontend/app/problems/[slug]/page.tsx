import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { getProblem } from "@/lib/api";
import { formats } from "@/components/catalog";
import { Workspace } from "@/components/workspace";

export default async function ProblemPage({ params, searchParams }: { params: Promise<{ slug: string }>; searchParams: Promise<{ contest?: string }> }) {
  const { slug } = await params;
  const { contest } = await searchParams;
  const problem = await getProblem(slug);
  if (!problem) notFound();
  return (
    <>
      <Link className="back-link" href={contest ? `/arena/${encodeURIComponent(contest)}` : "/problems"}><ArrowLeft size={16} /> {contest ? "Back to contest" : "Problem Catalog"}</Link>
      <header className="page-header compact"><p className="eyebrow"><span className="signal"/> PRACTICE / CHALLENGE</p><h1>{problem.title}</h1><div className="problem-tags"><span className={`difficulty ${problem.difficulty.toLowerCase()}`}>{problem.difficulty}</span><span className="pill">{problem.topic}</span><span className="pill">{formats[problem.format]}</span></div></header>
      <div className="problem-layout">
        <article className="card statement">
          <h2>Description</h2><p>{problem.description}</p>
          <h2>Constraints</h2><ul>{problem.constraints.map((constraint) => <li key={constraint}>{constraint}</li>)}</ul>
          {problem.examples.map(({ input, output }, index) => <div className="example" key={index}><h2>Example {index + 1}</h2><small>Input</small><pre>{input}</pre><small>Expected output</small><pre>{output}</pre></div>)}
        </article>
        <Workspace key={`${problem.slug}-${contest ?? "practice"}`} problem={problem} contestSlug={contest} />
      </div>
    </>
  );
}
