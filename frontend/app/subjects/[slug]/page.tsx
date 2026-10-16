import Link from "next/link";
import styles from "./subject.module.css";

interface Topic {
  id: number;
  slug: string;
  title: string;
  difficulty: string;
  access_level: string;
  status: string;
  course?: {
    id: number;
    slug: string;
    title: string;
  };
}

interface Course {
  id: number;
  slug: string;
  title: string;
  description: string;
  icon: string;
  difficulty: string;
  status: string;
  order: number;
  topic_count: number;
}

interface Subject {
  id: number;
  slug: string;
  name: string;
  icon: string;
  description: string;
  course_count?: number;
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

async function getCourses(subjectSlug: string): Promise<Course[]> {
  const apiBase = process.env.NEXT_INTERNAL_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiBase}/api/catalogue/courses/?subject=${subjectSlug}`, { cache: "no-store" });
    const data = await res.json();
    return data.results || data;
  } catch {
    return [];
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

export default async function SubjectPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const [subject, courses, topics] = await Promise.all([
    getSubject(slug),
    getCourses(slug),
    getTopics(slug),
  ]);

  if (!subject) return <div className={styles.notFound}>Subject not found.</div>;

  // Group topics by course
  const topicsByCourse: Record<number, Topic[]> = {};
  const ungroupedTopics: Topic[] = [];

  topics.forEach((topic) => {
    if (topic.course && topic.course.id) {
      if (!topicsByCourse[topic.course.id]) {
        topicsByCourse[topic.course.id] = [];
      }
      topicsByCourse[topic.course.id].push(topic);
    } else {
      ungroupedTopics.push(topic);
    }
  });

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Link href="/" className={styles.backLink}>← Back to Catalogue</Link>
        <span className={styles.icon}>{subject.icon}</span>
        <h1 className={styles.title}>{subject.name}</h1>
        <p className={styles.desc}>{subject.description}</p>
      </div>

      <div className={styles.courseList}>
        {courses.map((course) => {
          const courseTopics = topicsByCourse[course.id] || [];
          return (
            <section key={course.id} className={styles.courseSection}>
              <div className={styles.courseHeader}>
                <div className={styles.courseHeaderLeft}>
                  {course.icon && <span className={styles.courseIcon}>{course.icon}</span>}
                  <div>
                    <div className={styles.courseTitleRow}>
                      <h2 className={styles.courseTitle}>{course.title}</h2>
                      <span
                        className={styles.difficultyBadge}
                        style={{ color: difficultyColors[course.difficulty] || "#94a3b8" }}
                      >
                        ● {course.difficulty}
                      </span>
                    </div>
                    {course.description && (
                      <p className={styles.courseDesc}>{course.description}</p>
                    )}
                  </div>
                </div>
                <span className={styles.courseCountBadge}>
                  {courseTopics.length} {courseTopics.length === 1 ? "topic" : "topics"}
                </span>
              </div>

              <div className={styles.topicList}>
                {courseTopics.map((topic, i) => (
                  <Link
                    key={topic.id}
                    href={`/subjects/${slug}/${topic.slug}`}
                    className={styles.topicCard}
                  >
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

                {courseTopics.length === 0 && (
                  <p className={styles.emptyTopics}>No topics published in this course yet.</p>
                )}
              </div>
            </section>
          );
        })}

        {ungroupedTopics.length > 0 && (
          <section className={styles.courseSection}>
            <div className={styles.courseHeader}>
              <h2 className={styles.courseTitle}>Other Topics</h2>
            </div>
            <div className={styles.topicList}>
              {ungroupedTopics.map((topic, i) => (
                <Link
                  key={topic.id}
                  href={`/subjects/${slug}/${topic.slug}`}
                  className={styles.topicCard}
                >
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
            </div>
          </section>
        )}

        {courses.length === 0 && ungroupedTopics.length === 0 && (
          <p style={{ color: "var(--text-muted)", padding: "2rem 0" }}>
            No courses or topics published yet. Check back soon!
          </p>
        )}
      </div>
    </div>
  );
}
