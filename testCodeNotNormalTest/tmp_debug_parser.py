from pathlib import Path
from lexer import Lexer
from parser import Parser

text = Path('test/Semantico/bad/bad7.bminor').read_text(encoding='utf-8')
lexer = Lexer()
parser = Parser()
ast = parser.parse(lexer.tokenize(text))
print(type(ast))
for i,decl in enumerate(ast.decls, start=1):
    print('decl', i, type(decl), decl)
    if hasattr(decl, 'body') and decl.name == 'find_max':
        for j, stmt in enumerate(decl.body, start=1):
            print('  stmt', j, type(stmt), stmt)
            if isinstance(stmt, type(decl.body[0])) and hasattr(stmt, 'value'):
                print('    value', stmt.value, type(stmt.value), getattr(stmt.value, '__dict__', None))
                if isinstance(stmt.value, object):
                    print('    raw', repr(stmt.value))
            if hasattr(stmt, 'expr') and hasattr(stmt.expr, 'lval'):
                print('    expr', stmt.expr, type(stmt.expr), getattr(stmt.expr.lval, 'index_list', None), type(getattr(stmt.expr.lval, 'index_list', None)))
print('Done')
