/**
 * Top toolbar with main navigation buttons.
 */

import { useState, useRef, useEffect } from "react";
import {
  FilePlus,
  FolderOpen,
  Save,
  Download,
  BookOpen,
  Search,
  Sparkles,
  ListOrdered,
} from "lucide-react";
import type { CitationStyle } from "../../services/api";
import styles from "./Toolbar.module.css";

const CITATION_STYLES: { id: CitationStyle; label: string }[] = [
  { id: "vancouver", label: "Vancouver [1]" },
  { id: "apa", label: "APA (Author, Year)" },
  { id: "gb-t-7714", label: "GB/T 7714 [1]" },
];

interface ToolbarProps {
  documentTitle: string;
  onTitleChange: (title: string) => void;
  onSave: () => void;
  onNewDoc: () => void;
  onOpen: () => void;
  onExport: () => void;
  onToggleAI: () => void;
  onToggleLibrary: () => void;
  onToggleSearch: () => void;
  showLibrary: boolean;
  showSearch: boolean;
  showAI: boolean;
  saving: boolean;
  onFormatCitations: (style: CitationStyle) => void;
  formatting?: boolean;
}

export default function Toolbar({
  documentTitle,
  onTitleChange,
  onSave,
  onNewDoc,
  onOpen,
  onExport,
  onToggleAI,
  onToggleLibrary,
  onToggleSearch,
  showLibrary,
  showSearch,
  showAI,
  saving,
  onFormatCitations,
  formatting,
}: ToolbarProps) {
  const [styleMenuOpen, setStyleMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!styleMenuOpen) return;
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setStyleMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [styleMenuOpen]);

  return (
    <div className={styles.toolbar}>
      <div className={styles.left}>
        <span className={styles.logo}>Syntara</span>
        <div className={styles.divider} />
        <button onClick={onNewDoc} className={styles.btn} title="New Document">
          <FilePlus size={15} />
          <span>New</span>
        </button>
        <button onClick={onOpen} className={styles.btn} title="Open Document">
          <FolderOpen size={15} />
          <span>Open</span>
        </button>
        <button onClick={onSave} disabled={saving} className={styles.btn} title="Save">
          <Save size={15} />
          <span>{saving ? "Saving..." : "Save"}</span>
        </button>
        <button onClick={onExport} className={styles.btn} title="Export Document">
          <Download size={15} />
          <span>Export</span>
        </button>
      </div>

      <div className={styles.center}>
        <input
          className={styles.titleInput}
          value={documentTitle}
          onChange={(e) => onTitleChange(e.target.value)}
          placeholder="Document title..."
        />
      </div>

      <div className={styles.right}>
        <div className={styles.formatGroup} ref={menuRef}>
          <button
            onClick={() => setStyleMenuOpen((p) => !p)}
            disabled={formatting}
            className={styles.btn}
            title="Format Citations"
          >
            <ListOrdered size={15} />
            <span>{formatting ? "Formatting..." : "Format"}</span>
          </button>
          {styleMenuOpen && (
            <div className={styles.styleMenu}>
              {CITATION_STYLES.map((s) => (
                <button
                  key={s.id}
                  className={styles.styleOption}
                  onClick={() => {
                    setStyleMenuOpen(false);
                    onFormatCitations(s.id);
                  }}
                >
                  {s.label}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className={styles.divider} />
        <button
          onClick={onToggleLibrary}
          className={`${styles.btnToggle} ${showLibrary ? styles.btnToggleActive : ""}`}
          title="Literature Library"
        >
          <BookOpen size={15} />
          <span>Library</span>
        </button>
        <button
          onClick={onToggleSearch}
          className={`${styles.btnToggle} ${showSearch ? styles.btnToggleActive : ""}`}
          title="Search (Local & PubMed)"
        >
          <Search size={15} />
          <span>Search</span>
        </button>
        <button
          onClick={onToggleAI}
          className={`${styles.btnToggle} ${showAI ? styles.btnToggleActive : ""}`}
          title="AI Writing Assistant"
        >
          <Sparkles size={15} />
          <span>AI助写</span>
        </button>
      </div>
    </div>
  );
}
