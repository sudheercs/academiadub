import Link from "next/link";
import { cookies } from "next/headers";
import QuizPlayer from "@/components/QuizPlayer";
import styles from "./quizpage.module.css";

export default async function QuizPage({
  params,
}: {
  params: Promise<{ slug: string; topicSlug: string; quizId: string }>;
}) {
  const { slug, topicSlug, quizId } = await params;
  const token = (await cookies()).get("access_token")?.value;

  return (
    <div className={styles.container}>
      <nav className={styles.breadcrumb}>
        <Link href="/">Catalogue</Link>
        <span>/</span>
        <Link href={`/subjects/${slug}`}>{slug}</Link>
        <span>/</span>
        <Link href={`/subjects/${slug}/${topicSlug}`}>
          {topicSlug}
        </Link>
        <span>/</span>
        <span>Quiz</span>
      </nav>

      <div className={styles.playerWrapper}>
        <QuizPlayer quizId={quizId} isAuthenticated={Boolean(token)} />
      </div>
    </div>
  );
}
