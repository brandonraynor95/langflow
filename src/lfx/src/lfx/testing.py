"""pytest plugin providing flow_runner fixtures for local Langflow flow execution.

The plugin is auto-discovered via the ``pytest11`` entry-point, so no
``conftest.py`` changes are needed.  Configure defaults via CLI options or
environment variables::

    pytest --lfx-env-file .env --lfx-timeout 60 tests/

Per-test overrides via markers::

    @pytest.mark.lfx_env_file(".env.test")
    @pytest.mark.lfx_timeout(30)
    def test_my_flow(flow_runner):
        result = flow_runner("flows/greeting.json", input_value="Hello")
        assert result.status == "success"
        assert "hello" in result.text.lower()

Tweaks (component-level field overrides, keyed by node id/type/display_name)::

    def test_with_tweaks(flow_runner):
        result = flow_runner(
            "flows/rag.json",
            input_value="What is Langflow?",
            tweaks={"OpenAI": {"model_name": "gpt-4o-mini", "temperature": 0.0}},
        )
        assert result.status == "success"

Async tests::

    async def test_async(async_flow_runner):
        result = await async_flow_runner("flows/greeting.json", input_value="Hi")
        assert result.status == "success"
"""

from __future__ import annotations

import asyncio
import contextlib
import copy
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_TEXT_REPR_MAX = 60

try:
    import pytest
except ImportError as exc:
    msg = "pytest is required for lfx.testing. Install it with: pip install pytest  (or pip install 'lfx[dev]')"
    raise ImportError(msg) from exc


# ---------------------------------------------------------------------------
# FlowResult — the object returned to test code
# ---------------------------------------------------------------------------


@dataclass
class FlowResult:
    """Result of a local flow execution via the ``flow_runner`` fixture.

    Attributes:
        status:   ``"success"`` or ``"error"``.
        text:     Primary text output of the flow (first non-empty text/result key).
        messages: List of message dicts produced by the flow.
        outputs:  Raw outputs dict from graph execution.
        logs:     Captured stdout/stderr from execution.
        error:    Error message when status is ``"error"``, else ``None``.
        timing:   Per-component timing dict when ``timing=True`` was passed, else ``None``.
        raw:      The unprocessed result dict returned by ``run_flow()``.
    """

    status: str
    text: str | None
    messages: list[dict[str, Any]]
    outputs: dict[str, Any]
    logs: str
    error: str | None
    timing: dict[str, Any] | None
    raw: dict[str, Any]

    @property
    def ok(self) -> bool:
        """``True`` when *status* is ``"success"``."""
        return self.status == "success"

    def first_text_output(self) -> str | None:
        """Return the primary text output, or ``None`` if there is none.

        Convenience alias for :attr:`text`, compatible with the
        ``langflow_sdk.RunResponse`` interface so test code works against
        both local and remote runners without changes.
        """
        return self.text

    def __repr__(self) -> str:
        snippet = (
            repr(self.text[:_TEXT_REPR_MAX] + "…") if self.text and len(self.text) > _TEXT_REPR_MAX else repr(self.text)
        )
        return f"FlowResult(status={self.status!r}, text={snippet})"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_result(raw: dict[str, Any]) -> FlowResult:
    """Construct a :class:`FlowResult` from the dict returned by ``run_flow()``."""
    # ``success`` may be absent (treat as True for forward compat)
    is_error = (raw.get("success") is False) or raw.get("type") == "error"
    status = "error" if is_error else "success"

    # Extract primary text from several candidate keys, in priority order
    text: str | None = None
    for key in ("result", "text", "output"):
        val = raw.get(key)
        if val is not None:
            text = val if isinstance(val, str) else json.dumps(val)
            break

    messages: list[dict[str, Any]] = raw.get("messages") or []
    if not isinstance(messages, list):
        messages = []

    outputs: dict[str, Any] = raw.get("outputs") or raw.get("result_dict") or {}
    if not isinstance(outputs, dict):
        outputs = {}

    error_msg: str | None = None
    if is_error:
        error_msg = raw.get("exception_message") or raw.get("error") or "Unknown error"

    return FlowResult(
        status=status,
        text=text,
        messages=messages,
        outputs=outputs,
        logs=raw.get("logs", ""),
        error=error_msg,
        timing=raw.get("timing"),
        raw=raw,
    )


