/**
 * Backend API client for Syntara.
 */

const trimTrailingSlash = (value: string) => value.replace(/\/+$/, "");

const configuredApiBase = trimTrailingSlash(import.meta.env.VITE_API_BASE?.trim() || "");

export const API_BASE = configuredApiBase
  ? configuredApiBase.endsWith("/api")
    ? configuredApiBase
    : `${configuredApiBase}/api`
  : "/api";

export const apiUrl = (path: string) => `${API_BASE}${path}`;

export type SearchScope = "all" | "literature" | "corpus";
export type SearchSourceType = "literature" | "corpus";
export type AIProviderType =
  | "local_openai_compat"
  | "local_anthropic_compat"
  | "openai"
  | "anthropic"
  | "google"
  | "deepseek"
  | "mistral"
  | "groq"
  | "together"
  | "moonshot"
  | "zhipu"
  | "qwen"
  | "siliconflow"
  | "baichuan"
  | "cohere"
  | "perplexity"
  | "fireworks";

export interface Author {
  family: string;
  given: string;
  affiliation?: string | null;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(apiUrl(path), {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`API Error ${resp.status}: ${err}`);
  }
  return resp.json();
}

async function requestBlob(path: string, options?: RequestInit): Promise<Blob> {
  const resp = await fetch(apiUrl(path), {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`API Error ${resp.status}: ${err}`);
  }
  return resp.blob();
}

// --- Health ---
export interface HealthStatus {
  status: string;
  literature_count: number;
  document_count: number;
  corpus_count: number;
  vector_count: number;
  pandoc_available: boolean;
}

export const getHealth = () => request<HealthStatus>("/health");

// --- Literature ---
export interface LiteratureItem {
  id: string;
  cite_key: string;
  title: string;
  authors: Author[];
  abstract?: string | null;
  journal?: string | null;
  publisher?: string | null;
  volume?: string | null;
  issue?: string | null;
  pages?: string | null;
  year?: number | null;
  date?: string | null;
  doi?: string | null;
  pmid?: string | null;
  pmcid?: string | null;
  issn?: string | null;
  isbn?: string | null;
  type?: string;
  keywords?: string[];
  tags: string[];
  language?: string;
  file_path?: string | null;
  file_hash?: string | null;
  file_size?: number | null;
  full_text?: string | null;
  full_text_length?: number;
  processing_status?: string;
  processing_error?: string | null;
  processing_progress?: { stage: string; current: number; total: number } | null;
  search_ready_fts?: boolean;
  search_ready_vector?: boolean;
  metadata_sources?: Record<string, string>;
  metadata_confidence: number;
  manually_verified: boolean;
  created_at?: string;
  updated_at?: string;
  imported_at?: string;
}

export interface LiteraturePayload {
  title?: string;
  authors?: Author[];
  abstract?: string | null;
  journal?: string | null;
  publisher?: string | null;
  volume?: string | null;
  issue?: string | null;
  pages?: string | null;
  year?: number | null;
  date?: string | null;
  doi?: string | null;
  pmid?: string | null;
  pmcid?: string | null;
  issn?: string | null;
  isbn?: string | null;
  type?: string;
  keywords?: string[];
  tags?: string[];
  language?: string;
  manually_verified?: boolean;
}

export interface ImportPdfResponse {
  id: string;
  cite_key: string;
  title: string;
  confidence: number;
  processing_status: string;
  message: string;
}

export const listLiterature = (skip = 0, limit = 50, tag?: string) =>
  request<{ items: LiteratureItem[]; total: number }>(
    `/literature?skip=${skip}&limit=${limit}${tag ? `&tag=${tag}` : ""}`
  );

export const getLiterature = (id: string) =>
  request<LiteratureItem>(`/literature/${id}`);

export interface LiteraturePreview {
  snippet: string;
  char_count: number;
  word_count: number;
  page_count: number;
  file_size: number;
  search_ready_fts: boolean;
  search_ready_vector: boolean;
  outline: { depth: number; title: string; page?: number }[];
}

export const getLiteraturePreview = (id: string) =>
  request<LiteraturePreview>(`/literature/${id}/preview`);

