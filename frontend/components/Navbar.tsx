import Link from "next/link";
import { cookies } from "next/headers";
import styles from "./Navbar.module.css";
import LogoutButton from "./LogoutButton";
import SearchBar from "./SearchBar";

export default async function Navbar() {
  const token = (await cookies()).get("access_token")?.value;

  return (
    <nav className={styles.navbar}>
      <div className={styles.container}>
        <Link href="/" className={styles.logo}>
          <span className={styles.logoIcon}>🎓</span>
          <span className={styles.logoText}>AcademiaHub</span>
        </Link>
        <div className={styles.actions}>
          <SearchBar />
          <Link href="/codelab" className={styles.navLink}>
            Code Lab ⚡
          </Link>
          {token && (
            <Link href="/mycode" className={styles.navLink}>
              My Code 📁
            </Link>
          )}
          {token ? (
            <LogoutButton />
          ) : (
            <Link href="/login" className={styles.loginBtn}>
              Log In
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
