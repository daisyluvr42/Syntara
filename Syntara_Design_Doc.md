# Syntara — 文献管理与写作工作台 设计文档

> **版本**: v0.4 (新增 AI 辅助写作 + 语料库 + Pandoc 多格式导出)  
> **日期**: 2026-03-28  
> **作者**: Havonx / Monad Lab Works

---

## 1. 项目概述

### 1.1 目标

构建一个本地优先（local-first）的文献管理与学术写作工作台，核心能力包括：

- 导入 PDF/MD 文献，自动提取引用元数据
- 集成 PubMed 检索，扩充文献库
- 基于关键词或自然语言问题在文献库中语义检索
- 提供 Markdown 写作编辑器，支持边写边搜、一键插入引用
- 输出带格式化参考文献的完整文档，兼容 Zotero/EndNote 的 CSL 样式

### 1.2 用户画像

口腔种植专科医生，需要撰写书籍章节，手头有大量中英文 PDF 文献（几 MB 到几百 MB），时间有限无法逐篇通读，需要工具辅助定位信息与管理引用。

### 1.3 核心使用流程

```
导入文献 PDF/MD ──→ 自动提取元数据 ──→ 全文索引入库
                                           │
PubMed 搜索 ──→ 下载/导入 ─────────────────┘
                                           │
                                           ▼
                                     文献库（检索就绪）
                                           │
        ┌──────────────────────────────────┘
        ▼
  写作编辑器（MD）──→ 输入关键词搜索 ──→ 侧边返回匹配文献列表
        │                                    │
        │              光标定位 + 点选文献 ←──┘
        │                     │
        ▼                     ▼
  文档中插入引用标记    自动编号/格式化
        │
        ▼
  导出完整 MD + 参考文献列表（CSL 格式）
```

---

## 2. 功能模块拆解

### 2.1 文献导入与存储

| 功能点 | 说明 |
|--------|------|
| 本地文件导入 | 支持拖放或选择文件夹批量导入 PDF、MD 文件 |
| 文件大小处理 | 需处理几百 MB 的大 PDF（扫描版/高分辨率图片），需异步解析 |
| 文件去重 | 基于文件哈希（SHA-256）+ 元数据 DOI 双重去重 |
| 存储结构 | 原始文件保留在用户指定目录，数据库只存元数据 + 索引 + 文件路径引用 |
| PubMed 导入 | 搜索结果可选择性导入元数据，有 PDF 链接的可尝试自动下载 |

### 2.2 元数据自动提取

PDF 学术文献的元数据提取采用轻量方案，按优先级依次尝试：

**路径 A — DOI/PMID 提取 + API 反查（首选）**

大多数学术 PDF 中包含 DOI 或 PMID 信息。通过 PyMuPDF 提取前两页文本，用正则匹配找到 DOI（格式如 `10.xxxx/...`）或 PMID，然后通过外部 API 获取权威的结构化元数据：

- CrossRef API（`https://api.crossref.org/works/{DOI}`）→ 结构化元数据 JSON（标题、作者、期刊、卷期页码、日期等）
- PubMed E-utilities（`https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi`）→ XML（对生物医学文献覆盖最全）

这条路径返回的是出版社/数据库提供的权威数据，准确度最高。

**路径 B — PDF 内嵌元数据（补充）**

部分 PDF 在文件属性中嵌入了 Title / Author / Subject 等字段，可通过 PyMuPDF 的 `doc.metadata` 读取。这些信息通常不完整，但可作为路径 A 的补充或初始填充。

**路径 C — 手动录入/编辑（兜底）**

对于无法自动提取元数据的文献（老文献、扫描版、非标准格式），提供友好的手动录入 UI。同时，所有自动提取的元数据都支持手动修正。

**元数据来源标记**

每个字段附带来源标记（crossref / pubmed / pdf_meta / manual），供用户在 UI 中快速判断数据可信度。手动校验过的文献会被标记为 `manually_verified`。

### 2.3 全文索引与检索

需要支持两种检索模式：

**关键词检索（精确匹配）**

- 使用 SQLite FTS5 对文献的标题、摘要、全文建立全文索引
- 支持中英文混合分词（中文使用 jieba 或 pkuseg 分词后写入 FTS5）
- 响应速度快，适合精确术语查找

**语义检索（模糊/问题式查找）**

- 将文献全文按段落或语义块切分（chunk），生成向量嵌入
- 嵌入模型推荐：`bge-m3`（多语言，中英文表现好，1024 维）或 `nomic-embed-text`
- 向量存储：本地使用 `ChromaDB`（纯 Python，pip install 即用，数据存本地文件夹，无需 Docker）
- 查询时将用户输入也编码为向量，做 ANN 近似最近邻检索
- 返回 top-K 相关段落 + 所属文献

**混合检索策略**

实际使用中建议两种模式同时运行，用 RRF（Reciprocal Rank Fusion）融合排序结果，既保证术语命中又保证语义相关。

### 2.4 PubMed 集成

| 功能 | API | 说明 |
|------|-----|------|
| 搜索 | E-utilities `esearch` | 接受查询词，返回 PMID 列表 |
| 获取摘要/元数据 | E-utilities `efetch` | 输入 PMID，返回结构化 XML（含全部引用字段） |
| 获取全文链接 | PMC OA API | 对开放获取文献返回 PDF 下载链接 |
| 频率限制 | — | 无 API Key 限 3 req/s，注册 API Key 后限 10 req/s |

