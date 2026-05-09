import sys
from lexer import Lexer
from parser import Parser
from rich import print
from rich.pretty import pprint
from visualizers import ASTVisualizer
from visualizers import graphviz_ast
from checker import Checker
from ircode_starter import IRCodeGen
from irinterp import IRInterpreter
from errors import errors_detected
# from ircode_starter import IRCodeGen

def verifyLenghtFiles() -> str:
    if len(sys.argv) < 2:
        print("Uso: python parser.py archivo.bminor")
        sys.exit(1)
    #Filename es el directorio que busca del testeo, test/good0.bminor por ejemplo
    filename = sys.argv[1]
    with open(filename, "r", encoding="utf-8") as f:
        text = f.read()
    return text

def detectErrors():
    if not errors_detected():
        print("\n[green]Parser check: SUCCESS[/green]")
    else:
        print("\n[red]Parser check: FAILED[/red]")

    if ast is None: #Con lo que hay abajo, ¿Esto es necesario?
        print("No se generó AST debido a problemas de sintaxis")
        sys.exit(1)
    
def generateAST():
    print("\nAST generado:\n")
    tree = ASTVisualizer.ast_to_tree(ast)
    print(tree)

    dot = graphviz_ast.build_graphviz(ast)
    dot.render("AST graphviz/ast", format="png", view=True)

#----------------------------------
# Ejecutar main.py
#----------------------------------

text = verifyLenghtFiles()

lexer = Lexer()
parser = Parser()

ast = parser.parse(lexer.tokenize(text))

#Este manejador de errores solo será temporal
detectErrors()

#-----------No borrar esto-------------
# generateAST()
#---------------------------------------

checker = Checker()

checker.check(ast)

if errors_detected():
    print("\n[red]Semantic check: FAILED[/red]")
    sys.exit(1)

ir = IRCodeGen.generate(ast)
print(ir.format())

interp = IRInterpreter(ir, trace=True)
interp.run("main")