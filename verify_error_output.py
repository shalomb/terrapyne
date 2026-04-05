from typer.testing import CliRunner

from terrapyne.cli.main import app

runner = CliRunner()
# Use a non-existent output with --raw to trigger error
result = runner.invoke(
    app, ["state", "outputs", "missing", "-w", "test-ws", "-o", "test-org", "--raw"]
)
print(f"EXIT CODE: {result.exit_code}")
print(f"STDOUT: {result.stdout}")
# If CliRunner is used, stdout and stderr are mixed by default.
# But we can try to separate them if we use separate runners.
