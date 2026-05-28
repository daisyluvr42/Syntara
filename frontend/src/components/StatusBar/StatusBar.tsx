/**
 * Bottom status bar showing statistics.
 */

import { useEffect, useState } from "react";
import { getHealth } from "../../services/api";
import styles from "./StatusBar.module.css";

interface StatusBarProps {
  wordCount: number;
  citationCount: number;
  saving?: boolean;
  dirty?: boolean;
}

export default function StatusBar({ wordCount, citationCount, saving, dirty }: StatusBarProps) {
  const [litCount, setLitCount] = useState(0);
  const [pandoc, setPandoc] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const health = await getHealth();
        setLitCount(health.literature_count);
        setPandoc(health.pandoc_available);
      } catch (err) {
        console.error("Failed to load health status:", err);
      }
    };
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  const saveStatus = saving ? "Saving..." : dirty ? "Unsaved" : "Saved";
  const saveClass = saving ? styles.warn : dirty ? styles.warn : styles.ok;
  const saveDotClass = saving ? styles.dotWarn : dirty ? styles.dotWarn : styles.dotOk;

  return (
    <div className={styles.bar}>
      <span>Literature: {litCount}</span>
      <span>Citations: {citationCount}</span>
      <span>Words: {wordCount.toLocaleString()}</span>
      <span className={styles.spacer} />
      <span className={saveClass}>
        <span className={`${styles.statusDot} ${saveDotClass}`} />
        {saveStatus}
      </span>
      <span className={pandoc ? styles.ok : styles.warn}>
        Pandoc: {pandoc ? "Ready" : "Not installed"}
      </span>
    </div>
  );
}
