import Link from "next/link";

export default function NotFound() {
  return <section className="card state"><h1>Page unavailable</h1><p>Explore the catalog to find another challenge.</p><Link href="/problems" className="button">Browse problems</Link></section>;
}
