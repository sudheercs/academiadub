import Link from "next/link";
import styles from "./class.module.css";

interface Topic {
  id: number;
  slug: string;
  title: string;
  difficulty: string;
  subject: { slug: string; name: string };
}

interface Assignment {
  id: string;
  topic: Topic;
  title: string;
  due_at: string | null;
}

interface Enrollment {
  id: string;
  student_email: string;
  status: string;
  enrolled_at: string;
}

interface Analytics {
  classroom: string;
  total_students: number;
  assignments: {
    topic_id: string;
    topic_title: string;
    due_at: string | null;
    total_students: number;
    completed: number;
    completion_rate: number;
  }[];
}

interface ClassDetail {
  id: string;
  name: string;
  description: string;
  instructor_email: string;
  join_code: string;
  is_active: boolean;
  student_count: number;
  assignment_count: number;
  enrollments: Enrollment[];
  assignments: Assignment[];
}

async function getClass(id: string): Promise<ClassDetail | null> {
  const apiBase = process.env.NEXT_INTERNAL_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiBase}/api/classes/classrooms/${id}/`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch { return null; }
}

async function getAnalytics(id: string): Promise<Analytics | null> {
  const apiBase = process.env.NEXT_INTERNAL_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiBase}/api/classes/classrooms/${id}/analytics/`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch { return null; }
}

const difficultyColor: Record<string, string> = {
  beginner: "#4ade80",
  intermediate: "#fb923c",
  advanced: "#f87171",
};

export default async function ClassDetailPage({ params }: { params: { id: string } }) {
  const [cls, analytics] = await Promise.all([
    getClass(params.id),
    getAnalytics(params.id),
  ]);

  if (!cls) return (
    <div className={styles.notFound}>
      <p>Class not found.</p>
      <Link href="/classes" className={styles.back}>← Back to Classes</Link>
    </div>
  );

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <Link href="/classes" className={styles.back}>← Classes</Link>
        <div className={styles.headerInfo}>
          <div className={styles.titleRow}>
            <h1 className={styles.title}>{cls.name}</h1>
            {cls.is_active && <span className={styles.activeBadge}>Active</span>}
          </div>
          <p className={styles.desc}>{cls.description}</p>
          <div className={styles.meta}>
            <span>👨‍🏫 {cls.instructor_email}</span>
            <span>👥 {cls.student_count} students</span>
            <span className={styles.joinCode}>Code: <strong>{cls.join_code}</strong></span>
            <a href={`http://localhost:8000/api/classes/classrooms/${cls.id}/export/`} className={styles.exportBtn} download>
              ⬇ Export CSV
            </a>
          </div>
        </div>
      </div>

      <div className={styles.layout}>
        {/* Assignments + Analytics */}
        <div className={styles.main}>
          <h2 className={styles.sectionTitle}>📚 Assignments</h2>
          {cls.assignments.length === 0 ? (
            <p className={styles.empty}>No topics assigned yet.</p>
          ) : (
            <div className={styles.assignmentList}>
              {cls.assignments.map((a) => {
                const stat = analytics?.assignments.find(s => s.topic_id === String(a.topic.id));
                return (
                  <div key={a.id} className={styles.assignmentCard}>
                    <div className={styles.assignmentHeader}>
                      <Link
                        href={`/subjects/${a.topic.subject.slug}/${a.topic.slug}`}
                        className={styles.topicLink}
                      >
                        {a.topic.title}
                      </Link>
                      <span
                        className={styles.difficulty}
                        style={{ color: difficultyColor[a.topic.difficulty] }}
                      >
                        ● {a.topic.difficulty}
                      </span>
                    </div>
                    {a.due_at && (
                      <p className={styles.dueDate}>
                        Due: {new Date(a.due_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
                      </p>
                    )}
                    {stat && (
                      <div className={styles.progressBar}>
                        <div className={styles.progressFill} style={{ width: `${stat.completion_rate}%` }} />
                        <span className={styles.progressLabel}>
                          {stat.completed}/{stat.total_students} completed ({stat.completion_rate}%)
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Students sidebar */}
        <aside className={styles.sidebar}>
          <h2 className={styles.sectionTitle}>👥 Students</h2>
          {cls.enrollments.length === 0 ? (
            <p className={styles.empty}>No students enrolled yet.</p>
          ) : (
            <ul className={styles.studentList}>
              {cls.enrollments.map((e) => (
                <li key={e.id} className={styles.student}>
                  <span className={styles.avatar}>
                    {e.student_email.charAt(0).toUpperCase()}
                  </span>
                  <div>
                    <p className={styles.studentEmail}>{e.student_email}</p>
                    <p className={styles.enrollDate}>
                      Joined {new Date(e.enrolled_at).toLocaleDateString("en-IN")}
                    </p>
                  </div>
                  <span className={`${styles.statusBadge} ${styles[e.status]}`}>{e.status}</span>
                </li>
              ))}
            </ul>
          )}
        </aside>
      </div>
    </div>
  );
}
