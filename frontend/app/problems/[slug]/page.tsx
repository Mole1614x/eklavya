import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ChevronLeft, ChevronRight } from "lucide-react";
import { getProblem, getProblemNavigation, type ProblemNavigation } from "@/lib/api";
import { formats } from "@/components/catalog";
import { Workspace } from "@/components/workspace";
import { modules } from "@/lib/navigation";

type Query = Record<string, string | string[] | undefined>;
const categories = new Set(["foundations", "code", "data", "statistics", "big-data", "ai", "excel", "tableau", "linux", "multi-tool"]);
const difficulties = new Set(["Beginner", "Easy", "Medium", "Hard"]);

function navigationButtons({ navigation, context, placement }: {
  navigation: ProblemNavigation | null;
  context: string;
  placement: "top" | "bottom";
}) {
  const href = (slug: string, direction: -1 | 1) => {
    const params = new URLSearchParams(context);
    // Crossing the 50-question page boundary also updates "Back to catalog".
    const page = Math.ceil(((navigation?.position ?? 1) + direction) / 50);
    if (page > 1) params.set("page", String(page));
    else params.delete("page");
    const search = params.toString();
    return `/problems/${encodeURIComponent(slug)}${search ? `?${search}` : ""}`;
  };
  return (
    <nav className="problem-navigation" aria-label={placement === "top" ? "Question navigation" : "Question navigation at bottom"}>
      <span className="problem-navigation-position" aria-live="polite">
        {navigation ? `Question ${navigation.position.toLocaleString()} of ${navigation.total.toLocaleString()}` : "Navigation unavailable"}
      </span>
      {navigation?.previous
        ? <Link className="problem-navigation-button" href={href(navigation.previous, -1)} rel="prev"><ChevronLeft size={17}/> Previous</Link>
        : <button type="button" className="problem-navigation-button" disabled><ChevronLeft size={17}/> Previous</button>}
      {navigation?.next
        ? <Link className="problem-navigation-button problem-navigation-next" href={href(navigation.next, 1)} rel="next">Next <ChevronRight size={17}/></Link>
        : <button type="button" className="problem-navigation-button problem-navigation-next" disabled>Next <ChevronRight size={17}/></button>}
    </nav>
  );
}

export default async function ProblemPage({
  params, searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Query>;
}) {
  const { slug } = await params;
  const query = await searchParams;
  const contest = typeof query.contest === "string" && query.contest ? query.contest : undefined;

  // Preserve only validated catalog filters rather than forwarding arbitrary URL input.
  const filters: Record<string, string> = {};
  if (typeof query.category === "string" && categories.has(query.category)) filters.category = query.category;
  if (typeof query.difficulty === "string" && difficulties.has(query.difficulty)) filters.difficulty = query.difficulty;
  if (typeof query.topic === "string" && query.topic.length <= 80) filters.topic = query.topic;
  if (typeof query.q === "string" && query.q.length <= 100) filters.q = query.q;
  if (typeof query.subject === "string" && /^[a-z0-9-]{1,100}$/.test(query.subject)) filters.subject = query.subject;
  const page = Number(typeof query.page === "string" ? query.page : 1);
  const listingPage = Number.isSafeInteger(page) && page > 1 && page <= 1000000 ? page : 1;
  const section = typeof query.section === "string" && modules.some(item => item.slug === query.section)
    && filters.category === query.section ? query.section : null;
  const [problem, navigation] = await Promise.all([
    getProblem(slug),
    contest ? Promise.resolve(null) : getProblemNavigation(slug, filters).catch(() => null),
  ]);
  if (!problem) notFound();

  const currentPage = navigation ? Math.ceil(navigation.position / 50) : listingPage;
  const contextQuery = new URLSearchParams({
    ...filters,
    ...(section ? { section } : {}),
    ...(currentPage > 1 ? { page: String(currentPage) } : {}),
  });
  const catalogQuery = new URLSearchParams(filters);
  if (section) catalogQuery.delete("category");
  if (currentPage > 1) catalogQuery.set("page", String(currentPage));
  const backPath = section ? `/${section}` : "/problems";
  const backHref = contest
    ? `/arena/${encodeURIComponent(contest)}`
    : `${backPath}${catalogQuery.size ? `?${catalogQuery}` : ""}`;

  return (
    <>
      <div className="problem-navigation-bar">
        <Link className="back-link" href={backHref}>
          <ArrowLeft size={16}/> {contest ? "Back to contest" : "Problem Catalog"}
        </Link>
        {!contest && navigationButtons({ navigation, context: contextQuery.toString(), placement: "top" })}
      </div>
      <header className="page-header compact">
        <p className="eyebrow"><span className="signal"/> PRACTICE / CHALLENGE</p>
        <h1>{problem.title}</h1>
        <div className="problem-tags">
          {!contest && navigation && <span className="pill problem-number-pill">#{String(navigation.position).padStart(3, "0")}</span>}
          <span className={`difficulty ${problem.difficulty.toLowerCase()}`}>{problem.difficulty}</span>
          <span className="pill">{problem.topic}</span>
          <span className="pill">{formats[problem.format]}</span>
        </div>
      </header>
      <div className="problem-layout">
        <article className="card statement">
          <h2>Description</h2><p>{problem.description}</p>
          <h2>Constraints</h2><ul>{problem.constraints.map(constraint => <li key={constraint}>{constraint}</li>)}</ul>
          {problem.examples.map(({ input, output }, index) =>
            <div className="example" key={index}>
              <h2>Example {index + 1}</h2>
              <small>Input</small><pre>{input}</pre>
              <small>Expected output</small><pre>{output}</pre>
            </div>)}
        </article>
        <Workspace key={`${problem.slug}-${contest ?? "practice"}`} problem={problem} contestSlug={contest}/>
      </div>
      {!contest && <div className="problem-navigation-footer">
        {navigationButtons({ navigation, context: contextQuery.toString(), placement: "bottom" })}
      </div>}
    </>
  );
}
