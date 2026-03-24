# bminor_rd2.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional, List, Union
from rich import print
import re

# ===================================================
# AST (dataclasses) - basado en grammar.txt
# ===================================================

# ---------- Types ----------
class Type: ...

@dataclass(frozen=True)
class SimpleType(Type):
	name: str  # INTEGER, FLOAT, BOOLEAN, CHAR, STRING, VOID
	
@dataclass(frozen=True)
class ArrayType(Type):
	# type_array ::= ARRAY [ ] type_simple | ARRAY [ ] type_array
	elem: Type
	
@dataclass(frozen=True)
class ArraySizedType(Type):
	# type_array_sized ::= ARRAY index type_simple | ARRAY index type_array_sized
	size_expr: "Expr"
	elem: Type  # SimpleType o ArraySizedType (recursivo)
	
@dataclass(frozen=True)
class FuncType(Type):
	# type_func ::= FUNCTION type_simple '(' opt_param_list ')'
	#           |  FUNCTION type_array_sized '(' opt_param_list ')'
	ret: Type
	params: List["Param"]
	
@dataclass(frozen=True)
class Param:
	name: str
	typ: Type
	
# ---------- Program / Decl ----------
class Decl: ...

@dataclass
class Program:
	decls: List[Decl]
	
@dataclass
class DeclTyped(Decl):
	# decl ::= ID ':' type_simple ';' | ID ':' type_array_sized ';' | ID ':' type_func ';'
	name: str
	typ: Type
	
@dataclass
class DeclInit(Decl):
	# decl_init ::= ID ':' type_simple '=' expr ';'
	#            |  ID ':' type_array_sized '=' '{' opt_expr_list '}' ';'
	#            |  ID ':' type_func '=' '{' opt_stmt_list '}'
	name: str
	typ: Type
	init: Any  # Expr | List[Expr] | List[Stmt]
	
# ---------- Stmt ----------
class Stmt: ...

@dataclass
class Print(Stmt):
	values: List["Expr"]
	
@dataclass
class Return(Stmt):
	value: Optional["Expr"]
	
@dataclass
class Block(Stmt):
	stmts: List[Union[Stmt, Decl]]  # en tu gramática: stmt puede ser decl (simple_stmt)
	
@dataclass
class ExprStmt(Stmt):
	expr: "Expr"
	
@dataclass
class If(Stmt):
	cond: Optional["Expr"]     # if_cond usa opt_expr
	then: Stmt
	otherwise: Optional[Stmt] = None
	
@dataclass
class For(Stmt):
	init: Optional["Expr"]
	cond: Optional["Expr"]
	step: Optional["Expr"]
	body: Stmt
	
# ---------- Expr ----------
class Expr: ...

@dataclass
class Name(Expr):
	id: str
	
@dataclass
class Literal(Expr):
	kind: str
	value: Any
	
@dataclass
class Index(Expr):
	base: Expr         # típicamente Name(...)
	indices: List[Expr]  # index_list
	
@dataclass
class Call(Expr):
	func: str          # grammar: ID '(' opt_expr_list ')'
	args: List[Expr]
	
@dataclass
class Assign(Expr):
	target: Expr       # lval
	value: Expr
	
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
	op: str  # INC/DEC
	expr: Expr
	
	
# ===================================================
# Tokenizer
# ===================================================

@dataclass
class Token:
	type: str
	value: Any
	line: int
	col: int
	
KEYWORDS = {
	"if", "else", "for", "print", "return", "true", 
	"false", "integer", "float", "boolean", "char",
	"string", "void", "array", "function",
}

MULTI = {
    "||": "LOR",
    "&&": "LAND",
    "==": "EQ",
    "!=": "NE",
    "<=": "LE",
    ">=": "GE",
    "++": "INC",
    "--": "DEC",
}

SINGLE = {
    "+": "+", "-": "-", "*": "*", "/": "/", 
    "%": "%", "^": "^", "<": "LT", ">": "GT", 
    "=": "=", ":": ":", ",": ",", ";": ";",
    "(": "(", ")": ")", "{": "{", "}": "}", 
    "[": "[", "]": "]", 
    "!": "NOT", # en gramática: 'NOT' expr8
}

