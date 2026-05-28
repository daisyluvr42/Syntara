/**
 * Editor state management hook.
 */

import { useCallback, useRef, useState } from "react";
import type { EditorView } from "@codemirror/view";

export function useEditor() {
  const viewRef = useRef<EditorView | null>(null);
  const [wordCount, setWordCount] = useState(0);

  const setView = useCallback((view: EditorView | null) => {
    viewRef.current = view;
  }, []);

  const getContent = useCallback(() => {
    return viewRef.current?.state.doc.toString() ?? "";
  }, []);

  const insertAtCursor = useCallback((text: string) => {
    const view = viewRef.current;
    if (!view) return;

    const { from } = view.state.selection.main;
    view.dispatch({
      changes: { from, insert: text },
      selection: { anchor: from + text.length },
    });
    view.focus();
  }, []);

  const insertCitation = useCallback((citeKeys: string[]) => {
    if (citeKeys.length === 0) return;
    const markers = citeKeys.map((k) => `@${k}`).join("; ");
    insertAtCursor(`[${markers}]`);
  }, [insertAtCursor]);

  const replaceSelection = useCallback((text: string) => {
    const view = viewRef.current;
    if (!view) return;

    const { from, to } = view.state.selection.main;
    view.dispatch({
      changes: { from, to, insert: text },
    });
    view.focus();
  }, []);

  const getSelection = useCallback(() => {
    const view = viewRef.current;
    if (!view) return "";
    const { from, to } = view.state.selection.main;
    return view.state.sliceDoc(from, to);
  }, []);

  const replaceContent = useCallback((newContent: string) => {
    const view = viewRef.current;
    if (!view) return;
    view.dispatch({
      changes: { from: 0, to: view.state.doc.length, insert: newContent },
    });
    view.focus();
  }, []);

  const updateWordCount = useCallback((content: string) => {
    const text = content.trim();
    if (!text) {
      setWordCount(0);
      return;
    }
    // Count Chinese characters + English words
    const chineseChars = (text.match(/[\u4e00-\u9fff]/g) || []).length;
    const englishWords = text
      .replace(/[\u4e00-\u9fff]/g, " ")
      .split(/\s+/)
      .filter((w) => w.length > 0).length;
    setWordCount(chineseChars + englishWords);
  }, []);

  return {
    viewRef,
    setView,
    getContent,
    insertAtCursor,
    insertCitation,
    replaceContent,
    replaceSelection,
    getSelection,
    wordCount,
    updateWordCount,
  };
}
