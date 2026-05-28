/**
 * Extraction cache management dialog.
 * Lists, inspects, and deletes cached PDF parsing results (OCR / ODL).
 */

import { useEffect, useState } from "react";
import {
  clearExtractCache,
  deleteExtractCache,
  getExtractCacheStats,
  listExtractCache,
  type CacheItem,
  type CacheStats,
} from "../../services/api";
import styles from "./CacheManager.module.css";

interface CacheManagerProps {
  open: boolean;
  onClose: () => void;
}

function formatSize(kb: number): string {
  if (kb >= 1024) {
    return `${(kb / 1024).toFixed(1)} MB`;
  }
  return `${kb.toFixed(1)} KB`;
}

function sourceBadgeClass(source: string): string {
  switch (source) {
    case "paddleocr":
      return styles.badgeOcr;
    case "odl":
      return styles.badgeOdl;
    default:
      return styles.badgeUnknown;
  }
}

function sourceBadgeLabel(source: string): string {
  switch (source) {
    case "paddleocr":
      return "OCR";
    case "odl":
      return "ODL";
    default:
      return source.toUpperCase();
  }
}

export default function CacheManager({ open, onClose }: CacheManagerProps) {
  const [items, setItems] = useState<CacheItem[]>([]);
  const [stats, setStats] = useState<CacheStats | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) loadData();
  }, [open]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [listRes, statsRes] = await Promise.all([
        listExtractCache(),
        getExtractCacheStats(),
      ]);
      setItems(listRes.items);
      setStats(statsRes);
    } catch (err) {
      console.error("Failed to load extract cache:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (fileHash: string) => {
    if (!confirm("Delete this cache entry?")) return;
    try {
      await deleteExtractCache(fileHash);
      loadData();
    } catch (err) {
      console.error("Failed to delete cache entry:", err);
    }
  };

  const handleClearAll = async () => {
    if (!confirm("Clear ALL cached extractions? This cannot be undone.")) return;
    try {
      await clearExtractCache();
      loadData();
    } catch (err) {
      console.error("Failed to clear cache:", err);
    }
  };

  if (!open) return null;

  const statsText = stats
    ? `${stats.total_items} item${stats.total_items !== 1 ? "s" : ""}, ${formatSize(stats.total_size_kb)} total`
    : "";

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>
            Extract Cache
            {statsText && <span className={styles.headerStats}>{statsText}</span>}
          </h2>
          <button className={styles.closeBtn} onClick={onClose}>
            &times;
          </button>
        </div>

        <div className={styles.listSection}>
          {loading && <div className={styles.loading}>Loading...</div>}

          {!loading &&
            items.map((item) => (
              <div key={item.file_hash} className={styles.item}>
                <div className={styles.itemInfo}>
                  <div className={styles.itemTitle}>
                    {item.title || item.file_name || item.file_hash}
                  </div>
                  <div className={styles.itemMeta}>
                    <span className={`${styles.badge} ${sourceBadgeClass(item.source_type)}`}>
                      {sourceBadgeLabel(item.source_type)}
                    </span>
                    <span>{item.element_count} elements</span>
                    <span>{formatSize(item.file_size_kb)}</span>
                    <span>{new Date(item.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <button
                  className={styles.deleteBtn}
                  onClick={() => handleDelete(item.file_hash)}
                  title="Delete cache entry"
                >
                  &times;
                </button>
              </div>
            ))}

          {!loading && items.length === 0 && (
            <div className={styles.empty}>No cached extractions yet.</div>
          )}
        </div>

        {items.length > 0 && (
          <div className={styles.footer}>
            <button className={styles.clearBtn} onClick={handleClearAll}>
              Clear All
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