class Tokenizer:
	def __init__(self, text: str):
		self.s = text
		self.i = 0
		self.line = 1
		self.col = 1
		
	def _peek(self, k=0) -> str:
		j = self.i + k
		return self.s[j] if j < len(self.s) else ""
		
	def _adv(self, n=1) -> None:
		for _ in range(n):
			ch = self._peek()
			self.i += 1
			if ch == "\n":
				self.line += 1
				self.col = 1
			else:
				self.col += 1
				
	def tokens(self) -> Iterator[Token]:
		while self.i < len(self.s):
			ch = self._peek()
			
			# whitespace
			if ch.isspace():
				self._adv()
				continue
				
			# // comment
			if ch == "/" and self._peek(1) == "/":
				while self._peek() not in ("", "\n"):
					self._adv()
				continue
				
			# /* comment */
			if ch == "/" and self._peek(1) == "*":
				self._adv(2)
				while not (self._peek() == "*" and self._peek(1) == "/"):
					if self._peek() == "":
						raise SyntaxError(f"Comentario sin cerrar (línea {self.line})")
					self._adv()
				self._adv(2)
				continue
				
			# multi operators
			two = ch + self._peek(1)
			if two in MULTI:
				t = Token(MULTI[two], two, self.line, self.col)
				self._adv(2)
				yield t
				continue
				
			# string
			if ch == '"':
				L, C = self.line, self.col
				self._adv()
				buf = []
				while True:
					c = self._peek()
					if c == "":
						raise SyntaxError(f"STRING sin cerrar (línea {L})")
					if c == '"':
						self._adv()
						break
					if c == "\\":
						self._adv()
						esc = self._peek()
						mapping = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}
						buf.append(mapping.get(esc, esc))
						self._adv()
					else:
						buf.append(c)
						self._adv()
				yield Token("STRING_LITERAL", "".join(buf), L, C)
				continue
				
			# char
			if ch == "'":
				L, C = self.line, self.col
				self._adv()
				c = self._peek()
				if c == "\\":
					self._adv()
					esc = self._peek()
					mapping = {"n": "\n", "t": "\t", "'": "'", "\\": "\\"}
					val = mapping.get(esc, esc)
					self._adv()
				else:
					val = c
					self._adv()
				if self._peek() != "'":
					raise SyntaxError(f"CHAR inválido (línea {L})")
				self._adv()
				yield Token("CHAR_LITERAL", val, L, C)
				continue
				
			# number: INTEGER_LITERAL or FLOAT_LITERAL
			if ch.isdigit():
				L, C = self.line, self.col
				m = re.match(r"\d+(\.\d+)?", self.s[self.i:])
				lex = m.group(0)
				self._adv(len(lex))
				if "." in lex:
					yield Token("FLOAT_LITERAL", float(lex), L, C)
				else:
					yield Token("INTEGER_LITERAL", int(lex), L, C)
				continue
				
			# identifier / keyword
			if ch.isalpha() or ch == "_":
				L, C = self.line, self.col
				m = re.match(r"[A-Za-z_]\w*", self.s[self.i:])
				lex = m.group(0)
				self._adv(len(lex))
				if lex in KEYWORDS:
					yield Token(lex, lex, L, C)
				else:
					yield Token("ID", lex, L, C)
				continue
				
			# single
			if ch in SINGLE:
				t = Token(SINGLE[ch], ch, self.line, self.col)
				self._adv()
				yield t
				continue
				
			raise SyntaxError(f"Carácter ilegal '{ch}' (línea {self.line}, col {self.col})")
			
		yield Token("EOF", None, self.line, self.col)
		
		
# ===================================================
# Parser (Recursive Descent) - FIEL A grammar.txt
# ===================================================

