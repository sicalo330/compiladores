from multimethod import multimethod
from model import Node

class Visitor:
    def visit(self, node):
        if node is None:
            return None

        # 🔥 ESTA LÍNEA ES LA CLAVE
        if not isinstance(node, Node):
            return "error"

        return self._visit(node)

    @multimethod
    def _visit(self, node: Node):
        return None