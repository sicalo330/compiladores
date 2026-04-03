# model.py
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

@dataclass 
class SimpleType(Type): 
    name: str

@dataclass 
class ArraySizedType(Type): 
    size: 'Expr'
    elem_type: Type

@dataclass 
class ArrayType(Type): 
    elem_type: Type

@dataclass 
class FuncType(Type): 
    ret_type: Type
    params: List['Param']

@dataclass 
class Param(Node): 
    name: str
    datatype: Type

# ==========================================
# DECLARACIONES (Declarations)
# ==========================================
@dataclass 
class Program(Node): 
    decls: List['Decl']

class Decl(Node): pass

@dataclass 
class VarDecl(Decl): 
    name: str
    datatype: Type
    value: Optional['Expr'] = None

@dataclass 
class ArrayDecl(Decl): 
    name: str
    datatype: Type
    elements: Optional[List['Expr']] = None

@dataclass 
class FuncDecl(Decl): 
    name: str
    datatype: Type
    body: Optional[List['Stmt']] = None

# ==========================================
# SENTENCIAS (Statements)
# ==========================================
class Stmt(Node): pass

@dataclass 
class IfStmt(Stmt): 
    cond: 'Expr'
    then_b: Stmt
    else_b: Optional[Stmt] = None

@dataclass 
class WhileStmt(Stmt): 
    cond: 'Expr'
    body: Stmt

@dataclass 
class ForStmt(Stmt): 
    init: Optional['Expr']
    cond: Optional['Expr']
    step: Optional['Expr']
    body: Stmt

@dataclass 
class PrintStmt(Stmt): 
    exprs: List['Expr']

@dataclass 
class ReturnStmt(Stmt): 
    expr: Optional['Expr']

@dataclass 
class BlockStmt(Stmt): 
    stmts: List[Stmt]

@dataclass 
class ExprStmt(Stmt): 
    expr: 'Expr'

# ==========================================
# EXPRESIONES (Expressions)
# ==========================================
class Expr(Node): pass

@dataclass 
class AssignExpr(Expr): 
    lval: 'Expr'
    expr: Expr

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
class PostfixOp(Expr): 
    op: str
    expr: Expr

@dataclass 
class Location(Expr): 
    name: str

@dataclass 
class ArrayAccess(Expr): 
    name: str
    index: Expr

@dataclass 
class FuncCall(Expr): 
    name: str
    args: List[Expr]

@dataclass 
class Literal(Expr): 
    value: Any
    type_name: str