/**
 * Open document dialog: lists saved documents for selection.
 */

import { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { listDocuments, deleteDocument, type DocumentItem } from "../../services/api";
import styles from "./OpenDialog.module.css";

interface OpenDialogProps {
  open: boolean;
  onClose: () => void;
  onOpen: (doc: DocumentItem) => void;
  currentDocId: string | null;
}

export default function OpenDialog({ open, onClose, onOpen, currentDocId }: OpenDialogProps) {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    listDocuments()
      .then((res) => setDocs(res.items))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [open]);

  if (!open) return null;

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm("Delete this document?")) return;
    try {
      await deleteDocument(id);
      setDocs((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>Open Document</h2>
          <button className={styles.closeBtn} onClick={onClose}>&times;</button>
        </div>

        <div className={styles.body}>
          {loading ? (
            <div className={styles.empty}>Loading...</div>
          ) : docs.length === 0 ? (
            <div className={styles.empty}>No documents found.</div>
          ) : (
            <div className={styles.list}>
              {docs.map((doc) => (
                <div
                  key={doc.id}
                  className={`${styles.item} ${doc.id === currentDocId ? styles.itemCurrent : ""}`}
                  onClick={() => { onOpen(doc); onClose(); }}
                >
                  <div className={styles.itemInfo}>
                    <span className={styles.itemTitle}>{doc.title || "Untitled"}</span>
                    <span className={styles.itemDate}>{formatDate(doc.updated_at)}</span>
                  </div>
                  {doc.id !== currentDocId && (
                    <button
                      className={styles.deleteBtn}
                      onClick={(e) => handleDelete(e, doc.id)}
                      title="Delete document"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
