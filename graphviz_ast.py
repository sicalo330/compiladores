from graphviz import Digraph
import uuid

def build_graphviz(node, dot=None, parent_id=None):
    if dot is None:
        dot = Digraph()

    node_id = str(uuid.uuid4())

    label = type(node).__name__

    dot.node(node_id, label)

    if parent_id:
        dot.edge(parent_id, node_id)

    for field, value in vars(node).items():
        if isinstance(value, list):
            for item in value:
                if hasattr(item, "__dict__"):
                    build_graphviz(item, dot, node_id)
                else:
                    leaf_id = str(uuid.uuid4())
                    dot.node(leaf_id, f"{field}: {item}")
                    dot.edge(node_id, leaf_id)

        elif hasattr(value, "__dict__"):
            build_graphviz(value, dot, node_id)

        elif value is not None:
            leaf_id = str(uuid.uuid4())
            dot.node(leaf_id, f"{field}: {value}")
            dot.edge(node_id, leaf_id)

    return dot