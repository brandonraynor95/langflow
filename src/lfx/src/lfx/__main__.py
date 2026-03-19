"""LFX CLI entry point."""

import typer

app = typer.Typer(
    name="lfx",
    help="lfx - Langflow Executor",
    add_completion=False,
)


@app.command(name="serve", help="Serve a flow as an API", no_args_is_help=True)
def serve_command_wrapper(
    script_path: str | None = typer.Argument(
        None,
        help=(
            "Path to JSON flow (.json) or Python script (.py) file or stdin input. "
            "Optional when using --flow-json or --stdin."
        ),
    ),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind the server to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind the server to"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show diagnostic output and execution details"),
    env_file: str | None = typer.Option(
        None,
        "--env-file",
        help="Path to the .env file containing environment variables",
    ),
    log_level: str = typer.Option(
        "warning",
        "--log-level",
        help="Logging level. One of: debug, info, warning, error, critical",
    ),
    flow_json: str | None = typer.Option(
        None,
        "--flow-json",
        help="Inline JSON flow content as a string (alternative to script_path)",
    ),
    *,
    stdin: bool = typer.Option(
        False,
        "--stdin",
        help="Read JSON flow content from stdin (alternative to script_path)",
    ),
    check_variables: bool = typer.Option(
        True,
        "--check-variables/--no-check-variables",
        help="Check global variables for environment compatibility",
    ),
) -> None:
    """Serve LFX flows as a web API (lazy-loaded)."""
    from pathlib import Path

    from lfx.cli.commands import serve_command

    # Convert env_file string to Path if provided
    env_file_path = Path(env_file) if env_file else None

    return serve_command(
        script_path=script_path,
        host=host,
        port=port,
        verbose=verbose,
        env_file=env_file_path,
        log_level=log_level,
        flow_json=flow_json,
        stdin=stdin,
        check_variables=check_variables,
    )


@app.command(name="run", help="Run a flow directly", no_args_is_help=True)
def run_command_wrapper(
    script_path: str | None = typer.Argument(
        None, help="Path to the Python script (.py) or JSON flow (.json) containing a graph"
    ),
    input_value: str | None = typer.Argument(None, help="Input value to pass to the graph"),
    input_value_option: str | None = typer.Option(
        None,
        "--input-value",
        help="Input value to pass to the graph (alternative to positional argument)",
    ),
    output_format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json, text, message, or result",
    ),
    flow_json: str | None = typer.Option(
        None,
        "--flow-json",
        help="Inline JSON flow content as a string (alternative to script_path)",
    ),
    *,
    stdin: bool = typer.Option(
        default=False,
        show_default=True,
        help="Read JSON flow content from stdin (alternative to script_path)",
    ),
    check_variables: bool = typer.Option(
        default=True,
        show_default=True,
        help="Check global variables for environment compatibility",
    ),
    verbose: bool = typer.Option(
        False,
        "-v",
        "--verbose",
        help="Show basic progress information",
    ),
    verbose_detailed: bool = typer.Option(
        False,
        "-vv",
        help="Show detailed progress and debug information",
    ),
    verbose_full: bool = typer.Option(
        False,
        "-vvv",
        help="Show full debugging output including component logs",
    ),
    timing: bool = typer.Option(
        default=False,
        show_default=True,
        help="Include detailed timing information in output",
    ),
) -> None:
    """Run a flow directly (lazy-loaded)."""
    from pathlib import Path

    from lfx.cli.run import run

    # Convert script_path string to Path if provided
    script_path_obj = Path(script_path) if script_path else None

    return run(
        script_path=script_path_obj,
        input_value=input_value,
        input_value_option=input_value_option,
        output_format=output_format,
        flow_json=flow_json,
        stdin=stdin,
        check_variables=check_variables,
        verbose=verbose,
        verbose_detailed=verbose_detailed,
        verbose_full=verbose_full,
        timing=timing,
    )


