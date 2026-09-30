import Link from "next/link";
import styles from "./Navbar.module.css";

export default function Navbar() {
  return (
    <nav className={styles.navbar}>
      <div className={styles.container}>
        <Link href="/" className={styles.logo}>
          <span className={styles.logoIcon}>🎓</span>
          <span className={styles.logoText}>AcademiaHub</span>
        </Link>
        <div className={styles.actions}>
          <Link href="/login" className={styles.loginBtn}>
            Log In
          </Link>
        </div>
      </div>
    </nav>
  );
}
