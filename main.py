import sys
from lexer import Lexer
from parser import Parser
from rich import print
from rich.pretty import pprint
from visualizers import ASTVisualizer
from visualizers import graphviz_ast
from checker import Checker

if len(sys.argv) < 2:
    print("Uso: python parser.py archivo.bminor")
    sys.exit(1)
#Filename es el directorio que busca del testeo, test/good0.bminor por ejemplo
filename = sys.argv[1]

with open(filename, "r", encoding="utf-8") as f:
    text = f.read()

lexer = Lexer()
parser = Parser()

ast = parser.parse(lexer.tokenize(text))

if ast is None:
    print("No se generó AST debido a problemas de sintaxis")
    sys.exit(1)

# print("\nAST generado:\n")

# tree = ASTVisualizer.ast_to_tree(ast)
# print(tree)

# dot = graphviz_ast.build_graphviz(ast)
# dot.render("AST graphviz/ast", format="png", view=True)

checker = Checker()
checker.check(ast)