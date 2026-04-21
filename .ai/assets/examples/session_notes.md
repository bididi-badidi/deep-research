# Session Handover Notes

**Target:** Reviewer Agent or Next Coder Agent

## ⚠️ Fragile Code / Watch Out

- **Concurrency Lock:** I added an `asyncio.Lock` (a synchronization mechanism that prevents multiple concurrent processes from accessing shared resources simultaneously) inside the `StateManager` to handle rapid user message spam. Please review the `/reset` command flow. I am worried the lock might not release properly if the `gemini chat` subprocess raises an unexpected exception before reaching the `finally` block.
- **Subprocess Cleanup:** The `await session.active_process.wait()` call in `utils.py` seems stable, but it relies on the OS (Operating System) successfully sending SIGTERM (a signal used to request a program to terminate gracefully). If the user is running this bot on Windows, this might behave differently than on Linux.

## 🧠 Context / Technical Decisions

- **Why UUIDs?** We switched from incremental integer IDs to UUIDs (Universally Unique Identifiers) for the `session_id`. Do not revert this. When the Telegram bot restarts, integer IDs overlap with old log files, making debugging impossible.
- **Lookback Buffer Magic Number:** You will see a `BUFFER_SIZE = 1024` in `subprocess_manager.py`. I chose 1024 bytes because the Gemini API (Application Programming Interface) error strings max out around 800 bytes. A smaller buffer causes the error detection regex (a sequence of characters that specifies a search pattern in text) to split the error message in half, causing silent failures.

## ⏭️ Next Steps / Blockers

- The `/resume` logic is implemented and working for text.
- **Blocker:** We are currently blocked from handling images during a resumed session.
- **Your Task:** Do not attempt to pass raw image paths directly. We need to implement a queueing system for media files first. Look at the `.gemini/temp_media/` directory to build the staging area.
