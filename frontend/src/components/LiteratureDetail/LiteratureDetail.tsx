/**
 * Literature detail/edit dialog.
 * Fetches a full literature record and provides an editable form
 * for all metadata fields, grouped by section.
 */

import { useEffect, useState } from "react";
import {
  getLiterature,
  getLiteraturePreview,
  type LiteraturePreview,
  retryProcessing,
  updateLiterature,
} from "../../services/api";
import styles from "./LiteratureDetail.module.css";

interface LiteratureDetailProps {
  open: boolean;
  onClose: () => void;
  literatureId: string | null;
  onUpdated: () => void;
}

interface FormData {
  title: string;
  authors: string; // one "Given Family" per line
  year: string;
  journal: string;
  doi: string;
  pmid: string;
  abstract: string;
  volume: string;
  issue: string;
  pages: string;
  type: string;
  keywords: string; // comma-separated
  tags: string; // comma-separated
  language: string;
  cite_key: string;
  file_path: string;
  metadata_confidence: number;
  manually_verified: boolean;
}

const LITERATURE_TYPES = [
  { value: "journal_article", label: "Journal Article" },
  { value: "conference", label: "Conference Paper" },
  { value: "book_chapter", label: "Book Chapter" },
  { value: "thesis", label: "Thesis" },
  { value: "report", label: "Report" },
  { value: "other", label: "Other" },
];

function authorsToText(authors: { family: string; given: string }[]): string {
  if (!authors || authors.length === 0) return "";
  return authors.map((a) => `${a.given} ${a.family}`.trim()).join("\n");
}

function textToAuthors(text: string): { family: string; given: string }[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const parts = line.split(/\s+/);
      if (parts.length === 1) {
        return { family: parts[0], given: "" };
      }
      const family = parts[parts.length - 1];
      const given = parts.slice(0, -1).join(" ");
      return { family, given };
    });
}

