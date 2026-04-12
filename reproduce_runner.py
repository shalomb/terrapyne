import typer
from typer.testing import CliRunner

app = typer.Typer()


@app.command()
def hello():
    print("hello")


runner = CliRunner()
result = runner.invoke(app, ["hello"])
print(f"Exit code: {result.exit_code}")
print(f"Exception: {result.exception}")
print(f"Output: {result.stdout}")
