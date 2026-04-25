"""Gradio demo for the Deep Research multi-agent system.

Run:
    python app.py

Architecture:
    - Left panel:  Receptionist chat (multi-turn conversation via asyncio queues)
    - Right panel: Pipeline log (streaming stdout capture)
    - Bottom panel: File viewer for report.md and findings/*.md (revealed on completion)
"""

from __future__ import annotations

import asyncio
import os
import platform
import subprocess
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

from config import Config
from main import run_pipeline

load_dotenv()

WORKSPACE = Path(__file__).parent / "workspace"


# ── Helpers ───────────────────────────────────────────────────────────────────


_ROOT_FILES = {"report.md", "brief.json", "synthesis_raw.md"}


def _list_workspace_files(workspace: Path) -> list[str]:
    files: list[str] = []
    for name in ("brief.json", "report.md", "synthesis_raw.md"):
        if (workspace / name).exists():
            files.append(name)
    findings = workspace / "findings"
    if findings.exists():
        files += sorted(f.name for f in findings.glob("*.md"))
    return files


def _read_file(filename: str, workspace: Path) -> str:
    if not filename:
        return ""
    path = (
        workspace / filename
        if filename in _ROOT_FILES
        else workspace / f"findings/{filename}"
    )
    return (
        path.read_text(encoding="utf-8")
        if path.exists()
        else f"*File not found: {filename}*"
    )


def _open_folder(workspace: Path):
    """Open the workspace folder in the OS file explorer."""
    path = str(workspace.resolve())
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.run(["open", path])
    else:
        subprocess.run(["xdg-open", path])


# ── Wrapper: run_pipeline → log_q ─────────────────────────────────────────────


async def _run_pipeline_queued(
    config: Config, brief: dict, log_q: asyncio.Queue
) -> None:
    """Adapts run_pipeline's on_log callback to push lines into log_q."""

    def _log(msg: str | list[str]) -> None:
        if isinstance(msg, list):
            lines = msg
        else:
            lines = msg.splitlines()

        for line in lines:
            if isinstance(line, str):
                stripped = line.strip()
            else:
                stripped = str(line).strip()

            if stripped:
                try:
                    log_q.put_nowait(stripped)
                except asyncio.QueueFull:
                    pass

    try:
        await run_pipeline(config, brief, on_log=_log)
    except Exception as exc:
        log_q.put_nowait(f"Pipeline error: {exc}")
    finally:
        # Guarantee __DONE__ is delivered even if the queue is nearly full.
        try:
            log_q.put_nowait("__DONE__")
        except asyncio.QueueFull:
            # Drain one slot then retry.
            try:
                log_q.get_nowait()
            except asyncio.QueueEmpty:
                pass
            log_q.put_nowait("__DONE__")


# ── State factory ─────────────────────────────────────────────────────────────


def _new_state() -> dict:
    return {
        "in_q": None,
        "out_q": None,
        "log_q": None,
        "receptionist_task": None,
        "pipeline_task": None,
        "phase": "idle",  # idle | intake | researching | done
        "brief": None,
        "config": None,
        "workspace": WORKSPACE,
    }


CSS = """
.gradio-container {
    background: linear-gradient(135deg, #020617 0%, #0f172a 100%) !important;
    background-attachment: fixed !important;
    min-height: 100vh !important;
}

.glass-card {
    background: rgba(15, 23, 42, 0.3) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border: 1px solid rgba(56, 189, 248, 0.1) !important;
    border-radius: 1.5rem !important;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8) !important;
    padding: 1.5rem !important;
    margin-bottom: 1rem !important;
}

.glass-chatbot {
    # background: rgba(255, 255, 255, 0.02) !important;
    border-radius: 1rem !important;
}

/* Make text more readable on dark backgrounds */
h1, h3, p, span, label {
    color: rgba(255, 255, 255, 0.9) !important;
}

/* Polish input fields and buttons */
input, textarea, .secondary, button {
    border: 1px solid rgba(56, 189, 248, 0.2) !important;
    color: white !important;
    border-radius: 0.75rem !important;
}

button.primary {
    background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%) !important;
    border: none !important;
    box-shadow: 0 0 15px rgba(14, 165, 233, 0.4) !important;
}

button.primary:hover {
    box-shadow: 0 0 25px rgba(14, 165, 233, 0.6) !important;
    transform: translateY(-1px);
}
"""


