from rich.tree import Tree

def ast_to_tree(node):
    if node is None:
        return Tree("[italic]None[/italic]")

    label = f"[bold cyan]{type(node).__name__}[/bold cyan]"

    attrs = []
    for attr, value in vars(node).items():
        if isinstance(value, (str, int, float, bool)):
            attrs.append(f"{attr}={value}")

    if attrs:
        label += " (" + ", ".join(attrs) + ")"

    tree = Tree(label)

    for attr, value in vars(node).items():

        if isinstance(value, list):
            branch = tree.add(f"[yellow]{attr}[][/yellow]")
            for item in value:
                branch.add(ast_to_tree(item))

        elif hasattr(value, "__dict__"):  # nodo AST
            branch = tree.add(f"[green]{attr}[/green]")
            branch.add(ast_to_tree(value))

    return tree