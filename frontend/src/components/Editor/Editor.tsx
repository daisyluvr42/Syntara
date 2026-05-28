/**
 * CodeMirror 6 Markdown editor component.
 */

import { useEffect, useRef } from "react";
import { EditorView, keymap, lineNumbers, highlightActiveLine, drawSelection } from "@codemirror/view";
import { EditorState } from "@codemirror/state";
import { markdown } from "@codemirror/lang-markdown";
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
import { searchKeymap, highlightSelectionMatches } from "@codemirror/search";
import { syntaxHighlighting, defaultHighlightStyle } from "@codemirror/language";

interface EditorProps {
  initialContent?: string;
  onViewReady?: (view: EditorView) => void;
  onChange?: (content: string) => void;
}

export default function Editor({ initialContent = "", onViewReady, onChange }: EditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const updateListener = EditorView.updateListener.of((update) => {
      if (update.docChanged && onChange) {
        onChange(update.state.doc.toString());
      }
    });

    const state = EditorState.create({
      doc: initialContent,
      extensions: [
        lineNumbers(),
        highlightActiveLine(),
        drawSelection(),
        history(),
        markdown(),
        syntaxHighlighting(defaultHighlightStyle),
        highlightSelectionMatches(),
        keymap.of([...defaultKeymap, ...historyKeymap, ...searchKeymap]),
        updateListener,
        EditorView.lineWrapping,
        EditorView.theme({
          "&": { height: "100%", fontSize: "15px" },
          ".cm-scroller": {
            overflow: "auto",
            fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif",
            lineHeight: "1.7",
          },
          ".cm-content": { padding: "24px 32px", minHeight: "100%" },
          ".cm-gutters": {
            backgroundColor: "#f8f9fb",
            borderRight: "1px solid #e2e5ea",
            color: "#adb3bd",
            fontSize: "12px",
          },
          ".cm-activeLineGutter": { backgroundColor: "#edf2fc" },
          ".cm-activeLine": { backgroundColor: "rgba(74,143,231,0.04)" },
          ".cm-cursor": { borderLeftColor: "#4a8fe7" },
          "&.cm-focused .cm-selectionBackground, .cm-selectionBackground": {
            backgroundColor: "rgba(74,143,231,0.18)",
          },
        }),
      ],
    });

    const view = new EditorView({
      state,
      parent: containerRef.current,
    });

    viewRef.current = view;
    onViewReady?.(view);

    return () => {
      view.destroy();
      viewRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      ref={containerRef}
      style={{ height: "100%", width: "100%", overflow: "hidden" }}
    />
  );
}
