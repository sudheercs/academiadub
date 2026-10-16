"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { apiFetch } from "@/lib/api";
import styles from "./quiz.module.css";

/* ── Types ───────────────────────────────────────────────────────────────── */

interface Choice      { id: string; text: string; order: number; }
interface Question    { id: string; text: string; question_type: "mcq" | "multi"; order: number; choices: Choice[]; }
interface ChoiceWA    extends Choice    { is_correct: boolean; }
interface QuestionWA  extends Question  { choices: ChoiceWA[]; explanation: string; }

interface Quiz {
  id: string; title: string; description: string;
  pass_mark: number; time_limit_minutes: number | null; questions: Question[];
}

interface AttemptStub {
  id: string; status: "in_progress" | "submitted";
  answers: Record<string, string[]>;
  started_at: string; submitted_at: string | null;
}

interface AttemptResult extends AttemptStub {
  score_percent: number; passed: boolean;
  questions: QuestionWA[];
}

interface QuizPlayerProps { quizId: string; isAuthenticated?: boolean; }

type Phase = "checking" | "intro" | "resume_prompt" | "playing" | "saving" | "result";

const AUTOSAVE_MS = 30_000; // autosave every 30 seconds

/* ── Component ───────────────────────────────────────────────────────────── */

export default function QuizPlayer({ quizId, isAuthenticated = false }: QuizPlayerProps) {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const [quiz,        setQuiz]        = useState<Quiz | null>(null);
  const [phase,       setPhase]       = useState<Phase>("checking");
  const [currentIdx,  setCurrentIdx]  = useState(0);
  const [answers,     setAnswers]     = useState<Record<string, string[]>>({});
  const [attemptId,   setAttemptId]   = useState<string | null>(null);
  const [savedAt,     setSavedAt]     = useState<Date | null>(null);
  const [result,      setResult]      = useState<AttemptResult | null>(null);
  const [inProgress,  setInProgress]  = useState<AttemptStub | null>(null);
  const [error,       setError]       = useState<string | null>(null);
  const [timeLeft,    setTimeLeft]    = useState<number | null>(null);
  const isSavingRef = useRef(false);

  /* ── 1. On mount: load quiz + check for resumable attempt ────────────── */
  useEffect(() => {
    (async () => {
      try {
        // Load quiz metadata
        const qRes  = await apiFetch(`${apiBase}/api/practice/quizzes/${quizId}/`, {
          
        });
        const qData = await qRes.json();
        setQuiz(qData);

        // If logged in, check for an existing in_progress attempt to offer resume
        if (isAuthenticated) {
          const aRes  = await apiFetch(`${apiBase}/api/practice/quizzes/${quizId}/my-attempts/`, {
            
          });
          const aData = await aRes.json();
          const resumable = (aData.in_progress || [])[0] as AttemptStub | undefined;
          if (resumable) {
            setInProgress(resumable);
            setPhase("resume_prompt");
            return;
          }
        }
        setPhase("intro");
      } catch {
        setError("Failed to load quiz.");
        setPhase("intro");
      }
    })();
  }, [quizId, isAuthenticated, apiBase]);

  /* ── 2. Start a fresh attempt ────────────────────────────────────────── */
  const handleStart = useCallback(async () => {
    if (!isAuthenticated) { setPhase("playing"); return; }   // unauthenticated: local only
    try {
      const res  = await apiFetch(`${apiBase}/api/practice/quizzes/${quizId}/start/`, {
        method: "POST", headers: { "Content-Type": "application/json",  },
      });
      const data = await res.json();
      setAttemptId(data.attempt.id);
      setAnswers({});
      setCurrentIdx(0);
      setPhase("playing");
    } catch {
      setError("Could not start quiz. Try again.");
    }
  }, [isAuthenticated, quizId, apiBase]);

  /* ── 3. Resume an existing attempt ──────────────────────────────────── */
  const handleResume = useCallback(() => {
    if (!inProgress) return;
    setAttemptId(inProgress.id);
    setAnswers(inProgress.answers || {});
    setCurrentIdx(0);
    setInProgress(null);
    setPhase("playing");
  }, [inProgress]);

  /* ── 4. Save progress (server) ───────────────────────────────────────── */
  const saveProgress = useCallback(async (currentAnswers: Record<string, string[]>) => {
    if (!isAuthenticated || !attemptId || isSavingRef.current) return;
    isSavingRef.current = true;
    try {
      await apiFetch(`${apiBase}/api/practice/quizzes/${quizId}/save/${attemptId}/`, {
        method: "POST",
        headers: { "Content-Type": "application/json",  },
        body: JSON.stringify({ answers: currentAnswers }),
      });
      setSavedAt(new Date());
    } finally {
      isSavingRef.current = false;
    }
  }, [isAuthenticated, attemptId, quizId, apiBase]);

  /* ── 5. Save & Exit ──────────────────────────────────────────────────── */
  const handleSaveExit = useCallback(async () => {
    setPhase("saving");
    await saveProgress(answers);
    // Navigate back — in Next.js we can just go back
    window.history.back();
  }, [answers, saveProgress]);

  /* ── 6. Submit ───────────────────────────────────────────────────────── */
  const handleSubmit = useCallback(async () => {
    if (!isAuthenticated) {
      setError("You must be logged in to submit a quiz.");
      return;
    }
    setPhase("saving");
    try {
      const res  = await apiFetch(
        `${apiBase}/api/practice/quizzes/${quizId}/submit/${attemptId}/`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json",  },
          body: JSON.stringify({ answers }),
        }
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Submission failed.");
      setResult(data);
      setPhase("result");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Submission failed.");
      setPhase("playing");
    }
  }, [isAuthenticated, quizId, attemptId, answers, apiBase]);

  /* ── Autosave every 30 s while playing ──────────────────────────────── */
  useEffect(() => {
    if (phase !== "playing" || !attemptId) return;
    const t = setInterval(() => saveProgress(answers), AUTOSAVE_MS);
    return () => clearInterval(t);
  }, [phase, attemptId, answers, saveProgress]);

  /* ── Timer ───────────────────────────────────────────────────────────── */
  useEffect(() => {
    if (phase !== "playing" || !quiz?.time_limit_minutes) return;
    setTimeLeft(quiz.time_limit_minutes * 60);
  }, [phase, quiz]);

  useEffect(() => {
    if (timeLeft === null || phase !== "playing") return;
    if (timeLeft <= 0) { handleSubmit(); return; }
    const t = setTimeout(() => setTimeLeft(s => s !== null ? s - 1 : null), 1000);
    return () => clearTimeout(t);
  }, [timeLeft, phase, handleSubmit]);

  /* ── Choice toggle ───────────────────────────────────────────────────── */
  const toggleChoice = (questionId: string, choiceId: string, isMulti: boolean) => {
    setAnswers(prev => {
      const cur = prev[questionId] || [];
      const next = isMulti
        ? cur.includes(choiceId) ? cur.filter(id => id !== choiceId) : [...cur, choiceId]
        : [choiceId];
      return { ...prev, [questionId]: next };
    });
  };

  const formatTime = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  const totalQ        = quiz?.questions.length ?? 0;
  const answeredCount = Object.keys(answers).length;
  const question      = quiz?.questions[currentIdx];

  /* ── CHECKING ───────────────────────────────────────────────────────── */
  if (phase === "checking") {
    return (
      <div className={styles.loadingState}>
        <div className={styles.spinner} />
        <p>Loading quiz…</p>
      </div>
    );
  }

  if (error) {
    return <div className={styles.errorState}><span>⚠️</span> {error}</div>;
  }
  if (!quiz) return null;

  /* ── INTRO ──────────────────────────────────────────────────────────── */
  if (phase === "intro") {
    return (
      <div className={styles.intro}>
        <div className={styles.introIcon}>🧠</div>
        <h2 className={styles.introTitle}>{quiz.title}</h2>
        {quiz.description && <p className={styles.introDesc}>{quiz.description}</p>}
        <div className={styles.introMeta}>
          <span>{totalQ} questions</span>
          <span>·</span>
          <span>Pass mark: {quiz.pass_mark}%</span>
          {quiz.time_limit_minutes && <><span>·</span><span>⏱ {quiz.time_limit_minutes} min</span></>}
        </div>
        {!isAuthenticated && (
          <p className={styles.loginNotice}>
            ⚠️ You must be <a href="/login">logged in</a> to save progress and submit results.
          </p>
        )}
        <div className={styles.introFeatures}>
          <span>💾 Save &amp; resume anytime</span>
          <span>·</span>
          <span>✅ Submit with partial answers</span>
        </div>
        <button className={styles.startBtn} onClick={handleStart}>
          Start Quiz →
        </button>
      </div>
    );
  }

  /* ── RESUME PROMPT ──────────────────────────────────────────────────── */
  if (phase === "resume_prompt" && inProgress) {
    const startedDate = new Date(inProgress.started_at);
    const savedCount  = Object.keys(inProgress.answers || {}).length;
    return (
      <div className={styles.resumePrompt}>
        <span className={styles.resumeIcon}>💾</span>
        <h2 className={styles.resumeTitle}>Continue where you left off?</h2>
        <p className={styles.resumeDesc}>
          You started this quiz on <strong>{startedDate.toLocaleDateString()}</strong> at{" "}
          <strong>{startedDate.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</strong>{" "}
          and saved <strong>{savedCount}</strong> of {totalQ} answers.
        </p>
        <div className={styles.resumeActions}>
          <button className={styles.startBtn} onClick={handleResume}>
            Resume Quiz →
          </button>
          <button className={styles.cancelBtn} onClick={handleStart}>
            Start Fresh
          </button>
        </div>
      </div>
    );
  }

  /* ── SAVING spinner ─────────────────────────────────────────────────── */
  if (phase === "saving") {
    return (
      <div className={styles.loadingState}>
        <div className={styles.spinner} />
        <p>Saving your progress…</p>
      </div>
    );
  }

  /* ── RESULT ─────────────────────────────────────────────────────────── */
  if (phase === "result" && result) {
    const passed = result.passed;
    const duration = result.submitted_at
      ? Math.round((new Date(result.submitted_at).getTime() - new Date(result.started_at).getTime()) / 1000)
      : null;

    return (
      <div className={styles.result}>
        <div className={`${styles.scoreBadge} ${passed ? styles.pass : styles.fail}`}>
          <span className={styles.scoreValue}>{result.score_percent}%</span>
          <span className={styles.scoreLabel}>{passed ? "Passed 🎉" : "Try Again"}</span>
          {duration && (
            <span className={styles.durationLabel}>
              ⏱ Completed in {Math.floor(duration / 60)}m {duration % 60}s
            </span>
          )}
        </div>

        <div className={styles.reviewList}>
          <h3 className={styles.reviewTitle}>Answer Review</h3>
          {result.questions.map((q, qi) => {
            const userAns    = new Set(result.answers[q.id] || []);
            const correctIds = new Set(q.choices.filter(c => c.is_correct).map(c => c.id));
            const skipped    = userAns.size === 0;
            const isCorrect  = !skipped && Array.from(userAns).every(id => correctIds.has(id)) && userAns.size === correctIds.size;

            return (
              <div key={q.id} className={`${styles.reviewItem} ${skipped ? styles.reviewSkipped : isCorrect ? styles.reviewCorrect : styles.reviewWrong}`}>
                <div className={styles.reviewQ}>
                  <span className={styles.reviewNum}>{qi + 1}.</span>
                  <span>{q.text}</span>
                  <span className={styles.reviewIcon}>{skipped ? "—" : isCorrect ? "✓" : "✗"}</span>
                </div>
                <div className={styles.reviewChoices}>
                  {q.choices.map(c => (
                    <div key={c.id} className={`${styles.reviewChoice} ${c.is_correct ? styles.correctChoice : ""} ${userAns.has(c.id) && !c.is_correct ? styles.wrongChoice : ""}`}>
                      {c.is_correct ? "✓ " : userAns.has(c.id) ? "✗ " : "  "}{c.text}
                    </div>
                  ))}
                </div>
                {skipped && <div className={styles.skippedNote}>Not attempted</div>}
                {q.explanation && <div className={styles.explanation}>💡 {q.explanation}</div>}
              </div>
            );
          })}
        </div>

        <div className={styles.resultActions}>
          <button className={styles.retryBtn} onClick={() => { setAnswers({}); setCurrentIdx(0); setResult(null); setAttemptId(null); setPhase("intro"); }}>
            Retry Quiz
          </button>
        </div>
      </div>
    );
  }

  /* ── PLAYING ─────────────────────────────────────────────────────────── */
  if (!question) return null;

  const isMulti       = question.question_type === "multi";
  const selectedCh    = answers[question.id] || [];
  const progressPct   = ((currentIdx + 1) / totalQ) * 100;
  const isLastQ       = currentIdx === totalQ - 1;

  return (
    <div className={styles.player}>
      {/* Header */}
      <div className={styles.playerHeader}>
        <span className={styles.questionCounter}>Question {currentIdx + 1} / {totalQ}</span>
        <div className={styles.headerRight}>
          {savedAt && (
            <span className={styles.savedLabel}>
              ✓ Saved {savedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          )}
          {timeLeft !== null && (
            <span className={`${styles.timer} ${timeLeft < 60 ? styles.timerUrgent : ""}`}>
              ⏱ {formatTime(timeLeft)}
            </span>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className={styles.progressBar}>
        <div className={styles.progressFill} style={{ width: `${progressPct}%` }} />
      </div>

      {/* Question */}
      <div className={styles.questionCard}>
        <p className={styles.questionText}>{question.text}</p>
        {isMulti && <p className={styles.multiHint}>Select all that apply</p>}
        <div className={styles.choiceList}>
          {question.choices.map(choice => {
            const selected = selectedCh.includes(choice.id);
            return (
              <button key={choice.id} className={`${styles.choiceBtn} ${selected ? styles.choiceSelected : ""}`} onClick={() => toggleChoice(question.id, choice.id, isMulti)}>
                <span className={styles.choiceMark}>{isMulti ? (selected ? "☑" : "☐") : (selected ? "◉" : "○")}</span>
                <span>{choice.text}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Navigation */}
      <div className={styles.nav}>
        <button className={styles.navBtn} onClick={() => setCurrentIdx(i => Math.max(0, i - 1))} disabled={currentIdx === 0}>
          ← Prev
        </button>

        <span className={styles.answered}>{answeredCount}/{totalQ} answered</span>

        {isLastQ ? (
          <button className={styles.navBtn} style={{ opacity: 0.4 }} disabled>Last question</button>
        ) : (
          <button className={styles.navBtn} onClick={() => setCurrentIdx(i => Math.min(totalQ - 1, i + 1))}>
            Next →
          </button>
        )}
      </div>

      {/* Bottom action bar — always visible */}
      <div className={styles.actionBar}>
        {isAuthenticated && attemptId && (
          <button className={styles.saveExitBtn} onClick={handleSaveExit}>
            💾 Save &amp; Exit
          </button>
        )}
        <button
          className={styles.submitBtn}
          onClick={handleSubmit}
          disabled={!isAuthenticated}
          title={!isAuthenticated ? "Log in to submit" : `Submit with ${answeredCount}/${totalQ} answered`}
        >
          Submit Quiz ✓
        </button>
      </div>

      {!isAuthenticated && (
        <p className={styles.loginNotice} style={{ textAlign: "center", marginTop: "0.75rem" }}>
          <a href="/login">Log in</a> to save progress and submit.
        </p>
      )}
    </div>
  );
}
