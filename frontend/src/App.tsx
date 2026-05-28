/**
 * Syntara — Main application shell.
 * Three-column layout: Library | Editor | Search
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { EditorView } from "@codemirror/view";
import Editor from "./components/Editor/Editor";
import RightPanel from "./components/RightPanel/RightPanel";
import LibraryPanel from "./components/LibraryPanel/LibraryPanel";
import AIPanel from "./components/AIPanel/AIPanel";
import CacheManager from "./components/CacheManager/CacheManager";
import DocTreeManager from "./components/DocTreeManager/DocTreeManager";
import CorpusManager from "./components/CorpusManager/CorpusManager";
// SettingsDialog merged into AIPanel as "Providers" tab
import LiteratureDetail from "./components/LiteratureDetail/LiteratureDetail";
import ExportDialog from "./components/ExportDialog/ExportDialog";
import OpenDialog from "./components/OpenDialog/OpenDialog";
import StatusBar from "./components/StatusBar/StatusBar";
import Toolbar from "./components/Toolbar/Toolbar";
import { useEditor } from "./hooks/useEditor";
import { useSearch } from "./hooks/useSearch";
import { useCitation } from "./hooks/useCitation";
import { useResize } from "./hooks/useResize";
import {
  apiUrl,
  createDocument,
  formatCitations,
  getDocument,
  listDocuments,
  updateDocument,
  type CitationStyle,
  type LiteratureSearchItem,
} from "./services/api";
import "./App.css";

export default function App() {
  // Document state
  const [docId, setDocId] = useState<string | null>(null);
  const [docTitle, setDocTitle] = useState("Untitled");
  const [initialContent, setInitialContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [citationCount, setCitationCount] = useState(0);

  // Panel visibility
  const [showLibrary, setShowLibrary] = useState(true);
  const [showSearch, setShowSearch] = useState(true);

  // Citation formatting
  const [formatting, setFormatting] = useState(false);

  // Panel visibility — AI bottom panel
  const [showAI, setShowAI] = useState(false);

  // Resize handles
  const leftResize = useResize({ direction: "horizontal", initialSize: 240, minSize: 180, maxSize: 400 });
  const rightResize = useResize({ direction: "horizontal", initialSize: 340, minSize: 260, maxSize: 540, reverse: true });
  const aiResize = useResize({ direction: "vertical", initialSize: 280, minSize: 120, maxSize: 600, reverse: true });

  // Dialogs
  const [corpusOpen, setCorpusOpen] = useState(false);
  const [cacheOpen, setCacheOpen] = useState(false);
  const [docTreesOpen, setDocTreesOpen] = useState(false);
  // Settings merged into AI panel
  const [exportOpen, setExportOpen] = useState(false);
  const [openDialogOpen, setOpenDialogOpen] = useState(false);
  const [editLitId, setEditLitId] = useState<string | null>(null);
  const [libraryRefreshKey, setLibraryRefreshKey] = useState(0);

  // Hooks
  const editor = useEditor();
  const searchHook = useSearch();
  const citation = useCitation();

  // Load or create initial document
  useEffect(() => {
    (async () => {
      try {
        const docs = await listDocuments();
        if (docs.items.length > 0) {
          const doc = await getDocument(docs.items[0].id);
          setDocId(doc.id);
          setDocTitle(doc.title);
          setInitialContent(doc.content || "");
        } else {
          const created = await createDocument({ title: "Untitled" });
          setDocId(created.id);
          setDocTitle(created.title);
        }
      } catch (err) {
        console.error("Failed to load document:", err);
      }
    })();
  }, []);

  // Save document
  const handleSave = useCallback(async () => {
    if (!docId) return;
    setSaving(true);
    try {
      const content = editor.getContent();
      await updateDocument(docId, { title: docTitle, content });
      setDirty(false);
    } catch (err) {
      console.error("Save failed:", err);
    } finally {
      setSaving(false);
    }
  }, [docId, docTitle, editor]);

  // Auto-save on Ctrl/Cmd+S
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handleSave]);

  // New document
  const handleNewDoc = async () => {
    const created = await createDocument({ title: "Untitled" });
    setDocId(created.id);
    setDocTitle(created.title);
    setInitialContent("");
  };

  // Open existing document
  const handleOpenDoc = async (doc: import("./services/api").DocumentItem) => {
    try {
      const full = await getDocument(doc.id);
      setDocId(full.id);
      setDocTitle(full.title);
      setInitialContent(full.content || "");
      setDirty(false);
    } catch (err) {
      console.error("Failed to open document:", err);
    }
  };

  // Auto-save: debounce 2s after last keystroke
  const autoSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [dirty, setDirty] = useState(false);

  const scheduleAutoSave = useCallback(() => {
    if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
    setDirty(true);
    autoSaveTimer.current = setTimeout(() => {
      handleSave();
      setDirty(false);
    }, 2000);
  }, [handleSave]);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
    };
  }, []);

  // Save before page unload (closing tab / navigating away)
  useEffect(() => {
    const onBeforeUnload = () => {
      if (docId && dirty) {
        const content = editor.getContent();
        const blob = new Blob(
          [JSON.stringify({ title: docTitle, content })],
          { type: "application/json" }
        );
        navigator.sendBeacon(apiUrl(`/documents/${docId}/beacon-save`), blob);
      }
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [docId, docTitle, editor, dirty]);

  // Editor content change
  const handleContentChange = useCallback(
    (content: string) => {
      editor.updateWordCount(content);
      // Count citations
      const matches = content.match(/\[@[^\]]+\]/g) || [];
      setCitationCount(matches.length);
      // Trigger debounced auto-save
      scheduleAutoSave();
    },
    [editor, scheduleAutoSave]
  );

  // Insert citations from search panel
  const handleInsertCitations = useCallback(() => {
    const keys = citation.getSelectedCiteKeys();
    if (keys.length > 0) {
      editor.insertCitation(keys);
      citation.clearSelection();
    }
  }, [citation, editor]);

  const handleInsertSingleCitation = useCallback(
    (item: LiteratureSearchItem) => {
      if (item.cite_key) {
        editor.insertCitation([item.cite_key]);
      }
    },
    [editor]
  );

  // Format citations
  const handleFormatCitations = useCallback(
    async (style: CitationStyle) => {
      const content = editor.getContent();
      if (!content.trim()) return;
      setFormatting(true);
      try {
        const resp = await formatCitations(content, style);
        editor.replaceContent(resp.content);
      } catch (err) {
        console.error("Format citations failed:", err);
      } finally {
        setFormatting(false);
      }
    },
    [editor]
  );

  // Search panel toggle selection
  const selectedIds = new Set(citation.selectedItems.map((i) => i.id));

  return (
    <div className="app-root">
      <Toolbar
        documentTitle={docTitle}
        onTitleChange={setDocTitle}
        onSave={handleSave}
        onNewDoc={handleNewDoc}
        onOpen={() => setOpenDialogOpen(true)}
        onExport={() => setExportOpen(true)}
        onToggleAI={() => setShowAI((p) => !p)}
        showAI={showAI}
        onToggleLibrary={() => setShowLibrary((p) => !p)}
        onToggleSearch={() => setShowSearch((p) => !p)}
        showLibrary={showLibrary}
        showSearch={showSearch}
        saving={saving}
        onFormatCitations={handleFormatCitations}
        formatting={formatting}
      />

      <div className="app-main">
        {showLibrary && (
          <>
            <div className="panel-left" style={{ width: leftResize.size }}>
              <LibraryPanel
                key={libraryRefreshKey}
                onSelect={(lit) => setEditLitId(lit.id)}
                onOpenCache={() => setCacheOpen(true)}
                onOpenDocTrees={() => setDocTreesOpen(true)}
              />
            </div>
            <div className="resize-handle-v" onMouseDown={leftResize.onMouseDown}>
              <div className="resize-handle-v-line" />
            </div>
          </>
        )}

        <div className="panel-center">
          <div className="editor-area">
            <Editor
              key={docId || "new"}
              initialContent={initialContent}
              onViewReady={(view: EditorView) => editor.setView(view)}
              onChange={handleContentChange}
            />
          </div>
          {showAI && (
            <>
              <div className="resize-handle-h" onMouseDown={aiResize.onMouseDown}>
                <div className="resize-handle-h-line" />
              </div>
              <div className="ai-panel-area" style={{ height: aiResize.size }}>
                <AIPanel
                  open={showAI}
                  onClose={() => setShowAI(false)}
                  getSelection={editor.getSelection}
                  onInsertText={(text) => editor.insertAtCursor(text)}
                  onOpenCorpus={() => setCorpusOpen(true)}
                  inline
                />
              </div>
            </>
          )}
        </div>

        {showSearch && (
          <>
            <div className="resize-handle-v" onMouseDown={rightResize.onMouseDown}>
              <div className="resize-handle-v-line" />
            </div>
            <div className="panel-right" style={{ width: rightResize.size }}>
              <RightPanel
                zhQuery={searchHook.zhQuery}
                onZhQueryChange={searchHook.setZhQuery}
                enQuery={searchHook.enQuery}
                onEnQueryChange={searchHook.setEnQuery}
                results={searchHook.results}
                warnings={searchHook.warnings}
                usedQueries={searchHook.usedQueries}
                semanticAvailable={searchHook.semanticAvailable}
                loading={searchHook.loading}
                onSearch={searchHook.doSearch}
                selectedIds={selectedIds}
                onToggleSelect={(item: LiteratureSearchItem) => citation.toggleSelect(item)}
                onInsertCitations={handleInsertCitations}
                onInsertSingleCitation={handleInsertSingleCitation}
                onPubMedImported={() => setLibraryRefreshKey((k) => k + 1)}
              />
            </div>
          </>
        )}
      </div>

      <StatusBar wordCount={editor.wordCount} citationCount={citationCount} saving={saving} dirty={dirty} />

      {/* Dialogs */}
      <CacheManager open={cacheOpen} onClose={() => setCacheOpen(false)} />
      <DocTreeManager open={docTreesOpen} onClose={() => setDocTreesOpen(false)} />
      <CorpusManager open={corpusOpen} onClose={() => setCorpusOpen(false)} />
      {/* Settings merged into AIPanel "Providers" tab */}
      <LiteratureDetail
        open={editLitId !== null}
        literatureId={editLitId}
        onClose={() => setEditLitId(null)}
        onUpdated={() => setLibraryRefreshKey((k) => k + 1)}
      />
      <OpenDialog
        open={openDialogOpen}
        onClose={() => setOpenDialogOpen(false)}
        onOpen={handleOpenDoc}
        currentDocId={docId}
      />
      {docId && (
        <ExportDialog
          open={exportOpen}
          onClose={() => setExportOpen(false)}
          documentId={docId}
        />
      )}
    </div>
  );
}
