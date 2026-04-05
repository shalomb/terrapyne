from rich.console import Console

console = Console()
console.print("This should go to stdout")
console = Console(stderr=True)
console.print("This should go to stderr")
