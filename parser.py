import logging
import sly

from lexer import Lexer
from errors import error
from model import *

#Esto agrega número de línea a cada nodo del AST, sierve para errores semánticos y debug
def _L(node, lineno):
    node.lineno = lineno if lineno else 0
    return node

#Aquí se define la gramática del parser.py
class Parser(sly.Parser):
    #Los tokens se declaran aquí usando la variable tokens de la clase lexer en lexer.py
    tokens = Lexer.tokens
    start = 'prog'

    #Esto muestra los errores
    log = logging.getLogger()
    log.setLevel(logging.ERROR)

    expected_shift_reduce = 1

    #Esto va a generar un archivo grammar.txt
    debugfile = "additions/grammarAST.txt"

    #PROGRAMA
    @_("opt_decl_list")
    def prog(self, p):
        lineno = p.opt_decl_list[0].lineno if p.opt_decl_list else 0
        node = Program(p.opt_decl_list)
        node.lineno = lineno
        return node

#LISTAS DE DECLARACIONES
    @_('')
    def opt_decl_list(self, p):
        return []

    @_('decl_list')
    def opt_decl_list(self, p):
        return p.decl_list
    
    @_('decl')
    def decl_list(self, p):
        return [p.decl]

    @_('decl decl_list')
    def decl_list(self, p):
        return [p.decl] + p.decl_list

# DECLARACIONES
    @_('ID ":" type_simple ";"')
    def decl(self, p):
        return _L(VarDecl(p.ID, p.type_simple, None), p.lineno)

    @_('ID ":" type_array_sized ";"')
    def decl(self, p):
        return _L(ArrayDecl(p.ID, p.type_array_sized, None), p.lineno)

    @_('ID ":" type_func ";"')
    def decl(self, p):
        return _L(FuncDecl(p.ID, p.type_func, None), p.lineno)

    @_('decl_init')
    def decl(self, p):
        return p.decl_init

    @_('ID ":" type_simple "=" expr ";"')
    def decl_init(self, p):
        return _L(VarDecl(p.ID, p.type_simple, p.expr), p.lineno)

    @_("ID ':' type_array_sized '=' '{' opt_expr_list '}' ';'")
    def decl_init(self, p):
        return _L(ArrayDecl(p.ID, p.type_array_sized, p.opt_expr_list), p.lineno)

    @_('ID ":" type_func "=" "{" opt_stmt_list "}"')
    def decl_init(self, p):
        return _L(FuncDecl(p.ID, p.type_func, p.opt_stmt_list), p.lineno)

    @_("ID ':' CLASS '=' '{' opt_decl_list '}'")
    def class_decl(self, p):
        return _L(ClassDecl(p.ID, None, p.decl_list), p.lineno)
    
    @_("ID ':' CLASS EXTENDS ID '=' '{' opt_decl_list '}'")
    def class_decl(self, p):
        return _L(ClassDecl(p[0], p[4], p.decl_list), p.lineno)

# SENTENCIAS
    @_('')
    def opt_stmt_list(self, p):
        return []

    @_('stmt_list')
    def opt_stmt_list(self, p):
        return p.stmt_list

    @_('stmt')
    def stmt_list(self, p):
        return [p.stmt]

    @_('stmt stmt_list') 
    def stmt_list(self, p):
        return [p.stmt] + p.stmt_list

    @_('open_stmt',
       'closed_stmt')
    def stmt(self, p):
        return p[0]

    @_('if_stmt_closed',
       'for_stmt_closed',
       'while_stmt_closed',
       'simple_stmt')
    def closed_stmt(self, p):
        return p[0]

    @_('if_stmt_open',
       'for_stmt_open',
       'while_stmt_open')
    def open_stmt(self, p):
        return p[0]

# IF
    @_('IF "(" expr ")"')
    def if_cond(self, p):
        return p.expr

    @_('if_cond closed_stmt ELSE closed_stmt')
    def if_stmt_closed(self, p):
        return _L(IfStmt(p.if_cond, p.closed_stmt0, p.closed_stmt1), p.lineno)

    @_('if_cond stmt')
    def if_stmt_open(self, p):
        return _L(IfStmt(p.if_cond, p.stmt, None), p.lineno)

    @_('if_cond closed_stmt ELSE if_stmt_open')
    def if_stmt_open(self, p):
        return _L(IfStmt(p.if_cond, p.closed_stmt, p.if_stmt_open), p.lineno)

# FOR
    @_('FOR "(" opt_expr ";" opt_expr ";" opt_expr ")"')
    def for_header(self, p):
        return (p.opt_expr0, p.opt_expr1, p.opt_expr2)

    @_('for_header open_stmt')
    def for_stmt_open(self, p):
        return _L(
            ForStmt(
                p.for_header[0],
                p.for_header[1],
                p.for_header[2],
                p.open_stmt
            ),
            p.lineno
        )

    @_('for_header closed_stmt')
    def for_stmt_closed(self, p):
        return _L(
            ForStmt(
                p.for_header[0],
                p.for_header[1],
                p.for_header[2],
                p.closed_stmt
            ),
            p.lineno
        )

