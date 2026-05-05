# typesys.py
'''
Sistema de tipos
================
Este archivo implementa las características básicas del sistema de tipos. Existe
mucha flexibilidad, pero la mejor estrategia podría ser no darle demasiadas
vueltas al problema. Al menos no al principio. Estos son los requisitos
básicos mínimos:

1. Los tipos tienen identidad (p. ej., al menos un nombre como 'int', 'float', 'char').
2. Los tipos deben ser comparables (p. ej., int != float).
3. Los tipos admiten diferentes operadores (p. ej., +, -, *, /, etc.).
Una forma de lograr todos estos objetivos es comenzar con algún tipo de
enfoque basado en tablas. No es lo más sofisticado, pero funcionará
como punto de partida. Puede volver a refactorizar el sistema de tipos
más adelante.
'''

typenames: set[str] = {'integer', 'float', 'boolean', 'char', 'string'} # Cómo se añaden las clases? - JJ

# Capabilities
_tern_op: dict[tuple[str, str, str, str, str], str] = {
	('boolean', '?', 'integer', ':', 'integer') : 'integer',
	('boolean', '?', 'boolean', ':', 'boolean') : 'boolean',
	('boolean', '?', 'char', ':', 'char') : 'char',
	('boolean', '?', 'float', ':', 'float') : 'float',
	('boolean', '?', 'string', ':', 'string') : 'string'
}

_bin_ops: dict[tuple[str, str, str], str] = {
	# Integer operations
	('integer', '+', 'integer') : 'integer',
	('integer', '-', 'integer') : 'integer',
	('integer', '*', 'integer') : 'integer',
	('integer', '/', 'integer') : 'integer',
	('integer', '%', 'integer') : 'integer',

	('integer', '=', 'integer') : 'integer',

	('integer', '<', 'integer')  : 'boolean',
	('integer', '<=', 'integer') : 'boolean',
	('integer', '>', 'integer')  : 'boolean',
	('integer', '>=', 'integer') : 'boolean',
	('integer', '==', 'integer') : 'boolean',
	('integer', '!=', 'integer') : 'boolean',

	# Float operations
	('float', '+', 'float') : 'float',
	('float', '-', 'float') : 'float',
	('float', '*', 'float') : 'float',
	('float', '/', 'float') : 'float',
	('float', '%', 'float') : 'float',

	('float', '=', 'float') : 'float',

	('float', '<', 'float')  : 'boolean',
	('float', '<=', 'float') : 'boolean',
	('float', '>', 'float')  : 'boolean',
	('float', '>=', 'float') : 'boolean',
	('float', '==', 'float') : 'boolean',
	('float', '!=', 'float') : 'boolean',

	# Booleans
	('boolean', '&&', 'boolean') : 'boolean',
	('boolean', '||', 'boolean') : 'boolean',
	('boolean', '==', 'boolean') : 'boolean',
	('boolean', '!=', 'boolean') : 'boolean',

	# Char
	('char', '=', 'char')  : 'char',

	('char', '<', 'char')  : 'boolean',
	('char', '<=', 'char') : 'boolean',
	('char', '>', 'char')  : 'boolean',
	('char', '>=', 'char') : 'boolean',
	('char', '==', 'char') : 'boolean',
	('char', '!=', 'char') : 'boolean',
	
	# Strings
	('string', '+', 'string') : 'string',
	
	('string', '=', 'string') : 'string',
}

_unary_ops: dict[tuple[str, str], str] = {
	('+', 'integer') : 'integer',
	('-', 'integer') : 'integer',
	('^', 'integer') : 'integer',

	('+', 'float')   : 'float',
	('-', 'float')   : 'float',

	('!', 'boolean') : 'boolean',
}

# Check if a binary operator is supported. Returns the
# result type or None (if not supported). Type checker
# uses this function.

def loockup_type(name: str) -> (str | None):
	'''
	Dado el nombre de un tipo primitivo, se busca el objeto "type" apropiado.
	Para empezar, los tipos son solo nombres, pero mas adelante pueden ser
	objetos mas avanzados.
	'''
	if name in typenames: return name
	else: return None

def check_ternop(cond, then_r, else_r) -> (str | None): return _tern_op.get((cond, then_r, else_r))

def check_binop(left, op, right) -> (str | None): return _bin_ops.get((left, op, right)) #Creo que el órden de estos parámetros está dando error con bad5, debería preguntarle al profe

def check_unaryop(op, operand_type) -> (str | None): return _unary_ops.get((op, operand_type))
