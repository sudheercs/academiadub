import styles from "../login/login.module.css";
import Link from "next/link";

export default function RegisterPage() {
  return (
    <div className={styles.container}>
      <div className={`${styles.card} glass`}>
        <div className={styles.header}>
          <h2>Create an Account</h2>
          <p>Join AcademiaHub to unlock premium content.</p>
        </div>
        
        <form className={styles.form}>
          <div className={styles.inputGroup}>
            <label htmlFor="name">Full Name</label>
            <input type="text" id="name" placeholder="John Doe" required />
          </div>

          <div className={styles.inputGroup}>
            <label htmlFor="email">Email address</label>
            <input type="email" id="email" placeholder="student@example.com" required />
          </div>
          
          <div className={styles.inputGroup}>
            <label htmlFor="password">Password</label>
            <input type="password" id="password" placeholder="••••••••" required />
          </div>
          
          <button type="button" className={styles.submitBtn}>
            Sign Up
          </button>
        </form>
        
        <p className={styles.footer}>
          Already have an account? <Link href="/login">Log in</Link>
        </p>
      </div>
    </div>
  );
}
