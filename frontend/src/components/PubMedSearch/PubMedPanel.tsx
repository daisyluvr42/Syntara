/**
 * PubMed search — inline panel variant for right sidebar.
 * Shares all logic with PubMedSearch but renders without overlay/dialog wrapper.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  getPubMedFields,
  importFromPubMed,
  searchPubMedAdvanced,
  type Author,
  type PubMedAdvancedSearchRequest,
  type PubMedItem,
} from "../../services/api";
import styles from "./PubMedPanel.module.css";

/* ------- constants ------- */
const PER_PAGE_OPTIONS = [10, 20, 50, 100];

const DEFAULT_SORT_OPTIONS: Record<string, string> = {
  "Best Match": "relevance",
  "Most Recent": "most+recent",
  "Publication Date": "pub+date",
  "First Author": "Author",
  "Journal": "JournalName",
  "Title": "title",
};

const DATE_TYPE_OPTIONS = [
  { label: "Publication Date", value: "pdat" },
  { label: "Entry Date", value: "edat" },
  { label: "Modification Date", value: "mdat" },
  { label: "MeSH Date", value: "mhda" },
  { label: "Create Date", value: "crdt" },
];

/* ------- types ------- */
interface BuilderRow {
  id: number;
  term: string;
  field: string;
  op: "AND" | "OR" | "NOT";
}

interface PubMedPanelProps {
  onImported: () => void;
}

/* ------- helpers ------- */
let _rowId = 0;
const nextRowId = () => ++_rowId;

const formatAuthors = (authors: Author[]) => {
  if (!authors || authors.length === 0) return "";
  if (authors.length <= 3)
    return authors.map((a) => `${a.family} ${a.given?.[0] || ""}`).join(", ");
  return `${authors[0].family} ${authors[0].given?.[0] || ""} et al.`;
};