export default function LiteratureDetail({
  open,
  onClose,
  literatureId,
  onUpdated,
}: LiteratureDetailProps) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(
    null
  );
  const [processingStatus, setProcessingStatus] = useState<string | null>(null);
  const [processingError, setProcessingError] = useState<string | null>(null);
  const [processingProgress, setProcessingProgress] = useState<{
    stage: string;
    current: number;
    total: number;
  } | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [preview, setPreview] = useState<LiteraturePreview | null>(null);
  const [form, setForm] = useState<FormData>({
    title: "",
    authors: "",
    year: "",
    journal: "",
    doi: "",
    pmid: "",
    abstract: "",
    volume: "",
    issue: "",
    pages: "",
    type: "journal_article",
    keywords: "",
    tags: "",
    language: "en",
    cite_key: "",
    file_path: "",
    metadata_confidence: 0,
    manually_verified: false,
  });

  useEffect(() => {
    if (!open || !literatureId) return;
    setFeedback(null);
    setLoading(true);
    setPreview(null);

    getLiterature(literatureId)
      .then((data) => {
        setForm({
          title: data.title || "",
          authors: authorsToText(data.authors || []),
          year: data.year != null ? String(data.year) : "",
          journal: data.journal || "",
          doi: data.doi || "",
          pmid: data.pmid || "",
          abstract: data.abstract || "",
          volume: data.volume || "",
          issue: data.issue || "",
          pages: data.pages || "",
          type: data.type || "journal_article",
          keywords: Array.isArray(data.keywords) ? data.keywords.join(", ") : "",
          tags: Array.isArray(data.tags) ? data.tags.join(", ") : "",
          language: data.language || "en",
          cite_key: data.cite_key || "",
          file_path: data.file_path || "",
          metadata_confidence: data.metadata_confidence ?? 0,
          manually_verified: !!data.manually_verified,
        });
        setProcessingStatus(data.processing_status || null);
        setProcessingError(data.processing_error || null);
        setProcessingProgress(data.processing_progress || null);
        // Fetch preview for ready/partial items
        if (data.processing_status === "ready" || data.processing_status === "partial") {
          getLiteraturePreview(literatureId).then(setPreview).catch(() => {});
        }
      })
      .catch((err) => {
        console.error("Failed to load literature:", err);
        setFeedback({ type: "error", message: "Failed to load literature record." });
      })
      .finally(() => setLoading(false));
  }, [open, literatureId]);

  useEffect(() => {
    if (!open || !literatureId || !processingStatus || processingStatus === "ready" || processingStatus === "failed") return;

    const timer = setInterval(async () => {
      try {
        const data = await getLiterature(literatureId);
        setProcessingStatus(data.processing_status || null);
        setProcessingError(data.processing_error || null);
        setProcessingProgress(data.processing_progress || null);
        if (data.processing_status === "ready" || data.processing_status === "failed") {
          clearInterval(timer);
          onUpdated();
          if (data.processing_status === "ready" && literatureId) {
            getLiteraturePreview(literatureId).then(setPreview).catch(() => {});
          }
        }
      } catch (err) {
        console.error(err);
      }
    }, 2000);

    return () => clearInterval(timer);
  }, [open, literatureId, processingStatus, onUpdated]);

  const handleChange = (field: keyof FormData, value: string | boolean) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleRetry = async () => {
    if (!literatureId) return;
    setRetrying(true);
    setFeedback(null);
    try {
      await retryProcessing(literatureId);
      setProcessingStatus("processing");
      setProcessingError(null);
      setProcessingProgress(null);
      onUpdated(); // refresh list so status tag updates
    } catch (err: unknown) {
      setFeedback({
        type: "error",
        message: err instanceof Error ? err.message : "Retry failed.",
      });
    } finally {
      setRetrying(false);
    }
  };

  const handleSave = async () => {
    if (!literatureId) return;
    setSaving(true);
    setFeedback(null);

    try {
      const payload: Record<string, unknown> = {
        title: form.title,
        authors: textToAuthors(form.authors),
        journal: form.journal || null,
        doi: form.doi || null,
        pmid: form.pmid || null,
        abstract: form.abstract || null,
        volume: form.volume || null,
        issue: form.issue || null,
        pages: form.pages || null,
        year: form.year ? parseInt(form.year, 10) : null,
        type: form.type,
        keywords: form.keywords
          ? form.keywords.split(",").map((k) => k.trim()).filter(Boolean)
          : [],
        tags: form.tags
          ? form.tags.split(",").map((t) => t.trim()).filter(Boolean)
          : [],
        language: form.language,
        manually_verified: form.manually_verified,
      };

      await updateLiterature(literatureId, payload);
      setFeedback({ type: "success", message: "Saved successfully." });
      onUpdated();
    } catch (err: unknown) {
      console.error("Save failed:", err);
      setFeedback({
        type: "error",
        message: err instanceof Error ? err.message : "Failed to save changes.",
      });
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>Literature Details</h2>
          <button className={styles.closeBtn} onClick={onClose}>
            &times;
          </button>
        </div>

        <div className={styles.body}>
          {loading && <div className={styles.loading}>Loading...</div>}

          {!loading && (
            <>
              {feedback && (
                <div
                  className={
                    feedback.type === "success" ? styles.feedbackSuccess : styles.feedbackError
                  }
                >
                  {feedback.message}
                </div>
              )}

              {processingStatus && processingStatus !== "ready" && (
                <div className={`${styles.processingSection} ${processingStatus === "failed" ? styles.processingSectionFailed : ""}`}>
                  <div className={styles.processingHeader}>
                    <span className={styles.processingLabel}>
                      {processingStatus === "failed" ? "Processing Failed" : "Processing..."}
                    </span>
                    {processingProgress && processingStatus !== "failed" && (
                      <span className={styles.processingStage}>
                        {processingProgress.stage === "text_extract" && "Extracting text..."}
                        {processingProgress.stage === "ocr" && `OCR: page ${processingProgress.current}/${processingProgress.total}`}
                        {processingProgress.stage === "structure_extract" && "Structural analysis..."}
                        {processingProgress.stage === "indexing" && "Building search index..."}
                      </span>
                    )}
                  </div>
                  {processingProgress && processingStatus !== "failed" && (
                    <div className={styles.progressBar}>
                      <div
                        className={styles.progressFill}
                        style={{
                          width: `${processingProgress.total > 0 ? (processingProgress.current / processingProgress.total) * 100 : 0}%`,
                        }}
                      />
                    </div>
                  )}
                  {processingStatus === "failed" && (
                    <>
                      {processingError && (
                        <div className={styles.processingErrorMsg}>{processingError}</div>
                      )}
                      <button
                        className={styles.retryBtn}
                        onClick={handleRetry}
                        disabled={retrying}
                      >
                        {retrying ? "Retrying..." : "Retry Processing"}
                      </button>
                    </>
                  )}
                  {processingStatus === "partial" && (
                    <div className={styles.processingHint}>
                      Keyword search is available. Semantic search will be ready after processing completes.
                    </div>
                  )}
                </div>
              )}

              {/* -- Document Preview -- */}
              {preview && (
                <>
                  <div className={styles.sectionHeader}>Document Preview</div>

                  {/* Stats bar */}
                  <div className={styles.previewStats}>
                    {preview.page_count > 0 && (
                      <span className={styles.statItem}>
                        <span className={styles.statValue}>{preview.page_count}</span> pages
                      </span>
                    )}
                    <span className={styles.statItem}>
                      <span className={styles.statValue}>
                        {preview.char_count > 10000
                          ? `${(preview.char_count / 1000).toFixed(1)}k`
                          : preview.char_count.toLocaleString()}
                      </span>{" "}
                      chars
                    </span>
                    <span className={styles.statItem}>
                      <span className={styles.statValue}>
                        {preview.word_count > 10000
                          ? `${(preview.word_count / 1000).toFixed(1)}k`
                          : preview.word_count.toLocaleString()}
                      </span>{" "}
                      words
                    </span>
                    {preview.file_size > 0 && (
                      <span className={styles.statItem}>
                        <span className={styles.statValue}>
                          {preview.file_size > 1024 * 1024
                            ? `${(preview.file_size / 1024 / 1024).toFixed(1)} MB`
                            : `${(preview.file_size / 1024).toFixed(0)} KB`}
                        </span>
                      </span>
                    )}
                    <span className={styles.statItem}>
                      FTS{" "}
                      <span
                        className={
                          preview.search_ready_fts ? styles.statusDotOn : styles.statusDotOff
                        }
                      />
                    </span>
                    <span className={styles.statItem}>
                      Vector{" "}
                      <span
                        className={
                          preview.search_ready_vector ? styles.statusDotOn : styles.statusDotOff
                        }
                      />
                    </span>
                  </div>

                </>
              )}

              {/* -- Basic Info -- */}
              <div className={styles.sectionHeader}>Basic Info</div>

              <div className={styles.field}>
                <span className={styles.fieldLabel}>Title</span>
                <input
                  className={styles.fieldInput}
                  value={form.title}
                  onChange={(e) => handleChange("title", e.target.value)}
                  placeholder="Title"
                />
              </div>

              <div className={styles.field}>
                <span className={styles.fieldLabel}>
                  Authors <span className={styles.fieldHint}>(one per line: Given Family)</span>
                </span>
                <textarea
                  className={styles.fieldInput}
                  rows={3}
                  value={form.authors}
                  onChange={(e) => handleChange("authors", e.target.value)}
                  placeholder={"John Smith\nJane Doe"}
                />
              </div>

              <div className={styles.row2}>
                <div className={styles.field}>
                  <span className={styles.fieldLabel}>Year</span>
                  <input
                    className={styles.fieldInput}
                    type="number"
                    value={form.year}
                    onChange={(e) => handleChange("year", e.target.value)}
                    placeholder="2024"
                  />
                </div>
                <div className={styles.field}>
                  <span className={styles.fieldLabel}>Language</span>
                  <select
                    className={styles.fieldInput}
                    value={form.language}
                    onChange={(e) => handleChange("language", e.target.value)}
                  >
                    <option value="en">English</option>
                    <option value="zh">Chinese</option>
                  </select>
                </div>
              </div>

              <div className={styles.field}>
                <span className={styles.fieldLabel}>Abstract</span>
                <textarea
                  className={styles.fieldInput}
                  rows={4}
                  value={form.abstract}
                  onChange={(e) => handleChange("abstract", e.target.value)}
                  placeholder="Abstract"
                />
              </div>

              {/* -- Publication -- */}
              <div className={styles.sectionHeader}>Publication</div>

              <div className={styles.field}>
                <span className={styles.fieldLabel}>Journal</span>
                <input
                  className={styles.fieldInput}
                  value={form.journal}
                  onChange={(e) => handleChange("journal", e.target.value)}
                  placeholder="Journal name"
                />
              </div>

              <div className={styles.row3}>
                <div className={styles.field}>
                  <span className={styles.fieldLabel}>Volume</span>
                  <input
                    className={styles.fieldInput}
                    value={form.volume}
                    onChange={(e) => handleChange("volume", e.target.value)}
                    placeholder="Vol"
                  />
                </div>
                <div className={styles.field}>
                  <span className={styles.fieldLabel}>Issue</span>
                  <input
                    className={styles.fieldInput}
                    value={form.issue}
                    onChange={(e) => handleChange("issue", e.target.value)}
                    placeholder="Issue"
                  />
                </div>
                <div className={styles.field}>
                  <span className={styles.fieldLabel}>Pages</span>
                  <input
                    className={styles.fieldInput}
                    value={form.pages}
                    onChange={(e) => handleChange("pages", e.target.value)}
                    placeholder="e.g. 1-15"
                  />
                </div>
              </div>

              {/* -- Identifiers -- */}
              <div className={styles.sectionHeader}>Identifiers</div>

              <div className={styles.row2}>
                <div className={styles.field}>
                  <span className={styles.fieldLabel}>DOI</span>
                  <input
                    className={styles.fieldInput}
                    value={form.doi}
                    onChange={(e) => handleChange("doi", e.target.value)}
                    placeholder="10.xxxx/xxxxx"
                  />
                </div>
                <div className={styles.field}>
                  <span className={styles.fieldLabel}>PMID</span>
                  <input
                    className={styles.fieldInput}
                    value={form.pmid}
                    onChange={(e) => handleChange("pmid", e.target.value)}
                    placeholder="PubMed ID"
                  />
                </div>
              </div>

              {/* -- Classification -- */}
              <div className={styles.sectionHeader}>Classification</div>

              <div className={styles.field}>
                <span className={styles.fieldLabel}>Type</span>
                <select
                  className={styles.fieldInput}
                  value={form.type}
                  onChange={(e) => handleChange("type", e.target.value)}
                >
                  {LITERATURE_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className={styles.field}>
                <span className={styles.fieldLabel}>
                  Keywords <span className={styles.fieldHint}>(comma-separated)</span>
                </span>
                <input
                  className={styles.fieldInput}
                  value={form.keywords}
                  onChange={(e) => handleChange("keywords", e.target.value)}
                  placeholder="keyword1, keyword2"
                />
              </div>

              <div className={styles.field}>
                <span className={styles.fieldLabel}>
                  Tags <span className={styles.fieldHint}>(comma-separated)</span>
                </span>
                <input
                  className={styles.fieldInput}
                  value={form.tags}
                  onChange={(e) => handleChange("tags", e.target.value)}
                  placeholder="tag1, tag2"
                />
              </div>

              <div className={styles.checkboxField}>
                <input
                  type="checkbox"
                  id="manuallyVerified"
                  checked={form.manually_verified}
                  onChange={(e) => handleChange("manually_verified", e.target.checked)}
                />
                <label htmlFor="manuallyVerified">Manually Verified</label>
              </div>

              {/* -- File Info -- */}
              <div className={styles.sectionHeader}>File Info</div>

              <div className={styles.row2}>
                <div className={styles.field}>
                  <span className={styles.fieldLabel}>
                    Cite Key <span className={styles.fieldHint}>(auto-generated)</span>
                  </span>
                  <input
                    className={styles.fieldInput}
                    value={form.cite_key}
                    readOnly
                  />
                </div>
                <div className={styles.field}>
                  <span className={styles.fieldLabel}>Metadata Confidence</span>
                  <input
                    className={styles.fieldInput}
                    value={`${Math.round(form.metadata_confidence * 100)}%`}
                    readOnly
                  />
                </div>
              </div>

              {form.file_path && (
                <div className={styles.field}>
                  <span className={styles.fieldLabel}>File Path</span>
                  <input className={styles.fieldInput} value={form.file_path} readOnly />
                </div>
              )}

              {/* -- Outline & Text Preview (at bottom) -- */}
              {preview && preview.outline.length > 0 && (
                <>
                  <div className={styles.sectionHeader}>Outline</div>
                  <div className={styles.outlineBox}>
                    <div className={styles.outlineList}>
                      {preview.outline.map((item, i) => (
                        <div
                          key={i}
                          className={styles.outlineItem}
                          style={{ paddingLeft: `${(item.depth - 1) * 16}px` }}
                        >
                          <span className={styles.outlineText}>{item.title}</span>
                          {item.page ? (
                            <span className={styles.outlinePage}>p.{item.page}</span>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {preview && preview.snippet && (
                <>
                  <div className={styles.sectionHeader}>Text Preview</div>
                  <div className={styles.snippetBox}>
                    <div className={styles.snippetText}>{preview.snippet}</div>
                  </div>
                </>
              )}
            </>
          )}
        </div>

        {!loading && (
          <div className={styles.footer}>
            <div className={styles.spacer} />
            <button className={styles.cancelBtn} onClick={onClose}>
              Cancel
            </button>
            <button className={styles.saveBtn} onClick={handleSave} disabled={saving}>
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
