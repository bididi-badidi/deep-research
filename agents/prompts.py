"""Helpers for loading agent system prompts from Markdown files."""

from __future__ import annotations

from pathlib import Path

import re

# Root of the prompts directory, sibling to the agents/ package.
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_REFS_DIR = Path(__file__).parent.parent / "references"


def load_prompt(name: str, **variables: str) -> str:
    """Load a system prompt from ``prompts/<name>.md``.

    Automatically injects content from any files listed in a ``## Reference Files``
    section at the end of the prompt.

    Args:
        name: Filename without the ``.md`` extension (e.g. ``"subagent"``).
        **variables: Optional ``str.format_map`` substitutions applied to the
            file content after loading (e.g. ``task_id="market-size"``).

    Returns:
        The prompt text, with any ``{variable}`` placeholders replaced.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    path = _PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    text = path.read_text(encoding="utf-8")

    # Inject references
    text = _inject_references(text)

    if variables:
        text = text.format_map(variables)
    return text


def _inject_references(text: str) -> str:
    """Find a '## Reference Files' section and append the content of listed files."""
    ref_section_match = re.search(
        r"## Reference Files\n\n(.*?)(?:\n\n|\Z)", text, re.DOTALL
    )
    if not ref_section_match:
        return text

    ref_list = ref_section_match.group(1)
    # Match lines like "- `references/filename.md`" or "- [title](references/filename.md)"
    ref_paths = re.findall(r"- (?:`|\[.*?\]\()references/(.*?)(?:`|\))", ref_list)

    injected_content = []
    for ref_name in ref_paths:
        ref_path = _REFS_DIR / ref_name
        if ref_path.exists():
            content = ref_path.read_text(encoding="utf-8")
            injected_content.append(f"\n--- REFERENCE: {ref_name} ---\n\n{content}")
        else:
            # Skip missing references for now, or could raise an error
            print(f"Warning: Reference file not found: {ref_path}")

    if injected_content:
        # Append injected content after the main text, before the variables formatting
        return text + "\n\n" + "\n".join(injected_content)

    return text
