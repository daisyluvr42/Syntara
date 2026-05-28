/**
 * Document tree management dialog.
 * Lists, builds, summarizes, and deletes PageIndex-style document trees
 * used for hierarchical RAG navigation.
 */

import { useEffect, useState } from "react";
import {
  buildAllDocTrees,
  buildDocTree,
  deleteDocTree,
  getDocTreeStats,
  listDocTrees,
  summarizeAllDocTrees,
  summarizeDocTree,
  type DocTreeInfo,
  type DocTreeStats,
} from "../../services/api";
import styles from "./DocTreeManager.module.css";

interface DocTreeManagerProps {
  open: boolean;
  onClose: () => void;
}

function formatSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

export default function DocTreeManager({ open, onClose }: DocTreeManagerProps) {
  const [items, setItems] = useState<DocTreeInfo[]>([]);
  const [stats, setStats] = useState<DocTreeStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");

  useEffect(() => {
    if (open) loadData();
  }, [open]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [listRes, statsRes] = await Promise.all([
        listDocTrees(),
        getDocTreeStats(),
      ]);
      setItems(listRes.items);
      setStats(statsRes);
    } catch (err) {
      console.error("Failed to load doc trees:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleBuildAll = async () => {
    setBusy(true);
    setStatusMsg("Building trees for all literature...");
    try {
      const res = await buildAllDocTrees(false);
      setStatusMsg(
        `Built ${res.built} tree(s), skipped ${res.skipped}, errors ${res.errors}`
      );
      loadData();
    } catch (err: unknown) {
      setStatusMsg(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  const handleSummarizeAll = async () => {
    setBusy(true);
    setStatusMsg("Running LLM summarization on all trees...");
    try {
      const res = await summarizeAllDocTrees();
      setStatusMsg(
        `Summarized ${res.summarized} tree(s), errors ${res.errors}`
      );
      loadData();
    } catch (err: unknown) {
      setStatusMsg(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  const handleBuildOne = async (litId: string) => {
    setBusy(true);
    try {
      await buildDocTree(litId, false);
      loadData();
    } catch (err: unknown) {
      setStatusMsg(`Build failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  const handleSummarizeOne = async (litId: string) => {
    setBusy(true);
    setStatusMsg("Summarizing...");
    try {
      await summarizeDocTree(litId);
      setStatusMsg("");
      loadData();
    } catch (err: unknown) {
      setStatusMsg(`Summarize failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (litId: string) => {
    if (!confirm("Delete this document tree?")) return;
    try {
      await deleteDocTree(litId);
      loadData();
    } catch (err: unknown) {
      console.error("Failed to delete doc tree:", err);
    }
  };

  if (!open) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>
            Document Trees
            {stats && (
              <span className={styles.headerStats}>
                {stats.total_trees} tree(s), {stats.total_nodes} nodes,{" "}
                {formatSize(stats.total_size_bytes)}
              </span>
            )}
          </h2>
          <button className={styles.closeBtn} onClick={onClose}>
            &times;
          </button>
        </div>

        {stats && (
          <div className={styles.statsBar}>
            <div className={styles.statItem}>
              Trees: <span className={styles.statValue}>{stats.total_trees}</span>
            </div>
            <div className={styles.statItem}>
              Summarized:{" "}
              <span className={styles.statValue}>{stats.summarized}</span>
            </div>
            <div className={styles.statItem}>
              Pending:{" "}
              <span className={styles.statValue}>{stats.unsummarized}</span>
            </div>
            <div className={styles.statItem}>
              Leaves:{" "}
              <span className={styles.statValue}>{stats.total_leaves}</span>
            </div>
          </div>
        )}

        <div className={styles.actionBar}>
          <button
            className={`${styles.actionBtn} ${styles.actionBtnPrimary}`}
            onClick={handleBuildAll}
            disabled={busy}
          >
            Build All Trees
          </button>
          <button
            className={styles.actionBtn}
            onClick={handleSummarizeAll}
            disabled={busy || (stats?.unsummarized ?? 0) === 0}
          >
            Summarize All
          </button>
        </div>

        {statusMsg && <div className={styles.statusMsg}>{statusMsg}</div>}

        <div className={styles.listSection}>
          {loading && <div className={styles.loading}>Loading...</div>}

          {!loading &&
            items.map((item) => (
              <div key={item.literature_id} className={styles.item}>
                <div className={styles.itemInfo}>
                  <div className={styles.itemTitle}>
                    {item.cite_key && (
                      <span className={styles.itemCiteKey}>
                        @{item.cite_key}
                      </span>
                    )}
                    {item.lit_title || item.title || item.literature_id}
                  </div>
                  <div className={styles.itemMeta}>
                    <span
                      className={`${styles.badge} ${
                        item.summaries_generated
                          ? styles.badgeSummarized
                          : styles.badgePending
                      }`}
                    >
                      {item.summaries_generated ? "Summarized" : "Pending"}
                    </span>
                    <span>{item.node_count} nodes</span>
                    <span>{item.leaf_count} leaves</span>
                    <span>{formatSize(item.size_bytes)}</span>
                  </div>
                </div>
                <div className={styles.itemActions}>
                  {!item.summaries_generated && (
                    <button
                      className={styles.smallBtn}
                      onClick={() => handleSummarizeOne(item.literature_id)}
                      disabled={busy}
                      title="Run LLM summarization"
                    >
                      Summarize
                    </button>
                  )}
                  <button
                    className={styles.smallBtn}
                    onClick={() => handleBuildOne(item.literature_id)}
                    disabled={busy}
                    title="Rebuild tree from structured elements"
                  >
                    Rebuild
                  </button>
                </div>
                <button
                  className={styles.deleteBtn}
                  onClick={() => handleDelete(item.literature_id)}
                  title="Delete tree"
                >
                  &times;
                </button>
              </div>
            ))}

          {!loading && items.length === 0 && (
            <div className={styles.empty}>
              <p>No document trees yet</p>
              <p className={styles.emptyHint}>
                Click "Build All Trees" to generate structure trees from
                imported literature
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
