"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export type Contest = {
  slug: string;
  title: string;
  description: string;
  starts_at: string;
  ends_at: string;
  status: "UPCOMING" | "ACTIVE" | "FINISHED";
  is_rated: boolean;
};

function date(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function ArenaData() {
  const [contests, setContests] = useState<Contest[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    void fetch("/api/contests").then(async (response) => {
      if (!response.ok) throw new Error("Arena schedule unavailable");
      setContests(await response.json());
    }).catch((reason: Error) => setError(reason.message));
  }, []);
  if (error) return <section className="card state">{error}</section>;
  if (!contests) return <section className="card state" role="status">Loading the Arena schedule…</section>;
  if (!contests.length) return <section className="card state">The next contest will be announced soon.</section>;
  return <ul className="contest-grid clean-list">{contests.map((contest) => (
    <li className="card contest-card" key={contest.slug}>
      <div>
        <span className={`contest-status ${contest.status.toLowerCase()}`}>{contest.status}</span>
        <h2>{contest.title}</h2>
        <p>{contest.description}</p>
        <small>{date(contest.starts_at)} · {contest.is_rated ? "Rated" : "Unrated"}</small>
      </div>
      <Link className="button secondary" href={`/arena/${contest.slug}`}>{contest.status === "ACTIVE" ? "Enter Arena" : "View contest"}</Link>
    </li>
  ))}</ul>;
}
