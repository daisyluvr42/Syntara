/**
 * Export dialog: choose format, CSL style, template.
 */

import { useEffect, useState } from "react";
import {
  exportDocx,
  exportHtml,
  exportMarkdown,
  exportPdf,
  exportBibtex,
  getExportStyles,
  getPandocStatus,
  type ExportStyle,
} from "../../services/api";
import styles from "./ExportDialog.module.css";

interface ExportDialogProps {
  open: boolean;
  onClose: () => void;
  documentId: string;
}

export default function ExportDialog({ open, onClose, documentId }: ExportDialogProps) {
  const [format, setFormat] = useState("markdown");
  const [cslStyle, setCslStyle] = useState("vancouver");
  const [availableStyles, setAvailableStyles] = useState<ExportStyle[]>([]);
  const [pandocAvailable, setPandocAvailable] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (open) {
      getExportStyles().then(setAvailableStyles).catch(console.error);
      getPandocStatus().then((s) => setPandocAvailable(s.available)).catch(console.error);
    }
  }, [open]);

  if (!open) return null;

  const handleExport = async () => {
    setExporting(true);
    try {
      let blob: Blob;
      let filename: string;

      switch (format) {
        case "markdown":
          blob = await exportMarkdown(documentId, cslStyle);
          filename = "export.md";
          break;
        case "docx":
          blob = await exportDocx(documentId, cslStyle);
          filename = "export.docx";
          break;
        case "pdf":
          blob = await exportPdf(documentId, cslStyle);
          filename = "export.pdf";
          break;
        case "html":
          blob = await exportHtml(documentId, cslStyle);
          filename = "export.html";
          break;
        case "bibtex":
          blob = await exportBibtex();
          filename = "references.bib";
          break;
        default:
          return;
      }

      // Download
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
      onClose();
    } catch (err: unknown) {
      alert(`Export failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setExporting(false);
    }
  };

  const formats = [
    { id: "markdown", label: "Markdown (.md)", needsPandoc: false },
    { id: "docx", label: "Word (.docx)", needsPandoc: true },
    { id: "pdf", label: "PDF", needsPandoc: true },
    { id: "html", label: "HTML", needsPandoc: true },
    { id: "bibtex", label: "BibTeX (.bib)", needsPandoc: false },
  ];

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>Export Document</h2>
          <button className={styles.closeBtn} onClick={onClose}>&times;</button>
        </div>

        <div className={styles.body}>
          <div className={styles.section}>
            <h3>Format</h3>
            <div className={styles.formatGrid}>
              {formats.map((f) => {
                const disabled = f.needsPandoc && !pandocAvailable;
                return (
                  <button
                    key={f.id}
                    className={`${styles.formatBtn} ${format === f.id ? styles.formatActive : ""}`}
                    onClick={() => !disabled && setFormat(f.id)}
                    disabled={disabled}
                    title={disabled ? "Requires Pandoc: brew install pandoc" : ""}
                  >
                    {f.label}
                    {disabled && <span className={styles.pandocNote}>Needs Pandoc</span>}
                  </button>
                );
              })}
            </div>
          </div>

          {format !== "bibtex" && (
            <div className={styles.section}>
              <h3>Citation Style</h3>
              <select
                value={cslStyle}
                onChange={(e) => setCslStyle(e.target.value)}
                className={styles.styleSelect}
              >
                <option value="vancouver">Vancouver</option>
                <option value="apa-7th">APA 7th</option>
                <option value="harvard">Harvard</option>
                <option value="gb-t-7714">GB/T 7714 (Chinese)</option>
                {availableStyles
                  .filter((s) => !["vancouver", "apa-7th", "harvard", "gb-t-7714"].includes(s.id))
                  .map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
              </select>
            </div>
          )}

          {!pandocAvailable && (
            <div className={styles.pandocWarning}>
              Pandoc not detected. Install with: <code>brew install pandoc</code>
              <br />Markdown and BibTeX export will always work.
            </div>
          )}
        </div>

        <div className={styles.footer}>
          <button onClick={handleExport} disabled={exporting} className={styles.exportBtn}>
            {exporting ? "Exporting..." : "Export"}
          </button>
        </div>
      </div>
    </div>
  );
}
