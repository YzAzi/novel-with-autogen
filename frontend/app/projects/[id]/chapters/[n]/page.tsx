import { ChapterClient } from "./ui";

export default async function ChapterPage({ params }: { params: Promise<{ id: string; n: string }> }) {
  const { id, n } = await params;
  return <ChapterClient projectId={id} chapterNumber={Number(n)} />;
}
