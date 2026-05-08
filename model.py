# model.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Any

class Node:
    def __init__(self):
        self.lineno: int = 0
        self.type = None

# ==========================================
# TIPOS (Types)
# ==========================================
class Type(Node): pass
# No entiendo por qué al usar Expr como tipo de dato se pone entre comillas pero no con algo como Stmt. Eliminé las comillas
class Expr(Node): pass 

@dataclass 
class SimpleType(Type): 
    name: str

@dataclass 
class ArraySizedType(Type): 
    size: List[Expr]
    elem_type: Type

    # def accept(this, Visitor visitor):
    #     visitor.visitArraySizedType(this)

@dataclass 
class ArrayType(Type): 
    elem_type: Type

@dataclass 
class FuncType(Type): 
    ret_type: Type
    params: List[Param]

@dataclass 
class Param(Node): 
    name: str
    datatype: Type

# ==========================================
# DECLARACIONES (Declarations)
# ==========================================
@dataclass 
class Program(Node): 
    decls: List[Decls]

class Decls(Node): pass # Agrupa las declaraciones comunes y las declaraciones de clases

class Decl(Decls): pass

@dataclass
class VarDecl(Decl): 
    name: str
    datatype: Type
    value: Optional[Expr] = None

@dataclass 
class ArrayDecl(Decl): 
    name: str
    datatype: Type
    elements: Optional[List[Expr]] = None

@dataclass 
class FuncDecl(Decl): 
    name: str
    datatype: Type
    body: Optional[List[Stmt]] = None

@dataclass
class ClassDecl(Decls):
    name: str
    inheritance: Optional[str]
    content: Optional[List[Decl]]

# ==========================================
# SENTENCIAS (Statements)
# ==========================================
class Stmt(Node): pass

@dataclass 
class IfStmt(Stmt): 
    cond: Expr
    then_b: Stmt
    else_b: Optional[Stmt] = None

@dataclass 
class WhileStmt(Stmt): 
    cond: Expr
    body: Stmt

@dataclass 
class ForStmt(Stmt): 
    init: Optional[Expr]
    cond: Optional[Expr]
    step: Optional[Expr]
    body: Stmt

@dataclass 
class PrintStmt(Stmt): 
    exprs: List[Expr]

@dataclass 
class ReturnStmt(Stmt): 
    expr: Optional[Expr]

@dataclass 
class BlockStmt(Stmt): 
    stmts: List[Stmt]

@dataclass 
class ExprStmt(Stmt): 
    expr: Expr

# ==========================================
# EXPRESIONES (Expressions)
# ==========================================

@dataclass 
class AssignExpr(Expr): 
    lval: Expr
    expr: Expr

@dataclass
class TernOp(Expr):
    cond: Expr
    then_r: Expr
    else_r: Expr

@dataclass 
class BinOp(Expr): 
    op: str
    left: Expr
    right: Expr

@dataclass 
class UnaryOp(Expr): 
    op: str
    expr: Expr

@dataclass 
class AffixOp(Expr):
    op: str
    expr: Expr

@dataclass 
class Location(Expr): 
    name: str

@dataclass 
class ArrayAccess(Expr): 
    name: str
    index_list: List[Expr]

@dataclass 
class FuncCall(Expr): 
    name: str
    args: List[Expr]

@dataclass
class AttrAccess(Expr):
    class_: str
    attr: str | FuncCall

@dataclass 
class Literal(Expr): 
    value: Any
    type_name: str