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
from errors import *
# from ircode_starter import IRCodeGen

def load_file():
    if len(sys.argv) < 2:
        print("[bold red]Uso:[/bold red] python main.py <archivo.bminor>")
        sys.exit(1)
    
    filename = sys.argv[1]
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"[bold red]Error:[/bold red] El archivo '{filename}' no existe.")
        sys.exit(1)

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
#Al parecer esto es bueno porque a la larga se genera mucha basura
# clearErrors()

# text = verifyLenghtFiles()

# lexer = Lexer()
# parser = Parser()

# ast = parser.parse(lexer.tokenize(text))

#Este manejador de errores solo será temporal
# detectErrors()

#-----------No borrar esto-------------
# generateAST()
#---------------------------------------

# checker = Checker()

# checker.check(ast)

# if errors_detected():
#     print("\n[red]Semantic check: FAILED[/red]")
#     sys.exit(1)

# ir = IRCodeGen.generate(ast)
# print(ir.format())

# interp = IRInterpreter(ir, trace=True)
# interp.run("main")

def main():
    clearErrors() # Asegúrate que esta función limpie _errors_detected y la lista
    text = load_file()
    
    lexer = Lexer()
    parser = Parser()

    tokens = list(lexer.tokenize(text))
    if has_errors(stage="LEXER"):
        print("\n[red]Lexical check: FAILED[/red]. Abortando...")
        sys.exit(1)
    
    ast = parser.parse(iter(tokens))

    if has_errors(stage="PARSER") or ast is None:
        print("\n[red]Parser check: FAILED[/red].")
        sys.exit(1)
    
    print("\n[green]Parser check: SUCCESS[/green]")
    
    checker = Checker()
    checker.check(ast)

    if has_errors(stage="CHECKER") or ast is None:
        print("\n[red]Checker: FAILED[/red].")
        sys.exit(1)

    print("\n[green]Checker: SUCCESS[/green]")

    # ir = IRCodeGen.generate(ast)
    # print(ir.format())

    # interp = IRInterpreter(ir, trace=True)
    # interp.run("main")
    

if __name__ == '__main__':
    main()