# lexer.py
# -*- coding: utf-8 -*-

import sly
from errors import error, has_errors

class Lexer(sly.Lexer):
	tokens: set = {
		# keywords
		ARRAY, BOOLEAN, BREAK, CHAR, CLASS, CONSTANT,
		CONTINUE, ELSE, EXTENDS, FALSE, FLOAT, FOR, FUNCTION, IF,
		INTEGER, PRINT, RETURN, STRING, TRUE, VOID, WHILE,

		# operators
		LT, LE, GT, GE, EQ, NE, LAND, LOR, INC, DEC,
		ADDEQ, SUBEQ, MULEQ, DIVEQ, MODEQ,

		# other tokens
		ID, CHAR_LITERAL, FLOAT_LITERAL, INTEGER_LITERAL, STRING_LITERAL
	}
	literals: str = '+-*/%^=:;,()[]{}!?'

	ignore: str = ' \t\r'

	@_(r"\n+")
	def ignore_newline(self, t): self.lineno += t.value.count('\n') #Por si se pregunta, esto es lo que se encarga de aumentar en uno el lineno teniendo en cuenta los saltos de línea

	# ignore comentarios
	@_(r"\/\/[^\n]*")
	def ignore_cppcomment(self, t): pass

	@_(r"\/\*[^*]*\*(\*|[^*/][^*]*\*)*\/")
	def ignore_comment(self, t): self.lineno += t.value.count('\n')

	# Error de comentario
	@_(r"/\*(.|\n)*?")
	def malformed_comment(self, t): error("Comentario mal formado, sin cerrar", t.lineno)

	# Operadores de relacion
	LE = r'<='
	GE = r'>='
	EQ = r'=='
	NE = r'!='
	LT = r'<'
	GT = r'>'

	# Operadores Logicos
	LAND = r'&&'
	LOR  = r'\|\|'

	# Incremento y decremento
	INC = r'\+\+'
	DEC = r'--'

	# Operadores de asignación
	ADDEQ = r'\+='
	SUBEQ = r'-='
	MULEQ = r'\*='
	DIVEQ = r'/='
	MODEQ = r'%='

	# Definicion de Tokens
	ID = r'[a-zA-Z_]\w*'

	ID['array']    = ARRAY
	ID['boolean']  = BOOLEAN
	ID['break']    = BREAK
	ID['char']     = CHAR
	ID['class']    = CLASS
	ID['constant'] = CONSTANT
	ID['continue'] = CONTINUE
	ID['else']     = ELSE
	ID['extends']  = EXTENDS
	ID['false']    = FALSE
	ID['float']    = FLOAT
	ID['for']      = FOR
	ID['function'] = FUNCTION	
	ID['if']       = IF
	ID['integer']  = INTEGER
	ID['print']    = PRINT
	ID['return']   = RETURN
	ID['string']   = STRING
	ID['true']     = TRUE
	ID['void']     = VOID
	ID['while']    = WHILE

	# Char
	@_(r"'([\x20-\x7E]|\\([abefnrtv\\'\"]|0x[0-9A-Fa-f]{2}))'")
	def CHAR_LITERAL(self, t):
		t.value = t.value[1:-1]
		if t.value == '\\n': t.value = '\n'
		return t

	@_(r"'.")
	def malformed_char(self, t): error(f"malformado CHAR", t.lineno)

	# Float
	@_(r"\d*(\.\d+)?[eE][-+]?[1-9]\d*|\d*\.\d+")
	def FLOAT_LITERAL(self, t):
		t.value = float(t.value)
		return t

	@_(r'(0\d+)((\.\d+(e[-+]?\d+)?)|(e[-+]?\d+))')
	def malformed_float(self, t): error(f"Literal de punto flotante '{t.value}' no sportado", t.lineno)

	# Integer
	@_(r"[1-9]\d*|0")
	def INTEGER_LITERAL(self, t):
		t.value = int(t.value)
		return t

	@_(r'0\d+')
	def malformed_integer(self, t): error(f"Literal entero '{t.value}' no sportado", t.lineno)

	# String
	@_(r'\"([^"\\]*(\\.[^"\\]*)*)\"')
	def STRING_LITERAL(self, t):
		t.value = t.value[1:-1]
		return t

	def error(self, t):
		from errors import error
		error(f"Carácter ilegal '{t.value[0]}'", t.lineno, stage="LEXER")
		self.index += 1

def tokenize(filename: str) -> None:
    from rich.table import Table
    from rich.console import Console

    console = Console()
    txt = open(filename, encoding='utf-8').read()
    lex = Lexer()

    tokens_accumulated = []
    
    # Intentamos tokenizar todo
    for tok in lex.tokenize(txt):
        tokens_accumulated.append(tok)

    # Si hubo errores durante el loop de tokenize, el lexer ya los imprimió
    if has_errors():
		#El color amarillo no se muestra, no sé por qué
        print(f"\n[bold yellow]Se encontraron errores léxicos. La tabla no se mostrará.[/bold yellow]")
    else:
        # Solo armamos y mostramos la tabla si el análisis fue limpio
        table = Table(title='Análisis Léxico Exitoso')
        table.add_column('type', style="cyan")
        table.add_column('value', style="green")
        table.add_column('lineno', justify='right')

        for tok in tokens_accumulated:
            value = tok.value if isinstance(tok.value, str) else str(tok.value)
            table.add_row(tok.type, value, str(tok.lineno))
        
        console.print(table)

if __name__ == '__main__':
	import sys

	if sys.platform != 'ios':
		if len(sys.argv) != 2: raise SystemExit("Usage: python glexer.py <filename>")
		filename = sys.argv[1]
	else:
		from File_Picker import file_picker_dialog

		filename = file_picker_dialog(
			title='Seleccionar una archivo',
			root_dir='./test/cool/',
			file_pattern='^.*[.]bminor'
		)

	if filename: tokenize(filename)
