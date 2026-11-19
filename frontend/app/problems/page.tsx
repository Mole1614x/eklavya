import { Suspense } from "react";
import CatalogLoading from "@/components/catalog-loading";
import { CatalogView, type Query } from "@/components/catalog";

export const metadata = { title: "Problem Catalog" };

export default async function Problems({ searchParams }: { searchParams: Promise<Query> }) {
  const query = await searchParams;
  return <><header className="page-header"><h1>Problem Catalog</h1><p>Find a challenge by practice area, difficulty, or topic.</p></header><Suspense key={JSON.stringify(query)} fallback={<CatalogLoading />}><CatalogView query={query} /></Suspense></>;
}
