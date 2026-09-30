import styles from "./login.module.css";
import Link from "next/link";

export default function LoginPage() {
  return (
    <div className={styles.container}>
      <div className={`${styles.card} glass`}>
        <div className={styles.header}>
          <h2>Welcome Back</h2>
          <p>Sign in to continue your learning journey.</p>
        </div>
        
        <form className={styles.form}>
          <div className={styles.inputGroup}>
            <label htmlFor="email">Email address</label>
            <input type="email" id="email" placeholder="student@example.com" required />
          </div>
          
          <div className={styles.inputGroup}>
            <label htmlFor="password">Password</label>
            <input type="password" id="password" placeholder="••••••••" required />
          </div>
          
          <button type="button" className={styles.submitBtn}>
            Log In
          </button>
        </form>
        
        <p className={styles.footer}>
          Don't have an account? <Link href="/register">Sign up</Link>
        </p>
      </div>
    </div>
  );
}
