/**
 * Grouped literature search sidebar.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import type { LiteratureSearchItem, LiteratureSearchQuery, SearchHighlight } from "../../services/api";
import { getDismissedHits } from "../../services/api";
import AutocompleteInput from "./AutocompleteInput";
import SearchHitsDialog from "./SearchHitsDialog";
import styles from "./SearchPanel.module.css";

interface SearchPanelProps {
  zhQuery: string;
  onZhQueryChange: (q: string) => void;
  enQuery: string;
  onEnQueryChange: (q: string) => void;
  results: LiteratureSearchItem[];
  warnings: string[];
  usedQueries: LiteratureSearchQuery[];
  semanticAvailable: boolean;
  loading: boolean;
  onSearch: () => void;
  selectedIds: Set<string>;
  onToggleSelect: (item: LiteratureSearchItem) => void;
  onInsertCitations: () => void;
  onInsertSingleCitation: (item: LiteratureSearchItem) => void;
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

/** Build a stable query key from the search queries for dismissed hits tracking. */
function buildQueryKey(zhQuery: string, enQuery: string): string {
  const parts = [];
  if (zhQuery.trim()) parts.push(`zh:${zhQuery.trim()}`);
  if (enQuery.trim()) parts.push(`en:${enQuery.trim()}`);
  return parts.join("|");
}

export default function SearchPanel({
  zhQuery,
  onZhQueryChange,
  enQuery,
  onEnQueryChange,
  results,
  warnings,
  usedQueries,
  semanticAvailable,
  loading,
  onSearch,
  selectedIds,
  onToggleSelect,
  onInsertCitations,
  onInsertSingleCitation,
}: SearchPanelProps) {
  const [activeItem, setActiveItem] = useState<LiteratureSearchItem | null>(null);
  const [dismissedKeys, setDismissedKeys] = useState<Set<string>>(new Set());
  const hasSelected = selectedIds.size > 0;
  const hasQuery = zhQuery.trim() || enQuery.trim();
  const aiQueries = usedQueries.filter((item) => item.source === "ai");

  const queryKey = useMemo(() => buildQueryKey(zhQuery, enQuery), [zhQuery, enQuery]);

  // Load dismissed hits when results change
  useEffect(() => {
    if (!queryKey || results.length === 0) {
      setDismissedKeys(new Set());
      return;
    }
    getDismissedHits(queryKey)
      .then((resp) => setDismissedKeys(new Set(resp.dismissed)))
      .catch(() => setDismissedKeys(new Set()));
  }, [queryKey, results]);

  const handleDismiss = useCallback(
    (litId: string, chunkIndex: number) => {
      setDismissedKeys((prev) => new Set(prev).add(`${litId}:${chunkIndex}`));
    },
    []
  );

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") onSearch();
  };

  const formatAuthors = (authors?: { family: string; given: string }[]) => {
    if (!authors || authors.length === 0) return "";
    if (authors.length === 1) return authors[0].family;
    if (authors.length <= 3) return authors.map((author) => author.family).join(", ");
    return `${authors[0].family} et al.`;
  };

  /** Count visible (non-dismissed) hits for an item. */
  const visibleHitCount = (item: LiteratureSearchItem) =>
    item.hits.filter((h) => !dismissedKeys.has(`${item.id}:${h.chunk_index}`)).length;

  return (
    <>
      <div className={styles.panel}>
        <div className={styles.searchBox}>
          <div className={styles.fieldGroup}>
            <label className={styles.fieldLabel}>Chinese Query</label>
            <AutocompleteInput
              placeholder="中文检索词"
              value={zhQuery}
              onChange={onZhQueryChange}
              onKeyDown={handleKeyDown}
              lang="zh"
              className={styles.input}
            />
          </div>

          <div className={styles.fieldGroup}>
            <label className={styles.fieldLabel}>English Query</label>
            <AutocompleteInput
              placeholder="English search query"
              value={enQuery}
              onChange={onEnQueryChange}
              onKeyDown={handleKeyDown}
              lang="en"
              className={styles.input}
            />
          </div>

          <button onClick={() => onSearch()} disabled={loading || !hasQuery} className={styles.searchBtn}>
            {loading ? "Searching..." : "Search"}
          </button>

          {warnings.map((warning) => (
            <div key={warning} className={styles.warningBanner}>
              {warning}
            </div>
          ))}

          {aiQueries.length > 0 && (
            <div className={styles.queryInfo}>
              {aiQueries.map((item) => (
                <div key={`${item.lang}-${item.text}`} className={styles.queryInfoRow}>
                  AI {item.lang === "zh" ? "Chinese" : "English"} query: {item.text}
                </div>
              ))}
            </div>
          )}

          {!semanticAvailable && (
            <div className={styles.queryInfo}>
              当前语义检索不可用，已自动降级为关键词检索。
            </div>
          )}
        </div>

        <div className={styles.results}>
          {results.length === 0 && !loading && hasQuery && (
            <div className={styles.noResults}>No results found</div>
          )}

          {results.map((item) => {
            const vCount = visibleHitCount(item);
            return (
              <div
                key={item.id}
                className={`${styles.resultItem} ${selectedIds.has(item.id) ? styles.selected : ""}`}
              >
                <div className={styles.checkbox} onClick={(event) => event.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={selectedIds.has(item.id)}
                    onChange={() => onToggleSelect(item)}
                  />
                </div>

                <button
                  type="button"
                  className={styles.resultBody}
                  onClick={() => setActiveItem(item)}
                >
                  <div className={styles.resultTopRow}>
                    <div className={styles.resultTitle}>{item.title || "Untitled"}</div>
                    <span className={styles.hitCount}>
                      {vCount < item.hit_count ? `${vCount}/${item.hit_count}` : item.hit_count} hits
                    </span>
                  </div>

                  <div className={styles.resultMeta}>
                    {formatAuthors(item.authors)}
                    {item.year ? ` (${item.year})` : ""}
                  </div>

                  {item.journal && (
                    <div className={styles.resultJournal}>{item.journal}</div>
                  )}

                  <div className={styles.resultSnippet}>
                    <HighlightedText
                      text={item.preview_hit.content}
                      highlights={item.preview_hit.highlights}
                    />
                  </div>

                  <div className={styles.resultFooter}>
                    {item.preview_hit.heading && (
                      <span className={styles.metaBadge}>{item.preview_hit.heading}</span>
                    )}
                    {item.preview_hit.page_number > 0 && (
                      <span className={styles.metaBadge}>p. {item.preview_hit.page_number}</span>
                    )}
                    {item.match_languages.length > 0 && (
                      <span className={styles.metaBadge}>
                        {item.match_languages.join(" + ")}
                      </span>
                    )}
                  </div>
                </button>
              </div>
            );
          })}
        </div>

        {hasSelected && (
          <div className={styles.insertBar}>
            <button onClick={onInsertCitations} className={styles.insertBtn}>
              Insert Citation ({selectedIds.size})
            </button>
          </div>
        )}
      </div>

      <SearchHitsDialog
        item={activeItem}
        queryKey={queryKey}
        dismissedKeys={dismissedKeys}
        onClose={() => setActiveItem(null)}
        onInsertCitation={onInsertSingleCitation}
        onDismiss={handleDismiss}
      />
    </>
  );
}