@app.command(name="requirements", help="Generate requirements.txt for a flow", no_args_is_help=True)
def requirements_command_wrapper(
    flow_path: str = typer.Argument(help="Path to the Langflow flow JSON file"),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: stdout)",
    ),
    lfx_package: str = typer.Option(
        "lfx",
        "--lfx-package",
        help="Name of the LFX package (default: lfx)",
    ),
    *,
    no_lfx: bool = typer.Option(
        False,
        "--no-lfx",
        help="Exclude the LFX package from output",
    ),
    no_pin: bool = typer.Option(
        False,
        "--no-pin",
        help="Do not pin package versions (default: pin to currently installed versions)",
    ),
) -> None:
    """Generate requirements.txt from a Langflow flow JSON (lazy-loaded)."""
    import json
    from pathlib import Path

    from lfx.utils.flow_requirements import generate_requirements_txt

    path = Path(flow_path)
    if not path.is_file():
        typer.echo(f"Error: File not found: {path}", err=True)
        raise typer.Exit(1)

    try:
        flow = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        typer.echo(f"Error: Could not read flow JSON: {e}", err=True)
        raise typer.Exit(1) from e

    content = generate_requirements_txt(
        flow,
        lfx_package=lfx_package,
        include_lfx=not no_lfx,
        pin_versions=not no_pin,
    )

    if output:
        try:
            Path(output).write_text(content, encoding="utf-8")
        except OSError as e:
            typer.echo(f"Error: Could not write to {output}: {e}", err=True)
            raise typer.Exit(1) from e
        typer.echo(f"Requirements written to {output}")
    else:
        typer.echo(content, nl=False)


@app.command(name="init", help="Scaffold a new Flow DevOps project")
def init_command_wrapper(
    project_dir: str = typer.Argument(
        ".",
        help="Directory to scaffold (created if it does not exist; default: current directory).",
    ),
    github_actions: bool = typer.Option(
        True,
        "--github-actions/--no-github-actions",
        help="Copy GitHub Actions workflow templates into .github/workflows/.",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Write files even if the target directory already contains files.",
    ),
) -> None:
    """Scaffold a Flow DevOps project: flows/, tests/, environments config, and CI templates."""
    from pathlib import Path

    from lfx.cli.init import init_command

    init_command(project_dir=Path(project_dir), github_actions=github_actions, overwrite=overwrite)


@app.command(name="status", help="Compare local flow files against a remote Langflow instance")
def status_command_wrapper(
    flow_paths: list[str] = typer.Argument(
        default=None,
        help="Specific flow JSON file(s) to check. Omit to scan --dir (default: flows/).",
    ),
    env: str | None = typer.Option(
        None,
        "--env",
        "-e",
        help="Environment name from langflow-environments.toml. Uses [defaults] if omitted.",
    ),
    dir_path: str | None = typer.Option(
        None,
        "--dir",
        "-d",
        help="Directory of flow JSON files to compare (default: flows/ in cwd).",
    ),
    environments_file: str | None = typer.Option(
        None,
        "--environments-file",
        help="Path to langflow-environments.toml (overrides default lookup).",
    ),
    show_remote_only: bool = typer.Option(
        False,
        "--remote-only",
        help="Also list flows that exist on the server but have no local file.",
    ),
) -> None:
    """Show whether local flow files are in sync, ahead, or missing vs the remote instance."""
    from lfx.cli.status import status_command

    status_command(
        dir_path=dir_path,
        flow_paths=flow_paths or [],
        env=env,
        environments_file=environments_file,
        show_remote_only=show_remote_only,
    )


@app.command(name="export", help="Normalize flow JSON for git (local) or pull from a remote instance")
def export_command_wrapper(
    flow_paths: list[str] = typer.Argument(
        default=None,
        help="Path(s) to local flow JSON file(s) to normalize. Omit when using --flow-id or --project-id.",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (single-file local mode only).",
    ),
    output_dir: str | None = typer.Option(
        None,
        "--output-dir",
        "-d",
        help="Directory to write exported flows into (remote mode or multi-file).",
    ),
    env: str | None = typer.Option(
        None,
        "--env",
        "-e",
        help="Environment name from langflow-environments.toml (required for remote mode).",
    ),
    flow_id: str | None = typer.Option(
        None,
        "--flow-id",
        help="Pull and export a single flow by UUID from the remote instance.",
    ),
    project_id: str | None = typer.Option(
        None,
        "--project-id",
        help="Pull and export all flows in a project by UUID from the remote instance.",
    ),
    environments_file: str | None = typer.Option(
        None,
        "--environments-file",
        help="Path to langflow-environments.toml (overrides default lookup).",
    ),
    in_place: bool = typer.Option(
        False,
        "--in-place",
        "-i",
        help="Overwrite each input file with its normalized version.",
    ),
    strip_volatile: bool = typer.Option(
        True,
        "--strip-volatile/--keep-volatile",
        help="Strip instance-specific fields (updated_at, user_id, folder_id).",
    ),
    strip_secrets: bool = typer.Option(
        True,
        "--strip-secrets/--keep-secrets",
        help="Clear values of password/load_from_db template fields.",
    ),
    code_as_lines: bool = typer.Option(
        False,
        "--code-as-lines",
        help="Convert code-type template field values to a list of lines.",
    ),
    strip_node_volatile: bool = typer.Option(
        True,
        "--strip-node-volatile/--keep-node-volatile",
        help="Strip transient node keys (positionAbsolute, dragging, selected).",
    ),
    indent: int = typer.Option(
        2,
        "--indent",
        help="JSON indentation level.",
    ),
) -> None:
    """Export and normalize Langflow flow JSON for version control (lazy-loaded)."""
    from lfx.cli.export import export_command

    export_command(
        flow_paths=flow_paths or [],
        output=output,
        output_dir=output_dir,
        env=env,
        flow_id=flow_id,
        project_id=project_id,
        environments_file=environments_file,
        in_place=in_place,
        strip_volatile=strip_volatile,
        strip_secrets=strip_secrets,
        code_as_lines=code_as_lines,
        strip_node_volatile=strip_node_volatile,
        indent=indent,
    )


