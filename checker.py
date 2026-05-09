# checker.py
from symtab import Symtab
from typesys import check_binop, check_unaryop
from multimethod import multimethod
from model import *
from rich import print
from visitor import Visitor
import errors

class Checker(Visitor):
    def __init__(self):
            self.symtab = Symtab("global")
            self._func_stack = []  #Es necesario poner una lista para simular una pila de funciones, creo que será util para bad1
            self.error_set = set()
    
    @property
    def current_function(self):
        return self._func_stack[-1] if self._func_stack else None
    
    # ==========================================
    # SISTEMA DE ERRORES UNIFICADO
    # ==========================================
    def error(self, msg, node=None):
        # Evitamos reportar el mismo error varias veces si el nodo es el mismo
        error_key = (msg, node.lineno if node else None)
        if error_key not in self.error_set:
            errors.error(msg, lineno=node.lineno if node else None, stage="CHECKER")
            self.error_set.add(error_key)

    # ==========================================
    # ENTRY POINT
    # ==========================================
    def check(self, node):
        self.visit(node)
        # if self.errors:
        #     print("\n[red]Errores semánticos encontrados:[/red]")
        #     for e in self.errors:
        #         print(f" - {e}")
        #     print("\n[red]Semantic check: FAILED[/red]")
        # else:
        #     print("\n[green]Semantic check: SUCCESS[/green]")

    # def error(self, msg, n    ode=None):
    #     if node:
    #         msg = f"Línea {node.lineno}: {msg}"
        
    #     if msg not in self.error_set:
    #         self.errors.append(msg)
    #         self.error_set.add(msg)

    # ==========================================
    # DISPATCH (USANDO MULTIMETHOD)
    # ==========================================

    @multimethod
    def _visit(self, node: Node):
        return None

    @multimethod
    def _visit(self, node: Program):
        for decl in node.decls:
            if isinstance(decl, ExprStmt):
                self.error("No se permiten expresiones en el nivel superior", decl)
            else:
                self.visit(decl)

    # ==========================================
    # DECLARATIONS
    # ==========================================
    @multimethod
    def _visit(self, node: VarDecl):
        target_type = self.get_type(node.datatype) 

        if node.name in self.symtab._map: 
            self.error(f"Variable '{node.name}' ya declarada en este ámbito", node)
            return "error"

        self.symtab.add(node.name, {"kind": "var", "type": target_type})

        if node.value:
            value_type = self.visit(node.value)
            if value_type != "error" and target_type != value_type:
                #Esta linea de aquí está horriblemente larga
                self.error(f"Asignación incompatible en '{node.name}':"
                f"Se esperaba {self.type_to_string(target_type)} y se obtuvo {self.type_to_string(value_type)}", node)
        node.type = target_type
        return target_type

    @multimethod
    def _visit(self, node: ArrayDecl):
        full_type = self.get_type(node.datatype)
        # Extraer el tipo de los elementos para validar la lista de inicialización
        elem_type = self.get_type(node.datatype.elem_type)
        
        if node.name in self.symtab._map:
            self.error(f"Arreglo '{node.name}' ya declarado en este ámbito", node)
            return "error"

        self.symtab.add(node.name, {"kind": "array", "type": full_type})

        if node.elements:
            for el in node.elements:
                actual_type = self.visit(el)
                if actual_type != "error" and actual_type != elem_type:
                    self.error(f"Elemento inválido en array '{node.name}': "
                    f"se esperaba {self.type_to_string(elem_type)}, se obtuvo {self.type_to_string(actual_type)}", el)
        return full_type

    @multimethod
    def _visit(self, node: FuncDecl):
        self.symtab.add(node.name, {"type": node.datatype, "category": "function"})
                
        ret_type = self.get_type(node.datatype.ret_type)
        self._func_stack.append(ret_type)
        
        old_tab = self.symtab
        self.symtab = Symtab(node.name, parent=old_tab)
        
        for p in node.datatype.params:
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
        if cond_type != "boolean" and cond_type != "error":
            self.error(f"La condición del if debe ser boolean, se obtuvo {self.type_to_string(cond_type)}", node.cond)
        
        self.visit(node.then_b)
        if node.else_b:
            self.visit(node.else_b)

    @multimethod
    def _visit(self, node: WhileStmt):
        cond_type = self.visit(node.cond)
        if cond_type != "boolean" and cond_type != "error":
            self.error(f"La condición del while debe ser boolean, se obtuvo {self.type_to_string(cond_type)}", node.cond)
        self.visit(node.body)

    @multimethod
    def _visit(self, node: ForStmt):
        if node.init: self.visit(node.init)
        if node.cond:
            cond_type = self.visit(node.cond)
            if cond_type != "boolean" and cond_type != "error":
                self.error(f"Condición de for debe ser boolean, se obtuvo {self.type_to_string(cond_type)}", node.cond)
        if node.step: self.visit(node.step)
        self.visit(node.body)

    @multimethod
    def _visit(self, node: ReturnStmt):
        actual_ret = self.visit(node.expr) if node.expr else "void"
        expected_ret = self.current_function
        
        if actual_ret != "error" and actual_ret != expected_ret:
            self.error(f"Tipo de retorno incorrecto: se esperaba {self.type_to_string(expected_ret)}, "
                       f"se obtuvo {self.type_to_string(actual_ret)}", node)

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
        if l_type != "error" and r_type != "error" and l_type != r_type:
            self.error(f"Asignación incompatible: se esperaba {self.type_to_string(l_type)}, "
                       f"se obtuvo {self.type_to_string(r_type)}", node)
        node.type = l_type
        return l_type

    @multimethod
    def _visit(self, node: BinOp):
        left_type = self.visit(node.left)
        right_type = self.visit(node.right)

        if left_type == "error" or right_type == "error":
            return "error"

        if node.op in {"/", "%"} and isinstance(node.right, Literal) and node.right.value == 0:
            self.error("División por cero detectada", node.right)
            return "error"

        res = check_binop(left_type, node.op, right_type)
        if res is None:
            self.error(f"Operación inválida: {self.type_to_string(left_type)} {node.op} {self.type_to_string(right_type)}", node)
            return "error"
        return res

    @multimethod
    def _visit(self, node: UnaryOp):
        operand = self.visit(node.expr)
        result = check_unaryop(node.op, operand)
        if result is None:
            self.error(f"Operador '{node.op}' no aplicable al tipo {self.type_to_string(operand)}",node)
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

    @multimethod
    def _visit(self, node: ArrayAccess):
        symbol = self.symtab.get(node.name)
        if symbol is None:
            self.error(f"Arreglo '{node.name}' no declarado", node)
            return "error"
        
        base_type = symbol.get("type", "error")
        
        indices = node.index_list if isinstance(node.index_list, list) else [node.index_list]
        for index in indices:
            idx_type = self.visit(index)
            if idx_type != "error" and idx_type != "integer":
                self.error(f"El índice del arreglo debe ser integer, se obtuvo {idx_type}", node)

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

        func_type = symbol.get("type")
        
        if not isinstance(func_type, FuncType):
            self.error(f"'{node.name}' no es una función", node)
            return "error"

        params = func_type.params
        args = node.args

        if len(params) != len(args):
            self.error(f"La función '{node.name}' esperaba {len(params)} argumentos, recibió {len(args)}", node)

        for i, (param, arg_expr) in enumerate(zip(params, args)):
            arg_type = self.visit(arg_expr)
            param_type = self.get_type(param.datatype)

            if arg_type == "error":
                continue

            compatible = False

            if arg_type == param_type:
                compatible = True
            
            elif isinstance(arg_type, (ArrayType, ArraySizedType)) and \
                    isinstance(param_type, (ArrayType, ArraySizedType)):
                
                arg_elem = self.get_type(arg_type.elem_type)
                param_elem = self.get_type(param_type.elem_type)
                
                if arg_elem == param_elem:
                    compatible = True

            if not compatible:
                self.error(f"Argumento {i+1} de '{node.name}' incorrecto: se esperaba {self.type_to_string(param_type)}, se obtuvo {self.type_to_string(arg_type)}", arg_expr)

        if len(args) > len(params):
            for extra_arg in args[len(params):]:
                self.visit(extra_arg)

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

    def type_to_string(self, t):
        if isinstance(t, str):
            return t
        if isinstance(t, SimpleType):
            return self.normalize_type(t.name)
        if isinstance(t, ArrayType):
            return f"array<{self.type_to_string(t.elem_type)}>"
        if isinstance(t, ArraySizedType):
            return f"array<{self.type_to_string(t.elem_type)}>"
        if isinstance(t, FuncType):
            params_str = ", ".join(self.type_to_string(p.datatype) for p in t.params)
            return f"function {self.type_to_string(t.ret_type)} ({params_str})"
        return str(t)

        return "void"

    def get_type(self, datatype):
        if isinstance(datatype, SimpleType):
            return self.normalize_type(datatype.name)

        if isinstance(datatype, ArrayType):
            return ArrayType(
                self.get_type(datatype.elem_type)
            )

        if isinstance(datatype, ArraySizedType):
            return ArraySizedType(
                datatype.size,
                self.get_type(datatype.elem_type)
            )

        if isinstance(datatype, FuncType):
            return FuncType(
                datatype.params,
                self.get_type(datatype.ret_type)
            )

        return datatype