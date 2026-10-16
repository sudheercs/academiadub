"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import styles from "./classDetail.module.css";

interface Assignment {
  id: string;
  topic: {
    id: string;
    title: string;
    slug: string;
  };
  due_at: string | null;
}

interface ClassroomDetail {
  id: string;
  name: string;
  description: string;
  join_code: string;
  instructor: { id: string; email: string };
  assignments: Assignment[];
  is_active: boolean;
}

interface Analytics {
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

export default function ClassDetailPage() {
  const params = useParams();
  const id = params?.id as string;
  const router = useRouter();

  const [classroom, setClassroom] = useState<ClassroomDetail | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    const fetchData = async () => {
      try {
        const meResponse = await apiFetch(`${apiBase}/api/auth/me/`);
        if (meResponse.status === 401) {
          router.push("/login");
          return;
        }
        if (!meResponse.ok) throw new Error("Could not check your account.");
        const me = await meResponse.json();
        setUserEmail(me.email);

        const res = await apiFetch(`${apiBase}/api/classes/classrooms/${id}/`, {
        });
        if (res.ok) {
          const data = await res.json();
          setClassroom(data);
          
          // If instructor, fetch analytics
          if (data.instructor.email === me.email) {
            const analyticsRes = await apiFetch(`${apiBase}/api/classes/classrooms/${id}/analytics/`, {
            });
            if (analyticsRes.ok) {
              const analyticsData = await analyticsRes.json();
              setAnalytics(analyticsData);
            }
          }
        } else {
          setError("Failed to load class details.");
        }
      } catch {
        setError("Network error.");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id, apiBase, router]);

  if (loading) return <div className={styles.loading}>Loading...</div>;
  if (error || !classroom) return <div className={styles.error}>{error || "Class not found"}</div>;

  const isInstructor = userEmail === classroom.instructor.email;

  return (
    <div className={styles.container}>
      <Link href="/classes" className={styles.backBtn}>← Back to Classes</Link>
      
      <div className={styles.header}>
        <h1 className={styles.title}>{classroom.name}</h1>
        <p className={styles.description}>{classroom.description}</p>
        <div className={styles.meta}>
          <span>Code: <strong>{classroom.join_code}</strong></span>
          <span>Instructor: {classroom.instructor.email}</span>
        </div>
      </div>

      <div className={styles.content}>
        <div className={styles.mainColumn}>
          <h2 className={styles.sectionTitle}>Assignments</h2>
          {classroom.assignments.length === 0 ? (
            <p>No assignments posted yet.</p>
          ) : (
            <ul className={styles.assignmentList}>
              {classroom.assignments.map((assignment) => (
                <li key={assignment.id} className={styles.assignmentCard}>
                  <h3>{assignment.topic.title}</h3>
                  <p>Due: {assignment.due_at ? new Date(assignment.due_at).toLocaleDateString() : "No due date"}</p>
                  {/* Note: In a real app we'd construct the full path to the topic, e.g. /subjects/.../topic-slug */}
                  <span className={styles.topicSlug}>Topic: {assignment.topic.slug}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {isInstructor && (
          <div className={styles.sideColumn}>
            <h2 className={styles.sectionTitle}>Instructor Analytics</h2>
            <div className={styles.analyticsCard}>
              <p>Total Active Students: <strong>{analytics?.total_students || 0}</strong></p>
              <a href={`${apiBase}/api/classes/classrooms/${id}/export/`} className={styles.exportBtn}>
                📥 Export CSV Report
              </a>
            </div>

            {analytics?.assignments && analytics.assignments.length > 0 && (
              <div className={styles.progressList}>
                <h3>Completion Rates</h3>
                {analytics.assignments.map((a) => (
                  <div key={a.topic_id} className={styles.progressItem}>
                    <div className={styles.progressHeader}>
                      <span>{a.topic_title}</span>
                      <span>{a.completion_rate}%</span>
                    </div>
                    <div className={styles.progressBar}>
                      <div className={styles.progressFill} style={{ width: `${a.completion_rate}%` }}></div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
