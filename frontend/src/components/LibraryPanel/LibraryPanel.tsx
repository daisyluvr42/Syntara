/**
 * Literature library browsing panel (left sidebar).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Settings } from "lucide-react";
import {
  deleteLiterature,
  getAllTags,
  getEmbeddingConfig,
  importPdf,
  listEmbeddingBrands,
  listLiterature,
  updateEmbeddingConfig,
  type EmbeddingBrand,
  type EmbeddingConfigData,
  type EmbeddingConfigPayload,
  type LiteratureItem,
} from "../../services/api";
import styles from "./LibraryPanel.module.css";

interface LibraryPanelProps {
  onSelect?: (lit: LiteratureItem) => void;
  onOpenCache?: () => void;
  onOpenDocTrees?: () => void;
}

interface ImportProgress {
  total: number;
  current: number;
  currentFile: string;
  results: { name: string; ok: boolean; title?: string; error?: string; note?: string }[];
}

export default function LibraryPanel({ onSelect, onOpenCache, onOpenDocTrees }: LibraryPanelProps) {
  const [items, setItems] = useState<LiteratureItem[]>([]);
  const [total, setTotal] = useState(0);
  const [tags, setTags] = useState<string[]>([]);
  const [selectedTag, setSelectedTag] = useState<string | undefined>();
  const [importing, setImporting] = useState(false);
  const [progress, setProgress] = useState<ImportProgress | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [showEmbedding, setShowEmbedding] = useState(false);
  const [embeddingBrands, setEmbeddingBrands] = useState<EmbeddingBrand[]>([]);
  const [embeddingConfig, setEmbeddingConfig] = useState<EmbeddingConfigData>({
    mode: "python",
    api_base: "http://localhost:1234/v1",
    api_key_set: false,
    model: "bge-m3",
    cloud_brand: "openai",
  });
  const [embeddingApiKey, setEmbeddingApiKey] = useState("");
  const [embeddingSaving, setEmbeddingSaving] = useState(false);

  const fetchData = useCallback(async () =>
    Promise.all([
      listLiterature(0, 200, selectedTag),
      getAllTags(),
    ]), [selectedTag]);

  const loadData = useCallback(async () => {
    try {
      const [litRes, tagRes] = await fetchData();
      setItems(litRes.items);
      setTotal(litRes.total);
      setTags(tagRes);
    } catch (err) {
      console.error("Failed to load library:", err);
    }
  }, [fetchData]);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      try {
        const [litRes, tagRes] = await fetchData();
        if (cancelled) return;
        setItems(litRes.items);
        setTotal(litRes.total);
        setTags(tagRes);
      } catch (err) {
        if (!cancelled) {
          console.error("Failed to load library:", err);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [fetchData]);

  useEffect(() => {
    const hasProcessing = items.some((item) => item.processing_status === "processing");
    if (!hasProcessing) return;

    const timer = window.setInterval(() => {
      void loadData();
    }, 3000);

    return () => window.clearInterval(timer);
  }, [items, loadData]);

  useEffect(() => {
    getEmbeddingConfig().then(setEmbeddingConfig).catch(() => {});
    listEmbeddingBrands().then(setEmbeddingBrands).catch(() => {});
  }, []);

  const handleSaveEmbedding = async () => {
    setEmbeddingSaving(true);
    try {
      const payload: EmbeddingConfigPayload = { mode: embeddingConfig.mode };
      if (embeddingConfig.mode === "local") {
        payload.api_base = embeddingConfig.api_base;
        payload.model = embeddingConfig.model;
      } else if (embeddingConfig.mode === "cloud") {
        payload.cloud_brand = embeddingConfig.cloud_brand;
        if (embeddingApiKey) payload.api_key = embeddingApiKey;
      }
      await updateEmbeddingConfig(payload);
      const updated = await getEmbeddingConfig();
      setEmbeddingConfig(updated);
      setEmbeddingApiKey("");
    } catch (err) {
      console.error(err);
    } finally {
      setEmbeddingSaving(false);
    }
  };

  const importFiles = async (files: File[]) => {
    if (files.length === 0) return;

    // Warn about large files
    const largeFiles = files.filter((f) => f.size > 200 * 1024 * 1024);
    if (largeFiles.length > 0) {
      const names = largeFiles.map((f) => `${f.name} (${Math.round(f.size / 1024 / 1024)}MB)`).join(", ");
      if (!confirm(`以下文件较大，处理可能较慢：\n${names}\n\n建议 PDF 不超过 200MB 以获得最佳体验。是否继续？`)) {
        return;
      }
    }

    setImporting(true);
    const prog: ImportProgress = { total: files.length, current: 0, currentFile: "", results: [] };
    setProgress({ ...prog });

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      prog.current = i + 1;
      prog.currentFile = file.name;
      setProgress({ ...prog, results: [...prog.results] });

      try {
        const res = await importPdf(file);
        prog.results.push({
          name: file.name,
          ok: true,
          title: res.title,
          note: res.message,
        });
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        prog.results.push({ name: file.name, ok: false, error: msg });
        console.error(`Failed to import ${file.name}:`, err);
      }
    }

    setProgress({ ...prog, results: [...prog.results] });
    setImporting(false);
    loadData();

    // Auto-dismiss progress after 5s if all succeeded
    const allOk = prog.results.every((r) => r.ok);
    if (allOk) {
      setTimeout(() => setProgress(null), 5000);
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    await importFiles(Array.from(files));
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files).filter((f) =>
      f.name.toLowerCase().endsWith(".pdf")
    );
    await importFiles(files);
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Delete this literature?")) return;
    await deleteLiterature(id);
    loadData();
  };

  const formatAuthors = (authors: { family: string; given: string }[]) => {
    if (!authors || authors.length === 0) return "";
    if (authors.length <= 2) return authors.map((a) => a.family).join(", ");
    return `${authors[0].family} et al.`;
  };

  const getStatusMeta = (lit: LiteratureItem) => {
    if (lit.processing_status === "failed") {
      return {
        label: "Failed",
        className: styles.statusFailed,
        title: lit.processing_error || "Import failed during extraction or indexing.",
      };
    }
    if (lit.processing_status === "processing") {
      return {
        label: "Processing",
        className: styles.statusProcessing,
        title: "Metadata is saved. Full-text extraction and indexing are still running.",
      };
    }
    if ((lit.full_text_length ?? 0) > 0 && lit.search_ready_fts && lit.search_ready_vector) {
      return {
        label: "Ready",
        className: styles.statusReady,
        title: "Full text, keyword search, and semantic search are ready.",
      };
    }
    if ((lit.full_text_length ?? 0) > 0 && lit.search_ready_fts) {
      return {
        label: "Keyword Only",
        className: styles.statusPartial,
        title: "Full text is available and keyword search works, but semantic search is not ready.",
      };
    }
    return {
      label: "Metadata Only",
      className: styles.statusMetadata,
      title: "Only metadata is available right now. Full-text evidence is not searchable yet.",
    };
  };

  return (
    <div
      className={styles.panel}
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
    >
      <div className={styles.header}>
        <h3>Literature Library</h3>
        <span className={styles.count}>{total}</span>
      </div>

      <div className={styles.actions}>
        <button
          className={styles.importBtn}
          onClick={() => fileInputRef.current?.click()}
          disabled={importing}
        >
          {importing
            ? `Importing ${progress?.current ?? 0}/${progress?.total ?? 0}...`
            : "+ Import PDF"}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          multiple
          style={{ display: "none" }}
          onChange={handleImport}
        />
        <div className={styles.manageRow}>
          <button className={styles.manageBtn} onClick={onOpenCache} title="Manage extraction cache">
            Cache
          </button>
          <button className={styles.manageBtn} onClick={onOpenDocTrees} title="Manage document trees (RAG)">
            Trees
          </button>
          <button
            className={`${styles.settingsBtn} ${showEmbedding ? styles.manageBtnActive : ""}`}
            onClick={() => setShowEmbedding((p) => !p)}
            title="Embedding settings"
          >
            <Settings size={14} />
          </button>
        </div>
      </div>

      {showEmbedding && (
        <div className={styles.embeddingPanel}>
          <label className={styles.embField}>
            <span className={styles.embLabel}>Mode</span>
            <select
              value={embeddingConfig.mode}
              onChange={(e) => setEmbeddingConfig({ ...embeddingConfig, mode: e.target.value })}
              className={styles.embSelect}
            >
              <option value="python">Python (no model)</option>
              <option value="local">Local Model</option>
              <option value="cloud">Cloud Provider</option>
            </select>
          </label>
          {embeddingConfig.mode === "python" && (
            <div className={styles.embHint}>
              Built-in character n-gram hashing. No external model required.
            </div>
          )}
          {embeddingConfig.mode === "local" && (
            <>
              <label className={styles.embField}>
                <span className={styles.embLabel}>API Base URL</span>
                <input
                  value={embeddingConfig.api_base}
                  onChange={(e) => setEmbeddingConfig({ ...embeddingConfig, api_base: e.target.value })}
                  placeholder="http://localhost:1234/v1"
                  className={styles.embInput}
                />
              </label>
              <label className={styles.embField}>
                <span className={styles.embLabel}>Model</span>
                <input
                  value={embeddingConfig.model}
                  onChange={(e) => setEmbeddingConfig({ ...embeddingConfig, model: e.target.value })}
                  placeholder="bge-m3"
                  className={styles.embInput}
                />
              </label>
            </>
          )}
          {embeddingConfig.mode === "cloud" && (
            <>
              <label className={styles.embField}>
                <span className={styles.embLabel}>Provider</span>
                <select
                  value={embeddingConfig.cloud_brand}
                  onChange={(e) => setEmbeddingConfig({ ...embeddingConfig, cloud_brand: e.target.value })}
                  className={styles.embSelect}
                >
                  {embeddingBrands.map((b) => (
                    <option key={b.key} value={b.key}>{b.display_name}</option>
                  ))}
                </select>
              </label>
              <div className={styles.embHint}>
                Model: {embeddingBrands.find((b) => b.key === embeddingConfig.cloud_brand)?.default_model ?? "—"}
              </div>
              <label className={styles.embField}>
                <span className={styles.embLabel}>API Key</span>
                <input
                  type="password"
                  value={embeddingApiKey}
                  onChange={(e) => setEmbeddingApiKey(e.target.value)}
                  placeholder={embeddingConfig.api_key_set ? "Key set (blank = keep)" : "Enter API key"}
                  className={styles.embInput}
                />
              </label>
            </>
          )}
          <button
            onClick={handleSaveEmbedding}
            disabled={embeddingSaving}
            className={styles.embSaveBtn}
          >
            {embeddingSaving ? "Saving..." : "Save"}
          </button>
        </div>
      )}

      {progress && (
        <div className={styles.progressPanel}>
          {importing && progress.currentFile && (
            <div className={styles.progressCurrent}>
              <div className={styles.progressBar}>
                <div
                  className={styles.progressFill}
                  style={{ width: `${(progress.current / progress.total) * 100}%` }}
                />
              </div>
              <div className={styles.progressFile} title={progress.currentFile}>
                {progress.currentFile}
              </div>
            </div>
          )}
          {progress.results.length > 0 && (
            <div className={styles.progressResults}>
              {progress.results.map((r, i) => (
                <div key={i} className={r.ok ? styles.resultOk : styles.resultErr}>
                  <span className={styles.resultIcon}>{r.ok ? "\u2713" : "\u2717"}</span>
                  <span className={styles.resultText} title={r.ok ? r.note || r.title : r.error}>
                    {r.ok ? `${r.title || r.name} · ${r.note || "Imported"}` : `${r.name}: ${r.error}`}
                  </span>
                </div>
              ))}
            </div>
          )}
          {!importing && (
            <button className={styles.dismissBtn} onClick={() => setProgress(null)}>
              Dismiss
            </button>
          )}
        </div>
      )}

      {tags.length > 0 && (
        <div className={styles.tagFilter}>
          <button
            className={`${styles.tagBtn} ${!selectedTag ? styles.tagActive : ""}`}
            onClick={() => setSelectedTag(undefined)}
          >
            All
          </button>
          {tags.map((tag) => (
            <button
              key={tag}
              className={`${styles.tagBtn} ${selectedTag === tag ? styles.tagActive : ""}`}
              onClick={() => setSelectedTag(tag)}
            >
              {tag}
            </button>
          ))}
        </div>
      )}

      <div className={styles.list}>
        {items.map((lit) => (
          <div key={lit.id} className={styles.item} onClick={() => onSelect?.(lit)}>
            {(() => {
              const status = getStatusMeta(lit);
              return (
                <div className={styles.itemStatusRow}>
                  <span className={`${styles.statusBadge} ${status.className}`} title={status.title}>
                    {status.label}
                  </span>
                </div>
              );
            })()}
            {(formatAuthors(lit.authors) || lit.year) && (
              <div className={styles.itemMeta}>
                {formatAuthors(lit.authors)}
                {lit.year && ` (${lit.year})`}
              </div>
            )}
            <div className={styles.itemTitle}>{lit.title || "Untitled"}</div>
            {lit.journal && (
              <div className={styles.itemJournal}>{lit.journal}</div>
            )}
            <div className={styles.itemFooter}>
              <span className={styles.citeKey}>@{lit.cite_key}</span>
              {lit.metadata_confidence > 0 && (
                <span
                  className={lit.metadata_confidence >= 0.7 ? styles.confHigh : styles.confLow}
                  title={`Metadata confidence: ${Math.round(lit.metadata_confidence * 100)}%`}
                >
                  {Math.round(lit.metadata_confidence * 100)}%
                </span>
              )}
              {lit.manually_verified && (
                <span className={styles.verified} title="Manually verified">&#10003;</span>
              )}
              <button
                className={styles.deleteBtn}
                onClick={(e) => handleDelete(lit.id, e)}
                title="Delete"
              >
                &times;
              </button>
            </div>
          </div>
        ))}

        {items.length === 0 && !importing && (
          <div className={styles.empty}>
            <p>No literature yet</p>
            <p className={styles.hint}>Drop PDF files here or click Import</p>
          </div>
        )}
      </div>
    </div>
  );
}
