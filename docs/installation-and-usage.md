# Syntara 安装与使用教程 / Installation and Usage Guide

**中文** | [English](#english)

本文档说明如何安装 Syntara、启动本地服务、连接 WorkBuddy MCP、安装 Skill，并把文献和语料导入到本地项目级 RAG 库。

## 1. 环境要求

建议环境：

- macOS
- Python 3.12 或较新的 Python 3
- Node.js 和 npm
- WorkBuddy，若要使用 MCP 和 Skill
- Java 21，若要使用 `opendataloader-pdf` 的部分 PDF 解析能力
- Pandoc，若要导出或格式化部分文档格式

`./start.sh` 会自动创建 `.venv`、安装 Python 依赖、安装前端依赖并启动服务。Java 和 Pandoc 是可选增强项；没有它们时，基础的文献库、检索、MCP 和 WorkBuddy 写作流程仍然可以使用。

## 2. 获取项目

```bash
git clone https://github.com/daisyluvr42/Syntara.git
cd Syntara
```

如果你已经在本机有项目目录：

```bash
cd /path/to/Syntara
git pull
```

## 3. 启动本地服务

最简单的方式：

```bash
./start.sh
```

脚本会启动：

- 后端 API：`http://127.0.0.1:8888`
- 前端界面：`http://127.0.0.1:5173`
- API 文档：`http://127.0.0.1:8888/docs`

如果要换端口：

```bash
SYNTARA_PORT=8890 FRONTEND_PORT=5174 ./start.sh
```

服务停止方式：在运行 `./start.sh` 的终端按 `Ctrl+C`。

## 4. 连接 WorkBuddy MCP

第一次连接前，先确保 Python 依赖已经安装。最稳妥的方式是先运行一次：

```bash
./start.sh
```

确认服务能启动后，另开一个终端，在项目根目录执行：

```bash
python mcp/install_syntara_workbuddy.py
```

安装脚本会把 `syntara` 写入 `~/.workbuddy/mcp.json`，并保留已有 MCP 配置。默认 MCP 指向：

```text
/path/to/Syntara/.venv/bin/python
/path/to/Syntara/mcp/syntara_mcp.py
```

然后打开 WorkBuddy：

1. 进入 MCP 或 Custom Connector 管理页。
2. 找到 `syntara`。
3. 点击信任或启用。
4. 刷新后应能看到 `syntara_*` 工具。

Syntara MCP 支持在工具调用时自动启动后端。如果你已经手动运行 `./start.sh`，MCP 会复用本地后端。

如果你已经有一份整理好的风格文档，可以在安装 MCP 时顺便导入：

```bash
python mcp/install_syntara_workbuddy.py \
  --style-file /path/to/my-style.md \
  --style-name "公众号长文风格" \
  --style-project default \
  --style-type wechat-longform
```

也可以用交互式方式：

```bash
python mcp/install_syntara_workbuddy.py --setup-style
```

## 5. 安装 WorkBuddy Skill

仓库内置四个 Skill：

```text
skills/syntara-style-profiler
skills/syntara-knowledge-writing
skills/syntara-academic-writing
skills/syntara-literature-review
```

默认安装命令已经会把这四个 Skill 安装到 WorkBuddy，并写入用户导入元数据：

```bash
python mcp/install_syntara_workbuddy.py
```

然后在 WorkBuddy 中刷新 Skill 列表。

四个 Skill 的分工：

- `syntara-style-profiler`：专门从旧文、书稿、腾讯文档、ima 或 WorkBuddy 资料库中提炼风格，并保存为 Syntara Markdown + JSON style profile。
- `syntara-knowledge-writing`：通用资料写作流程，也就是 general source-based writing，适用于 ima、Syntara、腾讯文档或其他资料库来源。
- `syntara-academic-writing`：学术书籍写作，适用于基于 PDF、给定来源文档、Syntara 项目库、PubMed 和其他可用学术源的书籍章节或长篇学术/专业写作。
- `syntara-literature-review`：文献综述、related work、研究差距、主题证据综合，使用同一套 PDF、给定来源文档、Syntara 项目库、PubMed 和其他可用学术源。

## 6. 导入资料

Syntara 把资料分成两类：

- **Literature**：论文、PDF、PubMed 记录，可用于正式引用。
- **Corpus**：你的笔记、书稿、风格样本、腾讯文档内容、WorkBuddy 资料库内容，可用于风格、结构、背景和个人知识。

每次导入时建议指定 `project`，例如：

```text
implant-flap-review
professional-book
ai-agent-notes
```

这样不同主题的文献库不会混在一起。

### 6.1 通过网页界面导入

启动 `./start.sh` 后打开：

```text
http://127.0.0.1:5173
```

可在本地界面中管理文献、语料、搜索、引用和 AI 配置。

### 6.2 通过 WorkBuddy 导入本地 PDF

在 WorkBuddy 中使用 Syntara MCP，可让它调用：

```text
syntara_import_literature_pdfs
```

常用参数：

- `file_paths`：PDF 文件路径列表
- `folder_path`：PDF 文件夹
- `recursive`：是否递归读取子文件夹
- `project`：项目 slug

### 6.3 通过 PubMed 导入

先搜索：

```text
syntara_search_pubmed
```

再导入选中的 PMID：

```text
syntara_import_pubmed
```

如果导入到某个主题，记得传入 `project`。

### 6.4 通过 WorkBuddy 资料库或腾讯文档导入语料

WorkBuddy 可以先读取资料库或腾讯文档内容，再调用：

```text
syntara_import_corpus_text
```

适合导入：

- 你的旧书稿章节
- 写作风格样本
- 研究笔记
- 会议记录
- 章节大纲
- 腾讯文档中的协作材料

这些内容默认属于 Corpus，不应当当作正式文献引用。若笔记中提到论文，应通过 PDF 或 PubMed 把原始论文加入 Literature。

## 7. 建立和复用风格档案

Syntara 可以把你的旧文章、旧章节或腾讯文档语料提炼成项目级 style profile。建议用 `syntara-style-profiler` 专门完成这一步，它会按固定维度提炼风格，并保存为 Markdown + JSON。正式写作时，其他 Skill 会优先查找当前 `project` 的默认风格档案；如果存在，会自动应用。没有默认档案时，Skill 会使用默认去 AI 化风格，并轻提示你可以提供风格样本。

常用 MCP 工具：

```text
syntara_build_style_profile
syntara_update_style_profile_from_revision
syntara_save_style_profile
syntara_list_style_profiles
syntara_get_style_profile
syntara_set_default_style_profile
```

推荐做法：

1. 导入或指向你的代表性旧文、章节、腾讯文档或 ima / WorkBuddy 资料库内容，标签可用 `style-corpus`。
2. 使用 `syntara-style-profiler` 为对应 `project` 和 `style_type` 生成规范 Markdown + JSON 风格档案。
3. 设置为默认后，后续正式写作会自动读取该风格档案。

如果 Syntara 后端没有配置 AI provider，WorkBuddy 也可以先提炼一份 Markdown/JSON 风格档案，再调用 `syntara_save_style_profile` 保存为项目默认风格。

如果用户先让 WorkBuddy 生成文章，随后自己做了一版修改，可以把“原始生成稿 + 用户修改稿”回传给 `syntara-style-profiler`。它会调用 `syntara_update_style_profile_from_revision`，从差异中提炼删改偏好、措辞偏好、结构偏好和反 AI 味偏好，并整合进当前项目默认 style profile，而不是另存成一份孤立的 diff 文档。

后续如果要补充新的题材或文体，不需要重新安装。可以继续调用：

```text
syntara_build_style_profile
syntara_update_style_profile_from_revision
syntara_save_style_profile
syntara_set_default_style_profile
```

关键是为不同文体设置不同 `style_type`，例如 `wechat-longform`、`professional-book`、`literature-review`、`tutorial` 或 `ppt`。Syntara 会把它们保存为不同风格档案，Skill 写作时按任务类型调用对应档案。

## 8. 在 WorkBuddy 中写作

推荐流程：

1. 选择一个 Syntara Skill，例如 `syntara-literature-review`。
2. 告诉 WorkBuddy 主题、目标文体、读者、输出长度和 `project`。
3. 如果已有文献库，让 WorkBuddy 先调用 `syntara_project_summary` 看项目内容。
4. 正式写作时，Skill 会先查找当前项目默认 style profile。
5. 让 WorkBuddy 用 `syntara_search_literature_grouped` 或 `syntara_search` 找证据。
6. 对关键证据调用 `syntara_get_chunk_context` 检查上下文。
7. 对窄问题调用 `syntara_rag_answer`，不要让 RAG 直接写整篇文章。
8. 让 Skill 负责组织结构、应用风格、写正文、检查 unsupported claims。
9. 完成后用 `syntara_format_citations` 或 `syntara_export_bibtex` 处理引用。

可以这样对 WorkBuddy 说：

```text
使用 syntara-literature-review。项目是 implant-flap-review。
请围绕“软组织减张技术对种植骨增量创口关闭的影响”写一份中文叙述性综述。
先检索项目内文献，列出证据矩阵，再起草正文。强结论必须带 cite key。
```

或者：

```text
使用 syntara-academic-writing。项目是 professional-book。
请读取我附上的旧章节作为风格语料，再围绕“垂直骨增量中的软组织管理”写一个专业书章节提纲。
先用 Syntara 检索证据，不要直接编造引用。
```

## 9. AI 与 Embedding 配置

Syntara 支持本地和云端 AI provider。常用方式：

- 在前端界面中配置 AI provider 和 Embedding。
- 或通过环境变量配置默认 embedding。

常见环境变量：

```bash
EMBEDDING_MODE=local
EMBEDDING_API_BASE=http://localhost:1234/v1
EMBEDDING_MODEL=bge-m3
EMBEDDING_API_KEY=
```

如果没有本地 embedding 服务，可以把 `EMBEDDING_MODE` 设为 `python` 使用内置轻量向量模式：

```bash
EMBEDDING_MODE=python ./start.sh
```

## 10. 本地数据位置

本地数据默认写入：

```text
data/
```

其中包括：

- `data/syntara.db`：SQLite 数据库
- `data/files/`：导入的 PDF
- `data/corpus/`：导入的语料
- `data/chromadb/`：向量库
- `data/extract_cache/`：PDF 解析缓存
- `data/doc_trees/`：文档树缓存
- `styles/`：可读的 Markdown/JSON 风格档案副本和引用样式文件

`data/` 不会提交到 Git。备份或迁移文献库时，备份整个 `data/` 目录即可。

## 10. 常见问题

### WorkBuddy 看不到 `syntara`

重新执行：

```bash
python mcp/install_syntara_workbuddy.py
```

然后在 WorkBuddy 的 MCP 管理页刷新、信任并启用 `syntara`。

### MCP 工具存在，但调用失败

先确认后端能启动：

```bash
./start.sh
```

再打开：

```text
http://127.0.0.1:8888/api/health
```

如果返回 `status: ok`，说明后端正常。

### PDF 导入慢

PDF 解析、OCR 和向量索引本来就可能耗时。建议先少量导入，确认流程正常后再批量导入。

### 不想使用网页界面

可以只使用 WorkBuddy + MCP + Skill。网页界面是可选的，本地 RAG 和导入能力都可以通过 MCP 工具调用。

---

## English

This guide explains how to install Syntara, start the local services, connect the WorkBuddy MCP server, install the WorkBuddy skills, and import literature or personal corpora into project-scoped local RAG libraries.

## 1. Requirements

Recommended environment:

- macOS
- Python 3.12 or a recent Python 3 release
- Node.js and npm
- WorkBuddy, if you want MCP and skill integration
- Java 21, for parts of the `opendataloader-pdf` PDF extraction flow
- Pandoc, for some document export and citation formatting flows

`./start.sh` creates `.venv`, installs Python dependencies, installs frontend dependencies, and starts the services. Java and Pandoc are optional enhancements; the core library, retrieval, MCP, and WorkBuddy writing workflow can still run without them.

## 2. Clone the Project

```bash
git clone https://github.com/daisyluvr42/Syntara.git
cd Syntara
```

If you already have a local checkout:

```bash
cd /path/to/Syntara
git pull
```

## 3. Start Local Services

The simplest path:

```bash
./start.sh
```

This starts:

- Backend API: `http://127.0.0.1:8888`
- Frontend UI: `http://127.0.0.1:5173`
- API docs: `http://127.0.0.1:8888/docs`

To use custom ports:

```bash
SYNTARA_PORT=8890 FRONTEND_PORT=5174 ./start.sh
```

To stop the services, press `Ctrl+C` in the terminal running `./start.sh`.

## 4. Connect WorkBuddy MCP

Before installing the MCP entry, make sure Python dependencies exist. The safest path is to run once:

```bash
./start.sh
```

After confirming the services start, open another terminal in the project root:

```bash
python mcp/install_syntara_workbuddy.py
```

The installer writes `syntara` into `~/.workbuddy/mcp.json` while preserving existing MCP entries. By default, the MCP entry points to:

```text
/path/to/Syntara/.venv/bin/python
/path/to/Syntara/mcp/syntara_mcp.py
```

Then open WorkBuddy:

1. Go to the MCP or Custom Connector management page.
2. Find `syntara`.
3. Trust or enable it.
4. Refresh and confirm that `syntara_*` tools are available.

Syntara MCP can auto-start the backend on tool calls. If `./start.sh` is already running, MCP reuses that local backend.

If you already have a maintained style document, import it during MCP setup:

```bash
python mcp/install_syntara_workbuddy.py \
  --style-file /path/to/my-style.md \
  --style-name "WeChat Longform Style" \
  --style-project default \
  --style-type wechat-longform
```

Or use the interactive setup:

```bash
python mcp/install_syntara_workbuddy.py --setup-style
```

## 5. Install WorkBuddy Skills

The repository includes four skills:

```text
skills/syntara-style-profiler
skills/syntara-knowledge-writing
skills/syntara-academic-writing
skills/syntara-literature-review
```

The default installer copies these skills into WorkBuddy and writes user-import metadata:

```bash
python mcp/install_syntara_workbuddy.py
```

Then refresh the WorkBuddy skill list.

Skill roles:

- `syntara-style-profiler`: extracts user writing style from prior writing, book chapters, Tencent Docs, ima, or WorkBuddy knowledge-base material, then saves a Markdown + JSON Syntara style profile.
- `syntara-knowledge-writing`: general source-based writing from ima, Syntara, Tencent Docs, or other knowledge-base materials.
- `syntara-academic-writing`: academic book writing for chapters or long-form scholarly/professional prose from PDFs, provided source documents, Syntara project libraries, PubMed, and other available academic sources.
- `syntara-literature-review`: literature reviews, related work, research gaps, and thematic evidence synthesis using the same PDF, provided-document, Syntara project, PubMed, and available academic-source base.

## 6. Import Materials

Syntara separates materials into two groups:

- **Literature**: papers, PDFs, and PubMed records that can support formal citations.
- **Corpus**: your notes, book drafts, style samples, Tencent Docs content, and WorkBuddy knowledge-base content.

When importing, use a `project` slug such as:

```text
implant-flap-review
professional-book
ai-agent-notes
```

This keeps unrelated topics separate.

### 6.1 Import Through the Web UI

After starting `./start.sh`, open:

```text
http://127.0.0.1:5173
```

The web UI can manage literature, corpora, search, citations, and AI provider settings.

### 6.2 Import Local PDFs Through WorkBuddy

In WorkBuddy, use the Syntara MCP tool:

```text
syntara_import_literature_pdfs
```

Common arguments:

- `file_paths`: a list of PDF file paths
- `folder_path`: a folder containing PDFs
- `recursive`: whether to include subfolders
- `project`: the project slug

### 6.3 Import From PubMed

Search first:

```text
syntara_search_pubmed
```

Then import selected PMIDs:

```text
syntara_import_pubmed
```

Pass `project` when importing into a specific topic library.

### 6.4 Import WorkBuddy Knowledge Base or Tencent Docs Content

WorkBuddy can read knowledge-base or Tencent Docs content first, then call:

```text
syntara_import_corpus_text
```

Use this for:

- Previous book chapters
- Writing style samples
- Research notes
- Meeting notes
- Chapter outlines
- Collaborative Tencent Docs materials

These materials belong to Corpus by default and should not be treated as formal literature citations. If a note mentions a paper, add the original paper through PDF or PubMed import.

## 7. Build And Reuse Style Profiles

Syntara can turn prior articles, book chapters, or Tencent Docs corpora into project-scoped style profiles. Use `syntara-style-profiler` for this step: it extracts style along fixed dimensions and saves both Markdown and JSON. For formal writing, other skills first look for the default style profile for the current `project`; if one exists, it is applied automatically. If none exists, the skill uses the default de-AI pass and lightly suggests providing style samples.

Common MCP tools:

```text
syntara_build_style_profile
syntara_update_style_profile_from_revision
syntara_save_style_profile
syntara_list_style_profiles
syntara_get_style_profile
syntara_set_default_style_profile
```

Recommended flow:

1. Import or point WorkBuddy to representative prior writing, optionally tagged `style-corpus`.
2. Use `syntara-style-profiler` to extract a normalized Markdown + JSON profile for the target `project` and `style_type`.
3. Set it as default so future formal writing uses it automatically.

If the Syntara backend has no AI provider configured, WorkBuddy can extract a compact Markdown/JSON profile itself and save it with `syntara_save_style_profile`.

If WorkBuddy generates a draft and the user later edits it, send the original generated draft plus the user-edited version back to `syntara-style-profiler`. It calls `syntara_update_style_profile_from_revision`, learns deletion, diction, structure, and anti-AI preferences from the diff, then merges those preferences into the current project default style profile instead of saving a separate diff note.

Later, you can add new topic- or genre-specific style samples without reinstalling. Use:

```text
syntara_build_style_profile
syntara_update_style_profile_from_revision
syntara_save_style_profile
syntara_set_default_style_profile
```

Set a different `style_type` for each writing form, such as `wechat-longform`, `professional-book`, `literature-review`, `tutorial`, or `ppt`. Syntara stores them as separate style profiles, and skills choose the matching profile for the current writing task.

## 8. Writing With WorkBuddy

Recommended workflow:

1. Choose a Syntara skill, such as `syntara-literature-review`.
2. Tell WorkBuddy the topic, genre, audience, target length, and `project`.
3. If a library already exists, ask WorkBuddy to call `syntara_project_summary`.
4. For formal writing, the skill checks the project default style profile.
5. Retrieve evidence with `syntara_search_literature_grouped` or `syntara_search`.
6. Check key passages with `syntara_get_chunk_context`.
7. Use `syntara_rag_answer` only for narrow evidence questions.
8. Let the skill handle structure, style application, drafting, and unsupported-claim checks.
9. Use `syntara_format_citations` or `syntara_export_bibtex` for final citation work.

Example prompt:

```text
Use syntara-literature-review. The project is implant-flap-review.
Write a Chinese narrative review on how soft-tissue releasing techniques affect wound closure in implant bone augmentation.
Search the project literature first, build an evidence matrix, then draft the review. Strong claims must include cite keys.
```

Another example:

```text
Use syntara-academic-writing. The project is professional-book.
Read my attached previous chapter as style corpus, then outline a professional book chapter on soft-tissue management in vertical bone augmentation.
Use Syntara for evidence retrieval first. Do not invent citations.
```

## 9. AI and Embedding Configuration

Syntara supports local and cloud AI providers. Common options:

- Configure AI providers and embeddings in the web UI.
- Or configure default embedding through environment variables.

Common environment variables:

```bash
EMBEDDING_MODE=local
EMBEDDING_API_BASE=http://localhost:1234/v1
EMBEDDING_MODEL=bge-m3
EMBEDDING_API_KEY=
```

If you do not have a local embedding service, use the built-in lightweight Python embedding mode:

```bash
EMBEDDING_MODE=python ./start.sh
```

## 10. Local Data

Local data is written to:

```text
data/
```

It includes:

- `data/syntara.db`: SQLite database
- `data/files/`: imported PDFs
- `data/corpus/`: imported corpora
- `data/chromadb/`: vector store
- `data/extract_cache/`: PDF extraction cache
- `data/doc_trees/`: document tree cache
- `styles/`: readable Markdown/JSON style profile copies and citation style files

`data/` is excluded from Git. To back up or move your library, back up the entire `data/` directory.

## 11. Troubleshooting

### WorkBuddy Does Not Show `syntara`

Run:

```bash
python mcp/install_syntara_workbuddy.py
```

Then refresh the WorkBuddy MCP management page, trust, and enable `syntara`.

### MCP Tools Exist but Calls Fail

Confirm that the backend can start:

```bash
./start.sh
```

Then open:

```text
http://127.0.0.1:8888/api/health
```

If it returns `status: ok`, the backend is running.

### PDF Import Is Slow

PDF extraction, OCR, and vector indexing can take time. Start with a small batch, confirm the flow works, then import larger folders.

### I Do Not Want the Web UI

You can use WorkBuddy + MCP + skills only. The web UI is optional; local RAG and import workflows are also available through MCP tools.
