from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Dict, List
from uuid import uuid4

from flask import Flask, Response, jsonify, render_template, request

from document_loader.universal_loader import ProgressUpdate, UniversalDocumentLoader
from helpers.log import get_logger

app = Flask(__name__)
logger = get_logger(__name__)

TASKS: Dict[str, Dict[str, object]] = {}
TASKS_LOCK = threading.Lock()


def _update_task(task_id: str, **updates: object) -> None:
    with TASKS_LOCK:
        if task_id not in TASKS:
            return
        TASKS[task_id].update(updates)


def _append_recent(task_id: str, entry: Dict[str, object], limit: int = 10) -> None:
    with TASKS_LOCK:
        if task_id not in TASKS:
            return
        recent = TASKS[task_id].get("recent", [])
        recent.append(entry)
        TASKS[task_id]["recent"] = recent[-limit:]


def _run_loader(task_id: str, directory: Path, recursive: bool, max_workers: int) -> None:
    loader = UniversalDocumentLoader(
        root_directory=directory,
        recursive=recursive,
        show_progress=False,
        use_multithreading=True,
        max_workers=max_workers,
    )

    def progress_callback(update: ProgressUpdate) -> None:
        _update_task(
            task_id,
            status="processing",
            progress={"current": update.current, "total": update.total},
            loaded=update.loaded,
            failed=update.failed,
            current_file=update.current_file,
        )
        if update.event in {"loaded", "skipped", "failed"}:
            _append_recent(
                task_id,
                {
                    "path": update.current_file,
                    "event": update.event,
                    "message": update.message,
                },
            )

    start = time.perf_counter()
    try:
        documents = loader.load(progress_callback=progress_callback)
    except Exception as exc:  # noqa: BLE001
        logger.error("event=load_failed task=%s error=%s", task_id, exc)
        _update_task(task_id, status="failed", error=str(exc))
        return

    duration = round(time.perf_counter() - start, 3)

    documents_payload = [
        {"page_content": doc.page_content, "metadata": doc.metadata} for doc in documents
    ]
    previews: List[Dict[str, object]] = []
    for doc in documents:
        preview = " ".join(doc.page_content.split())[:140]
        previews.append(
            {
                "source": doc.metadata.get("source"),
                "size_bytes": doc.metadata.get("size_bytes"),
                "modified_at": doc.metadata.get("modified_at"),
                "preview": preview,
            }
        )

    stats = {
        "total_files": loader.stats.get("total_files", 0),
        "loaded": loader.stats.get("loaded", 0),
        "failed": loader.stats.get("failed", 0),
        "duration_seconds": duration,
    }

    _update_task(
        task_id,
        status="complete",
        progress={
            "current": stats["total_files"],
            "total": stats["total_files"],
        },
        loaded=stats["loaded"],
        failed=stats["failed"],
        current_file="",
        documents=documents_payload,
        previews=previews,
        errors=loader.errors,
        stats=stats,
    )


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/loading/<task_id>")
def loading(task_id: str) -> str:
    return render_template("loading.html", task_id=task_id)


@app.route("/results/<task_id>")
def results(task_id: str) -> str:
    return render_template("results.html", task_id=task_id)


@app.post("/api/load")
def api_load() -> Response:
    payload = request.get_json(silent=True) or {}
    directory = payload.get("directory")
    recursive = bool(payload.get("recursive", True))
    max_workers = int(payload.get("max_workers", 4))

    if not directory:
        return jsonify({"status": "error", "error": "directory_required"}), 400

    root_path = Path(directory)
    if not root_path.exists() or not root_path.is_dir():
        return jsonify({"status": "error", "error": "directory_not_found"}), 400

    task_id = str(uuid4())
    with TASKS_LOCK:
        TASKS[task_id] = {
            "status": "queued",
            "directory": str(root_path),
            "recursive": recursive,
            "max_workers": max_workers,
            "progress": {"current": 0, "total": 0},
            "loaded": 0,
            "failed": 0,
            "current_file": "",
            "documents": [],
            "previews": [],
            "errors": [],
            "recent": [],
            "stats": {},
        }

    thread = threading.Thread(
        target=_run_loader,
        args=(task_id, root_path, recursive, max_workers),
        daemon=True,
    )
    thread.start()

    return jsonify({"task_id": task_id, "status": "started"})


@app.get("/api/status/<task_id>")
def api_status(task_id: str) -> Response:
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        if not task:
            return jsonify({"status": "error", "error": "task_not_found"}), 404

        response = {
            "status": task.get("status"),
            "progress": task.get("progress"),
            "loaded": task.get("loaded"),
            "failed": task.get("failed"),
            "current_file": task.get("current_file"),
            "recent": task.get("recent", []),
        }
    return jsonify(response)


@app.get("/api/results/<task_id>")
def api_results(task_id: str) -> Response:
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        if not task:
            return jsonify({"status": "error", "error": "task_not_found"}), 404

        response = {
            "status": task.get("status"),
            "documents": task.get("documents", []),
            "previews": task.get("previews", []),
            "stats": task.get("stats", {}),
            "errors": task.get("errors", []),
        }
    return jsonify(response)


@app.get("/api/download/<task_id>")
def api_download(task_id: str) -> Response:
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        if not task:
            return jsonify({"status": "error", "error": "task_not_found"}), 404

        payload = {
            "status": task.get("status"),
            "documents": task.get("documents", []),
            "stats": task.get("stats", {}),
            "errors": task.get("errors", []),
        }

    data = json.dumps(payload, ensure_ascii=True, indent=2)
    return Response(
        data,
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=documents.json"},
    )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5001)
