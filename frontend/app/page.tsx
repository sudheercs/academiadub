export const dynamic = 'force-dynamic';
import Link from "next/link";
import styles from "./page.module.css";

interface Subject {
  id: number;
  slug: string;
  name: string;
  icon: string;
  description: string;
}

// Fetch data on the server side
async function getSubjects() {
  // The frontend Docker container runs on the same docker network, but Server Components
  // might fetch from localhost if using host networking, or `api` if using docker DNS.
  try {
    const apiBase = process.env.NEXT_INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const res = await fetch(`${apiBase}/api/catalogue/subjects/`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`Failed to fetch subjects: ${res.status} ${res.statusText}`);
    const data = await res.json();
    // Django REST Framework pagination returns { count, next, previous, results }
    return data.results || data;
  } catch (error) {
    console.error("Error fetching subjects:", error);
    return [];
  }
}

export default async function Home() {
  const subjects = await getSubjects();

  return (
    <main className={styles.container}>
      <div className={styles.hero}>
        <h1 className={styles.title}>Welcome to AcademiaHub</h1>
        <p className={styles.subtitle}>
          Your premium destination for high-quality, interactive learning. 
          Explore our catalogue and start mastering new skills today.
        </p>
      </div>

      <div className={styles.grid}>
        {subjects.length > 0 ? (
          subjects.map((subject: Subject) => (
            <Link key={subject.id} href={`/subjects/${subject.slug}`} className={`${styles.card} glass`} style={{ textDecoration: 'none' }}>
              <div className={styles.cardIcon}>{subject.icon}</div>
              <h3 className={styles.cardTitle}>{subject.name}</h3>
              <p className={styles.cardDesc}>{subject.description}</p>
            </Link>
          ))
        ) : (
          <div className="glass" style={{ padding: "2rem", gridColumn: "1 / -1", textAlign: "center" }}>
            <p>No subjects found. Is the API running and seeded?</p>
          </div>
        )}
      </div>
    </main>
  );
}
