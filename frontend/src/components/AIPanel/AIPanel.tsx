/**
 * AI assistant panel — Actions, Workflows, RAG Q&A, and Provider settings.
 */

import { useCallback, useEffect, useState } from "react";
import {
  aiAction,
  createProvider,
  deleteProvider,
  listProviders,
  listProviderBrands,
  ragQuery,
  updateProvider,
  type AIAction,
  type AIProviderItem,
  type AIProviderPayload,
  type AIProviderType,
  type ProviderBrand,
  type SearchResult,
} from "../../services/api";
import styles from "./AIPanel.module.css";
import WorkflowTab from "./WorkflowTab";

interface AIPanelProps {
  open: boolean;
  onClose: () => void;
  getSelection: () => string;
  onInsertText: (text: string) => void;
  onOpenCorpus?: () => void;
  inline?: boolean;
}

type AITab = "actions" | "rag" | "workflow" | "providers";

type AIProviderDraft = AIProviderPayload & {
  id?: string;
  api_key_set?: boolean;
};

export default function AIPanel({ open, onClose, getSelection, onInsertText, onOpenCorpus, inline }: AIPanelProps) {
  const [tab, setTab] = useState<AITab>("actions");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState("");

  // Actions tab
  const [selectedAction, setSelectedAction] = useState<AIAction>("summarize");
  const [sourceLang, setSourceLang] = useState("en");
  const [targetLang, setTargetLang] = useState("zh");

  // RAG tab
  const [question, setQuestion] = useState("");
  const [ragSources, setRagSources] = useState<SearchResult[]>([]);

  // Providers tab
  const [providers, setProviders] = useState<AIProviderItem[]>([]);
  const [editing, setEditing] = useState<AIProviderDraft | null>(null);
  const [brands, setBrands] = useState<ProviderBrand[]>([]);

  const fetchProviders = useCallback(async () => listProviders(), []);

  const loadProviders = useCallback(async () => {
    try {
      const data = await fetchProviders();
      setProviders(data);
    } catch (err) {
      console.error(err);
    }
  }, [fetchProviders]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    void (async () => {
      try {
        const data = await fetchProviders();
        if (!cancelled) setProviders(data);
        const brandsData = await listProviderBrands();
        if (!cancelled) setBrands(brandsData);
      } catch (err) {
        if (!cancelled) console.error(err);
      }
    })();
    return () => { cancelled = true; };
  }, [open, fetchProviders]);

  const isLocalProvider = (p: AIProviderType) => p === "local_openai_compat" || p === "local_anthropic_compat";

  if (!open) return null;

  /* --- Actions handlers --- */
  const handleAction = async () => {
    const text = getSelection();
    if (!text) {
      setResult("Please select text in the editor first.");
      return;
    }
    setLoading(true);
    setResult("");
    try {
      const res = await aiAction(selectedAction, text, undefined, sourceLang, targetLang);
      setResult(res.result);
    } catch (err: unknown) {
      setResult(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  /* --- RAG handler --- */
  const handleRAG = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setResult("");
    setRagSources([]);
    try {
      const res = await ragQuery(question);
      setResult(res.answer);
      setRagSources(res.sources || []);
    } catch (err: unknown) {
      setResult(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const handleInsert = () => {
    if (result) onInsertText(result);
  };

  /* --- Provider handlers --- */
  const handleSaveProvider = async () => {
    if (!editing) return;
    const payload: AIProviderPayload = {
      provider: editing.provider,
      name: editing.name,
      is_default: editing.is_default,
      max_tokens: editing.max_tokens,
      temperature: editing.temperature,
    };
    // Only include api_base and model_id if they have values
    if (editing.api_base) payload.api_base = editing.api_base;
    if (editing.model_id) payload.model_id = editing.model_id;

    const trimmedApiKey = editing.api_key?.trim() ?? "";
    if (!editing.id || trimmedApiKey || !editing.api_key_set) {
      payload.api_key = trimmedApiKey;
    }
    try {
      if (editing.id) {
        await updateProvider(editing.id, payload);
      } else {
        await createProvider(payload);
      }
      setEditing(null);
      await loadProviders();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteProvider = async (id: string) => {
    if (!confirm("Delete this provider?")) return;
    await deleteProvider(id);
    await loadProviders();
  };

  const newProvider = () => {
    setEditing({
      provider: "openai",
      name: "",
      api_base: "",
      api_key: "",
      model_id: "",
      is_default: false,
      max_tokens: 4096,
      temperature: 0.7,
    });
  };

  const actions: { id: AIAction; label: string }[] = [
    { id: "summarize", label: "Summarize" },
    { id: "translate", label: "Translate" },
    { id: "rewrite", label: "Rewrite / Polish" },
    { id: "expand", label: "Expand" },
    { id: "explain_term", label: "Explain Term" },
    { id: "logic_check", label: "Logic Check" },
    { id: "deai", label: "De-AI" },
    { id: "research_gap", label: "Research Gap" },
    { id: "paper_structure", label: "Paper Structure" },
    { id: "citation_check", label: "Citation Check" },
    { id: "abstract_draft", label: "Abstract Draft" },
  ];

  const tabBar = (
    <div className={inline ? styles.inlineTabs : styles.tabs}>
      <button
        className={`${styles.tab} ${tab === "actions" ? styles.tabActive : ""}`}
        onClick={() => setTab("actions")}
      >
        Actions
      </button>
      <button
        className={`${styles.tab} ${tab === "rag" ? styles.tabActive : ""}`}
        onClick={() => setTab("rag")}
      >
        Q&A (RAG)
      </button>
      <button
        className={`${styles.tab} ${tab === "workflow" ? styles.tabActive : ""}`}
        onClick={() => setTab("workflow")}
      >
        Workflow
      </button>
      <button
        className={`${styles.tab} ${tab === "providers" ? styles.tabActive : ""}`}
        onClick={() => setTab("providers")}
      >
        Providers
      </button>
      {inline && (
        <button className={styles.inlineCloseBtn} onClick={onClose} title="Close">&times;</button>
      )}
    </div>
  );

  const body = (
    <div className={styles.body}>
      {/* ---- Actions ---- */}
      {tab === "actions" && (
        <div className={styles.actionsTab}>
          <div className={styles.actionGrid}>
            {actions.map((a) => (
              <button
                key={a.id}
                className={`${styles.actionBtn} ${selectedAction === a.id ? styles.actionActive : ""}`}
                onClick={() => setSelectedAction(a.id)}
              >
                {a.label}
              </button>
            ))}
          </div>

          {selectedAction === "translate" && (
            <div className={styles.langRow}>
              <select value={sourceLang} onChange={(e) => setSourceLang(e.target.value)}>
                <option value="en">English</option>
                <option value="zh">Chinese</option>
              </select>
              <span>&rarr;</span>
              <select value={targetLang} onChange={(e) => setTargetLang(e.target.value)}>
                <option value="zh">Chinese</option>
                <option value="en">English</option>
              </select>
            </div>
          )}

          <button onClick={handleAction} disabled={loading} className={styles.runBtn}>
            {loading ? "Processing..." : "Run on Selected Text"}
          </button>
        </div>
      )}

      {/* ---- RAG ---- */}
      {tab === "rag" && (
        <div className={styles.ragTab}>
          <textarea
            placeholder="Ask a question based on your literature..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            className={styles.ragInput}
          />
          <button onClick={handleRAG} disabled={loading} className={styles.runBtn}>
            {loading ? "Searching & Generating..." : "Ask"}
          </button>
        </div>
      )}

      {/* ---- Workflow ---- */}
      {tab === "workflow" && (
        <WorkflowTab getSelection={getSelection} onInsertText={onInsertText} onOpenCorpus={onOpenCorpus} />
      )}

      {/* ---- Providers (formerly Settings) ---- */}
      {tab === "providers" && (
        <div className={styles.providersTab}>
          <div className={styles.providerList}>
            {providers.map((p) => (
              <div key={p.id} className={styles.providerItem}>
                <div className={styles.providerInfo}>
                  <div className={styles.providerNameRow}>
                    <strong>{p.name}</strong>
                    <span className={styles.providerType}>{p.provider}</span>
                    {p.is_default ? <span className={styles.providerBadge}>Default</span> : null}
                  </div>
                  <div className={styles.providerDetail}>
                    {p.model_id ? `Model: ${p.model_id}` : ""}
                    {p.model_id && p.api_base ? " · " : ""}
                    {isLocalProvider(p.provider) ? p.api_base : ""}
                  </div>
                </div>
                <div className={styles.providerActions}>
                  <button
                    onClick={() => setEditing({ ...p, is_default: Boolean(p.is_default) })}
                    className={styles.providerEditBtn}
                  >
                    Edit
                  </button>
                  <button onClick={() => handleDeleteProvider(p.id)} className={styles.providerDeleteBtn}>
                    &times;
                  </button>
                </div>
              </div>
            ))}
            {providers.length === 0 && (
              <div className={styles.providerEmpty}>No AI providers configured yet.</div>
            )}
          </div>

          <button onClick={newProvider} className={styles.providerAddBtn}>+ Add Provider</button>

          {editing && (
            <div className={styles.providerForm}>
              <h4>{editing.id ? "Edit Provider" : "New Provider"}</h4>
              <label className={styles.providerField}>
                Type
                <select
                  value={editing.provider}
                  onChange={(e) => {
                    const val = e.target.value as AIProviderType;
                    const brand = brands.find((b) => b.key === val);
                    setEditing({
                      ...editing,
                      provider: val,
                      name: editing.name || (brand ? brand.display_name : ""),
                      api_base: "",
                      model_id: "",
                    });
                  }}
                >
                  <optgroup label="Local">
                    <option value="local_openai_compat">Local (OpenAI Compatible)</option>
                    <option value="local_anthropic_compat">Local (Anthropic Compatible)</option>
                  </optgroup>
                  <optgroup label="Cloud">
                    {brands.map((b) => (
                      <option key={b.key} value={b.key}>{b.display_name}</option>
                    ))}
                  </optgroup>
                </select>
              </label>
              <label className={styles.providerField}>
                Name
                <input
                  value={editing.name}
                  onChange={(e) => setEditing({ ...editing, name: e.target.value })}
                  placeholder={isLocalProvider(editing.provider) ? "e.g., Local Qwen" : "e.g., My OpenAI"}
                />
              </label>
              {isLocalProvider(editing.provider) && (
                <>
                  <label className={styles.providerField}>
                    API Base URL
                    <input
                      value={editing.api_base}
                      onChange={(e) => setEditing({ ...editing, api_base: e.target.value })}
                      placeholder="http://localhost:1234/v1"
                    />
                  </label>
                  <label className={styles.providerField}>
                    Model ID
                    <input
                      value={editing.model_id}
                      onChange={(e) => setEditing({ ...editing, model_id: e.target.value })}
                      placeholder="e.g., qwen2.5-7b-instruct"
                    />
                  </label>
                </>
              )}
              {!isLocalProvider(editing.provider) && (
                <div className={styles.providerHint}>
                  Default model: {brands.find((b) => b.key === editing.provider)?.default_model ?? "\u2014"}
                  <br />
                  <span style={{ fontSize: "10px", color: "var(--color-text-tertiary)" }}>
                    API URL and model are preset. You can override Model ID below if needed.
                  </span>
                </div>
              )}
              {!isLocalProvider(editing.provider) && (
                <label className={styles.providerField}>
                  Model ID (optional override)
                  <input
                    value={editing.model_id}
                    onChange={(e) => setEditing({ ...editing, model_id: e.target.value })}
                    placeholder={brands.find((b) => b.key === editing.provider)?.default_model ?? ""}
                  />
                </label>
              )}
              <label className={styles.providerField}>
                API Key
                <input
                  type="password"
                  value={editing.api_key || ""}
                  onChange={(e) => setEditing({ ...editing, api_key: e.target.value })}
                  placeholder={
                    editing.api_key_set
                      ? "Leave blank to keep existing key"
                      : isLocalProvider(editing.provider)
                      ? "Leave empty if not required"
                      : "Required"
                  }
                />
              </label>
              <label className={styles.providerCheckbox}>
                <input
                  type="checkbox"
                  checked={editing.is_default}
                  onChange={(e) => setEditing({ ...editing, is_default: e.target.checked })}
                />
                Set as default
              </label>
              <div className={styles.providerFormActions}>
                <button onClick={handleSaveProvider} className={styles.runBtn}>Save</button>
                <button onClick={() => setEditing(null)} className={styles.secondaryBtn}>Cancel</button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ---- Result area (for Actions & RAG tabs) ---- */}
      {(tab === "actions" || tab === "rag") && result && (
        <div className={styles.resultArea}>
          <div className={styles.resultHeader}>
            <span>Result</span>
            <button onClick={handleInsert} className={styles.insertBtn}>
              Insert into Editor
            </button>
          </div>
          <div className={styles.resultText}>{result}</div>
          {ragSources.length > 0 && (
            <div className={styles.sources}>
              <strong>Sources:</strong>
              {ragSources.slice(0, 5).map((s, i) => (
                <div key={i} className={styles.sourceItem}>
                  {s.cite_key && <span className={styles.citeKey}>@{s.cite_key}</span>}
                  <span>{s.title}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );

  /* --- Inline bottom panel mode --- */
  if (inline) {
    return (
      <div className={styles.inlinePanel}>
        {tabBar}
        {body}
      </div>
    );
  }

  /* --- Dialog mode (fallback) --- */
  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>AI Assistant</h2>
          <button className={styles.closeBtn} onClick={onClose}>&times;</button>
        </div>
        {tabBar}
        {body}
      </div>
    </div>
  );
}
