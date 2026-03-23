from rich import print
from rich.tree import Tree


def build_tree(data, tree):
    if isinstance(data, dict):
        for key, value in data.items():
            subtree = tree.add(f"[bold green]{key}")
            build_tree(value, subtree)
    elif isinstance(data, list):
        for item in data:
            subtree = tree.add("")
            build_tree(item, subtree)
    else:
        tree.add(f"[bold cyan]{data}")


data = {
    "nombre": "Empresa",
    "departamentos": {
        "IT": {"empleados": ["Ana", "Luis"]},
        "Ventas": {"empleados": ["Carlos", "Marta"]},
    },
}

tree = Tree("sexy tree")
build_tree(data, tree)
print(tree)
