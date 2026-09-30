import Link from "next/link";
import BlockRenderer from "@/components/BlockRenderer";
import styles from "./topic.module.css";

interface Block {
  type: string;
  content?: string;
  language?: string;
  url?: string;
  caption?: string;
}

interface Topic {
  id: number;
  slug: string;
  title: string;
  difficulty: string;
  access_level: string;
  content: Block[];
  subject: { slug: string; name: string; icon: string };
}

async function getTopic(subjectSlug: string, topicSlug: string): Promise<Topic | null> {
  const apiBase = process.env.NEXT_INTERNAL_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(
      `${apiBase}/api/catalogue/topics/?subject=${subjectSlug}`,
      { cache: "no-store" }
    );
    const data = await res.json();
    const topics: Topic[] = data.results || data;
    return topics.find((t) => t.slug === topicSlug) || null;
  } catch {
    return null;
  }
}

const difficultyColors: Record<string, string> = {
  beginner: "#4ade80",
  intermediate: "#fb923c",
  advanced: "#f87171",
};

export default async function TopicPage({
  params,
}: {
  params: { slug: string; topicSlug: string };
}) {
  const topic = await getTopic(params.slug, params.topicSlug);

  if (!topic)
    return (
      <div className={styles.notFound}>
        <p>Topic not found or not yet published.</p>
        <Link href={`/subjects/${params.slug}`} className={styles.backLink}>
          ← Back
        </Link>
      </div>
    );

  return (
    <div className={styles.container}>
      {/* Breadcrumb */}
      <nav className={styles.breadcrumb}>
        <Link href="/">Catalogue</Link>
        <span>/</span>
        <Link href={`/subjects/${params.slug}`}>{topic.subject.name}</Link>
        <span>/</span>
        <span>{topic.title}</span>
      </nav>

      {/* Header */}
      <header className={styles.header}>
        <h1 className={styles.title}>{topic.title}</h1>
        <div className={styles.meta}>
          <span
            className={styles.difficulty}
            style={{ color: difficultyColors[topic.difficulty] }}
          >
            ● {topic.difficulty}
          </span>
          {topic.access_level !== "free" && (
            <span className={styles.badge}>
              {topic.access_level === "paid" ? "💎 Premium" : "🔐 Login required"}
            </span>
          )}
        </div>
      </header>

      {/* Divider */}
      <hr className={styles.divider} />

      {/* Content Blocks */}
      <article className={styles.article}>
        <BlockRenderer blocks={topic.content} />
      </article>

      {/* Footer nav */}
      <div className={styles.footer}>
        <Link href={`/subjects/${params.slug}`} className={styles.backLink}>
          ← Back to {topic.subject.name}
        </Link>
      </div>
    </div>
  );
}