export const createLiterature = (data: LiteraturePayload) =>
  request<{ id: string; cite_key: string }>("/literature", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateLiterature = (id: string, data: LiteraturePayload) =>
  request<{ ok: boolean }>(`/literature/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });

export const deleteLiterature = (id: string) =>
  request<{ ok: boolean }>(`/literature/${id}`, { method: "DELETE" });

export const retryProcessing = (id: string) =>
  request<{ ok: boolean; message: string }>(`/literature/${id}/retry`, { method: "POST" });

export const importPdf = async (file: File) => {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(apiUrl("/literature/import/pdf"), {
    method: "POST",
    body: form,
  });
  if (!resp.ok) {
    const raw = await resp.text();
    let msg = raw;
    try {
      const parsed = JSON.parse(raw);
      msg = parsed.detail || parsed.message || raw;
    } catch { /* not JSON, use raw */ }
    throw new Error(msg);
  }
  return resp.json() as Promise<ImportPdfResponse>;
};

export const getAllTags = () => request<string[]>("/literature/tags/all");

// --- Search ---
export interface SearchResult {
  id: string;
  source_type: SearchSourceType;
  score: number;
  snippet?: string;
  cite_key?: string;
  title?: string;
  authors?: Author[];
  year?: number;
  journal?: string;
  abstract?: string;
  description?: string;
  heading?: string;
  page_number?: number;
  element_type?: string;
}

export const search = (query: string, scope: SearchScope = "all", top_k = 20) =>
  request<{ results: SearchResult[]; total: number }>("/search", {
    method: "POST",
    body: JSON.stringify({ query, scope, top_k }),
  });

export interface SearchHighlight {
  start: number;
  end: number;
}

export interface LiteratureSearchHit {
  chunk_index: number;
  content: string;
  heading: string;
  page_number: number;
  element_type: string;
  score: number;
  matched_by: string[];
  matched_terms: string[];
  highlights: SearchHighlight[];
}

export interface LiteratureSearchPreview {
  content: string;
  heading: string;
  page_number: number;
  highlights: SearchHighlight[];
}

export interface LiteratureSearchQuery {
  lang: "zh" | "en";
  text: string;
  source: "user" | "ai";
}

export interface LiteratureSearchItem {
  id: string;
  cite_key: string;
  title: string;
  authors: Author[];
  year?: number | null;
  journal?: string | null;
  hit_count: number;
  top_score: number;
  match_languages: string[];
  preview_hit: LiteratureSearchPreview;
  hits: LiteratureSearchHit[];
}

export interface GroupedLiteratureSearchResponse {
  semantic_available: boolean;
  warnings: string[];
  used_queries: LiteratureSearchQuery[];
  results: LiteratureSearchItem[];
  total: number;
}

export const searchLiteratureGrouped = (
  zhQuery: string,
  enQuery: string,
  providerId?: string,
  topK = 20,
) =>
  request<GroupedLiteratureSearchResponse>("/search/literature-grouped", {
    method: "POST",
    body: JSON.stringify({
      zh_query: zhQuery,
      en_query: enQuery,
      provider_id: providerId,
      top_k: topK,
    }),
  });

// --- Search history ---
export const getSearchHistory = (lang: string, prefix: string, limit = 10) =>
  request<{ suggestions: string[] }>(
    `/search/history?lang=${encodeURIComponent(lang)}&prefix=${encodeURIComponent(prefix)}&limit=${limit}`
  );

// --- Chunk context ---
export interface PageContextResponse {
  page_number: number;
  page_text: string;
  highlight_start: number;
  highlight_end: number;
}

export const fetchChunkContext = (litId: string, chunkIndex: number) =>
  request<PageContextResponse>("/search/chunk-context", {
    method: "POST",
    body: JSON.stringify({ lit_id: litId, chunk_index: chunkIndex }),
  });

// --- Dismissed hits ---
export interface DismissedHitPayload {
  query_key: string;
  lit_id: string;
  chunk_index: number;
}

export const dismissHit = (payload: DismissedHitPayload) =>
  request<{ ok: boolean }>("/search/dismiss-hit", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const getDismissedHits = (queryKey: string) =>
  request<{ dismissed: string[] }>(`/search/dismissed-hits?query_key=${encodeURIComponent(queryKey)}`);

// --- Documents ---
export interface DocumentItem {
  id: string;
  title: string;
  content?: string;
  csl_style: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentUpdatePayload {
  title?: string;
  content?: string;
  csl_style?: string;
}

export interface CitationItem {
  id: string;
  document_id: string;
  literature_id: string;
  cite_key: string;
  position: number;
  context: string;
  order: number;
  lit_title: string;
  authors: Author[];
  year?: number | null;
  journal?: string | null;
}

export const listDocuments = () =>
  request<{ items: DocumentItem[]; total: number }>("/documents");

export const getDocument = (id: string) =>
  request<DocumentItem>(`/documents/${id}`);

export const createDocument = (data: { title?: string; content?: string; csl_style?: string }) =>
  request<{ id: string; title: string }>("/documents", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateDocument = (id: string, data: DocumentUpdatePayload) =>
  request<{ ok: boolean }>(`/documents/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });

