import { cookies } from "next/headers";
import CodeLab from "@/components/CodeLab";
import Link from "next/link";
import styles from "./codelab.module.css";

const STARTER_CODE: Record<string, string> = {
  python: `# Python Playground 🐍
# Try editing and running this code!

def greet(name: str) -> str:
    return f"Hello, {name}! 👋"

print(greet("AcademiaHub"))

# Fibonacci example
def fib(n):
    a, b = 0, 1
    for _ in range(n):
        print(a, end=" ")
        a, b = b, a + b
    print()

fib(10)
`,
  javascript: `// JavaScript Playground 🟨
// Try editing and running this code!

function greet(name) {
  return \`Hello, \${name}! 👋\`;
}

console.log(greet("AcademiaHub"));

// Fibonacci example
function fib(n) {
  let a = 0, b = 1;
  const result = [];
  for (let i = 0; i < n; i++) {
    result.push(a);
    [a, b] = [b, a + b];
  }
  return result;
}

console.log(fib(10).join(" "));
`,
};

export default async function CodeLabPage({
  searchParams,
}: {
  searchParams: Promise<{ lang?: string }>;
}) {
  const { lang: langParam } = await searchParams;
  const lang = langParam === "javascript" ? "javascript" : "python";
  const token = (await cookies()).get("access_token")?.value;

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        {/* Header */}
        <header className={styles.header}>
          <div className={styles.titleRow}>
            <span className={styles.icon}>⚡</span>
            <div>
              <h1 className={styles.title}>Code Lab</h1>
              <p className={styles.subtitle}>
                Write, run, and experiment with code directly in your browser.
              </p>
            </div>
          </div>

          <div className={styles.headerRight}>
            {/* Language switcher */}
            <div className={styles.langSwitcher}>
              <a
                href={`/codelab?lang=python`}
                className={`${styles.langTab} ${lang === "python" ? styles.langActive : ""}`}
              >
                🐍 Python
              </a>
              <a
                href={`/codelab?lang=javascript`}
                className={`${styles.langTab} ${lang === "javascript" ? styles.langActive : ""}`}
              >
                🟨 JavaScript
              </a>
            </div>

            {/* My Code shortcut */}
            {token && (
              <Link href="/mycode" className={styles.myCodeLink}>
                📁 My Saved Code
              </Link>
            )}
          </div>
        </header>

        {/* Login notice for guests */}
        {!token && (
          <div className={styles.loginNotice}>
            <a href="/login">Log in</a> to save your code snippets and organise them in folders.
          </div>
        )}

        {/* Editor — token is passed down so the component shows the Save button */}
        <div className={styles.editorWrapper}>
          <CodeLab
            initialCode={STARTER_CODE[lang]}
            language={lang}
            isAuthenticated={Boolean(token)}
          />
        </div>

        {/* Tips */}
        <div className={styles.tips}>
          <h2 className={styles.tipsTitle}>💡 Tips</h2>
          <ul className={styles.tipsList}>
            {lang === "python" ? (
              <>
                <li>Use <code>print()</code> to output values</li>
                <li>Standard library is available — try <code>import math</code> or <code>import json</code></li>
                <li>Code runs in an isolated sandbox — max {5} seconds execution time</li>
              </>
            ) : (
              <>
                <li>Use <code>console.log()</code> to output values</li>
                <li>Modern ES2022 syntax is supported</li>
                <li>Node.js built-ins are available — try <code>require(&apos;fs&apos;)</code></li>
              </>
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}
