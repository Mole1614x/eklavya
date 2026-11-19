import { ContestDetail } from "@/components/contest-detail";

export default async function ArenaContest({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <ContestDetail slug={slug} />;
}
