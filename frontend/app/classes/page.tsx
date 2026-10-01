import Link from "next/link";
import styles from "./classes.module.css";

interface Assignment {
  id: string;
  topic: { title: string; difficulty: string };
  due_at: string | null;
}

interface Classroom {
  id: string;
  name: string;
  description: string;
  instructor_email: string;
  join_code: string;
  is_active: boolean;
  student_count: number;
  assignment_count: number;
  created_at: string;
}

async function getClasses(): Promise<Classroom[]> {
  const apiBase = process.env.NEXT_INTERNAL_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiBase}/api/classes/classrooms/`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.results || data;
  } catch {
    return [];
  }
}

const difficultyColor: Record<string, string> = {
  beginner: "#4ade80",
  intermediate: "#fb923c",
  advanced: "#f87171",
};

export default async function ClassesPage() {
  const classes = await getClasses();

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Classes</h1>
          <p className={styles.subtitle}>
            Manage cohorts, assign topics, and track student progress.
          </p>
        </div>
        <div className={styles.headerActions}>
          <JoinCodeForm />
        </div>
      </header>

      {classes.length === 0 ? (
        <div className={styles.empty}>
          <span className={styles.emptyIcon}>🏫</span>
          <p>No classes yet. Log in as an instructor to create one.</p>
        </div>
      ) : (
        <div className={styles.grid}>
          {classes.map((cls) => (
            <Link key={cls.id} href={`/classes/${cls.id}`} className={styles.card}>
              <div className={styles.cardHeader}>
                <span className={styles.classIcon}>🎓</span>
                {cls.is_active && <span className={styles.activeBadge}>Active</span>}
              </div>
              <h2 className={styles.className}>{cls.name}</h2>
              <p className={styles.classDesc}>{cls.description}</p>
              <div className={styles.cardMeta}>
                <span>👥 {cls.student_count} students</span>
                <span>📚 {cls.assignment_count} topics</span>
              </div>
              <div className={styles.cardFooter}>
                <span className={styles.joinCode}>
                  Code: <strong>{cls.join_code}</strong>
                </span>
                <span className={styles.instructor}>{cls.instructor_email}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

// Client-side join form component (rendered as a server component placeholder)
function JoinCodeForm() {
  return (
    <form className={styles.joinForm} action="/api/classes/join-action" method="GET">
      <input
        type="text"
        name="code"
        placeholder="Enter join code…"
        className={styles.joinInput}
        maxLength={10}
      />
      <button type="submit" className={styles.joinBtn}>Join Class</button>
    </form>
  );
}
