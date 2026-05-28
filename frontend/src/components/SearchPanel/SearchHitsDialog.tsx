/**
 * Literature hit details dialog with context viewer and dismiss functionality.
 */

import { useCallback, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import type {
  LiteratureSearchHit,
  LiteratureSearchItem,
  PageContextResponse,
  SearchHighlight,
} from "../../services/api";
import { dismissHit, fetchChunkContext } from "../../services/api";
import styles from "./SearchHitsDialog.module.css";

interface SearchHitsDialogProps {
  item: LiteratureSearchItem | null;
  queryKey: string;
  dismissedKeys: Set<string>;
  onClose: () => void;
  onInsertCitation: (item: LiteratureSearchItem) => void;
  onDismiss: (litId: string, chunkIndex: number) => void;
}

function HighlightedText({ text, highlights }: { text: string; highlights?: SearchHighlight[] }) {
  const normalized = useMemo(() => {
    if (!highlights || highlights.length === 0) return [];
    return [...highlights].sort((a, b) => a.start - b.start);
  }, [highlights]);

  if (normalized.length === 0) {
    return <>{text}</>;
  }

  const parts = [];
  let cursor = 0;
  for (let i = 0; i < normalized.length; i++) {
    const item = normalized[i];
    if (item.start > cursor) {
      parts.push(<span key={`plain-${i}-${cursor}`}>{text.slice(cursor, item.start)}</span>);
    }
    parts.push(
      <mark key={`mark-${i}-${item.start}`} className={styles.highlight}>
        {text.slice(item.start, item.end)}
      </mark>
    );
    cursor = item.end;
  }
  if (cursor < text.length) {
    parts.push(<span key={`plain-tail-${cursor}`}>{text.slice(cursor)}</span>);
  }
  return <>{parts}</>;
}

/** Render a text string, converting double-newlines into visual paragraph breaks. */
function TextWithBreaks({ text, keyPrefix }: { text: string; keyPrefix: string }) {
  const paras = text.split(/\n\n+/);
  return (
    <>
      {paras.map((p, i) => (
        <span key={`${keyPrefix}-${i}`}>
          {i > 0 && <><br /><br /></>}
          {p}
        </span>
      ))}
    </>
  );
}

function PageContextViewer({ ctx }: { ctx: PageContextResponse }) {
  let text = ctx.page_text;
  const hEnd = ctx.highlight_end;

  // Trim references / bibliography section if it appears after the highlighted chunk
  const refMatch = /\n\s*(References|参考文献|Bibliography|REFERENCES|参考文献)\b/.exec(text);
  if (refMatch && refMatch.index >= hEnd) {
    text = text.slice(0, refMatch.index).trimEnd();
  }

  const before = text.slice(0, ctx.highlight_start);
  const target = text.slice(ctx.highlight_start, Math.min(hEnd, text.length));
  const after = text.slice(Math.min(hEnd, text.length));

  return (
    <div className={styles.contextPanel}>
      <div className={styles.contextPageHeader}>
        <span className={styles.hitBadge}>p. {ctx.page_number || "?"}</span>
      </div>
      <div className={styles.contextPageText}>
        <TextWithBreaks text={before} keyPrefix="ctx-before" />
        <mark className={styles.contextHighlight}>
          <TextWithBreaks text={target} keyPrefix="ctx-target" />
        </mark>
        <TextWithBreaks text={after} keyPrefix="ctx-after" />
      </div>
    </div>
  );
}

export default function SearchHitsDialog({
  item,
  queryKey,
  dismissedKeys,
  onClose,
  onInsertCitation,
  onDismiss,
}: SearchHitsDialogProps) {
  const [copiedLabel, setCopiedLabel] = useState("");
  const [expandedContext, setExpandedContext] = useState<Record<number, PageContextResponse | "loading">>(
    {}
  );

  const handleToggleContext = useCallback(
    async (chunkIndex: number, litId: string) => {
      if (expandedContext[chunkIndex]) {
        setExpandedContext((prev) => {
          const next = { ...prev };
          delete next[chunkIndex];
          return next;
        });
        return;
      }
      setExpandedContext((prev) => ({ ...prev, [chunkIndex]: "loading" }));
      try {
        const resp = await fetchChunkContext(litId, chunkIndex);
        setExpandedContext((prev) => ({ ...prev, [chunkIndex]: resp }));
      } catch {
        setExpandedContext((prev) => {
          const next = { ...prev };
          delete next[chunkIndex];
          return next;
        });
      }
    },
    [expandedContext]
  );

  if (!item) return null;

  const visibleHits = item.hits.filter(
    (hit) => !dismissedKeys.has(`${item.id}:${hit.chunk_index}`)
  );

  const formatAuthors = (authors?: { family: string; given: string }[]) => {
    if (!authors || authors.length === 0) return "";
    if (authors.length === 1) return authors[0].family;
    if (authors.length <= 3) return authors.map((author) => author.family).join(", ");
    return `${authors[0].family} et al.`;
  };

  const handleCopy = async (label: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedLabel(label);
      window.setTimeout(() => setCopiedLabel(""), 1200);
    } catch (err) {
      console.error("Copy failed:", err);
    }
  };

  const handleDismiss = async (hit: LiteratureSearchHit) => {
    await dismissHit({ query_key: queryKey, lit_id: item.id, chunk_index: hit.chunk_index });
    onDismiss(item.id, hit.chunk_index);
  };

  const allHitsText = visibleHits
    .map((hit, index) => {
      const meta = [
        hit.heading || "",
        hit.page_number > 0 ? `p. ${hit.page_number}` : "",
      ]
        .filter(Boolean)
        .join(" | ");
      return [`[${index + 1}] ${meta}`.trim(), hit.content].filter(Boolean).join("\n");
    })
    .join("\n\n");

  const dismissedCount = item.hits.length - visibleHits.length;

  return createPortal(
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.dialog} onClick={(event) => event.stopPropagation()}>
        <div className={styles.header}>
          <div>
            <h2>{item.title}</h2>
            <div className={styles.meta}>
              {formatAuthors(item.authors)}
              {item.year ? ` (${item.year})` : ""}
              {item.journal ? ` · ${item.journal}` : ""}
            </div>
          </div>
          <button className={styles.closeBtn} onClick={onClose}>
            &times;
          </button>
        </div>

        <div className={styles.actions}>
          <button className={styles.primaryBtn} onClick={() => onInsertCitation(item)}>
            Insert Citation
          </button>
          <button
            className={styles.secondaryBtn}
            onClick={() => handleCopy("all", allHitsText)}
          >
            {copiedLabel === "all" ? "Copied" : "Copy All Hits"}
          </button>
          {dismissedCount > 0 && (
            <span className={styles.dismissedCount}>
              {dismissedCount} dismissed
            </span>
          )}
        </div>

        <div className={styles.body}>
          {visibleHits.length === 0 && (
            <div className={styles.emptyState}>All hits have been dismissed.</div>
          )}
          {visibleHits.map((hit, index) => {
            const ctx = expandedContext[hit.chunk_index];
            return (
              <div key={`${item.id}-${hit.chunk_index}-${index}`} className={styles.hitCard}>
                <div className={styles.hitHeader}>
                  <div className={styles.hitMeta}>
                    <span className={styles.hitIndex}>#{index + 1}</span>
                    {hit.heading && <span className={styles.hitBadge}>{hit.heading}</span>}
                    {hit.page_number > 0 && (
                      <span className={styles.hitBadge}>p. {hit.page_number}</span>
                    )}
                    {hit.matched_by.map((tag) => (
                      <span key={tag} className={styles.hitTag}>
                        {tag}
                      </span>
                    ))}
                  </div>
                  <div className={styles.hitActions}>
                    <button
                      className={styles.contextBtn}
                      onClick={() => handleToggleContext(hit.chunk_index, item.id)}
                      title={ctx ? "Hide context" : "View context"}
                    >
                      {ctx ? "Hide" : "Context"}
                    </button>
                    <button
                      className={styles.copyBtn}
                      onClick={() => handleCopy(String(index), hit.content)}
                    >
                      {copiedLabel === String(index) ? "Copied" : "Copy"}
                    </button>
                    <button
                      className={styles.dismissBtn}
                      onClick={() => handleDismiss(hit)}
                      title="Dismiss this hit"
                    >
                      &times;
                    </button>
                  </div>
                </div>

                <div className={styles.hitContent}>
                  <HighlightedText text={hit.content} highlights={hit.highlights} />
                </div>

                {ctx === "loading" && (
                  <div className={styles.contextLoading}>Loading context...</div>
                )}
                {ctx && ctx !== "loading" && <PageContextViewer ctx={ctx} />}
              </div>
            );
          })}
        </div>
      </div>
    </div>,
    document.body
  );
}
