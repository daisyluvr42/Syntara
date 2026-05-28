/**
 * Corpus (user knowledge base) management dialog.
 */

import { useEffect, useRef, useState } from "react";
import { deleteCorpus, listCorpus, uploadCorpus, type CorpusItem } from "../../services/api";
import styles from "./CorpusManager.module.css";

interface CorpusManagerProps {
  open: boolean;
  onClose: () => void;
}

export default function CorpusManager({ open, onClose }: CorpusManagerProps) {
  const [items, setItems] = useState<CorpusItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) loadData();
  }, [open]);

  const loadData = async () => {
    try {
      const res = await listCorpus();
      setItems(res.items);
    } catch (err) {
      console.error(err);
    }
  };

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      await uploadCorpus(file, title || file.name, description, tags);
      setTitle("");
      setDescription("");
      setTags("");
      if (fileRef.current) fileRef.current.value = "";
      loadData();
    } catch (err) {
      console.error(err);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this corpus entry?")) return;
    await deleteCorpus(id);
    loadData();
  };

  if (!open) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>Corpus Manager</h2>
          <button className={styles.closeBtn} onClick={onClose}>&times;</button>
        </div>

        <div className={styles.uploadSection}>
          <h3>Import Corpus</h3>
          <input ref={fileRef} type="file" accept=".md,.txt,.pdf" className={styles.fileInput} />
          <input
            type="text"
            placeholder="Title (optional)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className={styles.input}
          />
          <input
            type="text"
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className={styles.input}
          />
          <input
            type="text"
            placeholder="Tags (comma-separated)"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            className={styles.input}
          />
          <button onClick={handleUpload} disabled={uploading} className={styles.uploadBtn}>
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </div>

        <div className={styles.listSection}>
          <h3>Corpus Library ({items.length})</h3>
          {items.map((item) => (
            <div key={item.id} className={styles.item}>
              <div className={styles.itemInfo}>
                <div className={styles.itemTitle}>{item.title}</div>
                {item.description && <div className={styles.itemDesc}>{item.description}</div>}
                <div className={styles.itemMeta}>
                  {item.file_type.toUpperCase()} &middot;{" "}
                  {item.tags?.length > 0 && item.tags.join(", ")}
                </div>
              </div>
              <button className={styles.deleteBtn} onClick={() => handleDelete(item.id)}>
                &times;
              </button>
            </div>
          ))}
          {items.length === 0 && (
            <div className={styles.empty}>No corpus entries. Upload files to enhance AI knowledge.</div>
          )}
        </div>
      </div>
    </div>
  );
}
