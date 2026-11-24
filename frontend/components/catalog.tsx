import Link from "next/link";
import { ArrowRight, Check, Search } from "lucide-react";
import { getCatalog } from "@/lib/api";
import { modules } from "@/lib/navigation";

export type Query = Record<string, string | string[] | undefined>;
const difficulties = ["Beginner", "Easy", "Medium", "Hard"];
const extraCategories = [{ slug: "excel", label: "Excel" }, { slug: "tableau", label: "Tableau" }, { slug: "linux", label: "Linux & Bash" }, { slug: "multi-tool", label: "Multi-Tool" }];
export const formats: Record<string, string> = {
  CODE: "Program", EXPRESSION: "Expression", SQL_QUERY: "SQL query",
  NUMERICAL: "Numerical", MULTIPLE_CHOICE: "Multiple choice", DATASET_ANALYSIS: "Dataset analysis",
};

export async function CatalogView({ query, fixedCategory }: { query: Query; fixedCategory?: string }) {
  const categories = [...modules, ...extraCategories];
  const category = fixedCategory ?? categories.find((module) => module.slug === query.category)?.slug ?? "";
  const difficulty = difficulties.find((value) => value === query.difficulty) ?? "";
  const topic = typeof query.topic === "string" ? query.topic.slice(0, 80) : "";
  const q = typeof query.q === "string" ? query.q.slice(0, 100) : "";
  const subject = typeof query.subject === "string" ? query.subject.slice(0, 100) : "";
  const requestedPage = Number(typeof query.page === "string" ? query.page : 1);
  const page = Number.isSafeInteger(requestedPage) && requestedPage >= 1 && requestedPage <= 1000000 ? requestedPage : 1;
  const values = { category, difficulty, topic, q, subject };
  const filters = Object.fromEntries(Object.entries(values).filter(([, value]) => value));
  const path = fixedCategory ? `/${fixedCategory}` : "/problems";
  const { items, total, topics, solved_slugs } = await getCatalog({ ...filters, offset: String((page - 1) * 50) });
  const solved = new Set(solved_slugs);
  const pageHref = (index: number) => `${path}?${new URLSearchParams({ ...filters, page: String(index) })}`;
  // Pass the current listing context into each question, including when it
  // originated from a subject track or a later catalog page.
  const questionContext = new URLSearchParams({
    ...filters, ...(fixedCategory ? { category: fixedCategory, section: fixedCategory } : {}),
    ...(page > 1 ? { page: String(page) } : {}),
  });
  const questionHref = (slug: string) => `/problems/${encodeURIComponent(slug)}${questionContext.size ? `?${questionContext}` : ""}`;


  return (
    <section className="catalog" aria-label="Problem catalog">
      <form className="card filters" action={path}>
        {subject && <input type="hidden" name="subject" value={subject} />}
        <label className="search"><span>Search</span><div><Search size={16} /><input type="search" name="q" placeholder="Title or topic" defaultValue={q} maxLength={100} /></div></label>
        {!fixedCategory && <label>Category<select name="category" defaultValue={category}><option value="">All categories</option>{categories.map((module) => <option key={module.slug} value={module.slug}>{module.label}</option>)}</select></label>}
        <label>Difficulty<select name="difficulty" defaultValue={difficulty}><option value="">All levels</option>{difficulties.map((value) => <option key={value}>{value}</option>)}</select></label>
        <label>Topic<select name="topic" defaultValue={topic}><option value="">All topics</option>{topic && !topics.includes(topic) && <option>{topic}</option>}{topics.map((value) => <option key={value}>{value}</option>)}</select></label>
        <button className="button" type="submit">Apply filters</button>
        {Object.keys(filters).some((key) => key !== "category" || !fixedCategory) && <Link className="button secondary" href={path}>Clear</Link>}
      </form>
      <div className="section-heading result-count"><h2>{total} {total === 1 ? "problem" : "problems"}</h2></div>
      {items.length > 0 ? (
        <ul className="card problem-list">
          {items.map((item, index) => (
            <li key={item.slug} className={solved.has(item.slug) ? "problem-solved" : undefined}>
              <Link href={questionHref(item.slug)}>
                <span className="problem-index" aria-label={`Question ${(page - 1) * 50 + index + 1}`}>
                  {String((page - 1) * 50 + index + 1).padStart(3, "0")}
                </span>
                <div className="problem-list-info">
                  <div className="problem-title-line">
                    <strong>{item.title}</strong>
                    {solved.has(item.slug) && <span className="problem-solved-tick" aria-label="Solved" title="Solved"><Check size={13} strokeWidth={3}/></span>}
                  </div>
                  <p>{item.topic} · {formats[item.format]}</p>
                </div>
                <span className={`difficulty ${item.difficulty.toLowerCase()}`}>{item.difficulty}</span>
                <ArrowRight size={16}/>
              </Link>
            </li>
          ))}
        </ul>
      ) : <div className="card state">No problems match this page and these filters. <Link href={path}>Reset filters</Link></div>}
      {(page > 1 || total > page * 50) && <nav className="pagination" aria-label="Catalog pagination">{page > 1 && <Link className="button secondary" href={pageHref(page - 1)}>Previous</Link>}{total > page * 50 && <Link className="button secondary" href={pageHref(page + 1)}>Next</Link>}</nav>}
    </section>
  );
}