@app.command(name="push", help="Push flow JSON to a remote Langflow instance (upsert by stable ID)")
def push_command_wrapper(
    flow_paths: list[str] = typer.Argument(
        default=None,
        help="Path(s) to flow JSON file(s) to push. Use --dir for a whole directory.",
    ),
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Environment name from langflow-environments.toml.",
    ),
    dir_path: str | None = typer.Option(
        None,
        "--dir",
        "-d",
        help="Directory of flow JSON files to push (pushes all *.json files).",
    ),
    project: str | None = typer.Option(
        None,
        "--project",
        "-p",
        help="Target project name on the remote instance. Created if it does not exist.",
    ),
    project_id: str | None = typer.Option(
        None,
        "--project-id",
        help="Target project UUID (alternative to --project).",
    ),
    environments_file: str | None = typer.Option(
        None,
        "--environments-file",
        help="Path to langflow-environments.toml (overrides default lookup).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be pushed without making any changes.",
    ),
    normalize: bool = typer.Option(
        True,
        "--normalize/--no-normalize",
        help="Normalize (strip volatile fields, sort keys) before pushing.",
    ),
    strip_secrets: bool = typer.Option(
        True,
        "--strip-secrets/--keep-secrets",
        help="Clear password/load_from_db field values before pushing.",
    ),
) -> None:
    """Push Langflow flows to a remote instance using stable IDs for upsert (lazy-loaded)."""
    from lfx.cli.push import push_command

    push_command(
        flow_paths=flow_paths or [],
        env=env,
        dir_path=dir_path,
        project=project,
        project_id=project_id,
        environments_file=environments_file,
        dry_run=dry_run,
        normalize=normalize,
        strip_secrets=strip_secrets,
    )


@app.command(name="validate", help="Validate one or more flow JSON files", no_args_is_help=True)
def validate_command_wrapper(
    flow_paths: list[str] = typer.Argument(
        help="Path(s) to Langflow flow JSON file(s) to validate",
    ),
    level: int = typer.Option(
        4,
        "--level",
        "-l",
        min=1,
        max=4,
        help=(
            "Validation depth: "
            "1=structural JSON, "
            "2=+component existence, "
            "3=+edge type compatibility, "
            "4=+required inputs connected"
        ),
    ),
    skip_components: bool = typer.Option(
        False,
        "--skip-components",
        help="Skip component existence checks (level 2)",
    ),
    skip_edge_types: bool = typer.Option(
        False,
        "--skip-edge-types",
        help="Skip edge type compatibility checks (level 3)",
    ),
    skip_required_inputs: bool = typer.Option(
        False,
        "--skip-required-inputs",
        help="Skip required-inputs checks (level 4)",
    ),
    skip_version_check: bool = typer.Option(
        False,
        "--skip-version-check",
        help="Skip version-mismatch / outdated-component warnings",
    ),
    skip_credentials: bool = typer.Option(
        False,
        "--skip-credentials",
        help="Skip missing-credentials warnings for password/secret fields",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Treat warnings as errors (exit 1 if any warnings are found)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Print all issues including warnings for passing flows",
    ),
    output_format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format: text (default) or json",
    ),
) -> None:
    """Validate Langflow flow JSON files without executing them (lazy-loaded)."""
    from lfx.cli.validate import validate_command

    validate_command(
        flow_paths=flow_paths,
        level=level,
        skip_components=skip_components,
        skip_edge_types=skip_edge_types,
        skip_required_inputs=skip_required_inputs,
        skip_version_check=skip_version_check,
        skip_credentials=skip_credentials,
        strict=strict,
        verbose=verbose,
        output_format=output_format,
    )


def main():
    """Main entry point for the LFX CLI."""
    app()


if __name__ == "__main__":
    main()
