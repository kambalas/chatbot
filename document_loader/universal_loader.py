from __future__ import annotations

import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from tqdm import tqdm

from document_loader.extractors import EXTRACTOR_BY_EXTENSION
from entities.document import Document
from helpers.log import get_logger

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024


@dataclass
class ProgressUpdate:
    current: int
    total: int
    loaded: int
    failed: int
    current_file: str
    event: str
    message: Optional[str]


@dataclass
class ProcessResult:
    path: Path
    document: Optional[Document]
    reason: Optional[str]
    error: Optional[str]
    duration: float
    file_type: str
    size_bytes: int


class UniversalDocumentLoader:
    def __init__(
        self,
        root_directory: Path,
        recursive: bool = True,
        show_progress: bool = True,
        use_multithreading: bool = True,
        max_workers: int = 4,
    ) -> None:
        self.root_directory = Path(root_directory)
        self.recursive = recursive
        self.show_progress = show_progress
        self.use_multithreading = use_multithreading
        self.max_workers = max_workers
        self.errors: List[Dict[str, str]] = []
        self.stats: Dict[str, object] = {}
        self._logger = get_logger(__name__)

    def load(self, progress_callback: Optional[Callable[[ProgressUpdate], None]] = None) -> List[Document]:
        start_time = time.perf_counter()
        self.errors = []
        self.stats = {}

        self._logger.info(
            f"event=scan_start directory={self.root_directory} recursive={self.recursive}"
        )

        paths, ext_counts = self._scan_files()
        total_files = len(paths)
        self._logger.info(f"event=files_found total={total_files} extensions={ext_counts}")

        if progress_callback:
            progress_callback(
                ProgressUpdate(
                    current=0,
                    total=total_files,
                    loaded=0,
                    failed=0,
                    current_file="",
                    event="scan_complete",
                    message=None,
                )
            )

        documents: List[Document] = []
        loaded = 0
        failed = 0
        processed = 0

        progress_bar = tqdm(total=total_files, disable=not self.show_progress)

        def handle_result(result: ProcessResult) -> None:
            nonlocal loaded, failed, processed
            processed += 1
            relative_path = self._relative_path(result.path)
            if result.document:
                documents.append(result.document)
                loaded += 1
                event = "loaded"
                message = None
            else:
                failed += 1
                self.errors.append(
                    {
                        "path": relative_path,
                        "reason": result.reason or "extraction_failed",
                        "error": result.error or "",
                    }
                )
                event = "skipped" if result.reason else "failed"
                message = result.error or result.reason

            if progress_callback:
                progress_callback(
                    ProgressUpdate(
                        current=processed,
                        total=total_files,
                        loaded=loaded,
                        failed=failed,
                        current_file=relative_path,
                        event=event,
                        message=message,
                    )
                )

            progress_bar.update(1)

        if self.use_multithreading and total_files > 1:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(self._process_file, path) for path in paths]
                for future in as_completed(futures):
                    handle_result(future.result())
        else:
            for path in paths:
                handle_result(self._process_file(path))

        progress_bar.close()

        duration = time.perf_counter() - start_time
        self.stats = {
            "total_files": total_files,
            "loaded": loaded,
            "failed": failed,
            "duration_seconds": round(duration, 3),
        }

        self._logger.info(
            "event=load_complete documents=%s duration=%ss success=%s failed=%s",
            loaded,
            round(duration, 3),
            loaded,
            failed,
        )

        return documents

    def _scan_files(self) -> Tuple[List[Path], Dict[str, int]]:
        if not self.root_directory.exists():
            raise FileNotFoundError(f"Directory not found: {self.root_directory}")
        if not self.root_directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {self.root_directory}")

        ext_counts: Dict[str, int] = {}
        paths: List[Path] = []

        if self.recursive:
            for dirpath, dirnames, filenames in os.walk(self.root_directory, topdown=True):
                visible_dirnames = []
                for dirname in dirnames:
                    if dirname.startswith("."):
                        continue
                    candidate = Path(dirpath) / dirname
                    if candidate.is_symlink():
                        self._logger.warning(
                            f"event=file_skipped path={candidate} reason=symlink_unsupported"
                        )
                        continue
                    visible_dirnames.append(dirname)
                dirnames[:] = visible_dirnames

                for filename in filenames:
                    if filename.startswith("."):
                        continue
                    path = Path(dirpath) / filename
                    if path.is_dir():
                        continue
                    paths.append(path)
                    ext = path.suffix.lower() or "no_ext"
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1
        else:
            for path in self.root_directory.iterdir():
                if path.name.startswith("."):
                    continue
                if path.is_symlink():
                    self._logger.warning(
                        f"event=file_skipped path={path} reason=symlink_unsupported"
                    )
                    continue
                if path.is_dir():
                    continue
                paths.append(path)
                ext = path.suffix.lower() or "no_ext"
                ext_counts[ext] = ext_counts.get(ext, 0) + 1

        return paths, ext_counts

    def _process_file(self, path: Path) -> ProcessResult:
        start_time = time.perf_counter()
        file_type = path.suffix.lower().lstrip(".") or "unknown"
        size_bytes = 0

        try:
            if path.is_symlink():
                self._logger.warning(
                    f"event=file_skipped path={path} reason=symlink_unsupported"
                )
                return ProcessResult(path, None, "symlink_unsupported", None, 0.0, file_type, 0)

            if not path.exists():
                self._logger.warning(f"event=file_skipped path={path} reason=file_not_found")
                return ProcessResult(path, None, "file_not_found", None, 0.0, file_type, 0)

            try:
                size_bytes = path.stat().st_size
            except PermissionError as exc:
                self._logger.warning(
                    f"event=file_skipped path={path} reason=permission_denied"
                )
                return ProcessResult(path, None, "permission_denied", str(exc), 0.0, file_type, 0)

            if size_bytes == 0:
                self._logger.warning(f"event=file_skipped path={path} reason=empty_file")
                return ProcessResult(path, None, "empty_file", None, 0.0, file_type, size_bytes)

            if size_bytes > MAX_FILE_SIZE_BYTES:
                self._logger.warning(f"event=file_skipped path={path} reason=file_too_large")
                return ProcessResult(path, None, "file_too_large", None, 0.0, file_type, size_bytes)

            extractor = EXTRACTOR_BY_EXTENSION.get(path.suffix.lower())
            if extractor is None:
                reason = (
                    "dependency_missing" if path.suffix.lower() == ".pptx" else "unsupported_format"
                )
                self._logger.warning(f"event=file_skipped path={path} reason={reason}")
                return ProcessResult(path, None, reason, None, 0.0, file_type, size_bytes)

            text = extractor(path)
            if not text or not text.strip():
                self._logger.warning(f"event=file_skipped path={path} reason=empty_file")
                return ProcessResult(path, None, "empty_file", None, 0.0, file_type, size_bytes)

            metadata = {
                "source": self._relative_path(path),
                "file_type": file_type,
                "size_bytes": size_bytes,
                "modified_at": datetime.fromtimestamp(
                    path.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
            }

            duration = round(time.perf_counter() - start_time, 3)
            self._logger.info(
                "event=file_loaded path=%s type=%s size=%s duration=%ss",
                path,
                file_type,
                size_bytes,
                duration,
            )
            return ProcessResult(
                path=path,
                document=Document(page_content=text, metadata=metadata),
                reason=None,
                error=None,
                duration=duration,
                file_type=file_type,
                size_bytes=size_bytes,
            )
        except PermissionError as exc:
            self._logger.warning(f"event=file_skipped path={path} reason=permission_denied")
            return ProcessResult(path, None, "permission_denied", str(exc), 0.0, file_type, size_bytes)
        except Exception as exc:  # noqa: BLE001 - explicit error handling
            self._logger.error(
                "event=extraction_failed path=%s error=%s traceback=%s",
                path,
                exc,
                traceback.format_exc(),
            )
            return ProcessResult(path, None, None, str(exc), 0.0, file_type, size_bytes)

    def _relative_path(self, path: Path) -> str:
        try:
            relative = path.relative_to(self.root_directory)
        except ValueError:
            relative = Path(os.path.relpath(path, self.root_directory))
        return str(relative).replace(os.sep, "/")
