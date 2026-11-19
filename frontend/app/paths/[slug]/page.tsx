import { PathDetail } from "@/components/path-detail";

export default async function LearningPathPage({ params }: { params: Promise<{ slug: string }> }) {
  return <PathDetail slug={(await params).slug} />;
}
