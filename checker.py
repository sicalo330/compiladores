# checker.py
from symtab import Symtab
from typesys import check_binop, check_unaryop
from multimethod import multimethod
from model import *

class Checker:
    def __init__(self):
            self.symtab = Symtab("global")
            self._func_stack = []  #Es necesario poner una lista para simular una pila de funciones, creo que será util para bad1
            self.error_set = set()
            self.errors = []
    
    @property
    def current_function(self):
        return self._func_stack[-1] if self._func_stack else None

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
        # ... lógica de registro ...
        ret_type = self.get_type(node.datatype.ret_type)
        self._func_stack.append(ret_type) # Guardamos el tipo de retorno esperado
        
        if node.body:
            for stmt in node.body:
                self.visit(stmt)
        
        self._func_stack.pop()
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
        if cond_type != "boolean" and cond_type != "error":
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
        actual_ret = self.visit(node.expr) if node.expr else "void"
        expected_ret = self.current_function
        
        if actual_ret != "error" and actual_ret != expected_ret:
            self.error(f"Tipo de retorno incorrecto en función: se esperaba {expected_ret}, se obtuvo {actual_ret}")

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
        left_type = self.visit(node.left)
        right_type = self.visit(node.right)

        if left_type == "error" or right_type == "error":
            return "error" # Silenciamos el error consecuente

        res = check_binop(left_type, node.op, right_type)
        if res is None:
            self.error(f"Operación inválida: {left_type} {node.op} {right_type}")
            return "error"
        return res

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
        if not symbol:
            self.error(f"'{node.name}' no es una función declarada")
            return "error"

        # Extraemos el tipo de la función
        func_type = symbol["type"]
        
        # IMPORTANTE: Validar que sea realmente una función
        if not isinstance(func_type, FuncType):
            self.error(f"'{node.name}' no es una función")
            return "error"

        params = func_type.params

        # 1. Validar cantidad de argumentos
        if len(params) != len(node.args):
            self.error(f"La función '{node.name}' esperaba {len(params)} argumentos, recibió {len(node.args)}")

        # 2. Validar tipos de argumentos (usando zip para no romper si las listas difieren)
        for i, (param, arg) in enumerate(zip(params, node.args)):
            arg_type = self.visit(arg)
            param_type = self.get_type(param.datatype)
            if arg_type != "error" and arg_type != param_type:
                self.error(f"Argumento {i+1} de '{node.name}' incorrecto: se esperaba {param_type}, se obtuvo {arg_type}")

        # 3. DEVOLVER EL TIPO DE RETORNO (Esto arregla el error de "integer % error")
        return self.get_type(func_type.ret_type)

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