工作流：用户在工作台输入检索词 → 调用 esearch → 展示结果列表 → 用户勾选 → 调用 efetch 拉取元数据 → 尝试下载 PDF → 入库。

### 2.5 写作编辑器

**编辑器内核选型**

| 方案 | 优势 | 劣势 |
|------|------|------|
| CodeMirror 6 | 轻量、Markdown 原生支持、扩展性强 | 需自行实现预览 |
| ProseMirror | 结构化文档模型、适合复杂编辑 | 学习曲线较陡 |
| Milkdown | 基于 ProseMirror，开箱即用 Markdown | 社区较小 |
| Tiptap | 基于 ProseMirror，API 友好 | 同上 |

**推荐方案**：CodeMirror 6 —— 因为目标是 Markdown 纯文本写作（非富文本），CM6 的 Markdown 语法高亮、光标控制、自定义补全（用于引用插入）都很成熟。

**关键交互设计**

1. **搜索触发**：编辑器上方或侧边有搜索框，输入关键词后侧栏显示匹配文献列表
2. **文献列表项**：每项显示标题、作者（缩写）、年份、相关度评分、匹配段落摘要
3. **引用插入**：
   - 用户将光标放在目标位置
   - 在侧栏点选一篇或多篇文献（复选框）
   - 点击「插入引用」按钮
   - 编辑器光标位置自动插入引用标记，如 `[@smith2024]` 或 `[^ref-a1b2c3]`
4. **引用标记格式**：使用 Pandoc 风格的 citation key（`[@citekey]`），便于后续用 Pandoc 或 CSL 处理器渲染

### 2.6 引用管理与参考文献生成

**引用标记体系**

文档内使用 Pandoc citation 语法：

```markdown
种植体早期失败率约为 1-3% [@esposito2012; @jung2018]，
其中上颌后牙区的失败率显著高于下颌前牙区 [@moy2005]。
```

**Citation Key 生成规则**

`第一作者姓氏小写 + 年份`，冲突时追加 a/b/c，如 `smith2024a`。

**参考文献格式化**

使用 CSL（Citation Style Language）引擎进行格式化：

- CSL 是 Zotero、Mendeley、EndNote 共用的开放格式标准
- 样式文件（`.csl`）可从 Zotero Style Repository 下载（9000+ 种期刊样式）
- JS 端可用 `citeproc-js`（CSL 的参考实现），Python 端可用 `citeproc-py`

**导出流程**

1. 扫描文档中所有 `[@...]` 引用标记
2. 从文献库中查找对应元数据
3. 调用 CSL 处理器，按选定样式生成格式化引用（正文内的编号或作者-年份格式）和参考文献列表
4. 将正文引用标记替换为格式化结果，文末附上完整参考文献列表
5. 输出最终 Markdown 文件

**与 Zotero/EndNote 的兼容性**

- 文献库支持导出为 BibTeX（`.bib`）或 CSL-JSON 格式 → 可直接导入 Zotero
- CSL 样式文件通用 → 用户可从 Zotero 复制 `.csl` 文件到本项目使用
- 支持导入 Zotero 导出的 BibTeX/RIS 文件 → 反向兼容

### 2.7 AI 辅助写作

在写作过程中，LLM 可以辅助完成多种任务，提升效率。本模块同时支持本地推理和云端 API，用户按需切换。

**支持的 AI 能力**

| 能力 | 说明 | 典型场景 |
|------|------|---------|
| 文献摘要 | 对选中的文献段落生成结构化摘要 | 快速了解一篇未读文献的核心观点 |
| 翻译 | 中英互译，保留学术术语准确性 | 阅读英文文献 / 用英文撰写内容 |
| 改写/润色 | 对已写段落进行学术风格润色或降重 | 初稿改写为正式学术语言 |
| 扩写 | 根据提纲或关键词展开段落 | 从笔记快速生成初稿 |
| 问答 | 基于文献库内容回答问题（RAG 模式） | "种植体周围炎的风险因素有哪些？" |
| 术语解释 | 对选中术语给出定义和相关文献 | 写作中遇到不确定的专业概念 |

**LLM Provider 架构**

采用统一的 Provider 抽象层，底层对接不同来源：

```
┌─────────────────────────────────┐
│        AI Service 抽象层         │
│  统一接口：chat / summarize /    │
│  translate / rewrite / expand   │
├─────────┬───────────┬───────────┤
│  Local  │  Cloud    │  Cloud    │
│ LM Studio│ Anthropic │ OpenAI   │
│ (本地)   │ (API Key) │(API Key) │
└─────────┴───────────┴───────────┘
```

- **本地 LLM**：通过 LM Studio 的 OpenAI 兼容 API（`http://localhost:1234/v1/chat/completions`），使用已部署的模型（如 Qwen 系列），零成本、离线可用
- **Cloud Provider**：支持 Anthropic Claude API 和 OpenAI API，用户在设置页面填入自己的 API Key 即可，Key 仅存本地，不上传任何服务
- **切换逻辑**：UI 提供下拉选择当前 Provider；本地模型离线可用，Cloud 需联网；长文本/高质量任务推荐 Cloud，日常摘要/翻译本地模型即可

