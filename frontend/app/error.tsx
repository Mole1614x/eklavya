"use client";

import { useRouter } from "next/navigation";
import { startTransition } from "react";

export default function ErrorPage({ reset }: { reset: () => void }) {
  const router = useRouter();
  return (
    <section className="card state" role="alert">
      <h1>This page couldn’t load</h1>
      <p>Try again in a moment.</p>
      <button className="button" onClick={() => startTransition(() => { router.refresh(); reset(); })}>Try again</button>
    </section>
  );
}