export const deleteDocument = (id: string) =>
  request<{ ok: boolean }>(`/documents/${id}`, { method: "DELETE" });

export const getDocumentCitations = (id: string) =>
  request<CitationItem[]>(`/documents/${id}/citations`);

export const addCitation = (docId: string, literatureId: string, citeKey: string, position = 0, context = "") =>
  request<{ id: string; order: number }>(
    `/documents/${docId}/citations?literature_id=${literatureId}&cite_key=${citeKey}&position=${position}&context=${encodeURIComponent(context)}`,
    { method: "POST" }
  );

// --- Citation Formatting ---
export type CitationStyle = "vancouver" | "apa" | "gb-t-7714";

export const formatCitations = (content: string, style: CitationStyle) =>
  request<{ content: string }>("/documents/format-citations", {
    method: "POST",
    body: JSON.stringify({ content, style }),
  });

export const unformatCitations = (content: string) =>
  request<{ content: string }>("/documents/unformat-citations", {
    method: "POST",
    body: JSON.stringify({ content }),
  });

// --- PubMed ---
export interface PubMedMeshTerm {
  term: string;
  major: boolean;
}

export interface PubMedItem {
  pmid: string;
  title: string;
  authors: Author[];
  abstract?: string;
  journal?: string;
  year?: number | null;
  doi?: string | null;
  pmcid?: string | null;
  volume?: string | null;
  issue?: string | null;
  pages?: string | null;
  keywords?: string[];
  mesh_terms?: PubMedMeshTerm[];
  pub_types?: string[];
  language?: string | null;
}

export interface PubMedImportItem {
  id: string;
  cite_key: string;
  title: string;
  pmid: string;
}

export interface PubMedSkippedItem {
  pmid: string;
  reason: string;
}

export interface PubMedSearchTerm {
  term: string;
  field: string;
  op: string; // AND / OR / NOT
}

export interface PubMedAdvancedSearchRequest {
  terms?: PubMedSearchTerm[];
  raw_query?: string;
  max_results?: number;
  page?: number;
  sort?: string;
  date_type?: string;
  min_date?: string;
  max_date?: string;
  rel_date?: number;
}

export interface PubMedSearchResponse {
  results: PubMedItem[];
  total: number;
  page?: number;
  max_results?: number;
  pages?: number;
  built_query?: string;
  query_translation?: string;
}

export interface PubMedFieldsResponse {
  fields: string[];
  sort_options: Record<string, string>;
}

export const getPubMedFields = () =>
  request<PubMedFieldsResponse>("/pubmed/fields");

export const searchPubMed = (query: string, maxResults = 20) =>
  request<PubMedSearchResponse>(
    `/pubmed/search?query=${encodeURIComponent(query)}&max_results=${maxResults}`
  );

export const searchPubMedAdvanced = (req: PubMedAdvancedSearchRequest) =>
  request<PubMedSearchResponse>("/pubmed/search/advanced", {
    method: "POST",
    body: JSON.stringify(req),
  });

export const importFromPubMed = (pmids: string[]) =>
  request<{ imported: PubMedImportItem[]; skipped: PubMedSkippedItem[] }>("/pubmed/import", {
    method: "POST",
    body: JSON.stringify(pmids),
  });

// --- AI ---
export type AIAction =
  | "summarize"
  | "translate"
  | "rewrite"
  | "expand"
  | "explain_term"
  | "logic_check"
  | "deai"
  | "research_gap"
  | "paper_structure"
  | "citation_check"
  | "abstract_draft";

export interface WorkflowStepResult {
  action: AIAction;
  result: string;
}

export interface WorkflowRunResponse {
  result: string;
  steps: WorkflowStepResult[];
  completed: boolean;
  error: string | null;
}

export const aiAction = (action: AIAction, text: string, providerId?: string, sourceLang = "en", targetLang = "zh") =>
  request<{ result: string }>("/ai/action", {
    method: "POST",
    body: JSON.stringify({
      action,
      text,
      provider_id: providerId,
      source_lang: sourceLang,
      target_lang: targetLang,
    }),
  });