**RAG（检索增强生成）流程**

当用户提问或要求基于文献生成内容时，系统自动走 RAG 流程：

```
用户提问 / 选择「基于文献回答」
      │
      ▼
  ① 将问题通过检索引擎（FTS5 + ChromaDB）查找相关段落
      │
      ▼
  ② 取 Top-K 相关段落作为上下文
      │
      ▼
  ③ 构造 Prompt：系统指令 + 相关段落（含出处标注）+ 用户问题
      │
      ▼
  ④ 调用 LLM（本地或 Cloud）生成回答
      │
      ▼
  ⑤ 回答中附带段落来源引用 → 用户可一键将引用插入文档
```

**自定义语料库导入**

除了文献库中的 PDF/MD 文献外，用户可以额外导入自己的语料库，用于增强 AI 的领域知识：

| 支持格式 | 说明 |
|---------|------|
| Markdown 文件/文件夹 | 个人笔记、已写章节、教案、课件笔记等 |
| 纯文本文件 (.txt) | 任意文本材料 |
| PDF | 教科书、手册、指南等非文献类 PDF |
| BibTeX 附带笔记 | Zotero 导出的带注释条目 |

导入的语料与文献库走相同的索引 Pipeline（分块 → FTS5 + 向量嵌入），但在数据库中用 `source_type` 字段区分（`literature` vs `corpus`），检索时可选择搜索范围：仅文献库 / 仅语料库 / 全部。

语料库的典型用途：

- 导入自己过去写的章节，让 AI 保持一致的写作风格和术语用法
- 导入教科书内容，补充文献库中没有的基础知识
- 导入临床笔记或案例，让 AI 在生成内容时参考实际经验

### 2.8 Pandoc 集成与多格式导出

在 2.6 的 CSL 引用引擎基础上，集成 Pandoc 实现从 Markdown 到多种最终格式的转换。

**为什么用 Pandoc**

Pandoc 是文档格式转换的瑞士军刀，原生支持 `[@citekey]` 引用语法 + CSL 样式文件，也就是说本项目的 Markdown + 引用标记可以直接被 Pandoc 处理，无需任何中间转换。

**支持的导出格式**

| 目标格式 | 方式 | 说明 |
|---------|------|------|
| Markdown (.md) | 内置 CSL 引擎直接输出 | 引用标记替换为格式化文本 + 参考文献列表 |
| Word (.docx) | Pandoc 转换 | 支持自定义 Word 模板（reference.docx），控制字体/页面/标题样式 |
| PDF | Pandoc + WeasyPrint 或 Typst | 避免安装完整 LaTeX；WeasyPrint 通过 HTML 中间层生成 PDF，Typst 更轻量 |
| HTML | Pandoc 转换 | 适合在线分享或嵌入网站 |
| LaTeX (.tex) | Pandoc 转换 | 供需要进一步排版的用户使用 |

**Pandoc 安装**

macOS 上通过 Homebrew 安装即可：`brew install pandoc`，无需 Docker。

**导出流程（以 Word 为例）**

```
用户选择导出为 Word → 选择 CSL 样式 → 选择 Word 模板（可选）
      │
      ▼
  ① 将当前 Markdown 文档写入临时文件
      │
      ▼
  ② 将文献库中被引用的文献元数据导出为临时 .bib 或 CSL-JSON 文件
      │
      ▼
  ③ 调用 Pandoc：
     pandoc input.md \
       --citeproc \
       --bibliography=refs.bib \
       --csl=vancouver.csl \
       --reference-doc=template.docx \
       -o output.docx
      │
      ▼
  ④ 返回生成的 .docx 文件供下载
```

---

## 3. 数据模型

### 3.1 文献记录（Literature）

```
Literature {
  id:            UUID (主键)
  cite_key:      String (如 "esposito2012"，唯一)
  
  // —— 核心元数据 ——
  title:         String
  authors:       Author[]  // [{family, given, affiliation?}]
  abstract:      String?
  
  // —— 出版信息 ——
  journal:       String?   // 期刊名
  publisher:     String?
  volume:        String?
  issue:         String?
  pages:         String?   // 如 "123-130"
  year:          Int?
  date:          String?   // 完整日期 "2024-03-15"
  doi:           String?
  pmid:          String?
  pmcid:         String?
  issn:          String?
  isbn:          String?
  
  // —— 分类与标签 ——
  type:          Enum (journal_article, book_chapter, conference, thesis, report, other)
  keywords:      String[]
  tags:          String[]  // 用户自定义标签
  language:      String    // "en" / "zh" / "ja" 等
  
  // —— 文件与索引 ——
  file_path:     String?   // 原始 PDF/MD 文件路径
  file_hash:     String?   // SHA-256
  file_size:     Int?      // 字节
  full_text:     String?   // 提取的全文（用于 FTS 索引，不存大文件全文到单字段，见下方说明）
  
  // —— 元数据质量 ——
  metadata_sources: Map<field, source>  // 每个字段的来源标记（crossref / pubmed / pdf_meta / manual）
  metadata_confidence: Float            // 0-1 综合置信度
  manually_verified: Boolean            // 用户是否手动校验过
  
  // —— 时间戳 ——
  created_at:    DateTime
  updated_at:    DateTime
  imported_at:   DateTime
}
```

