import { Suspense } from "react";
import CatalogLoading from "@/components/catalog-loading";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRight, Star } from "lucide-react";
import { community, modules, ranks } from "@/lib/navigation";
import { Dashboard } from "@/components/dashboard";
import { PracticeChart } from "@/components/practice-chart";
import { ModuleIcon } from "@/components/icons";
import { CatalogView, type Query } from "@/components/catalog";

const activities: Record<string, { href: string; label: string }> = {
  "daily-sadhana": { href: "/problems/star-staircase", label: "Try Star Staircase" },
  arena: { href: "/code", label: "Practice algorithms" },
  "vidya-paths": { href: "/foundations", label: "Browse Foundations" },
};

type Props = { params: Promise<{ section: string }>; searchParams: Promise<Query> };

export async function generateMetadata({ params }: Props) {
  const { section } = await params;
  return { title: section === "dashboard" ? "Dashboard" : [...modules, ...community].find((item) => item.slug === section)?.label };
}

export default async function Section({ params, searchParams }: Props) {
  const { section } = await params;
  if (section === "dashboard") return <Dashboard />;
  const module = modules.find((item) => item.slug === section);
  const item = module ?? community.find((entry) => entry.slug === section);
  if (!item) notFound();
  const activity = activities[section];
  const query = module ? await searchParams : {};

  return (
    <>
      <header className="page-header">
        <p className="eyebrow"><ModuleIcon name={item.icon} size={16} /> {item.label}</p>
        <h1>{item.title}</h1><p>{item.description}</p>
        {activity && <Link className="button" href={activity.href}>{activity.label} <ArrowRight size={16} /></Link>}
      </header>
      {module && <Suspense key={JSON.stringify(query)} fallback={<CatalogLoading />}><CatalogView query={query} fixedCategory={module.slug} /></Suspense>}
      {!module && item.topics.length > 0 && <ul className="skills-grid clean-list">{item.topics.map((topic) => <li className="card feature-card" key={topic}><ModuleIcon name={item.icon} /><h2>{topic}</h2></li>)}</ul>}
      {section === "rankings" && <ul className="skills-grid clean-list">{ranks.map(([name, xp], index) => <li key={name} className="card feature-card"><div className="stars" aria-label={`${index + 1} stars`}>{Array.from({ length: index + 1 }, (_, star) => <Star key={star} size={16} fill="currentColor" aria-hidden="true" />)}</div><h2>{name}</h2><p>{xp.toLocaleString("en-US")} XP</p></li>)}</ul>}
      {section === "progress-insights" && <PracticeChart />}
    </>
  );
}