class Parser:
	def __init__(self):
		self.tok: Optional[Token] = None
		self.la : Optional[Token] = None
		self.it : Optional[Iterator[Token]] = None
		
	def parse(self, tokens: Iterator[Token]) -> Program:
		self.it = iter(tokens)
		self.tok = None
		self.la = next(self.it)
		return self.prog()
		
	# ----- core helpers -----
	def _advance(self) -> None:
		self.tok = self.la
		self.la = next(self.it)
		
	def _accept(self, t: str) -> bool:
		if self.la and self.la.type == t:
			self._advance()
			return True
		return False
		
	def _expect(self, t: str) -> Token:
		if not self._accept(t):
			got = self.la.type if self.la else None
			line = self.la.line if self.la else -1
			col = self.la.col if self.la else -1
			raise SyntaxError(f"Esperaba {t}, obtuve {got} (línea {line}, col {col})")
		return self.tok
		
	# =================================================
	# prog ::= decl_list EOF
	# =================================================
	def prog(self) -> Program:
		decls = self.decl_list()
		self._expect("EOF")
		return Program(decls)
		
	def decl_list(self) -> List[Decl]:
		decls: List[Decl] = []
		while self.la.type != "EOF":
			decls.append(self.decl())
		return decls
		
	# decl ::= ID ':' type_simple ';'
	#       |  ID ':' type_array_sized ';'
	#       |  ID ':' type_func ';'
	#       |  decl_init
	def decl(self) -> Decl:
		# todos arrancan con ID ':'
		name = self._expect("ID").value
		self._expect(":")
		typ = self.type_any_decl_head()
		
		# decl_init se detecta por '=' o por tipo_func con '=' '{'
		if self._accept("="):
			# decl_init variantes
			if isinstance(typ, FuncType):
				self._expect("{")
				body = self.opt_stmt_list()
				self._expect("}")
				return DeclInit(name, typ, body)
			if isinstance(typ, ArraySizedType):
				self._expect("{")
				xs = self.opt_expr_list()
				self._expect("}")
				self._expect(";")
				return DeclInit(name, typ, xs)
			# simple
			e = self.expr()
			self._expect(";")
			return DeclInit(name, typ, e)
			
		# no init -> decl tipada
		self._expect(";")
		return DeclTyped(name, typ)
		
	# helper: decide entre type_simple, type_array_sized, type_func
	def type_any_decl_head(self) -> Type:
		# mira el lookahead: FUNCTION, ARRAY, o tipo simple
		if self.la.type == "FUNCTION":
			return self.type_func()
		if self.la.type == "ARRAY":
			# en decl sin init, tu gramática usa type_array_sized (no type_array)
			return self.type_array_sized()
		return self.type_simple()
		
	# =================================================
	# Statements (open/closed)
	# =================================================
	def opt_stmt_list(self) -> List[Union[Stmt, Decl]]:
		# opt_stmt_list ::= epsilon | stmt_list
		if self._starts_stmt():
			return self.stmt_list()
		return []
		
	def stmt_list(self) -> List[Union[Stmt, Decl]]:
		# stmt_list ::= stmt | stmt stmt_list
		items: List[Union[Stmt, Decl]] = []
		while self._starts_stmt():
			items.append(self.stmt())
		return items
		
	def _starts_stmt(self) -> bool:
		# stmt ::= open_stmt | closed_stmt
		# simple_stmt ::= PRINT | RETURN | block | decl | expr ';'
		if self.la.type in {"IF", "FOR", "PRINT", "RETURN", "{", "ID"}:
			return True
		# decl empieza con ID ':' ...  (pero ID también puede iniciar expr)
		return False
		
	def stmt(self) -> Union[Stmt, Decl]:
		# Si viene IF/FOR -> open/closed según gramática
		if self.la.type == "IF":
			return self.if_stmt()   # maneja open/closed internamente
		if self.la.type == "FOR":
			return self.for_stmt()  # maneja open/closed internamente
			
		# simple_stmt
		if self.la.type == "PRINT":
			return self.print_stmt()
		if self.la.type == "RETURN":
			return self.return_stmt()
		if self.la.type == "{":
			return self.block_stmt()
			
		# decl o expr ';' (ambigüedad por ID)
		# decl necesita ver patrón: ID ':' ...
		if self.la.type == "ID":
			# lookahead manual: si después de ID viene ':', es decl
			save = self.la
			# consumimos ID temporalmente para inspeccionar
			self._advance()
			is_decl = (self.la.type == ":")
			# “des-consumir”: lo más simple es guardar y recrear parser,
			# pero aquí lo resolvemos con un mini-buffer: retroceso 1.
			# Para mantenerlo simple: implementamos un buffer de 1 token:
			self._unadvance(save)
			
			if is_decl:
				return self.decl()
				
		# expr ';'
		e = self.expr()
		self._expect(";")
		return ExprStmt(e)
		
	# mini retroceso de 1 token (solo usado para distinguir decl vs expr con ID)
	def _unadvance(self, previous_la: Token) -> None:
		# dejaremos self.la como previous_la y self.tok como None;
		# y crearemos un iterador “pegado” (previous_la + old stream).
		assert self.it is not None
		old_la = self.la
		old_it = self.it
		
		def chain():
			yield previous_la
			yield old_la
			yield from old_it
			
		self.it = iter(chain())
		self.tok = None
		self.la = next(self.it)
		
	# if_cond ::= IF '(' opt_expr ')'
	def if_cond(self) -> Optional[Expr]:
		self._expect("IF")
		self._expect("(")
		cond = self.opt_expr()
		self._expect(")")
		return cond
		
	# if_stmt_open / if_stmt_closed (dangling else)
	def if_stmt(self) -> Stmt:
		cond = self.if_cond()
		then = self.stmt()
		if self._accept("ELSE"):
			otherwise = self.stmt()
			return If(cond, then, otherwise)
		return If(cond, then, None)
		
	# for_header ::= FOR '(' opt_expr ';' opt_expr ';' opt_expr ')'
	def for_header(self) -> tuple[Optional[Expr], Optional[Expr], Optional[Expr]]:
		self._expect("FOR")
		self._expect("(")
		init = self.opt_expr()
		self._expect(";")
		cond = self.opt_expr()
		self._expect(";")
		step = self.opt_expr()
		self._expect(")")
		return init, cond, step
		
	def for_stmt(self) -> Stmt:
		init, cond, step = self.for_header()
		body = self.stmt()
		return For(init, cond, step, body)
		
	# print_stmt ::= PRINT opt_expr_list ';'
	def print_stmt(self) -> Print:
		self._expect("PRINT")
		xs = self.opt_expr_list()
		self._expect(";")
		return Print(xs)
		
	# return_stmt ::= RETURN opt_expr ';'
	def return_stmt(self) -> Return:
		self._expect("RETURN")
		v = self.opt_expr()
		self._expect(";")
		return Return(v)
		
	# block_stmt ::= '{' stmt_list '}'
	def block_stmt(self) -> Block:
		self._expect("{")
		stmts = self.stmt_list()  # en tu gramática no hay epsilon aquí
		self._expect("}")
		return Block(stmts)
		
	# =================================================
	# Expressions (fiel a expr1..expr9 con precedencia)
	# =================================================
	def opt_expr(self) -> Optional[Expr]:
		# opt_expr ::= epsilon | expr
		# tokens que pueden iniciar expr (muy básico):
		if self.la.type in {"ID", "INTEGER_LITERAL", "FLOAT_LITERAL", "CHAR_LITERAL",
		"STRING_LITERAL", "TRUE", "FALSE", "(", "-", "NOT"}:
			return self.expr()
		return None
		
	def opt_expr_list(self) -> List[Expr]:
		if self._starts_expr():
			return self.expr_list()
		return []
		
	def _starts_expr(self) -> bool:
		return self.la.type in {"ID", "INTEGER_LITERAL", "FLOAT_LITERAL", "CHAR_LITERAL",
		"STRING_LITERAL", "TRUE", "FALSE", "(", "-", "NOT"}
		
	def expr_list(self) -> List[Expr]:
		xs = [self.expr()]
		while self._accept(","):
			xs.append(self.expr())
		return xs
		
	def expr(self) -> Expr:
		# expr ::= expr1
		return self.expr1()
		
	def expr1(self) -> Expr:
		# expr1 ::= lval '=' expr1 | expr2
		left = self.expr2()
		if self._accept("="):
			# lval en tu gramática es ID o ID index (nosotros lo representamos como Name/Index)
			if not isinstance(left, (Name, Index)):
				raise SyntaxError("Asignación: lado izquierdo no es lval")
			right = self.expr1()
			return Assign(left, right)
		return left
		
	def expr2(self) -> Expr:
		e = self.expr3()
		while self._accept("LOR"):
			e = BinOp("||", e, self.expr3())
		return e
		
	def expr3(self) -> Expr:
		e = self.expr4()
		while self._accept("LAND"):
			e = BinOp("&&", e, self.expr4())
		return e
		
	def expr4(self) -> Expr:
		e = self.expr5()
		while True:
			if self._accept("EQ"):
				e = BinOp("==", e, self.expr5()); continue
			if self._accept("NE"):
				e = BinOp("!=", e, self.expr5()); continue
			if self._accept("LT"):
				e = BinOp("<", e, self.expr5()); continue
			if self._accept("LE"):
				e = BinOp("<=", e, self.expr5()); continue
			if self._accept("GT"):
				e = BinOp(">", e, self.expr5()); continue
			if self._accept("GE"):
				e = BinOp(">=", e, self.expr5()); continue
			break
		return e
		
	def expr5(self) -> Expr:
		e = self.expr6()
		while True:
			if self._accept("+"):
				e = BinOp("+", e, self.expr6()); continue
			if self._accept("-"):
				e = BinOp("-", e, self.expr6()); continue
			break
		return e
		
	def expr6(self) -> Expr:
		e = self.expr7()
		while True:
			if self._accept("*"):
				e = BinOp("*", e, self.expr7()); continue
			if self._accept("/"):
				e = BinOp("/", e, self.expr7()); continue
			if self._accept("%"):
				e = BinOp("%", e, self.expr7()); continue
			break
		return e
		
	def expr7(self) -> Expr:
		# expr7 ::= expr7 '^' expr8 | expr8   (izquierda en tu gramática)
		e = self.expr8()
		while self._accept("^"):
			e = BinOp("^", e, self.expr8())
		return e
		
	def expr8(self) -> Expr:
		if self._accept("-"):
			return UnaryOp("-", self.expr8())
		if self._accept("NOT"):
			return UnaryOp("NOT", self.expr8())
		return self.expr9()
		
	def expr9(self) -> Expr:
		# expr9 ::= expr9 INC | expr9 DEC | group
		e = self.group()
		while True:
			if self._accept("INC"):
				e = PostfixOp("++", e); continue
			if self._accept("DEC"):
				e = PostfixOp("--", e); continue
			break
		return e
		
	def group(self) -> Expr:
		# group ::= '(' expr ')' | ID '(' opt_expr_list ')' | ID index | factor
		if self._accept("("):
			e = self.expr()
			self._expect(")")
			return e
			
		if self._accept("ID"):
			name = self.tok.value
			# call
			if self._accept("("):
				args = self.opt_expr_list()
				self._expect(")")
				return Call(name, args)
			# index
			if self.la.type == "[":
				indices = self.index_list()
				return Index(Name(name), indices)
			return Name(name)
			
		return self.factor()
		
	def index_list(self) -> List[Expr]:
		# index_list ::= index_list index | index
		idxs = [self.index()]
		while self.la.type == "[":
			idxs.append(self.index())
		return idxs
		
	def index(self) -> Expr:
		self._expect("[")
		e = self.expr()
		self._expect("]")
		return e
		
	def factor(self) -> Expr:
		if self._accept("ID"):
			return Name(self.tok.value)
		if self._accept("INTEGER_LITERAL"):
			return Literal("int", self.tok.value)
		if self._accept("FLOAT_LITERAL"):
			return Literal("float", self.tok.value)
		if self._accept("CHAR_LITERAL"):
			return Literal("char", self.tok.value)
		if self._accept("STRING_LITERAL"):
			return Literal("string", self.tok.value)
		if self._accept("TRUE"):
			return Literal("bool", True)
		if self._accept("FALSE"):
			return Literal("bool", False)
			
		raise SyntaxError(f"Factor inválido (línea {self.la.line}, col {self.la.col})")
		
	# =================================================
	# Types (fiel a grammar.txt)
	# =================================================
	def type_simple(self) -> SimpleType:
		# INTEGER | FLOAT | BOOLEAN | CHAR | STRING | VOID
		for t in ("integer", "float", "boolean", "char", "string", "void"):
			if self._accept(t):
				return SimpleType(t)
		raise SyntaxError(f"Se esperaba tipo simple (línea {self.la.line})")
		
	def type_array(self) -> ArrayType:
		# type_array ::= ARRAY '[' ']' type_simple | ARRAY '[' ']' type_array
		self._expect("ARRAY")
		self._expect("[")
		self._expect("]")
		# recursivo
		if self.la.type == "ARRAY":
			return ArrayType(self.type_array())
		return ArrayType(self.type_simple())
		
	def type_array_sized(self) -> ArraySizedType:
		# type_array_sized ::= ARRAY index type_simple | ARRAY index type_array_sized
		self._expect("ARRAY")
		size = self.index()  # index ::= '[' expr ']'
		if self.la.type == "ARRAY":
			return ArraySizedType(size, self.type_array_sized())
		return ArraySizedType(size, self.type_simple())
		
	def type_func(self) -> FuncType:
		# FUNCTION type_simple '(' opt_param_list ')'
		# FUNCTION type_array_sized '(' opt_param_list ')'
		self._expect("FUNCTION")
		if self.la.type == "ARRAY":
			ret = self.type_array_sized()
		else:
			ret = self.type_simple()
		self._expect("(")
		params = self.opt_param_list()
		self._expect(")")
		return FuncType(ret, params)
		
	def opt_param_list(self) -> List[Param]:
		if self.la.type == "ID":
			return self.param_list()
		return []
		
	def param_list(self) -> List[Param]:
		params = [self.param()]
		while self._accept(","):
			params.append(self.param())
		return params
		
	def param(self) -> Param:
		name = self._expect("ID").value
		self._expect(":")
		# param ::= ID ':' type_simple | type_array | type_array_sized
		if self.la.type == "ARRAY":
			# en param sí existe type_array (no-sized) y type_array_sized
			# lo distinguimos por mirar si viene '[' ']' (vacío) o '[' expr ']'
			# tokenizer no distingue, así que miramos el token tras '[':
			# ARRAY '[' ']' ... vs ARRAY '[' expr ']' ...
			# Implementación: consumimos ARRAY y '[' y miramos lookahead.
			# Para no duplicar lógica, hacemos un peek “por parsing”:
			# si tras '[' viene ']' -> type_array, si no -> type_array_sized.
			self._expect("ARRAY")
			self._expect("[")
			if self._accept("]"):
				# ARRAY [] ...
				# seguimos como type_array pero ya consumimos ARRAY []
				if self.la.type == "ARRAY":
					elem = self.type_array()
				else:
					elem = self.type_simple()
				return Param(name, ArrayType(elem))
			else:
				# ARRAY [ expr ] ...
				e = self.expr()
				self._expect("]")
				if self.la.type == "ARRAY":
					return Param(name, ArraySizedType(e, self.type_array_sized()))
				return Param(name, ArraySizedType(e, self.type_simple()))
				
		return Param(name, self.type_simple())
		
		
# ===================================================
# Demo rápido
# ===================================================
if __name__ == "__main__":
	import sys
	src = r'''
	// programa ejemplo
	
	x: integer = 3;
	a: array [10] integer = { 1, 2, 3 };
	
	f: function integer (x: integer, y: integer) = {
		if (x) print x, y;
		else print 0;
		return x;
	}
	'''
	
	'''
	tokens = []
	for tok in Tokenizer(src).tokens():
		tokens.append((tok.type, tok.value, tok.line))
	print(tokens)
	'''
	
	try:
		ast = Parser().parse(Tokenizer(src).tokens())
	except SyntaxError as e:
		print(f'SyntaxError: {e}')
		sys.exit(1)
	print(ast)