export const workflowRun = (
  steps: AIAction[],
  text: string,
  providerId?: string,
  sourceLang = "en",
  targetLang = "zh",
) =>
  request<WorkflowRunResponse>("/ai/workflow", {
    method: "POST",
    body: JSON.stringify({
      steps,
      text,
      provider_id: providerId,
      source_lang: sourceLang,
      target_lang: targetLang,
    }),
  });

export const ragQuery = (
  question: string,
  providerId?: string,
  searchScope: SearchScope = "all",
  topK = 5,
  useTree = true,
) =>
  request<{ answer: string; sources: SearchResult[]; cited_keys: string[] }>("/ai/rag", {
    method: "POST",
    body: JSON.stringify({
      question,
      provider_id: providerId,
      search_scope: searchScope,
      top_k: topK,
      use_tree: useTree,
    }),
  });

export interface AIProviderItem {
  id: string;
  provider: AIProviderType;
  name: string;
  api_base: string;
  api_key: string | null;
  model_id: string;
  is_default: boolean | number;
  max_tokens: number;
  temperature: number;
  api_key_set: boolean;
}

export interface AIProviderPayload {
  provider: AIProviderType;
  name: string;
  api_base?: string;
  api_key?: string | null;
  model_id?: string;
  is_default: boolean;
  max_tokens: number;
  temperature: number;
}

export const listProviders = () => request<AIProviderItem[]>("/ai/providers");

