import type { ReactNode } from "react";
import styles from "../styles/auth.module.css";

interface AuthLayoutProps {
  children: ReactNode;
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>
        {children}
      </div>
    </div>
  );
}
