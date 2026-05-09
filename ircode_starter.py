from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from model import *
from visitor import Visitor

Instruction = tuple

#Guardar información de variables
@dataclass
class Storage:
    name: str
    ty: Type
    is_global: bool = False
    is_param: bool = False
    is_const: bool = False

#Representación de una funcióin
@dataclass
class IRFunction:
    name: str
    params: list[tuple[str, Type]]
    return_type: Type
    instructions: list[Instruction] = field(default_factory=list)


@dataclass
class IRProgram:
    globals: list[Instruction] = field(default_factory=list)
    functions: list[IRFunction] = field(default_factory=list)

    def format(self) -> str:
        out = []

        if self.globals:
            out.append("# Globals")
            for inst in self.globals:
                out.append(str(inst))
            out.append("")

        for fn in self.functions:
            out.append(f"function {fn.name}")
            for inst in fn.instructions:
                out.append(f"  {inst}")
            out.append("")

        return "\n".join(out)


class IRCodeGen(Visitor):

    def __init__(self):
        self.program = IRProgram()
        self.current_function: Optional[IRFunction] = None
        self.current_return_type: Type = "void"
        self.temp_count = 0
        self.label_count = 0
        self.scopes: list[dict[str, Storage]] = []

    # =================================================
    # DISPATCHER (LA CLAVE)
    # =================================================

    def visit(self, node):
        if isinstance(node, Program):
            return self.visit_program(node)
        elif isinstance(node, VarDecl):
            return self.visit_vardecl(node)
        elif isinstance(node, ArrayDecl):
            return self.visit_arraydecl(node)
        elif isinstance(node, FuncDecl):
            return self.visit_funcdecl(node)
        elif isinstance(node, BlockStmt):
            return self.visit_block(node)
        elif isinstance(node, AssignExpr):
            return self.visit_assign(node)
        elif isinstance(node, PrintStmt):
            return self.visit_print(node)
        elif isinstance(node, ExprStmt):
            return self.visit_exprstmt(node)
        elif isinstance(node, WhileStmt):
            return self.visit_while(node)
        elif isinstance(node, IfStmt):
            return self.visit_if(node)
        elif isinstance(node, ReturnStmt):
            return self.visit_return(node)
        elif isinstance(node, ForStmt):
            return self.visit_for(node)
        elif isinstance(node, BinOp):
            return self.visit_binop(node)
        elif isinstance(node, UnaryOp):
            return self.visit_unary(node)
        elif isinstance(node, AffixOp):
            return self.visit_affix(node)
        elif isinstance(node, Literal):
            return self.visit_literal(node)
        elif isinstance(node, Location):
            return self.visit_location(node)
        elif isinstance(node, FuncCall):
            return self.visit_funccall(node)
        else:
            raise Exception(f"Visit no implementado para {type(node)}")

    # =================================================
    # HELPERS
    # =================================================

    #Esta función hace para guardar variables temporales
    #R1, R10 y demás
    def new_temp(self):
        self.temp_count += 1
        return f"R{self.temp_count}"

    #Lo mismo que arriba pero con L al principio
    def new_label(self):
        self.label_count += 1
        return f"L{self.label_count}"

    #Esto toma la acción en sí y lo pone en el log
    def emit(self, *inst):
        if self.current_function:
            self.current_function.instructions.append(inst)
        else:
            self.program.globals.append(inst)

    def push_scope(self):
        self.scopes.append({})

    def pop_scope(self):
        self.scopes.pop()

    def bind(self, storage: Storage):
        self.scopes[-1][storage.name] = storage

    def lookup(self, name):
        # print(self.current_function)
        # print(name)
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise Exception(f"Variable no encontrada: {name}")
    
    #============================
    #Manejo de tipos
    #============================

    def type_suffix(self, ty: Type) -> str:
        if isinstance(ty, SimpleType):
            if ty.name in ("integer", "boolean"):
                return "I"
            elif ty.name == "float":
                return "F"
            elif ty.name == "char":
                return "B"
            elif ty.name == "string":
                return "S"
            elif ty.name == "void":
                return "V"
        raise NotImplementedError(f"Tipo no soportado: {ty}")


    def load_opcode(self, ty: Type) -> str:
        return f"LOAD{self.type_suffix(ty)}"


    def store_opcode(self, ty: Type) -> str:
        return f"STORE{self.type_suffix(ty)}"


    def alloc_opcode(self, ty: Type) -> str:
        return f"ALLOC{self.type_suffix(ty)}"


    def print_opcode(self, ty: Type) -> str:
        return f"PRINT{self.type_suffix(ty)}"

    # =================================================
    # PROGRAM
    # =================================================

    def visit_program(self, node: Program):
        self.push_scope()

        for decl in node.decls:
            if isinstance(decl, VarDecl):
                self.bind(Storage(decl.name, decl.datatype, is_global=True))
            elif isinstance(decl, ArrayDecl):
                self.bind(Storage(decl.name, decl.datatype, is_global=True))
            elif isinstance(decl, FuncDecl):
                self.bind(Storage(decl.name, decl.datatype, is_global=True))

        for decl in node.decls:
            self.visit(decl)

        self.pop_scope()
        return self.program

    def visit_funcdecl(self, node: FuncDecl):
        fn = IRFunction(node.name, [(p.name, p.datatype) for p in node.datatype.params], node.datatype)
        self.program.functions.append(fn)

        prev = self.current_function
        self.current_function = fn

        self.push_scope()

        for p in node.datatype.params:
            self.bind(Storage(p.name, p.datatype, is_param=True))

        for stmt in node.body:
            self.visit(stmt)

        self.emit("RET")

        self.pop_scope()
        self.current_function = prev

    def visit_block(self, node: BlockStmt):
        self.emit("ENTER")
        self.push_scope()
        for stmt in node.stmts:
            self.visit(stmt)
        self.pop_scope()
        self.emit("EXIT")

    # =================================================
    # DECLARATIONS
    # =================================================

    def visit_vardecl(self, node: VarDecl):
        self.bind(Storage(node.name, node.datatype))
        self.emit("ALLOC", node.name)

        if node.value:
            val = self.visit(node.value)
            self.emit("STORE", val, node.name)

    def visit_arraydecl(self, node: ArrayDecl):
        # Bind the array storage
        self.bind(Storage(node.name, node.datatype))
        
        # For arrays, we allocate once per declaration
        self.emit("ALLOC", node.name)
        
        # If there are initial values, store them
        if node.elements:
            for i, elem in enumerate(node.elements):
                val = self.visit(elem)
                # For simplicity, we emit a STORE with index
                # The interpreter will handle array indexing
                self.emit("STOREA", val, node.name, i)

    # =================================================
    # STATEMENTS
    # =================================================

    def visit_assignment(self, node: Assignment):
        val = self.visit(node.expr)
        self.emit("STORE", val, node.loc.name)

    def visit_print(self, node: PrintStmt):
        for expr in node.exprs:
            if isinstance(expr, Literal):
                val = self.visit(expr)
                if isinstance(expr.value, str) and len(expr.value) == 1:
                    self.emit("PRINTB", val)
                else:
                    self.emit("PRINT", val)
            elif isinstance(expr, Location):
                storage = self.lookup(expr.name)
                val = self.visit(expr)
                if isinstance(storage.ty, SimpleType) and storage.ty.name == "char":
                    self.emit("PRINTB", val)
                else:
                    self.emit("PRINT", val)
            else:
                val = self.visit(expr)
                self.emit("PRINT", val)

    def visit_exprstmt(self, node: ExprStmt):
        self.visit(node.expr)

    def visit_assign(self, node: AssignExpr):
        val = self.visit(node.expr)
        # lval debe ser una Location
        if isinstance(node.lval, Location):
            self.emit("STORE", val, node.lval.name)
        else:
            raise Exception(f"Asignación a non-location no soportada: {type(node.lval)}")
        return val

    def visit_return(self, node: ReturnStmt):
        if node.expr:
            val = self.visit(node.expr)
            self.emit("RET", val)
        else:
            self.emit("RET")

    def visit_if(self, node: IfStmt):
        cond = self.visit(node.cond)

        L_then = self.new_label()
        L_end = self.new_label()

        self.emit("CBRANCH", cond, L_then, L_end)

        self.emit("LABEL", L_then)
        self.visit(node.then_b)
        self.emit("LABEL", L_end)

    def visit_while(self, node: WhileStmt):
        L_start = self.new_label()
        L_body = self.new_label()
        L_end = self.new_label()

        self.emit("LABEL", L_start)

        cond = self.visit(node.cond)
        self.emit("CBRANCH", cond, L_body, L_end)

        self.emit("LABEL", L_body)
        self.visit(node.body)
        self.emit("BRANCH", L_start)

        self.emit("LABEL", L_end)

    def visit_for(self, node: ForStmt):
        if node.init:
            self.visit(node.init)

        L_start = self.new_label()
        L_body = self.new_label()
        L_end = self.new_label()

        self.emit("LABEL", L_start)

        if node.cond:
            cond = self.visit(node.cond)
            self.emit("CBRANCH", cond, L_body, L_end)
        else:
            self.emit("BRANCH", L_body)

        self.emit("LABEL", L_body)
        self.visit(node.body)

        if node.step:
            self.visit(node.step)

        self.emit("BRANCH", L_start)
        self.emit("LABEL", L_end)

    def visit_funccall(self, node: FuncCall):
        for arg in node.args:
            val = self.visit(arg)
            self.emit("PUSH", val)

        self.emit("CALL", node.name, len(node.args))
        result = self.new_temp()
        self.emit("POP", result)
        return result

    # =================================================
    # EXPRESSIONS
    # =================================================
    #Para operaciones binarias
    def visit_binop(self, node: BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        out = self.new_temp()

        #Tengo entendido que python no usa case, entonces nos tocó usar if
        if node.op == "+":
            self.emit("ADD", left, right, out)
        elif node.op == "-":
            self.emit("SUB", left, right, out)
        elif node.op == "*":
            self.emit("MUL", left, right, out)
        elif node.op == "/":
            self.emit("DIV", left, right, out)
        elif node.op == "%":
            self.emit("REM", left, right, out)
        elif node.op in {"<", "<=", ">", ">=", "==", "!="}:
            self.emit("CMP", node.op, left, right, out)
        else:
            raise Exception(f"Operador no soportado: {node.op}")

        return out

    #Unarios 
    def visit_unary(self, node: UnaryOp):
        val = self.visit(node.expr)
        out = self.new_temp()

        if node.op == "-":
            self.emit("NEG", val, out)
        elif node.op == "!":
            self.emit("NOT", val, out)

        return out

    def visit_affix(self, node: AffixOp):
        if not isinstance(node.expr, Location):
            raise Exception(f"AffixOp solo soportado sobre Location, no {type(node.expr)}")

        storage = self.lookup(node.expr.name)
        if not isinstance(storage.ty, SimpleType):
            raise Exception(f"AffixOp no soportado para tipo: {storage.ty}")

        if storage.ty.name == "void" or storage.ty.name == "string":
            raise Exception(f"AffixOp no soportado para tipo: {storage.ty}")

        load = self.load_opcode(storage.ty)
        store = self.store_opcode(storage.ty)

        old_temp = self.new_temp()
        self.emit(load, node.expr.name, old_temp)

        increment = self.new_temp()
        if storage.ty.name == "float":
            self.emit("MOVF", 1.0, increment)
        else:
            self.emit("MOVI", 1, increment)

        result = self.new_temp()
        if node.op == "++":
            self.emit("ADD", old_temp, increment, result)
        else:
            self.emit("SUB", old_temp, increment, result)

        self.emit(store, result, node.expr.name)
        return result

    #Aquí hay booleanos, enteros, flotantes y strings
    # #En este caso los booleanos se representacn con 1 = true y 0 = false    
    def visit_literal(self, node):
        tmp = self.new_temp()

        if isinstance(node.value, bool):
            self.emit("MOVI", 1 if node.value else 0, tmp)
        elif isinstance(node.value, int):
            self.emit("MOVI", node.value, tmp)
        elif isinstance(node.value, float):
            self.emit("MOVF", node.value, tmp)
        elif isinstance(node.value, str):
            if len(node.value) == 1:
                self.emit("MOVB", ord(node.value), tmp)
            else:
                self.emit("MOVS", node.value, tmp)
        else:
            raise Exception(f"Tipo de literal no soportado: {node.value}")

        return tmp
    
    def visit_location(self, node):
        storage = self.lookup(node.name)
        tmp = self.new_temp()
        self.emit(self.load_opcode(storage.ty), node.name, tmp)
        return tmp

    @classmethod
    def generate(cls, node: Program) -> IRProgram:
        gen = cls()
        gen.visit(node)
        return gen.program