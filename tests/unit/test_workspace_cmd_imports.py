"""Test that workspace_cmd uses module-level imports (no function-body imports for non-circular cases)."""

import ast
import inspect


def test_runstatus_is_module_level_import():
    """RunStatus must be imported at module level in workspace_cmd, not inside a function body."""
    from terrapyne.cli import workspace_cmd

    source = inspect.getsource(workspace_cmd)
    tree = ast.parse(source)

    # Collect all import names at module level
    module_level_imports = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    module_level_imports.add(alias.asname or alias.name)
            else:
                for alias in node.names:
                    module_level_imports.add(alias.asname or alias.name)

    assert "RunStatus" in module_level_imports, (
        "RunStatus must be imported at module level in workspace_cmd.py, not inside a function body"
    )


def test_no_runstatus_function_body_import():
    """No function in workspace_cmd should import RunStatus inside its body."""
    from terrapyne.cli import workspace_cmd

    source = inspect.getsource(workspace_cmd)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                if isinstance(child, ast.ImportFrom):
                    for alias in child.names:
                        name = alias.asname or alias.name
                        assert name != "RunStatus", (
                            f"RunStatus imported inside function '{node.name}' — "
                            "move it to module level"
                        )