### 3.2 文本块（Chunk）— 用于向量检索

```
Chunk {
  id:            UUID
  source_id:     UUID            // 外键 → Literature 或 Corpus
  source_type:   Enum (literature, corpus)  // 区分来源
  content:       String         // 段落/语义块原文
  section:       String?        // 所属章节标题
  page_number:   Int?           // 所在页码
  chunk_index:   Int            // 在文献内的顺序号
  embedding:     Float[1024]    // 向量嵌入（维度取决于模型）
  token_count:   Int
}
```

### 3.3 语料记录（Corpus）— 用户自定义语料库

```
Corpus {
  id:            UUID
  title:         String          // 语料标题（文件名或用户命名）
  description:   String?         // 用户对该语料的说明
  file_path:     String          // 原始文件路径
  file_type:     Enum (md, txt, pdf)
  file_hash:     String          // SHA-256
  tags:          String[]        // 用户自定义标签
  created_at:    DateTime
  updated_at:    DateTime
}
```

### 3.4 引用记录（Citation）— 文档级

```
Citation {
  id:            UUID
  document_id:   UUID          // 所属写作文档
  literature_id: UUID          // 引用的文献
  cite_key:      String        // 如 "@esposito2012"
  position:      Int           // 在文档中的字符偏移量
  context:       String        // 引用所在的句子（用于预览）
  order:         Int           // 出现顺序（用于编号式引用）
}
```

### 3.5 写作文档（Document）

```
Document {
  id:            UUID
  title:         String
  content:       String        // Markdown 全文
  csl_style:     String        // 使用的 CSL 样式文件名
  created_at:    DateTime
  updated_at:    DateTime
}
```

### 3.6 AI 配置（AIProviderConfig）

```
AIProviderConfig {
  id:            UUID
  provider:      Enum (local_lmstudio, anthropic, openai)
  name:          String          // 显示名称，如 "本地 Qwen3.5" 或 "Claude Sonnet"
  api_base:      String          // API 地址，如 "http://localhost:1234/v1" 或 "https://api.anthropic.com/v1"
  api_key:       String?         // Cloud Provider 的 API Key（仅本地存储，加密）
  model_id:      String          // 模型标识，如 "qwen3.5-27b" 或 "claude-sonnet-4-20250514"
  is_default:    Boolean         // 是否为默认 Provider
  max_tokens:    Int             // 最大输出 token 数
  temperature:   Float           // 默认温度
}
```

---

## 4. 技术架构

### 4.1 整体架构

```
┌─────────────────────────────────────────────────────┐
│                    前端（Web UI）                     │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  MD 编辑器    │  │  搜索面板    │  │ 文献管理   │  │
│  │ (CodeMirror6) │  │  (侧栏)     │  │ (导入/浏览)│  │
│  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘  │
│         └─────────────────┼────────────────┘        │
│                           │ HTTP / WebSocket         │
└───────────────────────────┼─────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────┐
│                    后端（API Server）                 │
│                           │                          │
│  ┌────────────┐  ┌────────┴───────┐  ┌───────────┐  │
│  │ 文献处理    │  │  检索引擎      │  │ 引用引擎   │  │
│  │ Pipeline   │  │ FTS5 + Vector  │  │ CSL/BibTeX │  │
│  └────────────┘  └────────────────┘  └───────────┘  │
│                                                     │
│  ┌────────────────┐  ┌────────────────────────────┐  │
│  │  嵌入模型      │  │  AI Service 抽象层          │  │
│  │ (bge-m3 本地)  │  │ Local LLM / Anthropic /    │  │
│  └────────────────┘  │ OpenAI                     │  │
│                      └────────────────────────────┘  │
│  ┌────────────────┐                                  │
│  │  Pandoc (CLI)  │                                  │
│  └────────────────┘                                  │
│                                                     │
│  ┌──────────────────────────────────────────────┐    │
│  │              数据层                            │    │
│  │  SQLite (元数据 + FTS5)  │  ChromaDB (向量)   │    │
│  └──────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

### 4.2 技术栈推荐

| 层级 | 技术选型 | 理由 |
|------|---------|------|
| **前端** | React + TypeScript | 生态成熟，组件丰富 |
| **编辑器** | CodeMirror 6 | Markdown 原生支持，光标 API 完善 |
| **后端** | Python (FastAPI) | NLP/嵌入模型生态最好 |
| **数据库** | SQLite + FTS5 | 本地优先，零部署，FTS5 内建全文搜索 |
| **向量库** | ChromaDB | 纯 Python，pip install 即用，无需 Docker，数据存本地文件夹 |
| **PDF 文本提取** | PyMuPDF (fitz) | 速度快，支持大文件流式读取，兼做 DOI 提取 |
| **元数据获取** | CrossRef + PubMed API | 权威数据源，零部署，纯 HTTP 调用 |
| **嵌入模型** | bge-m3 (via LM Studio) | 中英双语，560M 参数仅占 1.2GB，本地轻量运行 |
| **引用格式化** | citeproc-py + CSL | 与 Zotero 完全兼容的开放标准 |
| **LLM 推理（本地）** | LM Studio (OpenAI 兼容 API) | 已有环境，支持 Qwen 等模型，离线可用 |
| **LLM 推理（云端）** | Anthropic / OpenAI API | 用户提供 API Key，高质量长文本任务 |
| **文档格式转换** | Pandoc (CLI) | brew install 即可，原生支持 citeproc + CSL，MD→DOCX/PDF/HTML |
| **中文分词** | jieba | 轻量，FTS5 索引前预处理 |
| **桌面封装** | Tauri 2 (可选) | Rust 内核轻量，比 Electron 省资源 |

### 4.3 为什么选 SQLite 而非 PostgreSQL

- 本项目是单用户本地工具，不需要并发写入
- SQLite 的 FTS5 扩展原生支持全文检索，无需额外部署
- 数据库就是一个文件，备份/迁移极简
- 与 Python 标准库直接集成，零依赖

### 4.4 关键依赖清单

```
# Python 后端
fastapi>=0.110
uvicorn
pymupdf>=1.24            # PDF 文本提取 + DOI 提取
requests                  # CrossRef / PubMed API 调用
jieba                     # 中文分词
chromadb>=0.5             # 向量库（纯 Python，内嵌运行）
citeproc-py               # CSL 引用格式化
bibtexparser              # BibTeX 导入导出
rispy                     # RIS 格式导入导出
python-multipart          # 文件上传
httpx                     # 异步 HTTP 客户端（调用 LLM API）
anthropic                 # Anthropic Claude SDK（可选，也可直接用 httpx）
openai                    # OpenAI SDK（可选，也可直接用 httpx）
cryptography              # API Key 本地加密存储

