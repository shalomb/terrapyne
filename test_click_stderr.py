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
print(f"STDOUT: {result.stdout!r}")
print(f"STDERR: {result.stderr!r}")
print(f"OUTPUT: {result.output!r}")
