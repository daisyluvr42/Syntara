/**
 * Grouped literature search hook.
 */

import { useCallback, useState } from "react";
import {
  searchLiteratureGrouped,
  type LiteratureSearchItem,
  type LiteratureSearchQuery,
} from "../services/api";

export function useSearch() {
  const [results, setResults] = useState<LiteratureSearchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [zhQuery, setZhQuery] = useState("");
  const [enQuery, setEnQuery] = useState("");
  const [warnings, setWarnings] = useState<string[]>([]);
  const [usedQueries, setUsedQueries] = useState<LiteratureSearchQuery[]>([]);
  const [semanticAvailable, setSemanticAvailable] = useState(true);

  const doSearch = useCallback(
    async (nextZhQuery?: string, nextEnQuery?: string) => {
      const finalZhQuery = (nextZhQuery ?? zhQuery).trim();
      const finalEnQuery = (nextEnQuery ?? enQuery).trim();

      if (!finalZhQuery && !finalEnQuery) {
        setResults([]);
        setWarnings([]);
        setUsedQueries([]);
        setSemanticAvailable(true);
        return;
      }

      setLoading(true);
      try {
        const res = await searchLiteratureGrouped(finalZhQuery, finalEnQuery);
        setResults(res.results);
        setWarnings(res.warnings);
        setUsedQueries(res.used_queries);
        setSemanticAvailable(res.semantic_available);
      } catch (err) {
        console.error("Search error:", err);
        setResults([]);
        setWarnings(["搜索失败，请稍后再试。"]);
        setUsedQueries([]);
        setSemanticAvailable(true);
      } finally {
        setLoading(false);
      }
    },
    [enQuery, zhQuery]
  );

  return {
    results,
    loading,
    zhQuery,
    setZhQuery,
    enQuery,
    setEnQuery,
    warnings,
    usedQueries,
    semanticAvailable,
    doSearch,
    setResults,
  };
}
