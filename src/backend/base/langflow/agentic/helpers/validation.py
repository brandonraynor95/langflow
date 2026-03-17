"""Component code validation."""

import ast
import re

from lfx.custom.validate import create_class, extract_class_name

from langflow.agentic.api.schemas import ValidationResult

# Regex pattern to extract class name that inherits from Component
CLASS_NAME_PATTERN = re.compile(r"class\s+(\w+)\s*\([^)]*Component[^)]*\)")


class _ReturnChecker(ast.NodeVisitor):
    """Check which methods have return statements with values."""

    def __init__(self):
        self.methods_with_return: set[str] = set()

    def visit_FunctionDef(self, node):
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value is not None:
                self.methods_with_return.add(node.name)
                break
        self.generic_visit(node)


def _extract_class_name_regex(code: str) -> str | None:
    """Extract class name using regex (fallback for syntax errors)."""
    match = CLASS_NAME_PATTERN.search(code)
    return match.group(1) if match else None


def _safe_extract_class_name(code: str) -> str | None:
    """Extract class name with fallback to regex for broken code."""
    try:
        return extract_class_name(code)
    except (ValueError, SyntaxError, TypeError):
        return _extract_class_name_regex(code)


def validate_component_code(code: str) -> ValidationResult:
    """Validate component code by attempting to create and instantiate the class.

    This instantiates the class to trigger __init__ validation checks,
    such as overlapping input/output names.
    """
    class_name = _safe_extract_class_name(code)

    try:
        if class_name is None:
            msg = "Could not extract class name from code"
            raise ValueError(msg)

        # create_class returns the class (not an instance)
        component_class = create_class(code, class_name)

        # Instantiate the class to trigger __init__ validation
        # This catches errors like overlapping input/output names
        instance = component_class()

        # Check that output methods have return statements with values
        if hasattr(instance, "outputs") and instance.outputs:
            try:
                tree = ast.parse(code)
                checker = _ReturnChecker()
                checker.visit(tree)
                for output in instance.outputs:
                    method_name = getattr(output, "method", None)
                    if method_name and method_name not in checker.methods_with_return:
                        return ValidationResult(
                            is_valid=False,
                            code=code,
                            error=f"Output method '{method_name}' does not have a return statement with a value",
                            class_name=class_name,
                        )
            except SyntaxError:
                pass  # AST parse failure already caught by create_class

        return ValidationResult(is_valid=True, code=code, class_name=class_name)
    except (
        ValueError,
        TypeError,
        SyntaxError,
        NameError,
        ModuleNotFoundError,
        AttributeError,
        ImportError,
        RuntimeError,
        KeyError,
    ) as e:
        return ValidationResult(is_valid=False, code=code, error=f"{type(e).__name__}: {e}", class_name=class_name)
