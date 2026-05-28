/**
 * Tabbed right sidebar — "Local Search" and "PubMed" tabs.
 */

import { useState } from "react";
import type { LiteratureSearchItem, LiteratureSearchQuery } from "../../services/api";
import SearchPanel from "../SearchPanel/SearchPanel";
import PubMedPanel from "../PubMedSearch/PubMedPanel";
import styles from "./RightPanel.module.css";

type RightTab = "local" | "pubmed";

interface RightPanelProps {
  // Local Search props
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
  // PubMed props
  onPubMedImported: () => void;
}

export default function RightPanel(props: RightPanelProps) {
  const [tab, setTab] = useState<RightTab>("local");

  return (
    <div className={styles.panel}>
      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${tab === "local" ? styles.tabActive : ""}`}
          onClick={() => setTab("local")}
        >
          Local Search
        </button>
        <button
          className={`${styles.tab} ${tab === "pubmed" ? styles.tabActive : ""}`}
          onClick={() => setTab("pubmed")}
        >
          PubMed
        </button>
      </div>

      <div className={styles.tabContent}>
        {tab === "local" && (
          <SearchPanel
            zhQuery={props.zhQuery}
            onZhQueryChange={props.onZhQueryChange}
            enQuery={props.enQuery}
            onEnQueryChange={props.onEnQueryChange}
            results={props.results}
            warnings={props.warnings}
            usedQueries={props.usedQueries}
            semanticAvailable={props.semanticAvailable}
            loading={props.loading}
            onSearch={props.onSearch}
            selectedIds={props.selectedIds}
            onToggleSelect={props.onToggleSelect}
            onInsertCitations={props.onInsertCitations}
            onInsertSingleCitation={props.onInsertSingleCitation}
          />
        )}
        {tab === "pubmed" && (
          <PubMedPanel onImported={props.onPubMedImported} />
        )}
      </div>
    </div>
  );
}