# LLM 推理（通过 LM Studio 本地 API 或 Cloud API 调用，无需额外安装模型库）

# CLI 工具（通过 Homebrew 安装）
# brew install pandoc

# 前端
react@18
@codemirror/view
@codemirror/lang-markdown
@codemirror/state
```

---

## 5. 核心流程详细设计

### 5.1 文献导入 Pipeline

```
用户上传 PDF 文件
      │
      ▼
  ① 计算文件 SHA-256 哈希
      │
      ├─ 已存在 → 跳过，提示重复
      │
      ▼
  ② PyMuPDF 提取前两页文本
      │
      ▼
  ③ 正则匹配 DOI（10.xxxx/...）或 PMID
      │
      ├─ 找到 DOI → ④ 调 CrossRef API 获取结构化元数据
      ├─ 找到 PMID → ④ 调 PubMed efetch 获取结构化元数据
      ├─ 都没找到 → 读取 PDF 内嵌元数据（doc.metadata）
      │               └─ 仍不完整 → 标记为「待手动补全」
      │
      ▼
  ⑤ 合并元数据，标记每个字段来源（crossref / pubmed / pdf_meta）
      │
      ▼
  ⑥ 生成 cite_key（作者姓 + 年份，冲突追加后缀）
      │
      ▼
  ⑦ PyMuPDF 提取全文 → 按段落切分 → 写入 FTS5 索引
      │
      ▼
  ⑧ 段落文本 → bge-m3 生成嵌入（LM Studio 本地 API）→ 写入 ChromaDB
      │
      ▼
  ⑨ 元数据 + 文件信息写入 SQLite
      │
      ▼
  导入完成 ✓（若有缺失字段，UI 提示用户补全）
```

**大文件处理策略**

- 几百 MB 的 PDF 通常是扫描版（每页是图片），文本提取会较慢
- 设计异步任务队列（`asyncio` + 后台 worker），导入后台进行，UI 显示进度
- 全文提取按页流式处理，避免一次性加载整个文档到内存
- 对于纯扫描版（无文字层），需先 OCR（可集成 `surya` 或 `PaddleOCR`，均支持中英混合）

### 5.2 检索流程

```
用户输入查询（关键词 or 自然语言问题）
      │
      ├──────────────────────┐
      ▼                      ▼
  FTS5 关键词检索        向量语义检索
  (SQLite)              (ChromaDB)
      │                      │
      ▼                      ▼
  返回文献 ID + 评分    返回 chunk ID + 相似度
      │                      │
      └──────────┬───────────┘
                 ▼
         RRF 融合排序
                 │
                 ▼
         Top-K 文献列表
         (含匹配段落摘要)
                 │
                 ▼
         返回前端侧栏展示
```

### 5.3 引用插入流程

```
用户在编辑器中定位光标
      │
      ▼
在搜索栏输入关键词 → 侧栏显示结果列表
      │
      ▼
用户勾选 1-N 篇文献 → 点击「插入引用」
      │
      ▼
前端获取光标位置（CodeMirror Transaction API）
      │
      ▼
在光标位置插入引用标记：[@citekey1; @citekey2]
      │
      ▼
