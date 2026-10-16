import Link from "next/link";
import { cookies } from "next/headers";
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
  access_gated: boolean;
  content: Block[];
  subject: { slug: string; name: string; icon: string };
  course?: { id: number; slug: string; title: string; icon?: string };
}

interface Download {
  id: string;
  title: string;
  description: string;
  file_url: string;
  file_size_bytes: number;
  mime_type: string;
}

interface QuizStub {
  id: string;
  title: string;
  description: string;
  pass_mark: number;
  time_limit_minutes: number | null;
  question_count: number;
}

async function getTopic(subjectSlug: string, topicSlug: string, token: string | undefined): Promise<Topic | null> {
  const apiBase = process.env.NEXT_INTERNAL_API_URL || "http://localhost:8000";
  try {
    const listRes = await fetch(
      `${apiBase}/api/catalogue/topics/?subject=${subjectSlug}`,
      {
        cache: "no-store",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }
    );
    const listData = await listRes.json();
    const topics = listData.results || listData;
    const stub = topics.find((t: { slug: string }) => t.slug === topicSlug);
    if (!stub) return null;

    const detailRes = await fetch(
      `${apiBase}/api/catalogue/topics/${stub.id}/`,
      {
        cache: "no-store",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }
    );
    if (!detailRes.ok) return null;
    return await detailRes.json();
  } catch {
    return null;
  }
}

async function getDownloads(topicId: number, token: string | undefined): Promise<Download[]> {
  const apiBase = process.env.NEXT_INTERNAL_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiBase}/api/downloads/files/?topic=${topicId}`, {
      cache: "no-store",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    const data = await res.json();
    return data.results || data;
  } catch {
    return [];
  }
}

async function getQuizzes(topicId: number, token: string | undefined): Promise<QuizStub[]> {
  const apiBase = process.env.NEXT_INTERNAL_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiBase}/api/practice/quizzes/?topic=${topicId}`, {
      cache: "no-store",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
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

function AccessGate({ level }: { level: string }) {
  const isPaid = level === "paid";
  return (
    <div className={styles.gate}>
      <span className={styles.gateIcon}>{isPaid ? "💎" : "🔐"}</span>
      <h2 className={styles.gateTitle}>
        {isPaid ? "Premium Content" : "Login Required"}
      </h2>
      <p className={styles.gateDesc}>
        {isPaid
          ? "This topic is part of a paid plan. Upgrade to access all premium content."
          : "You need to be signed in to read this topic. It's free — just create an account."}
      </p>
      <div className={styles.gateActions}>
        <Link href="/login" className={styles.gateLogin}>
          Log In
        </Link>
        {!isPaid && (
          <Link href="/register" className={styles.gateRegister}>
            Sign Up Free
          </Link>
        )}
      </div>
    </div>
  );
}

export default async function TopicPage({
  params,
}: {
  params: Promise<{ slug: string; topicSlug: string }>;
}) {
  const { slug, topicSlug } = await params;
  const token = (await cookies()).get("access_token")?.value;
  const topic = await getTopic(slug, topicSlug, token);
  const downloads = topic && !topic.access_gated ? await getDownloads(topic.id, token) : [];
  const quizzes = topic && !topic.access_gated ? await getQuizzes(topic.id, token) : [];

  if (!topic)
    return (
      <div className={styles.notFound}>
        <p>Topic not found or not yet published.</p>
        <Link href={`/subjects/${slug}`} className={styles.backLink}>
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
        <Link href={`/subjects/${slug}`}>{topic.subject?.name || "Subject"}</Link>
        {topic.course && (
          <>
            <span>/</span>
            <span>{topic.course.title}</span>
          </>
        )}
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

      {/* Access gate OR content */}
      {topic.access_gated ? (
        <AccessGate level={topic.access_level} />
      ) : (
        <>
          {/* Content Blocks */}
          <article className={styles.article}>
            <BlockRenderer blocks={topic.content} />
          </article>

          {/* Quizzes Section */}
          {quizzes.length > 0 && (
            <div className={styles.downloads}>
              <h3 className={styles.downloadsTitle}>🧠 Practice Quizzes</h3>
              <ul className={styles.downloadList}>
                {quizzes.map((q) => (
                  <li key={q.id} className={styles.downloadItem}>
                    <a
                      href={`/subjects/${slug}/${topicSlug}/quiz/${q.id}`}
                      className={styles.downloadLink}
                    >
                      <span className={styles.downloadIcon}>📝</span>
                      <div className={styles.downloadInfo}>
                        <strong>{q.title}</strong>
                        {q.description && <p>{q.description}</p>}
                      </div>
                      <span className={styles.downloadSize}>
                        {q.question_count}Q · {q.pass_mark}% pass
                        {q.time_limit_minutes ? ` · ${q.time_limit_minutes}min` : ""}
                      </span>
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Downloads Section */}
          {downloads.length > 0 && (
            <div className={styles.downloads}>
              <h3 className={styles.downloadsTitle}>Attachments</h3>
              <ul className={styles.downloadList}>
                {downloads.map((d) => (
                  <li key={d.id} className={styles.downloadItem}>
                    <a
                      href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/downloads/files/${d.id}/serve/`}
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
        </>
      )}

      {/* Footer nav */}
      <div className={styles.footer}>
        <Link href={`/subjects/${slug}`} className={styles.backLink}>
          ← Back to {topic.subject.name}
        </Link>
      </div>
    </div>
  );
}
