import multiprocessing
import platform
import queue
import threading
import time
from contextlib import suppress

from lfx.base.data import BaseFileComponent
from lfx.base.data.docling_utils import _serialize_pydantic_model, docling_worker
from lfx.inputs import BoolInput, DropdownInput, HandleInput, StrInput
from lfx.schema import Data

_USE_SUBPROCESS = platform.system() == "Darwin"


class DoclingInlineComponent(BaseFileComponent):
    display_name = "Docling"
    description = "Uses Docling to process input documents running the Docling models locally."
    documentation = "https://docling-project.github.io/docling/"
    trace_type = "tool"
    icon = "Docling"
    name = "DoclingInline"

    # https://docling-project.github.io/docling/usage/supported_formats/
    VALID_EXTENSIONS = [
        "adoc",
        "asciidoc",
        "asc",
        "bmp",
        "csv",
        "dotx",
        "dotm",
        "docm",
        "docx",
        "htm",
        "html",
        "jpeg",
        "json",
        "md",
        "pdf",
        "png",
        "potx",
        "ppsx",
        "pptm",
        "potm",
        "ppsm",
        "pptx",
        "tiff",
        "txt",
        "xls",
        "xlsx",
        "xhtml",
        "xml",
        "webp",
    ]

    inputs = [
        *BaseFileComponent.get_base_inputs(),
        DropdownInput(
            name="pipeline",
            display_name="Pipeline",
            info="Docling pipeline to use",
            options=["standard", "vlm"],
            value="standard",
        ),
        DropdownInput(
            name="ocr_engine",
            display_name="OCR Engine",
            info="OCR engine to use. None will disable OCR.",
            options=["None", "easyocr", "tesserocr", "rapidocr", "ocrmac"],
            value="None",
        ),
        BoolInput(
            name="do_picture_classification",
            display_name="Picture classification",
            info="If enabled, the Docling pipeline will classify the pictures type.",
            value=False,
        ),
        HandleInput(
            name="pic_desc_llm",
            display_name="Picture description LLM",
            info="If connected, the model to use for running the picture description task.",
            input_types=["LanguageModel"],
            required=False,
        ),
        StrInput(
            name="pic_desc_prompt",
            display_name="Picture description prompt",
            value="Describe the image in three sentences. Be concise and accurate.",
            info="The user prompt to use when invoking the model.",
            advanced=True,
        ),
        # TODO: expose more Docling options
    ]

    outputs = [
        *BaseFileComponent.get_base_outputs(),
    ]

    def _wait_for_result_with_worker_monitoring(self, result_queue, worker, timeout: int = 300):
        """Wait for result from queue while monitoring worker health.

        Works with both threading.Thread and multiprocessing.Process workers.
        Handles cases where the worker crashes without sending a result.
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            if not worker.is_alive():
                try:
                    result = result_queue.get_nowait()
                except queue.Empty:
                    exit_code = getattr(worker, "exitcode", None)
                    if exit_code is not None and exit_code != 0:
                        msg = f"Worker process exited with code {exit_code}"
                    else:
                        msg = "Worker crashed unexpectedly without producing result."
                    raise RuntimeError(msg) from None
                else:
                    self.log("Worker completed and result retrieved")
                    return result

            try:
                result = result_queue.get(timeout=1)
            except queue.Empty:
                continue
            except (EOFError, OSError):
                # Queue pipe broken — worker likely crashed
                if not worker.is_alive():
                    msg = "Worker crashed and queue connection lost."
                    raise RuntimeError(msg) from None
                continue
            else:
                self.log("Result received from worker")
                return result

        msg = f"Worker timed out after {timeout} seconds"
        raise TimeoutError(msg)

    def _terminate_worker_gracefully(self, worker, timeout: int = 10):
        """Terminate worker gracefully.

        For processes: sends SIGTERM, waits, then SIGKILL if still alive.
        For threads: waits for completion (threads cannot be forcefully killed).
        """
        if not worker.is_alive():
            return

        self.log("Waiting for worker to complete gracefully")

        if hasattr(worker, "terminate"):
            # multiprocessing.Process — can be forcefully terminated
            worker.terminate()
            worker.join(timeout=timeout)
            if worker.is_alive():
                self.log("Warning: Process still alive after timeout, killing")
                worker.kill()
                worker.join(timeout=5)
        else:
            # threading.Thread — can only wait
            worker.join(timeout=timeout)
            if worker.is_alive():
                self.log("Warning: Thread still alive after timeout")

    def process_files(self, file_list: list[BaseFileComponent.BaseFile]) -> list[BaseFileComponent.BaseFile]:
        try:
            from docling.document_converter import DocumentConverter  # noqa: F401
        except ImportError as e:
            msg = (
                "Docling is an optional dependency. Install with `uv pip install 'langflow[docling]'` or refer to the "
                "documentation on how to install optional dependencies."
            )
            raise ImportError(msg) from e

        file_paths = [file.path for file in file_list if file.path]

        if not file_paths:
            self.log("No files to process.")
            return file_list

        pic_desc_config: dict | None = None
        if self.pic_desc_llm is not None:
            pic_desc_config = _serialize_pydantic_model(self.pic_desc_llm)

        worker_kwargs = {
            "file_paths": file_paths,
            "pipeline": self.pipeline,
            "ocr_engine": self.ocr_engine,
            "do_picture_classification": self.do_picture_classification,
            "pic_desc_config": pic_desc_config,
            "pic_desc_prompt": self.pic_desc_prompt,
        }

        if _USE_SUBPROCESS:
            # Subprocess with "spawn" context keeps the parent's GIL free so
            # Gunicorn heartbeats continue during heavy model loading.
            ctx = multiprocessing.get_context("spawn")
            result_queue = ctx.Queue()
            worker = ctx.Process(
                target=docling_worker,
                kwargs={**worker_kwargs, "queue": result_queue},
                daemon=False,
            )
        else:
            # Threading shares the in-process DocumentConverter cache across runs.
            result_queue = queue.Queue()
            worker = threading.Thread(
                target=docling_worker,
                kwargs={**worker_kwargs, "queue": result_queue},
                daemon=False,
            )

        result = None
        worker.start()

        try:
            result = self._wait_for_result_with_worker_monitoring(result_queue, worker, timeout=300)
        except KeyboardInterrupt:
            self.log("Docling worker cancelled by user")
            result = []
        except Exception as e:
            self.log(f"Error during processing: {e}")
            raise
        finally:
            self._terminate_worker_gracefully(worker)
            if _USE_SUBPROCESS:
                with suppress(Exception):
                    result_queue.close()
                    result_queue.join_thread()

        # Enhanced error checking with dependency-specific handling
        if isinstance(result, dict) and "error" in result:
            error_msg = result["error"]

            # Handle dependency errors specifically
            if result.get("error_type") == "dependency_error":
                dependency_name = result.get("dependency_name", "Unknown dependency")
                install_command = result.get("install_command", "Please check documentation")

                # Create a user-friendly error message
                user_message = (
                    f"Missing OCR dependency: {dependency_name}. "
                    f"{install_command} "
                    f"Alternatively, you can set OCR Engine to 'None' to disable OCR processing."
                )
                raise ImportError(user_message)

            # Handle other specific errors
            if error_msg.startswith("Docling is not installed"):
                raise ImportError(error_msg)

            # Handle graceful shutdown
            if "Worker interrupted by SIGINT" in error_msg or "shutdown" in result:
                self.log("Docling process cancelled by user")
                result = []
            else:
                raise RuntimeError(error_msg)

        processed_data = [Data(data={"doc": r["document"], "file_path": r["file_path"]}) if r else None for r in result]
        return self.rollup_data(file_list, processed_data)