同时在 Citation 表中记录该引用（文档ID、文献ID、位置）
```

### 5.4 导出流程

```
用户点击「导出」
      │
      ▼
  ① 扫描文档内容，提取所有 [@...] 引用标记
      │
      ▼
  ② 从 Citation 表 / Literature 表获取各文献的完整元数据
      │
      ▼
  ③ 将元数据转为 CSL-JSON 格式
      │
      ▼
  ④ 加载用户选择的 .csl 样式文件
      │
      ▼
  ⑤ 调用 citeproc 引擎：
     - 生成正文内引用标注（如 [1,2] 或 (Esposito, 2012; Jung, 2018)）
     - 生成参考文献列表（完整格式化文本）
      │
      ▼
  ⑥ 替换文档中的 [@...] 标记 → 格式化引用标注
      │
      ▼
  ⑦ 文档末尾追加「参考文献」章节
      │
      ▼
  ⑧ 输出最终 .md 文件
     （可选：同时输出 .bib 文件供 Zotero 导入）
```

---

## 6. UI 布局设计

### 6.1 主界面结构

```
┌──────────────────────────────────────────────────────────┐
│  [工具栏]  文件 │ 编辑 │ 文献库 │ PubMed │ 导出 │ 设置   │
├────────────┬─────────────────────────┬───────────────────┤
│            │                         │                   │
│  文献库    │     Markdown 编辑器     │    搜索结果       │
│  浏览面板  │                         │    侧边栏         │
│            │                         │                   │
│ ┌────────┐ │  种植体早期失败率约为   │  ┌─────────────┐  │
│ │ 全部   │ │  1-3% |，其中上颌后   │  │ 🔍 搜索文献  │  │
│ │ 未读   │ │  牙区的失败率显著高于   │  │ [          ] │  │
│ │ 已标注 │ │  下颌前牙区。          │  ├─────────────┤  │
│ │ 按标签 │ │                        │  │ ☐ Esposito   │  │
│ │        │ │                        │  │   2012       │  │
│ │ ────── │ │                        │  │   "Early..." │  │
│ │ 最近   │ │                        │  │   ★★★★☆     │  │
│ │ 导入   │ │                        │  ├─────────────┤  │
│ │        │ │                        │  │ ☐ Jung 2018  │  │
│ │ Esposi │ │                        │  │   "Implant.."│  │
│ │ Jung.. │ │                        │  │   ★★★☆☆     │  │
│ │ Moy ..│ │                        │  ├─────────────┤  │
│ │        │ │                        │  │ [插入引用]   │  │
│ └────────┘ │                        │  └─────────────┘  │
│            │                         │                   │
├────────────┴─────────────────────────┴───────────────────┤
│  状态栏: 文献库 128 篇 │ 已引用 12 篇 │ 字数 3,542       │
└──────────────────────────────────────────────────────────┘
```

### 6.2 界面交互要点

- **左侧面板**：文献库浏览，支持标签筛选、排序、搜索
- **中央区域**：CodeMirror Markdown 编辑器，支持实时预览切换
- **右侧面板**：搜索结果列表，每条显示标题、第一作者、年份、匹配摘要
- **底部状态栏**：文献库统计、当前文档引用数、字数统计
- 三栏可拖拽调整宽度；左/右面板可折叠

---

## 7. CSL 样式兼容说明

### 7.1 什么是 CSL

CSL（Citation Style Language）是一个开放的 XML 格式标准，定义了引用和参考文献的排版规则。Zotero、Mendeley、EndNote（通过转换）都使用 CSL 样式。

### 7.2 兼容策略

| 操作 | 说明 |
|------|------|
| 导入 CSL 样式 | 用户将 `.csl` 文件放入项目的 `styles/` 目录即可使用 |
| 默认样式 | 内置几种常用样式：Vancouver、APA 7th、Harvard、GB/T 7714 (中文) |
| Zotero 样式库 | 提供入口链接到 [Zotero Style Repository](https://www.zotero.org/styles)，一键下载 |
| 输出 BibTeX | 文献库可整体或按选择导出为 `.bib` 文件，直接导入 Zotero 或 LaTeX |
| 输出 CSL-JSON | 更精确的元数据交换格式，Zotero 原生支持导入 |
| 导入 BibTeX/RIS | 支持从 Zotero/EndNote 导出的 `.bib` 或 `.ris` 文件导入本系统 |

### 7.3 EndNote 兼容

EndNote 使用自有的 `.ens` 样式格式，不直接兼容 CSL。但：

- EndNote 近年版本支持导入 CSL 样式（需转换）
- 本项目的 BibTeX 导出可直接被 EndNote 导入
- 建议用户如果需要 EndNote 特定样式，先在 Zotero Style Repository 查找等效 CSL

---

## 8. 开发路线图

### Phase 1 — 基础骨架（约 2-3 周）

- [ ] 项目脚手架搭建（FastAPI + React + SQLite + ChromaDB）
- [ ] 文献导入 Pipeline 实现（PDF → DOI 提取 → CrossRef/PubMed 反查 → 元数据入库）
- [ ] 手动元数据录入/编辑 UI
- [ ] 基本 CRUD API（文献的增删查改）
- [ ] 前端文献列表页面

### Phase 2 — 检索引擎（约 2 周）

- [ ] FTS5 全文索引建立（含中文分词）
- [ ] 文本切块 + bge-m3 嵌入生成
- [ ] ChromaDB 向量写入与检索
- [ ] RRF 混合排序
- [ ] 搜索 API + 前端搜索 UI

### Phase 3 — 写作编辑器（约 2-3 周）

- [ ] CodeMirror 6 编辑器集成
- [ ] 搜索结果侧栏
- [ ] 引用插入交互（光标定位 + 标记插入）
- [ ] 引用标记高亮与悬浮预览

### Phase 4 — 引用引擎与导出（约 1-2 周）

- [ ] CSL-JSON 元数据转换
- [ ] citeproc 引擎集成
- [ ] 文档导出（替换标记 + 生成参考文献）
- [ ] BibTeX/RIS 导入导出
- [ ] CSL 样式管理 UI

### Phase 5 — PubMed 集成与优化（约 1-2 周）

- [ ] PubMed 搜索 UI + API 集成
- [ ] 搜索结果预览与选择性导入
- [ ] 大文件异步处理队列
- [ ] OCR 集成（扫描版 PDF）

### Phase 6 — AI 辅助写作（约 3-4 周）

- [ ] AI Provider 抽象层实现（统一接口：chat / summarize / translate / rewrite）
- [ ] 本地 LLM 对接（LM Studio OpenAI 兼容 API）
- [ ] Cloud Provider 对接（Anthropic Claude API + OpenAI API）
- [ ] API Key 管理 UI（本地加密存储，Provider 切换）
- [ ] RAG 流程实现（检索相关段落 → 构造 Prompt → 调用 LLM → 返回带引用的回答）
- [ ] 编辑器内 AI 交互 UI（选中文本 → 右键菜单：摘要/翻译/改写/扩写）
- [ ] 自定义语料库导入（MD/TXT/PDF → 分块索引，source_type 区分）
- [ ] 语料库管理 UI（导入/删除/标签/搜索范围切换）

### Phase 7 — Pandoc 集成与多格式导出（约 1-2 周）

- [ ] Pandoc CLI 封装（Python subprocess 调用）
- [ ] 导出为 Word (.docx)，支持自定义 Word 模板（reference.docx）
- [ ] 导出为 PDF（通过 WeasyPrint 或 Typst，避免完整 LaTeX 依赖）
- [ ] 导出为 HTML
- [ ] 导出设置 UI（选择格式 / CSL 样式 / 模板）

### Phase 8 — 打磨与桌面化（持续）

- [ ] Tauri 封装（可选，将 Web 应用打包为 macOS 桌面应用）
- [ ] 元数据批量修正与批量导入优化
- [ ] 文献分组 / 项目管理
- [ ] 快捷键体系优化
- [ ] 数据备份与恢复

---

## 9. 项目目录结构（建议）

```
syntara/
├── backend/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置（路径、端口、模型等）
│   ├── models/
│   │   ├── literature.py       # 文献数据模型
│   │   ├── chunk.py            # 文本块模型
│   │   ├── citation.py         # 引用模型
│   │   └── document.py         # 写作文档模型
│   ├── services/
│   │   ├── pdf_extractor.py    # PyMuPDF 文本提取 + DOI/PMID 提取
│   │   ├── metadata.py         # CrossRef/PubMed 元数据获取与合并
│   │   ├── pubmed.py           # PubMed E-utilities 集成
│   │   ├── crossref.py         # CrossRef API 集成
│   │   ├── indexer.py          # FTS5 索引管理
│   │   ├── embedder.py         # 向量嵌入生成（调用本地 LM Studio API）
│   │   ├── searcher.py         # 混合检索 + RRF
│   │   ├── citation_engine.py  # CSL 格式化引擎
│   │   ├── exporter.py         # 文档导出
│   │   ├── ai_provider.py      # AI Provider 抽象层（Local / Anthropic / OpenAI）
│   │   ├── rag.py              # RAG 流程（检索 → Prompt 构造 → LLM 调用）
│   │   ├── corpus.py           # 语料库导入与管理
│   │   └── pandoc.py           # Pandoc CLI 封装与多格式导出
│   ├── db/
│   │   ├── sqlite.py           # SQLite 连接与 FTS5 管理
│   │   └── chromadb_store.py    # ChromaDB 向量存储
│   └── routers/
│       ├── literature.py       # 文献 CRUD API
│       ├── search.py           # 搜索 API
│       ├── pubmed.py           # PubMed 搜索 API
│       ├── document.py         # 文档 CRUD API
│       ├── export.py           # 导出 API（含 Pandoc 多格式导出）
│       ├── ai.py               # AI 辅助写作 API（摘要/翻译/改写/RAG 问答）
│       └── corpus.py           # 语料库管理 API
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── Editor/         # CodeMirror 编辑器组件
│   │   │   ├── SearchPanel/    # 搜索结果侧栏
│   │   │   ├── LibraryPanel/   # 文献库浏览面板
│   │   │   ├── PubMedSearch/   # PubMed 检索面板
│   │   │   ├── AIPanel/        # AI 辅助面板（摘要/翻译/改写/RAG 问答）
│   │   │   ├── CorpusManager/  # 语料库管理面板
│   │   │   ├── SettingsDialog/ # 设置（AI Provider / API Key / 导出模板）
│   │   │   └── ExportDialog/   # 导出设置对话框（格式/样式/模板选择）
│   │   ├── hooks/
│   │   │   ├── useSearch.ts    # 搜索逻辑
│   │   │   ├── useCitation.ts  # 引用插入逻辑
│   │   │   └── useEditor.ts   # 编辑器状态管理
│   │   └── services/
│   │       └── api.ts          # 后端 API 调用封装
│   └── package.json
├── styles/                     # CSL 样式文件目录
│   ├── vancouver.csl
│   ├── apa-7th.csl
│   ├── harvard.csl
│   └── gb-t-7714.csl
├── templates/                  # 导出模板
│   └── reference.docx          # Word 导出模板（可自定义）
├── data/                       # 运行时数据
│   ├── syntara.db             # SQLite 数据库文件
│   ├── chromadb/               # ChromaDB 向量数据目录
│   ├── files/                  # 文献文件存储目录
│   └── corpus/                 # 用户自定义语料库存储目录
└── README.md
```

---

## 10. 风险与注意事项

### 10.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| PDF 中无法自动提取 DOI/PMID | 元数据无法自动获取 | 提供手动录入 UI；文献量有限时手动补全成本可控 |
| 扫描版 PDF 无文字层 | 无法全文检索，也无法提取 DOI | 集成 OCR（PaddleOCR / Surya）；元数据手动录入 |
| 大文件处理耗时长 | 用户等待体验差 | 异步队列 + 进度条，后台批量处理 |
| 嵌入模型推理慢（大量文献） | 初始索引建立慢 | M4 MPS 加速；批量推理；增量索引 |
| FTS5 中文分词精度 | 检索召回不理想 | jieba 用户自定义词典（口腔/种植术语） |
| LLM 生成内容不准确 | 写入文档的信息可能有误 | RAG 附带引用来源供用户核实；AI 生成内容默认标记为「待确认」 |
| Cloud API 费用不可控 | 大量调用产生意外费用 | 显示预估 token 消耗；支持设置月度用量上限 |
| Pandoc 未安装 | 多格式导出不可用 | 启动时检测 Pandoc，未安装时提示 brew install 命令；MD 导出始终可用作兜底 |

### 10.2 设计决策记录

| 决策 | 选项 | 选定 | 理由 |
|------|------|------|------|
| 元数据提取 | GROBID (Docker) / DOI 反查 / 手动 | DOI 反查 + 手动 | 文献量有限，GROBID 部署成本不值得；DOI 反查数据更权威 |
| 前后端分离 vs 全栈 | Next.js 全栈 / 分离 | 分离 | Python 后端有 NLP 生态优势 |
| 向量库 | Qdrant / ChromaDB / 纯 SQLite | ChromaDB | 纯 Python，无需 Docker，pip install 即用，文献量有限时性能足够 |
| 编辑器 | CodeMirror / ProseMirror / Monaco | CodeMirror 6 | MD 原生支持，光标 API 好，轻量 |
| 引用格式 | Pandoc citation / 自定义 | Pandoc 风格 | 标准化，生态兼容，未来可直接用 Pandoc 处理 |
| 桌面封装 | Electron / Tauri / 纯 Web | Tauri（可选） | Rust 内核省资源，但前期可先跑浏览器 |
| 数据库 | SQLite / PostgreSQL | SQLite | 单用户场景，零部署，FTS5 内建 |
| AI 架构 | 纯本地 / 纯 Cloud / 混合 | 混合（Provider 抽象层） | 本地离线可用 + Cloud 高质量互补，用户自由切换 |
| 文档导出 | 自建渲染 / Pandoc | Pandoc | 成熟稳定，原生支持 citeproc，brew install 零成本 |
| PDF 生成 | LaTeX / WeasyPrint / Typst | WeasyPrint 或 Typst | 避免完整 LaTeX 安装，轻量且在 macOS 上体验好 |

### 10.3 未来扩展方向

- **文献关系图谱**：基于引用网络可视化文献间的引用关系
- **团队协作**：如果未来需多人使用，可将 SQLite 替换为 PostgreSQL + 用户鉴权
- **Zotero 双向同步**：通过 Zotero API 实现文献库实时同步
- **CNKI/万方集成**：为中文文献搜索增加国内数据库入口
- **AI 语音输入**：通过 Whisper 模型支持语音转文字，口述初稿
- **多文档项目管理**：支持一本书的多章节并行写作，共享同一文献库

---

## 11. 与现有环境的集成说明

本项目可充分利用已有的硬件和软件环境：

| 已有资源 | 在本项目中的角色 |
|---------|---------------|
| MacBook Air M4 24GB | 唯一运行环境：后端 API + ChromaDB + bge-m3 + 本地 LLM，全部本地运行 |
| LM Studio | 运行 bge-m3 嵌入模型 + 本地 LLM（如 Qwen 系列），提供 OpenAI 兼容 API |
| Pandoc (Homebrew) | 文档格式转换引擎（MD → DOCX / PDF / HTML） |
| 已有 Python/Node 环境 | 后端 FastAPI + 前端 React 开发 |

嵌入模型调用示例（通过 LM Studio 的 OpenAI 兼容 API）：

```python
import requests

def get_embedding(text: str) -> list[float]:
    response = requests.post(
        "http://localhost:1234/v1/embeddings",
        json={
            "model": "bge-m3",
            "input": text
        }
    )
    return response.json()["data"][0]["embedding"]
```

---

*本文档为初版设计草案，具体实现细节将在开发过程中迭代完善。*