# WHILE
    @_('WHILE "(" expr ")" open_stmt')
    def while_stmt_open(self, p):
        return _L(
            WhileStmt(
                p.expr,
                p.open_stmt
            ),
            p.lineno
        )

    @_('WHILE "(" expr ")" closed_stmt')
    def while_stmt_closed(self, p):
        return _L(
            WhileStmt(
                p.expr,
                p.closed_stmt
            ),
            p.lineno
        )

# SENTENCIAS SIMPLES
    @_('print_stmt',
       'return_stmt',
       'block_stmt',
       'BREAK',
       'CONTINUE')
    def simple_stmt(self, p):
        return p[0]

    @_('decl')
    def simple_stmt(self, p):
        return p.decl

    @_('expr ";"')
    def simple_stmt(self, p):
        return _L(ExprStmt(p.expr), p.lineno)

    @_('PRINT opt_expr_list ";"')
    def print_stmt(self, p):
        return _L(PrintStmt(p.opt_expr_list), p.lineno)

    @_('RETURN opt_expr ";"')
    def return_stmt(self, p):
        return _L(ReturnStmt(p.opt_expr), p.lineno)

    @_('"{" opt_stmt_list "}"')
    def block_stmt(self, p):
        return _L(BlockStmt(p.opt_stmt_list), p.lineno)

# EXPRESIONES
    @_('')
    def opt_expr_list(self, p):
        return []

    @_('expr_list')
    def opt_expr_list(self, p):
        return p.expr_list

    @_('expr')
    def expr_list(self, p):
        return [p.expr]

    @_('expr_list "," expr')
    def expr_list(self, p):
        return p.expr_list + [p.expr]
    
    @_('')
    def opt_expr(self, p):
        return None

    @_('expr')
    def opt_expr(self, p):
        return p.expr

    @_('lval assign_op expr',
       'CONSTANT lval assign_op expr')
    def expr(self, p):
        if p[1][0] == '=':
            return _L(AssignExpr(p.lval, p.expr), p.lineno)
        else:
            return _L(AssignExpr(p.lval,BinOp(p[1][0], p.lval, p.expr)),p.lineno)

    @_('expr2')
    def expr(self, p):
        return p.expr2

    @_('"="',
       'ADDEQ',
       'SUBEQ',
       'MULEQ',
       'DIVEQ',
       'MODEQ')
    def assign_op(self, p):
        return p[0]

# LVALUES
    @_('ID')
    def lval(self, p):
        return _L(Location(p.ID), p.lineno)

    @_('ID index_list')
    def lval(self, p):
        return _L(ArrayAccess(p.ID, p.index_list), p.lineno)
    
    @_('index index_list')
    def index_list(self, p):
        return p.index_list + [p.index]
    
    @_('index')
    def index_list(self, p):
        return [p.index]

    @_('"[" expr "]"')
    def index(self, p):
        return p.expr

# PRECEDENCIA OPERADORES
    @_('expr2 LOR expr3')
    def expr2(self, p):
        return _L(BinOp("||", p.expr2, p.expr3), p.lineno)

    @_('expr3')
    def expr2(self, p):
        return p.expr3

    @_('expr3 LAND expr4')
    def expr3(self, p):
        return _L(BinOp("&&", p.expr3, p.expr4), p.lineno)

    @_('expr4')
    def expr3(self, p):
        return p.expr4

    @_('expr4 comp_op expr5')
    def expr4(self, p):
        return _L(BinOp(p.comp_op, p.expr4, p.expr5), p.lineno)
    
    @_('EQ',
       'NE',
       'LT',
       'LE',
       'GT',
       'GE')
    def comp_op(self, p):
        return p[0]

    @_('expr5')
    def expr4(self, p):
        return p.expr5

    @_('expr5 "+" expr6',
        'expr5 "-" expr6')
    def expr5(self, p):
        return _L(BinOp(p[1], p.expr5, p.expr6), p.lineno)

    @_('expr6')
    def expr5(self, p):
        return p.expr6

    @_('expr6 "*" expr7',
        'expr6 "/" expr7',
        'expr6 "%" expr7')
    def expr6(self, p):
        return _L(BinOp(p[1], p.expr6, p.expr7), p.lineno)

    @_('expr7')
    def expr6(self, p):
        return p.expr7

    @_('expr7 "^" expr8')
    def expr7(self, p):
        return _L(BinOp("^", p.expr7, p.expr8), p.lineno)

    @_('expr8')
    def expr7(self, p):
        return p.expr8

    @_('"-" expr8',
       '"!" expr8')
    def expr8(self, p):
        return _L(UnaryOp(p[0], p.expr8), p.lineno)

    @_('expr9')
    def expr8(self, p):
        return p.expr9
    
    @_('expr "?" expr ":" expr')
    def expr9(self, p):
        return _L(TernOp(p.expr0, p.expr1, p.expr2))
    
    @_('ID index')
    def expr9(self, p):
        return _L(ArrayAccess(p.ID, p.index), p.lineno)
    
    @_('incdec_expr')
    def expr9(self, p):
        return p.incdec_expr

    @_('ID incdec_op',
       'incdec_op ID')
    def incdec_expr(self, p):
        return _L(AffixOp(p.incdec_op, p.ID), p.lineno)

    @_('INC',
       'DEC')
    def incdec_op(self, p):
        return p[0]

    @_('ID "." ID')
    def expr9(self, p):
        return _L(AttrAccess(p.ID0, p.ID1), p.lineno)

    @_('ID "." func_call')
    def expr9(self, p):
        return _L(AttrAccess(
            p.ID,
            FuncCall(
                p.func_call.ID,
                p.func_call.opt_expr_list
                )
            ),
            p.lineno
        )

    @_('ID "(" opt_expr_list ")"')
    def func_call(self, p):
        return _L(FuncCall(p.ID, p.opt_expr_list), p.lineno)
    
    @_('group')
    def expr9(self, p):
        return p.group

