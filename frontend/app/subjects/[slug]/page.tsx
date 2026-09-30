import Link from "next/link";
import styles from "./subject.module.css";

interface Topic {
  id: number;
  slug: string;
  title: string;
  difficulty: string;
  access_level: string;
  status: string;
}

interface Subject {
  id: number;
  slug: string;
  name: string;
  icon: string;
  description: string;
}

async function getSubject(slug: string): Promise<Subject | null> {
  const apiBase = process.env.NEXT_INTERNAL_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiBase}/api/catalogue/subjects/?format=json`, { cache: "no-store" });
    const data = await res.json();
    const subjects: Subject[] = data.results || data;
    return subjects.find((s) => s.slug === slug) || null;
  } catch {
    return null;
  }
}

async function getTopics(subjectSlug: string): Promise<Topic[]> {
  const apiBase = process.env.NEXT_INTERNAL_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiBase}/api/catalogue/topics/?subject=${subjectSlug}`, { cache: "no-store" });
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

const accessIcons: Record<string, string> = {
  free: "🔓",
  login: "🔐",
  paid: "💎",
};

export default async function SubjectPage({ params }: { params: { slug: string } }) {
  const [subject, topics] = await Promise.all([
    getSubject(params.slug),
    getTopics(params.slug),
  ]);

  if (!subject) return <div className={styles.notFound}>Subject not found.</div>;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Link href="/" className={styles.backLink}>← Back to Catalogue</Link>
        <span className={styles.icon}>{subject.icon}</span>
        <h1 className={styles.title}>{subject.name}</h1>
        <p className={styles.desc}>{subject.description}</p>
      </div>

      <div className={styles.topicList}>
        {topics.map((topic, i) => (
          <Link key={topic.id} href={`/subjects/${params.slug}/${topic.slug}`} className={styles.topicCard}>
            <div className={styles.topicIndex}>{String(i + 1).padStart(2, "0")}</div>
            <div className={styles.topicInfo}>
              <h3 className={styles.topicTitle}>{topic.title}</h3>
              <div className={styles.topicMeta}>
                <span
                  className={styles.difficulty}
                  style={{ color: difficultyColors[topic.difficulty] }}
                >
                  ● {topic.difficulty}
                </span>
                <span className={styles.access}>
                  {accessIcons[topic.access_level]} {topic.access_level}
                </span>
              </div>
            </div>
            <div className={styles.arrow}>→</div>
          </Link>
        ))}

        {topics.length === 0 && (
          <p style={{ color: "var(--text-muted)", padding: "2rem 0" }}>
            No topics published yet. Check back soon!
          </p>
        )}
      </div>
    </div>
  );
}