export const createProvider = (data: AIProviderPayload) =>
  request<{ id: string }>("/ai/providers", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateProvider = (id: string, data: Partial<AIProviderPayload>) =>
  request<{ ok: boolean }>(`/ai/providers/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });

export const deleteProvider = (id: string) =>
  request<{ ok: boolean }>(`/ai/providers/${id}`, { method: "DELETE" });

// --- Embedding Config ---
export interface EmbeddingConfigData {
  mode: string; // "python" | "local" | "cloud"
  api_base: string;
  api_key_set: boolean;
  model: string;
  cloud_brand: string;
}

export interface EmbeddingConfigPayload {
  mode: string;
  api_base?: string;
  api_key?: string;
  model?: string;
  cloud_brand?: string;
}

export interface EmbeddingBrand {
  key: string;
  display_name: string;
  default_model: string;
}

export const getEmbeddingConfig = () =>
  request<EmbeddingConfigData>("/ai/embedding-config");

export const updateEmbeddingConfig = (data: EmbeddingConfigPayload) =>
  request<{ ok: boolean }>("/ai/embedding-config", {
    method: "PUT",
    body: JSON.stringify(data),
  });

export const listEmbeddingBrands = () =>
  request<EmbeddingBrand[]>("/ai/embedding-brands");

export interface ProviderBrand {
  key: string;
  display_name: string;
  default_model: string;
}

export const listProviderBrands = () => request<ProviderBrand[]>("/ai/provider-brands");

// --- Corpus ---
export interface CorpusItem {
  id: string;
  title: string;
  description?: string | null;
  file_path: string;
  file_type: string;
  file_hash: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export const listCorpus = () =>
  request<{ items: CorpusItem[]; total: number }>("/corpus");

export const uploadCorpus = async (file: File, title: string, description: string, tags: string) => {
  const form = new FormData();
  form.append("file", file);
  form.append("title", title);
  form.append("description", description);
  form.append("tags", tags);
  const resp = await fetch(apiUrl("/corpus/upload"), {
    method: "POST",
    body: form,
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json() as Promise<{ id: string; title: string }>;
};

export const deleteCorpus = (id: string) =>
  request<{ ok: boolean }>(`/corpus/${id}`, { method: "DELETE" });

// --- Export ---
export interface ExportStyle {
  id: string;
  name: string;
  path: string;
}

export const getExportStyles = () => request<ExportStyle[]>("/export/styles");
export const getPandocStatus = () => request<{ available: boolean; version: string | null }>("/export/pandoc-status");

export const exportMarkdown = (docId: string, cslStyle = "vancouver") =>
  requestBlob(`/export/markdown/${docId}?csl_style=${cslStyle}`, { method: "POST" });

export const exportDocx = (docId: string, cslStyle = "vancouver") =>
  requestBlob(`/export/docx/${docId}?csl_style=${cslStyle}`, { method: "POST" });

export const exportPdf = (docId: string, cslStyle = "vancouver") =>
  requestBlob(`/export/pdf/${docId}?csl_style=${cslStyle}`, { method: "POST" });

export const exportHtml = (docId: string, cslStyle = "vancouver") =>
  requestBlob(`/export/html/${docId}?csl_style=${cslStyle}`, { method: "POST" });

export const exportBibtex = (citeKeys?: string[]) => {
  const param = citeKeys ? `?cite_keys=${citeKeys.join(",")}` : "";
  return requestBlob(`/export/bibtex${param}`);
};

// --- Extract Cache ---
export interface CacheItem {
  file_hash: string;
  file_name: string;
  title: string;
  source_type: string;
  element_count: number;
  file_size_kb: number;
  created_at: string;
}

export interface CacheStats {
  total_items: number;
  total_size_kb: number;
  by_source: Record<string, number>;
}

export interface CacheDetail {
  file_hash: string;
  file_name: string;
  title: string;
  source_type: string;
  element_count: number;
  file_size_kb: number;
  created_at: string;
  elements: Record<string, unknown>[];
  total_text_length: number;
}

export const listExtractCache = () =>
  request<{ items: CacheItem[] }>("/extract-cache");

export const getExtractCacheDetail = (fileHash: string) =>
  request<CacheDetail>(`/extract-cache/${fileHash}`);

export const deleteExtractCache = (fileHash: string) =>
  request<{ ok: boolean }>(`/extract-cache/${fileHash}`, { method: "DELETE" });

export const clearExtractCache = () =>
  request<{ ok: boolean; deleted: number }>("/extract-cache?all=true", { method: "DELETE" });

export const getExtractCacheStats = () =>
  request<CacheStats>("/extract-cache/stats");

// --- Document Trees (PageIndex RAG) ---
export interface DocTreeInfo {
  literature_id: string;
  lit_title?: string;
  cite_key?: string;
  title: string;
  node_count: number;
  leaf_count: number;
  summaries_generated: boolean;
  size_bytes: number;
}

export interface DocTreeStats {
  total_trees: number;
  summarized: number;
  unsummarized: number;
  total_size_bytes: number;
  total_nodes: number;
  total_leaves: number;
}

export interface DocTreeNode {
  id: string;
  title: string;
  level: number;
  summary: string;
  content: string;
  page_start: number;
  page_end: number;
  element_count: number;
  children: DocTreeNode[];
  _pruned_children?: number;
}

export interface DocTree {
  literature_id: string;
  title: string;
  node_count: number;
  leaf_count: number;
  summaries_generated: boolean;
  root: DocTreeNode;
}

export const listDocTrees = () =>
  request<{ items: DocTreeInfo[]; total: number }>("/doc-trees");

export const getDocTreeStats = () =>
  request<DocTreeStats>("/doc-trees/stats");

export const getDocTree = (litId: string, maxDepth?: number) =>
  request<DocTree>(`/doc-trees/${litId}${maxDepth != null ? `?max_depth=${maxDepth}` : ""}`);

export const buildDocTree = (litId: string, autoSummarize = false, providerId?: string) =>
  request<{ literature_id: string; node_count: number; leaf_count: number; summaries_generated: boolean }>(
    `/doc-trees/${litId}/build`,
    {
      method: "POST",
      body: JSON.stringify({ auto_summarize: autoSummarize, provider_id: providerId }),
    },
  );

export const summarizeDocTree = (litId: string, providerId?: string) =>
  request<{ literature_id: string; node_count: number; summaries_generated: boolean }>(
    `/doc-trees/${litId}/summarize`,
    {
      method: "POST",
      body: JSON.stringify({ provider_id: providerId }),
    },
  );

export const deleteDocTree = (litId: string) =>
  request<{ ok: boolean }>(`/doc-trees/${litId}`, { method: "DELETE" });

export const buildAllDocTrees = (autoSummarize = false, providerId?: string) =>
  request<{ built: number; skipped: number; errors: number }>("/doc-trees/build-all", {
    method: "POST",
    body: JSON.stringify({ auto_summarize: autoSummarize, provider_id: providerId }),
  });

export const summarizeAllDocTrees = (providerId?: string) =>
  request<{ summarized: number; errors: number }>("/doc-trees/summarize-all", {
    method: "POST",
    body: JSON.stringify({ provider_id: providerId }),
  });