# GRUPOS
    @_('"(" expr ")"')
    def group(self, p):
        return p.expr

    @_('func_call',
       'NEW func_call')
    def group(self, p):
        return p.func_call

    @_('factor')
    def group(self, p):
        return p.factor

# FACTORES
    @_('ID')
    def factor(self, p):
        return _L(Location(p.ID), p.lineno)

    @_('INTEGER_LITERAL')
    def factor(self, p):
        return _L(Literal(p.INTEGER_LITERAL, "integer"), p.lineno)

    @_('FLOAT_LITERAL')
    def factor(self, p):
        return _L(Literal(p.FLOAT_LITERAL, "float"), p.lineno)

    @_('CHAR_LITERAL')
    def factor(self, p):
        return _L(Literal(p.CHAR_LITERAL, "char"), p.lineno)

    @_('STRING_LITERAL')
    def factor(self, p):
        return _L(Literal(p.STRING_LITERAL, "string"), p.lineno)

    @_('TRUE')
    def factor(self, p):
        return _L(Literal(True, "boolean"), p.lineno)

    @_('FALSE')
    def factor(self, p):
        return _L(Literal(False, "boolean"), p.lineno)

# TIPOS
    @_('INTEGER',
        'FLOAT',
        'BOOLEAN',
        'CHAR',
        'STRING',
        'ID',
        'VOID')
    def type_simple(self, p):
        return _L(SimpleType(p[0].lower()), p.lineno)
    
    @_('ARRAY "[" "]" type_simple',
       'ARRAY "[" "]" type_array')
    def type_array(self, p):
        return _L(ArrayType(p[3]), p.lineno)

    @_('ARRAY index_list type_simple',
       'ARRAY index_list type_array_sized')
    def type_array_sized(self, p):
        return _L(ArraySizedType(p.index_list, p[2]), p.lineno)

    @_('FUNCTION type_simple "(" opt_param_list ")"',
       'FUNCTION type_array_sized "(" opt_param_list ")"')
    def type_func(self, p):
        return _L(FuncType(p[1], p.opt_param_list), p.lineno)

# PARAMETROS
    @_('')
    def opt_param_list(self, p):
        return []

    @_('param_list')
    def opt_param_list(self, p):
        return p.param_list

    @_('param')
    def param_list(self, p):
        return [p.param]

    @_('param "," param_list')
    def param_list(self, p):
        return p.param_list + [p.param]

    @_('ID ":" type_simple',
        'ID ":" type_array_sized',
        'ID ":" type_array')
    def param(self, p):
        return _L(Param(p.ID, p[2]), p.lineno)

# ERROR
    @_('stmt_list error ";"')
    def stmt_list(self, p):
        # Esto permite que el parser ignore una sentencia mal formada y siga con la siguiente
        print(f"Error de sintaxis en línea {p.lineno}: saltando hasta el próximo ';' para continuar.")
        return p.stmt_list

    def error(self, p): # Esto hay que mejorarlo mucho
        if p:
            error(f"Error de sintaxis cerca de '{p.value}'", p.lineno)
        else:
            error("Error de sintaxis al final del archivo", "EOF")

# if __name__ == "__main__":
#     import sys
#     from lexer import Lexer

#     if len(sys.argv) < 2:
#         print("Uso: python parser.py archivo.bminor")
#         sys.exit(1)
#     #Filename es el directorio que busca del testeo, test/good0.bminor por ejemplo
#     filename = sys.argv[1]

#     with open(filename, "r", encoding="utf-8") as f:
#         text = f.read()

#     lexer = Lexer()
#     parser = Parser()

#     ast = parser.parse(lexer.tokenize(text))

#     if ast is None:
#         print("No se generó AST debido a problemas de sintaxis")
#         sys.exit(1)

#     print("\nAST generado:\n")
    
#     from rich import print
#     from rich.pretty import pprint
#     from visualizers import ASTVisualizer
#     from visualizers import graphviz_ast

#     tree = ASTVisualizer.ast_to_tree(ast)
#     print(tree)

#     dot = graphviz_ast.build_graphviz(ast)
#     dot.render("AST graphviz/ast", format="png", view=True)

#     from checker import Checker

#     checker = Checker()
#     checker.check(ast)