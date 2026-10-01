"use client";

import { useState } from "react";
import styles from "./CodeLab.module.css";

interface CodeLabProps {
  initialCode: string;
  language: string;
}

export default function CodeLab({ initialCode, language }: CodeLabProps) {
  const [code, setCode] = useState(initialCode);
  const [output, setOutput] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState(false);

  const handleRun = async () => {
    setIsRunning(true);
    setOutput("Running...");
    setError(false);

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiBase}/api/codelab/run/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language, code }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(true);
        setOutput(data.error || "Execution failed.");
      } else {
        if (data.exit_code !== 0) {
          setError(true);
          setOutput(data.stderr || data.stdout || "Error occurred");
        } else {
          setError(false);
          setOutput(data.stdout || "Success (no output)");
        }
      }
    } catch (err) {
      setError(true);
      setOutput("Failed to connect to the runner.");
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.languageBadge}>{language}</span>
        <button
          className={styles.runButton}
          onClick={handleRun}
          disabled={isRunning}
        >
          {isRunning ? "Running..." : "Run Code ▶"}
        </button>
      </div>
      <div className={styles.editorWrapper}>
        <textarea
          className={styles.editor}
          value={code}
          onChange={(e) => setCode(e.target.value)}
          spellCheck={false}
        />
      </div>
      {output && (
        <div className={`${styles.outputWrapper} ${error ? styles.error : ""}`}>
          <div className={styles.outputHeader}>Output</div>
          <pre className={styles.output}>{output}</pre>
        </div>
      )}
    </div>
  );
}
