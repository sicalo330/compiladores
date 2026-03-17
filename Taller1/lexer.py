# lexer.py
import sly
from rich import print

class Lexer(sly.Lexer):
    tokens = {
        #Palabras reservadas
        ARRAY,
        BOOLEAN,
        CHAR,
        ELSE,
        FALSE,
        FLOAT,
        FOR,
        FUNCTION,
        IF,
        INTEGER,
        PRINT,
        STRING,
        TRUE,
        VOID,
        WHILE,
        CLASS,
        THIS,
        SUPER,
        NEW,
        RETURN,

        #Operadores de relación

        LT, LE, GT, GE, EQ, NE, LAND, LOR,

        #Operadores de asignación

        ADDEQ, SUBEQ, MULEQ, DIVEQ, MODEQ, INC, DEC,

        #Identificadores y literales
        ID, LITERAL_INTEGER, LITERAL_FLOAT, LITERAL_CHAR, LITERAL_STRING, QUESTION, COLON,
    }

    literals = '+-*/%^=;,.:(){}[]'

    ignore = ' \t\r\n'

    ignore_comment = r'/\*(.|\n)*?\*/'
    ignore_cppcomment = r'//.*\n'

    QUESTION = r'\?'
    COLON = r':'

    INC = r'\+\+'
    DEC = r'--'
    ADDEQ = r'\+='
    SUBEQ = r'-='
    MULEQ = r'\*='
    DIVEQ = r'/='
    MODEQ = r'%='

    #Expresiones regulares para tokens

    ID = r'[a-zA-Z_][a-zA-Z0-9_]*'

    #Palabras reservadas
    ID['array'] = ARRAY
    ID['boolean'] = BOOLEAN
    ID['super'] = SUPER
    ID['class'] = CLASS
    ID['function'] = FUNCTION
    ID['void'] = VOID
    ID['string'] = STRING
    ID['integer'] = INTEGER
    ID['true'] = TRUE
    ID['false'] = FALSE
    ID['print'] = PRINT
    ID['while'] = WHILE
    ID['new'] = NEW
    ID['return'] = RETURN
    ID['if'] = IF
    ID['else'] = ELSE
    ID['for'] = FOR

    #Operadores
    LE = r'<='
    LT = r'<'
    GE = r'>='
    GT = r'>'
    EQ = r'=='
    NE = r'!='
    LAND = r'&&'
    LOR = r'\|\|'

    LITERAL_INTEGER = r'\d+'

    def error(self, t):
        print(f"{self.lineno}: Caracter ilegal '{t.value[0]}'")
        self.index += 1

def tokenize(txt):
    lex = Lexer()

    tokens = []
    #Solo muestra los tokens, no los literales
    for tok in lex.tokenize(txt):
        tokens.append((tok.type,tok.value, tok.lineno))
    print(tokens)

if __name__ == '__main__':
    import sys

    if len(sys.argv) != 2:
        print(f'usage: python lexer.py <filename>')
        raise SyntaxError
    
    txt = open(sys.argv[1], encoding='utf-8').read()
    tokenize(txt)