def build_app() -> gr.Blocks:
    with gr.Blocks(title="Deep Research Demo", theme=gr.themes.Soft(), css=CSS) as demo:
        state = gr.State(_new_state)

        gr.Markdown("# Deep Research Demo")
        gr.Markdown("Multi-agent research system with real-time grounding.")

        with gr.Row():
            # ── Left: receptionist chat ───────────────────────────────────
            with gr.Column(scale=1, elem_classes="glass-card"):
                gr.Markdown("### 🤖 Receptionist")
                chatbot = gr.Chatbot(
                    height=420,
                    show_label=False,
                    layout="bubble",
                    elem_classes="glass-chatbot",
                )
                with gr.Row():
                    user_input = gr.Textbox(
                        placeholder="Describe your research topic…",
                        show_label=False,
                        scale=5,
                    )
                    send_btn = gr.Button("Send", scale=1, variant="primary")
                status_md = gr.Markdown("", container=False)

            # ── Right: pipeline log ───────────────────────────────────────
            with gr.Column(scale=1, elem_classes="glass-card"):
                gr.Markdown("### 📜 Pipeline Log")
                log_box = gr.Textbox(
                    value="",
                    show_label=False,
                    interactive=False,
                    lines=22,
                    max_lines=22,
                    autoscroll=True,
                )

        # ── Workspace access row (hidden until pipeline finishes) ─────────
        with gr.Row(visible=False) as workspace_row:
            with gr.Column(elem_classes="glass-card"):
                with gr.Row():
                    workspace_path_md = gr.Markdown("", container=False)
                    open_folder_btn = gr.Button(
                        "📁 Open Workspace Folder", scale=1, variant="primary"
                    )

        # ── Bottom: file viewer (hidden until done) ───────────────────────
        with gr.Row(visible=False, elem_classes="glass-card") as file_panel:
            with gr.Column():
                gr.Markdown("### 📂 Output Files")
                with gr.Row():
                    file_dropdown = gr.Dropdown(
                        label="Select file",
                        choices=[],
                        scale=4,
                        interactive=True,
                    )
                    refresh_btn = gr.Button("Refresh", scale=1)
                file_content = gr.Markdown(value="", height=600)

        # ── Polling timer (activated after brief is submitted) ────────────
        timer = gr.Timer(value=1.0, active=False)

        # ── Event handlers ────────────────────────────────────────────────

        async def send_message(
            user_msg: str,
            history: list,
            s: dict,
        ):
            if not user_msg.strip():
                yield history, "", s, gr.update(), gr.update(active=False)
                return

            history = history + [{"role": "user", "content": user_msg}]
            yield history, "", s, gr.update(), gr.update()  # show user msg immediately

            if s["phase"] in ("researching", "done"):
                history = history + [
                    {
                        "role": "assistant",
                        "content": "Research is already in progress — check the pipeline log →",
                    }
                ]
                yield history, "", s, gr.update(), gr.update()
                return

            if s["phase"] == "idle":
                # Bootstrap: create queues, base workspace dir, start receptionist task
                workspace: Path = s["workspace"]
                workspace.mkdir(parents=True, exist_ok=True)

                config = Config(workspace=workspace)
                s["config"] = config

                in_q: asyncio.Queue = asyncio.Queue()
                out_q: asyncio.Queue = asyncio.Queue()
                log_q: asyncio.Queue = asyncio.Queue(maxsize=1000)
                s["in_q"] = in_q
                s["out_q"] = out_q
                s["log_q"] = log_q
                s["phase"] = "intake"

                async def _on_brief(brief: dict) -> None:
                    import json as _json

                    s["brief"] = brief
                    s["phase"] = "researching"

                    # Initialize the specific research workspace
                    from utils import initialize_research_workspace

                    research_id = initialize_research_workspace(config, brief["topic"])
                    s["workspace"] = config.workspace  # research-specific path

                    # Persist the brief for documentation
                    (config.workspace / "brief.json").write_text(
                        _json.dumps(brief, indent=2, ensure_ascii=False)
                    )

                    log_q.put_nowait(f"Brief received: {brief['topic']}")
                    log_q.put_nowait(f"Research session ID: {research_id}")
                    log_q.put_nowait("Starting pipeline…")

                    s["pipeline_task"] = asyncio.create_task(
                        _run_pipeline_queued(config, brief, log_q)
                    )

                from agents.receptionist import run_with_queue

                s["receptionist_task"] = asyncio.create_task(
                    run_with_queue(config, in_q, out_q, _on_brief)
                )

            # Forward user message to the receptionist task
            await s["in_q"].put(user_msg)

            # Await the receptionist's reply (up to 5 min)
            try:
                response = await asyncio.wait_for(s["out_q"].get(), timeout=300)
            except asyncio.TimeoutError:
                response = "*(timeout — model took too long to respond)*"

            history = history + [{"role": "assistant", "content": response}]

            status_text = {
                "intake": "Gathering research brief…",
                "researching": "Research in progress… check the log →",
                "done": "Research complete!",
            }.get(s["phase"], "")

            # Activate the timer once we're in researching phase
            timer_active = s["phase"] in ("researching", "done")
            yield (
                history,
                "",
                s,
                gr.update(value=status_text),
                gr.update(active=timer_active),
            )

        async def poll_updates(s: dict, log_text: str):
            """Drain log_q into the log textbox; reveal panels when done."""
            if s.get("log_q") is None:
                return (
                    log_text, s,
                    gr.update(),
                    gr.update(visible=False), gr.update(),  # workspace_row, path_md
                    gr.update(visible=False),               # file_panel
                    gr.update(active=False),                # timer
                    gr.update(),                            # file_dropdown
                )

            lines: list[str] = []
            done = False
            while not s["log_q"].empty():
                line = s["log_q"].get_nowait()
                if line == "__DONE__":
                    done = True
                    s["phase"] = "done"
                else:
                    lines.append(line)

            if lines:
                log_text = (log_text + "\n" + "\n".join(lines)).lstrip("\n")

            if done:
                choices = _list_workspace_files(s["workspace"])
                workspace_path = str(s["workspace"].resolve())
                return (
                    log_text, s,
                    gr.update(value="Research complete!"),
                    gr.update(visible=True),                                          # workspace_row
                    gr.update(value=f"**Workspace:** `{workspace_path}`"),            # workspace_path_md
                    gr.update(visible=True),                                          # file_panel
                    gr.update(active=False),                                          # stop timer
                    gr.update(choices=choices, value=choices[0] if choices else None),# file_dropdown
                )

            return (
                log_text, s,
                gr.update(),
                gr.update(visible=False), gr.update(),  # workspace_row, path_md
                gr.update(visible=False),               # file_panel
                gr.update(active=True),                 # keep timer running
                gr.update(),                            # file_dropdown
            )

        def show_file(filename: str, s: dict) -> str:
            return _read_file(filename, s["workspace"])

        def refresh_files(s: dict):
            choices = _list_workspace_files(s["workspace"])
            return gr.update(choices=choices, value=choices[0] if choices else None)

        def handle_open_folder(s: dict):
            _open_folder(s["workspace"])

        # ── Wire events ───────────────────────────────────────────────────

        send_outputs = [chatbot, user_input, state, status_md, timer]

        send_btn.click(
            send_message,
            inputs=[user_input, chatbot, state],
            outputs=send_outputs,
        )
        user_input.submit(
            send_message,
            inputs=[user_input, chatbot, state],
            outputs=send_outputs,
        )

        timer.tick(
            poll_updates,
            inputs=[state, log_box],
            outputs=[
                log_box, state, status_md,
                workspace_row, workspace_path_md,
                file_panel, timer, file_dropdown,
            ],
        )

        file_dropdown.change(
            show_file,
            inputs=[file_dropdown, state],
            outputs=[file_content],
        )
        refresh_btn.click(
            refresh_files,
            inputs=[state],
            outputs=[file_dropdown],
        )
        open_folder_btn.click(
            handle_open_folder,
            inputs=[state],
            outputs=[],
        )

    return demo


if __name__ == "__main__":
    app = build_app()
    app.launch()
