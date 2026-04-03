# checker.py
from symtab import Symtab
from typesys import check_binop, check_unaryop
from multimethod import multimethod
from model import *
from rich import print

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

    # def error(self, msg, node=None):
    #     if node:
    #         msg = f"Línea {node.lineno}: {msg}"
        
    #     if msg not in self.error_set:
    #         self.errors.append(msg)
    #         self.error_set.add(msg)

    # ==========================================
    # DISPATCH (USANDO MULTIMETHOD)
    # ==========================================
    # Este método redirige a las implementaciones específicas de abajo
    def visit(self, node):
        if node is None:
            return None

        # 🚨 NO dejar pasar valores crudos
        if not isinstance(node, Node):
            return "error"

        return self._visit(node)

    @multimethod
    def _visit(self, node: Node):
        """Caso base para nodos no implementados explícitamente"""
        return None

    @multimethod
    def _visit(self, node: Program):
        for decl in node.decls:
            if isinstance(decl, ExprStmt):
                self.error(f"Línea {decl.lineno}: No se permiten expresiones en el nivel superior",node)
            else:
                self.visit(decl)

    # ==========================================
    # DECLARATIONS
    # ==========================================
    @multimethod
    def _visit(self, node: VarDecl):
        target_type = self.get_type(node.datatype) 

        if node.name in self.symtab._map: 
            self.error(f"Variable '{node.name}' ya declarada en este ámbito",node)
            return

        self.symtab.add(node.name, {"kind": "var", "type": target_type})

        if node.value:
            value_type = self.visit(node.value)
            if target_type != value_type:
                self.error(f"Asignación incompatible en '{node.name}': Se esperaba un {target_type} y se obtuvo un {value_type}",node)
        node.type = target_type

    @multimethod
    def _visit(self, node: ArrayDecl):
        full_type = self.get_type(node.datatype)
        elem_type = self.get_type(node.datatype.elem_type)
        
        if node.name in self.symtab._map:
            self.error(f"Arreglo '{node.name}' ya declarado en este ámbito",node)
            return

        # array_type = f"array<{base_type}>"
        # self.symtab.add(node.name, {"kind": "array", "type": array_type})
        # node.type = array_type

        self.symtab.add(node.name, {"kind": "array", "type": full_type})

        if node.elements:
            for el in node.elements:
                actual_type = self.visit(el)
                if actual_type != elem_type:
                    self.error(f"Elemento inválido en array '{node.name}': se esperaba {elem_type}, se obtuvo {actual_type}",node)

    @multimethod
    def _visit(self, node: FuncDecl):
        self.symtab.add(node.name, {"type": node.datatype, "category": "function"})
        
        ret_type = self.get_type(node.datatype.ret_type)
        self._func_stack.append(ret_type)
        
        old_tab = self.symtab
        self.symtab = Symtab(node.name, parent=old_tab)
        
        for p in node.datatype.params:
            # Esto llamará a _visit(self, node: Param)
            self.visit(p) 
        
        if node.body:
            for stmt in node.body:
                self.visit(stmt)

        self.symtab = old_tab
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

        # 🚨 PROTECCIÓN: evitar valores crudos
        if not isinstance(cond_type, str):
            cond_type = "error"

        if cond_type != "boolean" and cond_type != "error":
            self.error(f"La condición del if debe ser boolean, se obtuvo {cond_type}",node)
        
        self.visit(node.then_b)
        if node.else_b:
            self.visit(node.else_b)

    @multimethod
    def _visit(self, node: WhileStmt):
        cond_type = self.visit(node.cond)
        if cond_type != "boolean":
            self.error(f"La condición del while debe ser boolean, se obtuvo {cond_type}",node)
        self.visit(node.body)

    @multimethod
    def _visit(self, node: ForStmt):
        if node.init: self.visit(node.init)
        if node.cond:
            cond_type = self.visit(node.cond)
            if cond_type != "boolean":
                self.error("Condición de for debe ser boolean",node)
        if node.step: self.visit(node.step)
        self.visit(node.body)

    @multimethod
    def _visit(self, node: ReturnStmt):
        actual_ret = self.visit(node.expr) if node.expr else "void"
        expected_ret = self.current_function
        
        if actual_ret != "error" and actual_ret != expected_ret:
            self.error(f"Tipo de retorno incorrecto en función: se esperaba {expected_ret}, se obtuvo {actual_ret}",node)

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
            self.error(f"Asignación incompatible: se esperaba {l_type}, se obtuvo {r_type}",node)
        node.type = l_type
        return l_type

    @multimethod
    def _visit(self, node: BinOp):
        left_type = self.visit(node.left)
        right_type = self.visit(node.right)

        if left_type == "error" or right_type == "error":
            return "error"

        # 🚨 Validación clave
        if not isinstance(left_type, str) or not isinstance(right_type, str):
            self.error(f"Operación inválida: {left_type} {node.op} {right_type}",node)
            return "error"

        res = check_binop(left_type, node.op, right_type)
        if res is None:
            self.error(f"Operación inválida: {left_type} {node.op} {right_type}",node)
            return "error"

        return res

    @multimethod
    def _visit(self, node: UnaryOp):
        operand = self.visit(node.expr)
        result = check_unaryop(node.op, operand)
        if result is None:
            self.error(f"Operador '{node.op}' no aplicable al tipo {operand}",node)
            result = "error"
        node.type = result
        return result

    @multimethod
    def _visit(self, node: Location):
        symbol = self.symtab.get(node.name)
        if symbol is None:
            self.error(f"Variable '{node.name}' no declarada", node)
            return "error"
        return symbol.get("type", "error")

    #Cambios aquí
    @multimethod
    def _visit(self, node: ArrayAccess):
        # 1. Buscamos el nombre del arreglo directamente en la symtab
        # ya que en tu model.py 'name' es un string, no un nodo Location
        symbol = self.symtab.get(node.name)
        if symbol is None:
            self.error(f"Arreglo '{node.name}' no declarado", node)
            return "error"
        
        base_type = symbol.get("type", "error")
        
        # 2. Validamos el índice (el índice sí es un nodo Expr, así que lo visitamos)
        idx_type = self.visit(node.index)
        if idx_type != "error" and idx_type != "integer":
            self.error(f"El índice del arreglo debe ser integer, se obtuvo {idx_type}", node)

        # 3. Devolvemos el tipo de los ELEMENTOS
        # Si es un ArraySizedType o ArrayType, extraemos el elem_type
        if isinstance(base_type, (ArrayType, ArraySizedType)):
            return self.get_type(base_type.elem_type)
        
        if base_type != "error":
            self.error(f"Se intentó indexar '{node.name}', que no es un arreglo", node)
        
        return "error"

    @multimethod
    def _visit(self, node: FuncCall):
        symbol = self.symtab.get(node.name)
        if not symbol:
            self.error(f"'{node.name}' no es una función declarada", node)
            return "error"

        # Extraemos el tipo de la función
        func_type = symbol.get("type")
        
        # 1. Validar que realmente sea una función
        if not isinstance(func_type, FuncType):
            self.error(f"'{node.name}' no es una función", node)
            return "error"

        params = func_type.params
        args = node.args

        # 2. Validar cantidad de argumentos
        if len(params) != len(args):
            self.error(f"La función '{node.name}' esperaba {len(params)} argumentos, recibió {len(args)}", node)

        # 3. Validar tipos de argumentos
        # Usamos zip para comparar uno a uno hasta donde alcancen los parámetros
        for i, (param, arg_expr) in enumerate(zip(params, args)):
            arg_type = self.visit(arg_expr)
            param_type = self.get_type(param.datatype)

            if arg_type == "error":
                continue

            # Lógica de compatibilidad de tipos
            compatible = False
            
            # Caso A: Tipos básicos idénticos (integer == integer, etc.)
            if arg_type == param_type:
                compatible = True
            
            # Caso B: Compatibilidad de Arreglos (ArraySizedType vs ArrayType)
            # Esto arregla el error de good7 donde pasas numbers (sized) a arr (unsized)
            elif isinstance(arg_type, (ArrayType, ArraySizedType)) and \
                    isinstance(param_type, (ArrayType, ArraySizedType)):
                
                # Obtenemos el tipo base de ambos (ej: 'integer')
                arg_elem = self.get_type(arg_type.elem_type)
                param_elem = self.get_type(param_type.elem_type)
                
                if arg_elem == param_elem:
                    compatible = True

            if not compatible:
                self.error(f"Argumento {i+1} de '{node.name}' incorrecto: se esperaba {param_type}, se obtuvo {arg_type}", arg_expr)

        # 4. Visitar argumentos extra si los hay (para detectar errores internos en ellos)
        if len(args) > len(params):
            for extra_arg in args[len(params):]:
                self.visit(extra_arg)

        # 5. Retornar el tipo de retorno de la función (esto permite encadenar expresiones)
        return self.get_type(func_type.ret_type)

    @multimethod
    def _visit(self, node: Param):
        t = self.get_type(node.datatype)
        self.symtab.add(node.name, {"type": t, "category": "variable"})
        return t

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
                    # Esto es clave: para comparaciones de tipos básicos, 
                    # a veces queremos saber el tipo base, pero para la 
                    # estructura de datos, queremos el objeto completo.
                    return datatype
        if isinstance(datatype, FuncType):
            return self.get_type(datatype.ret_type)

        return "void"


    def error(self, msg, node=None):
            # Si nos pasan un nodo, extraemos su línea para el mensaje
            if node and hasattr(node, 'lineno') and node.lineno > 0:
                msg = f"Línea {node.lineno}: {msg}"

            # Evitamos mensajes duplicados
            if msg not in self.error_set:
                self.errors.append(msg)
                self.error_set.add(msg)