/* ================================================================ */
export default function PubMedPanel({ onImported }: PubMedPanelProps) {
  /* ------ fields from backend ------ */
  const [fields, setFields] = useState<string[]>([]);
  const [sortOptions, setSortOptions] = useState<Record<string, string>>(DEFAULT_SORT_OPTIONS);

  /* ------ UI mode ------ */
  const [showAdvanced, setShowAdvanced] = useState(false);

  /* ------ simple search ------ */
  const [simpleQuery, setSimpleQuery] = useState("");

  /* ------ builder rows ------ */
  const [rows, setRows] = useState<BuilderRow[]>([
    { id: nextRowId(), term: "", field: "All Fields", op: "AND" },
  ]);

  /* ------ query box (composed query, editable) ------ */
  const [queryBox, setQueryBox] = useState("");

  /* ------ filters ------ */
  const [sort, setSort] = useState("relevance");
  const [perPage, setPerPage] = useState(20);
  const [dateType, setDateType] = useState("");
  const [minDate, setMinDate] = useState("");
  const [maxDate, setMaxDate] = useState("");

  /* ------ results / pagination ------ */
  const [results, setResults] = useState<PubMedItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [queryTranslation, setQueryTranslation] = useState("");

  /* ------ selection & status ------ */
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState("");

  /* ------ expanded abstract ------ */
  const [expandedPmid, setExpandedPmid] = useState<string | null>(null);

  const resultsRef = useRef<HTMLDivElement>(null);

  /* ------ load fields on mount ------ */
  useEffect(() => {
    getPubMedFields()
      .then((data) => {
        setFields(data.fields);
        setSortOptions(data.sort_options);
      })
      .catch(() => {
        /* use defaults */
      });
  }, []);

  /* ------ builder helpers ------ */
  const updateRow = (id: number, patch: Partial<BuilderRow>) => {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  };

  const removeRow = (id: number) => {
    setRows((prev) => (prev.length <= 1 ? prev : prev.filter((r) => r.id !== id)));
  };

  const addBuilderTermToQuery = () => {
    const parts: string[] = [];
    for (let i = 0; i < rows.length; i++) {
      const r = rows[i];
      if (!r.term.trim()) continue;
      const fieldTag =
        r.field && r.field !== "All Fields" ? `[${r.field}]` : "";
      const value = r.term.includes(" ") && fieldTag ? `"${r.term}"` : r.term;
      const fragment = `${value}${fieldTag}`;
      if (parts.length === 0) {
        parts.push(fragment);
      } else {
        parts.push(`${r.op} ${fragment}`);
      }
    }
    const composed = parts.join(" ");
    if (!composed) return;
    if (queryBox.trim()) {
      setQueryBox((prev) => `${prev.trim()} AND ${composed}`);
    } else {
      setQueryBox(composed);
    }
    setRows([{ id: nextRowId(), term: "", field: "All Fields", op: "AND" }]);
  };

  /* ------ search ------ */
  const doSearch = useCallback(
    async (pageNum = 1) => {
      const q = showAdvanced ? queryBox.trim() : simpleQuery.trim();
      if (!q) return;
      setLoading(true);
      setError("");
      try {
        const req: PubMedAdvancedSearchRequest = {
          raw_query: q,
          max_results: perPage,
          page: pageNum,
          sort,
        };
        if (dateType) {
          req.date_type = dateType;
          if (minDate) req.min_date = minDate;
          if (maxDate) req.max_date = maxDate;
        }
        const res = await searchPubMedAdvanced(req);
        setResults(res.results);
        setTotal(res.total);
        setPage(res.page ?? pageNum);
        setTotalPages(res.pages ?? 1);
        setQueryTranslation(res.query_translation ?? "");
        if (pageNum === 1) setSelected(new Set());
        resultsRef.current?.scrollTo(0, 0);
      } catch (err: any) {
        setError(err?.message || "Search failed");
        console.error(err);
      } finally {
        setLoading(false);
      }
    },
    [showAdvanced, queryBox, simpleQuery, perPage, sort, dateType, minDate, maxDate],
  );

  const handleSimpleSearch = () => doSearch(1);
  const handleAdvancedSearch = () => doSearch(1);

  /* ------ selection ------ */
  const toggleSelect = (pmid: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(pmid)) next.delete(pmid);
      else next.add(pmid);
      return next;
    });
  };

  const selectAll = () => {
    if (selected.size === results.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(results.map((r) => r.pmid)));
    }
  };

  /* ------ import ------ */
  const handleImport = async () => {
    if (selected.size === 0) return;
    setImporting(true);
    try {
      const res = await importFromPubMed(Array.from(selected));
      onImported();
      const importedCount = res.imported.length;
      const skippedCount = res.skipped.length;
      if (skippedCount > 0) {
        setError(`Imported ${importedCount}, skipped ${skippedCount} (already exist)`);
      }
      const importedPmids = new Set(res.imported.map((i) => i.pmid));
      setSelected((prev) => {
        const next = new Set(prev);
        importedPmids.forEach((p) => next.delete(p));
        return next;
      });
    } catch (err: any) {
      setError(err?.message || "Import failed");
      console.error(err);
    } finally {
      setImporting(false);
    }
  };

  const defaultFieldList = [
    "All Fields", "Title", "Title/Abstract", "Author", "Author - First",
    "Author - Last", "Journal", "MeSH Terms", "MeSH Major Topic",
    "Publication Type", "Affiliation", "Language", "Date - Publication",
  ];

  return (
    <div className={styles.panel}>
      {/* ========== HEADER ========== */}
      <div className={styles.header}>
        <span className={styles.headerTitle}>PubMed Search</span>
        <button
          className={`${styles.modeToggle} ${showAdvanced ? styles.modeToggleActive : ""}`}
          onClick={() => setShowAdvanced((v) => !v)}
        >
          {showAdvanced ? "Simple" : "Advanced"}
        </button>
      </div>

      {/* ========== SIMPLE SEARCH ========== */}
      {!showAdvanced && (
        <div className={styles.searchRow}>
          <input
            type="text"
            placeholder="Search PubMed..."
            value={simpleQuery}
            onChange={(e) => setSimpleQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSimpleSearch()}
            className={styles.input}
          />
          <button onClick={handleSimpleSearch} disabled={loading} className={styles.searchBtn}>
            {loading ? "..." : "Search"}
          </button>
        </div>
      )}

      {/* ========== ADVANCED SEARCH BUILDER ========== */}
      {showAdvanced && (
        <div className={styles.advancedPanel}>
          {/* --- Builder rows --- */}
          <div className={styles.builderSection}>
            <div className={styles.builderLabel}>Build query</div>
            {rows.map((row, idx) => (
              <div key={row.id} className={styles.builderRow}>
                {idx > 0 ? (
                  <select
                    className={styles.boolSelect}
                    value={row.op}
                    onChange={(e) => updateRow(row.id, { op: e.target.value as "AND" | "OR" | "NOT" })}
                  >
                    <option value="AND">AND</option>
                    <option value="OR">OR</option>
                    <option value="NOT">NOT</option>
                  </select>
                ) : (
                  <div className={styles.boolPlaceholder} />
                )}
                <select
                  className={styles.fieldSelect}
                  value={row.field}
                  onChange={(e) => updateRow(row.id, { field: e.target.value })}
                >
                  {(fields.length > 0 ? fields : defaultFieldList).map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
                <input
                  type="text"
                  className={styles.termInput}
                  placeholder="Search term"
                  value={row.term}
                  onChange={(e) => updateRow(row.id, { term: e.target.value })}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addBuilderTermToQuery();
                    }
                  }}
                />
                {rows.length > 1 && (
                  <button className={styles.removeRowBtn} onClick={() => removeRow(row.id)} title="Remove">
                    &times;
                  </button>
                )}
              </div>
            ))}
            <div className={styles.builderActions}>
              <button
                className={styles.addRowBtn}
                onClick={() =>
                  setRows((prev) => [...prev, { id: nextRowId(), term: "", field: "All Fields", op: "AND" }])
                }
              >
                + Row
              </button>
              <button className={styles.addToQueryBtn} onClick={addBuilderTermToQuery}>
                ADD
              </button>
            </div>
          </div>

          {/* --- Date filter --- */}
          <div className={styles.dateRow}>
            <select
              className={styles.dateTypeSelect}
              value={dateType}
              onChange={(e) => setDateType(e.target.value)}
            >
              <option value="">No date filter</option>
              {DATE_TYPE_OPTIONS.map((d) => (
                <option key={d.value} value={d.value}>{d.label}</option>
              ))}
            </select>
            {dateType && (
              <>
                <input
                  type="text"
                  className={styles.dateInput}
                  placeholder="YYYY/MM/DD"
                  value={minDate}
                  onChange={(e) => setMinDate(e.target.value)}
                />
                <span className={styles.dateSep}>to</span>
                <input
                  type="text"
                  className={styles.dateInput}
                  placeholder="Present"
                  value={maxDate}
                  onChange={(e) => setMaxDate(e.target.value)}
                />
              </>
            )}
          </div>

          {/* --- Query box --- */}
          <div className={styles.queryBoxSection}>
            <textarea
              className={styles.queryBox}
              placeholder="Edit query here..."
              value={queryBox}
              onChange={(e) => setQueryBox(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleAdvancedSearch();
                }
              }}
              rows={2}
            />
            <div className={styles.queryBoxActions}>
              <button className={styles.clearBtn} onClick={() => setQueryBox("")}>Clear</button>
              <button
                className={styles.searchBtn}
                onClick={handleAdvancedSearch}
                disabled={loading || !queryBox.trim()}
              >
                {loading ? "..." : "Search"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========== SORT / PER PAGE BAR ========== */}
      {(results.length > 0 || total > 0) && (
        <div className={styles.filtersRow}>
          <span className={styles.totalCount}>
            {total.toLocaleString()} result{total !== 1 ? "s" : ""}
          </span>
          <div className={styles.filtersRight}>
            <select value={sort} onChange={(e) => setSort(e.target.value)} className={styles.filterSelect}>
              {Object.entries(sortOptions).map(([label, val]) => (
                <option key={val} value={val}>{label}</option>
              ))}
            </select>
            <select
              value={perPage}
              onChange={(e) => setPerPage(Number(e.target.value))}
              className={styles.filterSelect}
            >
              {PER_PAGE_OPTIONS.map((n) => (
                <option key={n} value={n}>{n}/pg</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* ========== QUERY TRANSLATION ========== */}
      {queryTranslation && (
        <div className={styles.queryTranslation} title={queryTranslation}>
          {queryTranslation.length > 100 ? queryTranslation.slice(0, 100) + "..." : queryTranslation}
        </div>
      )}

      {/* ========== ERROR ========== */}
      {error && (
        <div className={styles.errorBar}>
          {error}
          <button className={styles.errorClose} onClick={() => setError("")}>&times;</button>
        </div>
      )}

      {/* ========== RESULTS ========== */}
      <div className={styles.results} ref={resultsRef}>
        {loading && results.length === 0 && (
          <div className={styles.emptyState}>Searching PubMed...</div>
        )}
        {!loading && results.length === 0 && total === 0 && (
          <div className={styles.emptyState}>Enter keywords to search PubMed.</div>
        )}

        {results.length > 0 && (
          <div className={styles.selectAllRow}>
            <label className={styles.selectAllLabel}>
              <input
                type="checkbox"
                checked={selected.size === results.length && results.length > 0}
                onChange={selectAll}
              />
              Select all
            </label>
          </div>
        )}

        {results.map((r) => {
          const isExpanded = expandedPmid === r.pmid;
          return (
            <div
              key={r.pmid}
              className={`${styles.resultItem} ${selected.has(r.pmid) ? styles.selected : ""}`}
            >
              <input
                type="checkbox"
                checked={selected.has(r.pmid)}
                onChange={() => toggleSelect(r.pmid)}
                className={styles.resultCheckbox}
              />
              <div className={styles.resultContent}>
                <div className={styles.resultTitle} onClick={() => toggleSelect(r.pmid)}>
                  {r.title}
                </div>
                <div className={styles.resultMeta}>
                  <span>{formatAuthors(r.authors)}</span>
                  {r.year && <span className={styles.resultYear}>({r.year})</span>}
                </div>
                {r.journal && (
                  <div className={styles.resultJournal}>
                    {r.journal}
                    {r.volume && ` ${r.volume}`}
                    {r.issue && `(${r.issue})`}
                    {r.pages && `: ${r.pages}`}
                  </div>
                )}
                {r.pub_types && r.pub_types.length > 0 && (
                  <div className={styles.resultTags}>
                    {r.pub_types.map((pt) => (
                      <span key={pt} className={styles.pubTypeTag}>{pt}</span>
                    ))}
                  </div>
                )}
                {r.abstract && (
                  <div className={styles.resultAbstract}>
                    {isExpanded ? r.abstract : r.abstract.substring(0, 150) + (r.abstract.length > 150 ? "..." : "")}
                    {r.abstract.length > 150 && (
                      <button
                        className={styles.expandBtn}
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedPmid(isExpanded ? null : r.pmid);
                        }}
                      >
                        {isExpanded ? "Less" : "More"}
                      </button>
                    )}
                  </div>
                )}
                <div className={styles.resultIds}>
                  PMID: {r.pmid}
                  {r.doi && (
                    <>
                      {" | "}
                      <a
                        href={`https://doi.org/${r.doi}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.doiLink}
                        onClick={(e) => e.stopPropagation()}
                      >
                        DOI
                      </a>
                    </>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* ========== PAGINATION ========== */}
      {totalPages > 1 && (
        <div className={styles.pagination}>
          <button
            className={styles.pageBtn}
            disabled={page <= 1 || loading}
            onClick={() => doSearch(page - 1)}
          >
            &laquo;
          </button>
          <span className={styles.pageInfo}>{page} / {totalPages}</span>
          <button
            className={styles.pageBtn}
            disabled={page >= totalPages || loading}
            onClick={() => doSearch(page + 1)}
          >
            &raquo;
          </button>
        </div>
      )}

      {/* ========== FOOTER / IMPORT ========== */}
      {selected.size > 0 && (
        <div className={styles.footer}>
          <span className={styles.selectedCount}>{selected.size} selected</span>
          <button onClick={handleImport} disabled={importing} className={styles.importBtn}>
            {importing ? "Importing..." : "Import"}
          </button>
        </div>
      )}
    </div>
  );
}
