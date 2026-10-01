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

interface Download {
  id: string;
  title: string;
  description: string;
  file_url: string;
  file_size_bytes: number;
  mime_type: string;
}

async function getTopic(subjectSlug: string, topicSlug: string): Promise<Topic | null> {
  const apiBase = process.env.NEXT_INTERNAL_API_URL || "http://localhost:8000";
  try {
    // First fetch the list to find the topic's ID
    const listRes = await fetch(
      `${apiBase}/api/catalogue/topics/?subject=${subjectSlug}`,
      { cache: "no-store" }
    );
    const listData = await listRes.json();
    const topics = listData.results || listData;
    const stub = topics.find((t: { slug: string }) => t.slug === topicSlug);
    if (!stub) return null;

    // Then fetch the detail endpoint to get the content blocks
    const detailRes = await fetch(
      `${apiBase}/api/catalogue/topics/${stub.id}/`,
      { cache: "no-store" }
    );
    if (!detailRes.ok) return null;
    return await detailRes.json();
  } catch {
    return null;
  }
}

async function getDownloads(topicId: number): Promise<Download[]> {
  const apiBase = process.env.NEXT_INTERNAL_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiBase}/api/downloads/files/?topic=${topicId}`, { cache: "no-store" });
    const data = await res.json();
    return data.results || data;
  } catch {
    return [];
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
  const downloads = topic ? await getDownloads(topic.id) : [];

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

      {/* Downloads Section */}
      {downloads.length > 0 && (
        <div className={styles.downloads}>
          <h3 className={styles.downloadsTitle}>Attachments</h3>
          <ul className={styles.downloadList}>
            {downloads.map((d) => (
              <li key={d.id} className={styles.downloadItem}>
                <a
                  href={`http://localhost:8000/api/downloads/files/${d.id}/serve/`}
                  className={styles.downloadLink}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <span className={styles.downloadIcon}>📄</span>
                  <div className={styles.downloadInfo}>
                    <strong>{d.title}</strong>
                    {d.description && <p>{d.description}</p>}
                  </div>
                  {d.file_size_bytes && (
                    <span className={styles.downloadSize}>
                      {Math.round(d.file_size_bytes / 1024)} KB
                    </span>
                  )}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Footer nav */}
      <div className={styles.footer}>
        <Link href={`/subjects/${params.slug}`} className={styles.backLink}>
          ← Back to {topic.subject.name}
        </Link>
      </div>
    </div>
  );
}
