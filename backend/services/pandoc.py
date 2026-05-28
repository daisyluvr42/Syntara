"""Pandoc CLI wrapper for multi-format document export."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from backend.config import PANDOC_PATH, STYLES_DIR, TEMPLATES_DIR
from backend.services.citation_engine import (
    export_bibtex,
    export_csl_json,
    extract_citations_from_text,
    get_literature_csl_json,
)


def is_pandoc_available() -> bool:
    """Check if Pandoc is installed."""
    return shutil.which(PANDOC_PATH) is not None


def get_pandoc_version() -> str | None:
    """Get Pandoc version string."""
    try:
        result = subprocess.run(
            [PANDOC_PATH, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.split("\n")[0]
    except Exception:
        pass
    return None


def export_document(
    content: str,
    output_format: str,  # docx, pdf, html, latex
    csl_style: str = "vancouver",
    template_path: str | None = None,
) -> bytes:
    """
    Export markdown document to the specified format using Pandoc.
    Returns the output file bytes.
    """
    if not is_pandoc_available():
        raise RuntimeError(
            "Pandoc is not installed. Install with: brew install pandoc"
        )

    # Extract citation keys and generate bibliography
    cite_keys = extract_citations_from_text(content)
    unique_keys = list(dict.fromkeys(cite_keys))

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Write input markdown
        input_file = tmpdir / "input.md"
        input_file.write_text(content, encoding="utf-8")

        # Write bibliography (CSL-JSON)
        bib_file = tmpdir / "refs.json"
        if unique_keys:
            csl_items = get_literature_csl_json(unique_keys)
            bib_file.write_text(
                json.dumps(csl_items, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        # Determine output file extension
        ext_map = {"docx": ".docx", "pdf": ".pdf", "html": ".html", "latex": ".tex"}
        ext = ext_map.get(output_format, ".md")
        output_file = tmpdir / f"output{ext}"

        # Build Pandoc command
        cmd = [
            PANDOC_PATH,
            str(input_file),
            "-o",
            str(output_file),
            "--standalone",
        ]

        # Add citeproc if we have citations
        if unique_keys:
            cmd.extend(["--citeproc", f"--bibliography={bib_file}"])

            # CSL style file
            csl_file = STYLES_DIR / f"{csl_style}.csl"
            if csl_file.exists():
                cmd.extend([f"--csl={csl_file}"])

        # Word template
        if output_format == "docx" and template_path:
            tpl = Path(template_path)
            if tpl.exists():
                cmd.extend([f"--reference-doc={tpl}"])
        elif output_format == "docx":
            default_tpl = TEMPLATES_DIR / "reference.docx"
            if default_tpl.exists():
                cmd.extend([f"--reference-doc={default_tpl}"])

        # PDF engine
        if output_format == "pdf":
            # Try typst first, then weasyprint
            if shutil.which("typst"):
                cmd.extend(["--pdf-engine=typst"])
            elif shutil.which("weasyprint"):
                cmd.extend(["--pdf-engine=weasyprint"])

        # Run Pandoc
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Pandoc error: {result.stderr}")

        return output_file.read_bytes()
