# checker.py
from symtab import Symtab
from typesys import check_binop, check_unaryop
from multimethod import multimethod
from model import *

class Checker:
    def __init__(self):
        self.symtab = Symtab("global")
        self.current_function = None
        self.error_set = set()
        self.errors = []

    # ==========================================
    # ENTRY POINT
    # ==========================================
    def check(self, node):
        self.visit(node)
        if self.errors:
            print("\n[red]Errores semánticos encontrados:[/red]")
            for e in self.errors:
                print(f" - {e}")
            print("\n[red]Semantic check: FAILED[/red]")
        else:
            print("\n[green]Semantic check: SUCCESS[/green]")

    def error(self, msg):
        if msg not in self.error_set:
            self.errors.append(msg)
            self.error_set.add(msg)

    # ==========================================
    # DISPATCH (USANDO MULTIMETHOD)
    # ==========================================
    # Este método redirige a las implementaciones específicas de abajo
    def visit(self, node):
        if node is None: return None
        return self._visit(node)

    @multimethod
    def _visit(self, node: Node):
        """Caso base para nodos no implementados explícitamente"""
        return None

    @multimethod
    def _visit(self, node: Program):
        for decl in node.decls:
            self.visit(decl)

    # ==========================================
    # DECLARATIONS
    # ==========================================
    @multimethod
    def _visit(self, node: VarDecl):
        target_type = self.get_type(node.datatype) 

        if node.name in self.symtab._map: 
            self.error(f"Variable '{node.name}' ya declarada en este ámbito")
            return

        self.symtab.add(node.name, {"kind": "var", "type": target_type})

        if node.value:
            value_type = self.visit(node.value)
            if target_type != value_type:
                self.error(f"Asignación incompatible en '{node.name}': Se esperaba un {target_type} y se obtuvo un {value_type}")
        node.type = target_type

    @multimethod
    def _visit(self, node: ArrayDecl):
        base_type = self.get_type(node.datatype) 
        
        if node.name in self.symtab._map:
            self.error(f"Arreglo '{node.name}' ya declarado en este ámbito")
            return

        self.symtab.add(node.name, {"kind": "array", "type": base_type})

        if node.elements:
            for el in node.elements:
                actual_type = self.visit(el) 
                if actual_type != base_type:
                    self.error(f"Elemento inválido en array '{node.name}': se esperaba {base_type}, se obtuvo {actual_type}")
        node.type = base_type

    @multimethod
    def _visit(self, node: FuncDecl):
        if node.name in self.symtab._map:
            self.error(f"Función '{node.name}' ya declarada")

        func_ret_type = self.get_type(node.datatype)
        self.symtab.add(node.name, {
            "kind": "func",
            "type": func_ret_type,
            "params": node.datatype.params if hasattr(node.datatype, "params") else []
        })

        # Nuevo scope para parámetros y cuerpo
        old_symtab = self.symtab
        self.symtab = Symtab(f"func_{node.name}", parent=old_symtab)
        self.current_function = node

        if hasattr(node.datatype, "params"):
            for param in node.datatype.params:
                ptype = self.get_type(param.datatype)
                self.symtab.add(param.name, {"kind": "param", "type": ptype})

        if node.body:
            for stmt in node.body:
                self.visit(stmt)

        self.symtab = old_symtab
        self.current_function = None

    # ==========================================
    # STATEMENTS
    # ==========================================
    @multimethod
    def _visit(self, node: BlockStmt):
        old = self.symtab
        self.symtab = Symtab("block", parent=old)
        for stmt in node.stmts:
            self.visit(stmt)
        self.symtab = old

    @multimethod
    def _visit(self, node: IfStmt):
        cond_type = self.visit(node.cond)
        if cond_type != "boolean":
            self.error(f"La condición del if debe ser boolean, se obtuvo {cond_type}")
        self.visit(node.then_b)
        if node.else_b:
            self.visit(node.else_b)

    @multimethod
    def _visit(self, node: WhileStmt):
        cond_type = self.visit(node.cond)
        if cond_type != "boolean":
            self.error(f"La condición del while debe ser boolean, se obtuvo {cond_type}")
        self.visit(node.body)

    @multimethod
    def _visit(self, node: ForStmt):
        if node.init: self.visit(node.init)
        if node.cond:
            cond_type = self.visit(node.cond)
            if cond_type != "boolean":
                self.error("Condición de for debe ser boolean")
        if node.step: self.visit(node.step)
        self.visit(node.body)

    @multimethod
    def _visit(self, node: ReturnStmt):
        if not self.current_function:
            self.error("Sentencia 'return' fuera de una función")
            return

        expected = self.get_type(self.current_function.datatype.ret_type)
        if node.expr:
            actual = self.visit(node.expr)
            if actual != expected:
                self.error(f"Tipo de retorno incorrecto en '{self.current_function.name}': se esperaba {expected}, se obtuvo {actual}")
        elif expected != "void":
            self.error(f"La función '{self.current_function.name}' debe retornar un valor de tipo {expected}")

    @multimethod
    def _visit(self, node: PrintStmt):
        for expr in node.exprs:
            self.visit(expr)

    @multimethod
    def _visit(self, node: ExprStmt):
        self.visit(node.expr)

    # ==========================================
    # EXPRESSIONS
    # ==========================================
    @multimethod
    def _visit(self, node: AssignExpr):
        l_type = self.visit(node.lval)
        r_type = self.visit(node.expr)
        if l_type and r_type and l_type != r_type:
            self.error(f"Asignación incompatible: se esperaba {l_type}, se obtuvo {r_type}")
        node.type = l_type
        return l_type

    @multimethod
    def _visit(self, node: BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        # Nota: El orden en check_binop suele ser (op, left, right) o (left, op, right)
        # Ajustado al estándar de tu typesys.py:
        result = check_binop(left, node.op, right)
        if result is None:
            self.error(f"Operación inválida: {left} {node.op} {right}")
            result = "error"
        node.type = result
        return result

    @multimethod
    def _visit(self, node: UnaryOp):
        operand = self.visit(node.expr)
        result = check_unaryop(node.op, operand)
        if result is None:
            self.error(f"Operador '{node.op}' no aplicable al tipo {operand}")
            result = "error"
        node.type = result
        return result

    @multimethod
    def _visit(self, node: Location):
        symbol = self.symtab.get(node.name)
        if symbol is None:
            self.error(f"Variable '{node.name}' no declarada")
            return "error"
        return symbol["type"]

    @multimethod
    def _visit(self, node: ArrayAccess):
        symbol = self.symtab.get(node.name)
        if symbol is None:
            self.error(f"Arreglo '{node.name}' no declarado")
            return "error"
        
        idx_type = self.visit(node.index)
        if idx_type != "integer":
            self.error(f"El índice del arreglo debe ser integer, se obtuvo {idx_type}")
        
        return symbol["type"]

    @multimethod
    def _visit(self, node: FuncCall):
        symbol = self.symtab.get(node.name)
        if not symbol or symbol["kind"] != "func":
            self.error(f"'{node.name}' no es una función declarada")
            return "error"

        params = symbol.get("params", [])
        if len(params) != len(node.args):
            self.error(f"La función '{node.name}' esperaba {len(params)} argumentos, recibió {len(node.args)}")

        for i, (param, arg) in enumerate(zip(params, node.args)):
            arg_type = self.visit(arg)
            param_type = self.get_type(param.datatype)
            if arg_type != param_type:
                self.error(f"Argumento {i+1} de '{node.name}' incorrecto: se esperaba {param_type}, se obtuvo {arg_type}")

        return symbol["type"]

    @multimethod
    def _visit(self, node: Literal):
        # Anotamos el nodo con el tipo normalizado
        node.type = self.normalize_type(node.type_name)
        return node.type

    # ==========================================
    # HELPERS
    # ==========================================
    def normalize_type(self, t):
        # Sincronizado con typesys.py: usamos nombres completos
        mapping = {
            "int": "integer",
            "bool": "boolean",
            "float": "float",
            "char": "char",
            "string": "string"
        }
        return mapping.get(t, t)

    def get_type(self, datatype):
        if isinstance(datatype, SimpleType):
            return self.normalize_type(datatype.name)
        if isinstance(datatype, (ArrayType, ArraySizedType)):
            return self.get_type(datatype.elem_type)
        if isinstance(datatype, FuncType):
            return self.get_type(datatype.ret_type)
        return "void"