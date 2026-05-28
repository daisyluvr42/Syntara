/**
 * Citation management hook.
 */

import { useCallback, useState } from "react";
import type { LiteratureSearchItem } from "../services/api";

export function useCitation() {
  const [selectedItems, setSelectedItems] = useState<LiteratureSearchItem[]>([]);

  const toggleSelect = useCallback((item: LiteratureSearchItem) => {
    setSelectedItems((prev) => {
      const exists = prev.find((i) => i.id === item.id);
      if (exists) return prev.filter((i) => i.id !== item.id);
      return [...prev, item];
    });
  }, []);

  const isSelected = useCallback(
    (id: string) => selectedItems.some((i) => i.id === id),
    [selectedItems]
  );

  const clearSelection = useCallback(() => {
    setSelectedItems([]);
  }, []);

  const getSelectedCiteKeys = useCallback(() => {
    return selectedItems
      .filter((i) => i.cite_key)
      .map((i) => i.cite_key!);
  }, [selectedItems]);

  return {
    selectedItems,
    toggleSelect,
    isSelected,
    clearSelection,
    getSelectedCiteKeys,
  };
}
