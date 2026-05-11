from pathlib import Path
from lexer import Lexer
from parser import Parser

text = Path('test/Semantico/bad/bad7.bminor').read_text(encoding='utf-8')
ast = Parser().parse(Lexer().tokenize(text))
access = ast.decls[1].body[0].value
print(access)
print(access.__dict__)
print(type(access.index_list))
print(access.index_list)
