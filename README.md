# Syntara

**中文** | [English](#english)

Syntara 是一个面向专业写作的本地证据引擎：它把论文、笔记、PDF、个人语料和 WorkBuddy 资料库连接到本地 RAG、项目级文献库和可复用 Skill，让 WorkBuddy 能够写有证据、有引用、可追溯的章节、综述、报告和幻灯片草稿。

## 核心能力

- **项目级知识库**：用 `project` 区分不同主题、书稿、综述或研究方向。
- **本地 RAG**：在本地保存文献、语料、索引和向量库，避免把私有资料直接交给云端工作流。
- **可复用风格档案**：用专门的风格 Skill 从你的旧文章、书稿章节或腾讯文档语料中提炼 Markdown + JSON style profile，并在同一项目的后续写作中自动复用。
- **WorkBuddy MCP**：通过 `syntara_*` 工具让 WorkBuddy 检索文献、导入资料、生成 RAG 答案、格式化引用和导出 BibTeX。
- **双 Skill 入口**：当前只暴露写作和风格档案两个入口；文章、章节、文献综述、报告和脚本都由统一写作 Skill 内部分流。
- **可选网页界面**：用于本地管理文献、语料、搜索、引用和 AI 配置。

## 快速开始

```bash
git clone https://github.com/daisyluvr42/Syntara.git
cd Syntara
./start.sh
```

默认地址：

- Backend: `http://127.0.0.1:8888`
- Frontend: `http://127.0.0.1:5173`
- API docs: `http://127.0.0.1:8888/docs`

安装 WorkBuddy MCP 和内置 Skill：

```bash
python3 mcp/syntara.py install workbuddy
```

然后在 WorkBuddy 的 MCP 管理页信任并启用 `syntara`。

卸载 WorkBuddy 接入：

```bash
python3 mcp/syntara.py uninstall workbuddy
```

旧教程中的 `python3 mcp/install_syntara_workbuddy.py` 仍然可用，会自动转到新的统一入口。

如果使用 TRAE SOLO：

```bash
cd /path/to/Syntara
python3 mcp/syntara.py install trae
```

然后重启 TRAE SOLO，并在 MCP 面板中启用 `syntara`。

卸载 TRAE SOLO 接入：

```bash
cd /path/to/Syntara
python3 mcp/syntara.py uninstall trae
```

更新 Syntara 并刷新客户端接入：

```bash
python3 mcp/syntara.py update workbuddy
python3 mcp/syntara.py update trae
```

更新和卸载都不会删除本地 Syntara 数据库、PDF、语料或风格档案。

完整教程见 [docs/installation-and-usage.md](docs/installation-and-usage.md)。

## 仓库结构

```text
backend/      FastAPI backend for literature, corpus, search, RAG, and citations
mcp/          WorkBuddy-compatible MCP stdio bridge and installer
skills/       WorkBuddy skills that use Syntara MCP
frontend/     Optional local web interface
styles/       Citation styles
docs/         Installation, usage, and design notes
```

本地资料库、PDF、数据库、向量库和缓存都存放在 `data/`，不会提交到 Git。

---

## English

Syntara is a local evidence engine for professional writing. It connects papers, notes, PDFs, personal corpora, and WorkBuddy knowledge-base materials to local RAG, project-scoped source libraries, and reusable WorkBuddy skills, so WorkBuddy can draft evidence-grounded chapters, literature reviews, reports, and slides with traceable citations.

## Key Features

- **Project-scoped libraries**: separate topics, books, reviews, and research areas with `project` slugs.
- **Local RAG**: keep source files, corpora, indexes, and vector stores on your machine.
- **Reusable style profiles**: use a dedicated style skill to extract Markdown + JSON style profiles from prior articles, book chapters, or Tencent Docs corpora, then reuse them automatically in future writing for the same project.
- **WorkBuddy MCP**: expose `syntara_*` tools for retrieval, imports, RAG answers, citation formatting, and BibTeX export.
- **Modular skills**: includes style-profile extraction, general knowledge-base writing, academic chapter writing, and literature review skills, with room for future PPT, report, and proposal-writing skills.
- **Optional web UI**: manage literature, corpora, search, citations, and AI providers locally.

## Quick Start

```bash
git clone https://github.com/daisyluvr42/Syntara.git
cd Syntara
./start.sh
```

Default URLs:

- Backend: `http://127.0.0.1:8888`
- Frontend: `http://127.0.0.1:5173`
- API docs: `http://127.0.0.1:8888/docs`

Install the WorkBuddy MCP entry and built-in skills:

```bash
python3 mcp/syntara.py install workbuddy
```

Then trust and enable `syntara` in WorkBuddy's MCP management page.

Uninstall the WorkBuddy integration:

```bash
python3 mcp/syntara.py uninstall workbuddy
```

The older `python3 mcp/install_syntara_workbuddy.py` command still works and forwards to the unified entrypoint.

For TRAE SOLO:

```bash
cd /path/to/Syntara
python3 mcp/syntara.py install trae
```

Then restart TRAE SOLO and enable `syntara` from the MCP panel if prompted.

Uninstall the TRAE SOLO integration:

```bash
cd /path/to/Syntara
python3 mcp/syntara.py uninstall trae
```

Update Syntara and refresh a client integration:

```bash
python3 mcp/syntara.py update workbuddy
python3 mcp/syntara.py update trae
```

Update and uninstall do not delete local Syntara databases, PDFs, corpora, or style profiles.

For full setup and usage instructions, see [docs/installation-and-usage.md](docs/installation-and-usage.md).

## Repository Layout

```text
backend/      FastAPI backend for literature, corpus, search, RAG, and citations
mcp/          WorkBuddy-compatible MCP stdio bridge and installer
skills/       WorkBuddy skills that use Syntara MCP
frontend/     Optional local web interface
styles/       Citation styles
docs/         Installation, usage, and design notes
```

Local libraries, PDFs, databases, vector stores, and caches live under `data/` and are intentionally excluded from Git.