def _build_result_from_sdk_response(response: Any) -> FlowResult:
    """Convert a ``langflow_sdk.RunResponse`` to a :class:`FlowResult`.

    Extracts text, messages, and raw outputs from the SDK response so that
    test assertions written against :class:`FlowResult` work identically
    whether the runner is local or remote.
    """
    text = response.first_text_output()

    messages: list[dict[str, Any]] = []
    outputs: dict[str, Any] = {}
    for i, out in enumerate(response.outputs):
        outputs[str(i)] = out.results
        for component_out in out.outputs:
            msg = component_out.get("results", {}).get("message")
            if isinstance(msg, dict):
                messages.append(msg)

    return FlowResult(
        status="success",
        text=text,
        messages=messages,
        outputs=outputs,
        logs="",
        error=None,
        timing=None,
        raw=response.model_dump(),
    )


def _apply_tweaks(flow_dict: dict[str, Any], tweaks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Return a *deep copy* of *flow_dict* with template field values patched.

    *tweaks* maps a node identifier — one of the node's ``id``, ``data.type``,
    or ``display_name`` — to a ``{field_name: new_value}`` dict.  All nodes
    whose identifier matches a tweak key are updated.
    """
    flow = copy.deepcopy(flow_dict)
    nodes = flow.get("data", {}).get("nodes", [])
    for node in nodes:
        node_data: dict = node.get("data") or {}
        node_id: str = node.get("id", "")
        node_type: str = node_data.get("type", "")
        node_obj: dict = node_data.get("node") or {}
        display_name: str = node_obj.get("display_name", "")
        template: dict = node_obj.get("template") or {}

        for tweak_key, field_overrides in tweaks.items():
            if tweak_key not in (node_id, node_type, display_name):
                continue
            for fname, fvalue in field_overrides.items():
                if fname not in template:
                    continue
                if isinstance(template[fname], dict):
                    template[fname]["value"] = fvalue
                else:
                    template[fname] = fvalue
    return flow


def _load_dotenv(env_file: str | Path) -> None:
    """Load environment variables from *env_file* using python-dotenv."""
    from dotenv import load_dotenv

    load_dotenv(str(env_file), override=True)


def _resolve_flow_args(
    flow: str | Path | dict[str, Any],
    tweaks: dict[str, dict[str, Any]] | None,
    base_dir: Path,
) -> tuple[Path | None, str | None]:
    """Return ``(script_path, flow_json)`` suitable for passing to ``run_flow()``.

    When *tweaks* are requested for a JSON flow, the file is loaded, patched,
    and returned as an inline JSON string so that ``run_flow()`` picks up the
    overrides without modifying any file on disk.
    """
    if isinstance(flow, dict):
        patched = _apply_tweaks(flow, tweaks) if tweaks else flow
        return None, json.dumps(patched)

    flow_path = Path(flow)
    if not flow_path.is_absolute():
        flow_path = base_dir / flow_path

    if tweaks and flow_path.suffix.lower() == ".json":
        with contextlib.suppress(Exception):
            raw_dict = json.loads(flow_path.read_text(encoding="utf-8"))
            return None, json.dumps(_apply_tweaks(raw_dict, tweaks))

    return flow_path, None


# ---------------------------------------------------------------------------
# Async core execution
# ---------------------------------------------------------------------------


async def _run_async(
    *,
    script_path: Path | None,
    flow_json: str | None,
    input_value: str | None,
    check_variables: bool,
    global_variables: dict[str, str] | None,
    session_id: str | None,
    user_id: str | None,
    timing: bool,
    timeout: float | None,
) -> dict[str, Any]:
    """Invoke ``run_flow()`` with an optional timeout; always returns a dict."""
    from lfx.run.base import RunError, run_flow

    async def _inner() -> dict:
        return await run_flow(
            script_path=script_path,
            flow_json=flow_json,
            input_value=input_value,
            check_variables=check_variables,
            global_variables=global_variables,
            session_id=session_id,
            user_id=user_id,
            timing=timing,
        )

    try:
        if timeout is not None:
            return await asyncio.wait_for(_inner(), timeout=timeout)
        return await _inner()
    except asyncio.TimeoutError:
        return {
            "success": False,
            "type": "error",
            "exception_type": "TimeoutError",
            "exception_message": f"Flow execution timed out after {timeout:.1f}s",
        }
    except RunError as exc:
        orig = exc.original_exception
        return {
            "success": False,
            "type": "error",
            "exception_type": type(orig).__name__ if orig else "RunError",
            "exception_message": str(exc),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "type": "error",
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        }


def _run_sync(**kwargs: Any) -> dict[str, Any]:
    """Run ``_run_async`` synchronously, handling already-running event loops.

    When called from inside a running event loop (e.g. a ``pytest-asyncio``
    test that requests the sync ``flow_runner`` fixture), the coroutine is
    dispatched to a fresh thread with its own event loop so we don't deadlock.
    """
    coro = _run_async(**kwargs)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — safe to use asyncio.run() directly
        return asyncio.run(coro)

    # There is a running loop; run in an isolated thread to avoid deadlock
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        try:
            t = kwargs.get("timeout")
            return future.result(timeout=t)
        except Exception as exc:  # noqa: BLE001
            return {
                "success": False,
                "type": "error",
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            }


# ---------------------------------------------------------------------------
# Callable classes
# ---------------------------------------------------------------------------


class LocalFlowRunner:
    """Sync callable returned by the :func:`flow_runner` fixture.

    Instantiate via the ``flow_runner`` pytest fixture — do not construct
    directly in test code.  Call it like a function::

        def test_greeting(flow_runner):
            result = flow_runner("flows/greeting.json", input_value="Hello")
            assert result.status == "success"
            assert "hello" in result.text.lower()

    The first positional argument can be:

    * A path string or :class:`~pathlib.Path` to a ``.json`` or ``.py`` flow file.
    * A ``dict`` (already-parsed flow JSON).

    Relative paths are resolved against ``--lfx-flow-dir`` (default: ``cwd``).
    """

    def __init__(
        self,
        *,
        default_env_file: str | Path | None = None,
        default_timeout: float | None = None,
        base_dir: Path | None = None,
    ) -> None:
        self._default_env_file = default_env_file
        self._default_timeout = default_timeout
        self._base_dir = base_dir or Path.cwd()

    def __call__(
        self,
        flow: str | Path | dict[str, Any],
        input_value: str | None = None,
        *,
        tweaks: dict[str, dict[str, Any]] | None = None,
        global_variables: dict[str, str] | None = None,
        env_file: str | Path | None = None,
        timeout: float | None = None,
        check_variables: bool = False,
        session_id: str | None = None,
        user_id: str | None = None,
        timing: bool = False,
    ) -> FlowResult:
        """Execute a flow synchronously and return a :class:`FlowResult`.

        Args:
            flow: Path (``.json``/``.py``) or parsed flow dict.
            input_value: Chat/text input string to pass into the flow.
            tweaks: Component-level overrides — ``{node_id|type|name: {field: value}}``.
            global_variables: Key→value pairs injected into the graph context.
            env_file: ``.env`` file loaded before execution (overrides fixture default).
            timeout: Seconds before aborting; ``None`` means no limit.
            check_variables: Validate that global variables exist in the environment.
            session_id: Session ID for memory isolation between calls.
            user_id: User ID attached to the graph.
            timing: Include per-component timing in :attr:`FlowResult.timing`.
        """
        _load_dotenv(env_file or self._default_env_file) if (env_file or self._default_env_file) else None

        script_path, flow_json = _resolve_flow_args(flow, tweaks, self._base_dir)
        resolved_timeout = timeout if timeout is not None else self._default_timeout

        raw = _run_sync(
            script_path=script_path,
            flow_json=flow_json,
            input_value=input_value,
            check_variables=check_variables,
            global_variables=global_variables,
            session_id=session_id,
            user_id=user_id,
            timing=timing,
            timeout=resolved_timeout,
        )
        return _build_result(raw)


class AsyncLocalFlowRunner:
    """Async callable returned by the :func:`async_flow_runner` fixture.

    Use with ``await`` inside an ``async def`` test::

        async def test_greeting(async_flow_runner):
            result = await async_flow_runner("flows/greeting.json", input_value="Hello")
            assert result.status == "success"
    """

    def __init__(
        self,
        *,
        default_env_file: str | Path | None = None,
        default_timeout: float | None = None,
        base_dir: Path | None = None,
    ) -> None:
        self._default_env_file = default_env_file
        self._default_timeout = default_timeout
        self._base_dir = base_dir or Path.cwd()

    async def __call__(
        self,
        flow: str | Path | dict[str, Any],
        input_value: str | None = None,
        *,
        tweaks: dict[str, dict[str, Any]] | None = None,
        global_variables: dict[str, str] | None = None,
        env_file: str | Path | None = None,
        timeout: float | None = None,
        check_variables: bool = False,
        session_id: str | None = None,
        user_id: str | None = None,
        timing: bool = False,
    ) -> FlowResult:
        """Execute a flow asynchronously and return a :class:`FlowResult`."""
        _load_dotenv(env_file or self._default_env_file) if (env_file or self._default_env_file) else None

        script_path, flow_json = _resolve_flow_args(flow, tweaks, self._base_dir)
        resolved_timeout = timeout if timeout is not None else self._default_timeout

        raw = await _run_async(
            script_path=script_path,
            flow_json=flow_json,
            input_value=input_value,
            check_variables=check_variables,
            global_variables=global_variables,
            session_id=session_id,
            user_id=user_id,
            timing=timing,
            timeout=resolved_timeout,
        )
        return _build_result(raw)


# ---------------------------------------------------------------------------
# Remote runner (requires langflow-sdk)
# ---------------------------------------------------------------------------


class RemoteFlowRunner:
    """Sync callable that runs flows against a live Langflow instance.

    Returned by :func:`flow_runner` when ``--langflow-env`` or
    ``--langflow-url`` is passed to pytest.  Call it like a function::

        def test_greeting(flow_runner):
            result = flow_runner("greeting-endpoint", "Hello!")
            assert result.first_text_output() is not None

    The first argument is a flow endpoint name or UUID (not a local file
    path).  Keyword arguments that only apply to local execution (e.g.
    ``env_file``, ``global_variables``) are accepted but silently ignored
    so that test code is portable between local and remote modes.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def __call__(
        self,
        flow_id_or_endpoint: str,
        input_value: str = "",
        *,
        input_type: str = "chat",
        output_type: str = "chat",
        tweaks: dict[str, Any] | None = None,
        **_kwargs: Any,
    ) -> FlowResult:
        """Run *flow_id_or_endpoint* against the remote instance."""
        try:
            from langflow_sdk.models import RunRequest  # type: ignore[import-untyped]
        except ImportError as exc:
            msg = "langflow-sdk is required for remote flow testing. Install: pip install langflow-sdk"
            raise ImportError(msg) from exc

        try:
            response = self._client.run_flow(
                flow_id_or_endpoint,
                RunRequest(
                    input_value=input_value,
                    input_type=input_type,
                    output_type=output_type,
                    tweaks=tweaks,
                ),
            )
        except Exception as exc:  # noqa: BLE001
            return FlowResult(
                status="error",
                text=None,
                messages=[],
                outputs={},
                logs="",
                error=str(exc),
                timing=None,
                raw={},
            )

        return _build_result_from_sdk_response(response)


class AsyncRemoteFlowRunner:
    """Async callable that runs flows against a live Langflow instance.

    Returned by :func:`async_flow_runner` when ``--langflow-env`` or
    ``--langflow-url`` is passed to pytest.  Use with ``await``::

        async def test_greeting(async_flow_runner):
            result = await async_flow_runner("greeting-endpoint", "Hello!")
            assert result.first_text_output() is not None
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    async def __call__(
        self,
        flow_id_or_endpoint: str,
        input_value: str = "",
        *,
        input_type: str = "chat",
        output_type: str = "chat",
        tweaks: dict[str, Any] | None = None,
        **_kwargs: Any,
    ) -> FlowResult:
        """Run *flow_id_or_endpoint* asynchronously against the remote instance."""
        try:
            from langflow_sdk.models import RunRequest  # type: ignore[import-untyped]
        except ImportError as exc:
            msg = "langflow-sdk is required for remote flow testing. Install: pip install langflow-sdk"
            raise ImportError(msg) from exc

        try:
            response = await self._client.run_flow(
                flow_id_or_endpoint,
                RunRequest(
                    input_value=input_value,
                    input_type=input_type,
                    output_type=output_type,
                    tweaks=tweaks,
                ),
            )
        except Exception as exc:  # noqa: BLE001
            return FlowResult(
                status="error",
                text=None,
                messages=[],
                outputs={},
                logs="",
                error=str(exc),
                timing=None,
                raw={},
            )

        return _build_result_from_sdk_response(response)


# ---------------------------------------------------------------------------
# pytest plugin hooks & fixtures
# ---------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register lfx-specific CLI options."""
    group = parser.getgroup("lfx", "lfx local flow execution options")
    group.addoption(
        "--lfx-env-file",
        dest="lfx_env_file",
        default=None,
        metavar="PATH",
        help="Path to a .env file loaded before each flow execution.",
    )
    group.addoption(
        "--lfx-timeout",
        dest="lfx_timeout",
        default=None,
        type=float,
        metavar="SECONDS",
        help="Default timeout in seconds for flow execution (0 = no limit).",
    )
    group.addoption(
        "--lfx-flow-dir",
        dest="lfx_flow_dir",
        default=None,
        metavar="DIR",
        help="Base directory for resolving relative flow paths (default: cwd).",
    )

    # Guard against duplicate registration when langflow-sdk[testing] is also installed.
    # Both plugins expose the same --langflow-* options; only register them once.
    remote = parser.getgroup("langflow", "Langflow remote integration testing options")
    _remote_opts = {
        "--langflow-env": {
            "dest": "langflow_env",
            "default": None,
            "metavar": "NAME",
            "help": (
                "Named environment from .lfx/environments.yaml or langflow-environments.toml. "
                "When set, flow_runner targets the remote instance instead of running locally."
            ),
        },
        "--langflow-url": {
            "dest": "langflow_url",
            "default": None,
            "metavar": "URL",
            "help": "Base URL of the remote Langflow instance (overrides --langflow-env).",
        },
        "--langflow-api-key": {
            "dest": "langflow_api_key",
            "default": None,
            "metavar": "KEY",
            "help": "API key for the remote Langflow instance.",
        },
        "--langflow-environments-file": {
            "dest": "langflow_environments_file",
            "default": None,
            "metavar": "PATH",
            "help": "Path to environments config file (.yaml or .toml; overrides default lookup).",
        },
    }
    for flag, kwargs in _remote_opts.items():
        with contextlib.suppress(ValueError):
            remote.addoption(flag, **kwargs)


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers so pytest --strict-markers does not reject them."""
    config.addinivalue_line(
        "markers",
        "lfx_env_file(path): path to a .env file loaded before this test's flow execution",
    )
    config.addinivalue_line(
        "markers",
        "lfx_timeout(seconds): timeout in seconds for this test's flow execution",
    )
    config.addinivalue_line(
        "markers",
        "integration: integration test that requires a live Langflow instance",
    )


_SKIP_NO_REMOTE = (
    "No remote Langflow connection configured. "
    "Pass --langflow-url <URL> or --langflow-env <NAME> to run against a live instance."
)


def _resolve_remote_client(request: pytest.FixtureRequest) -> Any | None:
    """Return a sync SDK client if remote options are configured, else ``None``.

    Priority:
    1. ``--langflow-url`` / ``LANGFLOW_URL`` — direct URL (with optional ``--langflow-api-key``)
    2. ``--langflow-env`` / ``LANGFLOW_ENV`` — named environment from TOML/YAML file
    """
    url: str | None = request.config.getoption("langflow_url", default=None) or os.environ.get("LANGFLOW_URL")
    env_name: str | None = request.config.getoption("langflow_env", default=None) or os.environ.get("LANGFLOW_ENV")

    if not url and not env_name:
        return None

    try:
        import langflow_sdk  # type: ignore[import-untyped]
    except ImportError:
        pytest.skip("langflow-sdk is required for remote testing. Install: pip install langflow-sdk")

    if url:
        api_key: str | None = request.config.getoption("langflow_api_key", default=None) or os.environ.get(
            "LANGFLOW_API_KEY"
        )
        return langflow_sdk.Client(base_url=url, api_key=api_key)

    # Named environment
    env_file: str | None = request.config.getoption("langflow_environments_file", default=None) or os.environ.get(
        "LANGFLOW_ENVIRONMENTS_FILE"
    )
    try:
        from pathlib import Path as _Path

        from langflow_sdk.environments import get_client  # type: ignore[import-untyped]

        return get_client(env_name, config_file=_Path(env_file) if env_file else None)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Could not configure Langflow environment {env_name!r}: {exc}")


def _resolve_async_remote_client(request: pytest.FixtureRequest) -> Any | None:
    """Return an async SDK client if remote options are configured, else ``None``."""
    url: str | None = request.config.getoption("langflow_url", default=None) or os.environ.get("LANGFLOW_URL")
    env_name: str | None = request.config.getoption("langflow_env", default=None) or os.environ.get("LANGFLOW_ENV")

    if not url and not env_name:
        return None

    try:
        import langflow_sdk  # type: ignore[import-untyped]
    except ImportError:
        pytest.skip("langflow-sdk is required for remote testing. Install: pip install langflow-sdk")

    if url:
        api_key: str | None = request.config.getoption("langflow_api_key", default=None) or os.environ.get(
            "LANGFLOW_API_KEY"
        )
        return langflow_sdk.AsyncClient(base_url=url, api_key=api_key)

    env_file: str | None = request.config.getoption("langflow_environments_file", default=None) or os.environ.get(
        "LANGFLOW_ENVIRONMENTS_FILE"
    )
    try:
        from pathlib import Path as _Path

        from langflow_sdk.environments import get_async_client  # type: ignore[import-untyped]

        return get_async_client(env_name, config_file=_Path(env_file) if env_file else None)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Could not configure Langflow environment {env_name!r}: {exc}")


def _get_marker_arg(request: pytest.FixtureRequest, name: str) -> Any:
    """Return the first positional argument of marker *name*, or ``None``."""
    marker = request.node.get_closest_marker(name)
    return marker.args[0] if marker and marker.args else None


def _resolve_runner_config(
    request: pytest.FixtureRequest,
) -> tuple[str | None, float | None, Path | None]:
    """Return ``(env_file, timeout, base_dir)`` with marker > CLI > env-var precedence."""
    # env_file: marker > --lfx-env-file > LFX_ENV_FILE
    env_file: str | None = (
        _get_marker_arg(request, "lfx_env_file")
        or request.config.getoption("lfx_env_file", default=None)
        or os.environ.get("LFX_ENV_FILE")
    )

    # timeout: marker > --lfx-timeout > LFX_TIMEOUT
    timeout: float | None = _get_marker_arg(request, "lfx_timeout")
    if timeout is None:
        raw_t = request.config.getoption("lfx_timeout", default=None) or os.environ.get("LFX_TIMEOUT")
        if raw_t is not None:
            with contextlib.suppress(TypeError, ValueError):
                timeout = float(raw_t)

    # base_dir: --lfx-flow-dir > LFX_FLOW_DIR > None (defaults to cwd in runner)
    dir_str: str | None = request.config.getoption("lfx_flow_dir", default=None) or os.environ.get("LFX_FLOW_DIR")
    base_dir: Path | None = Path(dir_str) if dir_str else None

    return env_file, timeout, base_dir


@pytest.fixture
def flow_runner(
    request: pytest.FixtureRequest,
) -> LocalFlowRunner | RemoteFlowRunner:
    """Fixture providing a sync flow runner — local or remote depending on CLI options.

    **Local mode** (default)
        Runs the flow in-process.  Configure with:

        * ``@pytest.mark.lfx_env_file(path)`` / ``@pytest.mark.lfx_timeout(seconds)``
        * ``--lfx-env-file`` / ``--lfx-timeout`` / ``--lfx-flow-dir``
        * ``LFX_ENV_FILE`` / ``LFX_TIMEOUT`` / ``LFX_FLOW_DIR``

    **Remote mode** (when ``--langflow-env`` or ``--langflow-url`` is supplied)
        Calls the live Langflow API.  Requires ``langflow-sdk``.

        * ``--langflow-env <NAME>`` — named environment from ``.lfx/environments.yaml``
        * ``--langflow-url <URL>`` — direct URL
        * ``--langflow-api-key <KEY>`` / ``LANGFLOW_API_KEY``
        * ``--langflow-environments-file <PATH>`` / ``LANGFLOW_ENVIRONMENTS_FILE``
        * ``LANGFLOW_ENV`` / ``LANGFLOW_URL``

    Example (local)::

        def test_greeting(flow_runner):
            result = flow_runner("flows/greeting.json", input_value="Hello")
            assert result.ok

    Example (remote — run with ``pytest --langflow-env staging``)::

        @pytest.mark.integration
        def test_greeting(flow_runner):
            result = flow_runner("greeting-endpoint", "Hello!")
            assert result.first_text_output() is not None
    """
    client = _resolve_remote_client(request)
    if client is not None:
        return RemoteFlowRunner(client)

    env_file, timeout, base_dir = _resolve_runner_config(request)
    return LocalFlowRunner(
        default_env_file=env_file,
        default_timeout=timeout,
        base_dir=base_dir,
    )


@pytest.fixture
def async_flow_runner(
    request: pytest.FixtureRequest,
) -> AsyncLocalFlowRunner | AsyncRemoteFlowRunner:
    """Fixture providing an async flow runner — local or remote depending on CLI options.

    Same mode-selection logic as :func:`flow_runner`.

    Example (local)::

        async def test_greeting(async_flow_runner):
            result = await async_flow_runner("flows/greeting.json", input_value="Hi")
            assert result.ok

    Example (remote)::

        @pytest.mark.integration
        async def test_greeting(async_flow_runner):
            result = await async_flow_runner("greeting-endpoint", "Hi!")
            assert result.first_text_output() is not None
    """
    client = _resolve_async_remote_client(request)
    if client is not None:
        return AsyncRemoteFlowRunner(client)

    env_file, timeout, base_dir = _resolve_runner_config(request)
    return AsyncLocalFlowRunner(
        default_env_file=env_file,
        default_timeout=timeout,
        base_dir=base_dir,
    )
