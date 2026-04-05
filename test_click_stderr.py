from typer import Typer
from typer.testing import CliRunner

app = Typer()


@app.command()
def error():
    from rich.console import Console

    Console(stderr=True).print("This is an error")
    print("This is stdout")


runner = CliRunner()
# mix_stderr=True is default
result = runner.invoke(app, [])
print(f"STDOUT: {repr(result.stdout)}")
print(f"STDERR: {repr(result.stderr)}")
print(f"OUTPUT: {repr(result.output)}")
