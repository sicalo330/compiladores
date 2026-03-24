from graphviz import Digraph
import uuid

def build_graphviz(node, dot=None, parent_id=None):
    if dot is None:
        dot = Digraph()

    #Si no esto mal esto hace una identificación unica para cada nodo, supongo que es para que no haya confusiones
    node_id = str(uuid.uuid4())
    #Extrael el nombre de la clase
    label = type(node).__name__

    dot.node(node_id, label)

    #Si un nodo fue llamado desde un padre entonces hace una flecha desde el padre hacie el nodo actual
    if parent_id:
        dot.edge(parent_id, node_id)

    #vars(node) toma todos los atributos que tiene el objeto
    for field, value in vars(node).items():
        #Esto recorre cada elemento, si el elemento es otro objeto (un nodo), vuelve a llamar a la función mediante
        #Recursividad
        if isinstance(value, list):
            for item in value:
                if hasattr(item, "__dict__"):
                    #Llamada recursiva para procesar el nodo hijo contenido en una lisat
                    build_graphviz(item, dot, node_id)
                else:
                    #Si el atributo es algo como value = 10 o op = +, crea una hoja y lo conecta.
                    leaf_id = str(uuid.uuid4())
                    dot.node(leaf_id, f"{field}: {item}")
                    dot.edge(node_id, leaf_id)
        #Algo similar con el else de antes, si es simple se crea una hoja
        elif hasattr(value, "__dict__"):
            build_graphviz(value, dot, node_id)
        #Esto para atributos simples como numeros, operadores o cadenas:
        elif value is not None:
            leaf_id = str(uuid.uuid4())
            dot.node(leaf_id, f"{field}: {value}")
            dot.edge(node_id, leaf_id)

    return dot