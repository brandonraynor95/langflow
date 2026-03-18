"""Unit tests for SDK models and environment config."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path
from uuid import UUID

import pytest

from langflow_sdk.models import Flow, FlowCreate, FlowUpdate, Project, RunRequest, RunResponse


# ---------------------------------------------------------------------------
# Model round-trip tests
# ---------------------------------------------------------------------------


def test_flow_parse_minimal():
    data = {
        "id": "00000000-0000-0000-0000-000000000001",
        "name": "My Flow",
    }
    flow = Flow.model_validate(data)
    assert flow.id == UUID("00000000-0000-0000-0000-000000000001")
    assert flow.name == "My Flow"
    assert flow.is_component is False


def test_flow_create_exclude_none():
    fc = FlowCreate(name="Test")
    dumped = fc.model_dump(exclude_none=True)
    assert "description" not in dumped
    assert dumped["name"] == "Test"


def test_flow_update_partial():
    fu = FlowUpdate(name="Renamed")
    dumped = fu.model_dump(exclude_none=True)
    assert dumped == {"name": "Renamed"}


def test_project_parse():
    data = {
        "id": "00000000-0000-0000-0000-000000000002",
        "name": "My Project",
        "parent_id": None,
    }
    p = Project.model_validate(data)
    assert p.name == "My Project"


def test_run_request_defaults():
    req = RunRequest()
    assert req.input_type == "chat"
    assert req.output_type == "chat"
    assert req.stream is False


def test_run_response_empty():
    resp = RunResponse.model_validate({"outputs": []})
    assert resp.outputs == []


# ---------------------------------------------------------------------------
# Environment config tests
# ---------------------------------------------------------------------------


def test_load_environments(tmp_path: Path):
    config = tmp_path / "langflow-environments.toml"
    config.write_text(
        textwrap.dedent("""\
            [environments.staging]
            url = "https://staging.example.com"
            api_key_env = "TEST_KEY_STAGING"

            [environments.production]
            url = "https://prod.example.com"
            api_key = "literal-key"

            [defaults]
            environment = "staging"
        """),
        encoding="utf-8",
    )
    os.environ["TEST_KEY_STAGING"] = "sk-staging-123"

    from langflow_sdk.environments import get_environment, load_environments

    try:
        envs = load_environments(config)
        assert "staging" in envs
        assert envs["staging"].url == "https://staging.example.com"
        assert envs["staging"].api_key == "sk-staging-123"
        assert envs["production"].api_key == "literal-key"

        default_env = get_environment(config_file=config)
        assert default_env.name == "staging"
    finally:
        os.environ.pop("TEST_KEY_STAGING", None)


def test_environment_not_found(tmp_path: Path):
    config = tmp_path / "langflow-environments.toml"
    config.write_text("[environments.staging]\nurl = 'https://x.com'\n")

    from langflow_sdk.exceptions import EnvironmentNotFoundError
    from langflow_sdk.environments import get_environment

    with pytest.raises(EnvironmentNotFoundError, match="production"):
        get_environment("production", config_file=config)


def test_missing_url_raises(tmp_path: Path):
    config = tmp_path / "langflow-environments.toml"
    config.write_text("[environments.bad]\napi_key = 'sk-x'\n")

    from langflow_sdk.exceptions import EnvironmentConfigError
    from langflow_sdk.environments import load_environments

    with pytest.raises(EnvironmentConfigError, match="url"):
        load_environments(config)
