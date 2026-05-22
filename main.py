import sys
import pickle # Para poder guardar la representación intermedia y poder hacer pruebas en el optimizador
from lexer import Lexer
from parser import Parser
from rich import print
from rich.pretty import pprint
from visualizers import ASTVisualizer
from visualizers import graphviz_ast
from checker import Checker
from ircode_starter import IRCodeGen
from irinterp import IRInterpreter, IRRuntimeError
from errors import *
from iroptimizer import IROptimizer, parse_opt_level

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

def detectErrors(ast):
    if not errors_detected():
        print("\n[green]Parser check: SUCCESS[/green]")
    else:
        print("\n[red]Parser check: FAILED[/red]")

    if ast is None: #Con lo que hay abajo, ¿Esto es necesario?
        print("No se generó AST debido a problemas de sintaxis")
        sys.exit(1)
    
def generateAST(ast):
    print("\nAST generado:\n")
    tree = ASTVisualizer.ast_to_tree(ast)
    print(tree)

    dot = graphviz_ast.build_graphviz(ast)
    dot.render("AST graphviz/ast", format="png", view=True)

# Borré el código comentado de aquí ya que era inútil

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

    try:
        ir = IRCodeGen.generate(ast)
    except Exception as e:
        print(f"\n[red]Error de IR:[/red] {e}")
        sys.exit(1)

    opt_level = 0
    if len(sys.argv) >= 3: #Para poder ejecutar la optimización O1 se requiere poner un -O1 al final
        #Es decir python main.py test/test0.bminor -O1 por ejemplo
        try:
            opt_level = parse_opt_level(sys.argv[2])
        except Exception:
            try:
                opt_level = int(sys.argv[2])
            except Exception:
                opt_level = 0

    if opt_level >= 1:
        ir = IROptimizer.optimize(ir, level=opt_level)

    with open("test/IR/IRToOptimize.pickle", "wb") as f:
        pickle.dump(ir, f)

    print(ir.format())

    if ir.has_function("main"):
        main_fn = next((fn for fn in ir.functions if fn.name == "main"), None)
        if main_fn is not None and len(main_fn.params) == 0:
            interp = IRInterpreter(ir, trace=True)
            try:
                interp.run("main")
            except IRRuntimeError as e:
                print(f"\n[red]Error de ejecución:[/red] {e}")
                sys.exit(1)
        else:
            print("\n[yellow]La función 'main' existe pero no es de cero parámetros. La representación intermedia se generó correctamente.[/yellow]")
    else:
        print("\n[yellow]No se encontró función 'main'. La representación intermedia se generó correctamente, pero no se puede ejecutar.[/yellow]")
    
    if has_errors(stage="IR") or ast is None:
        print("\n[red]IR: FAILED[/red].")
        sys.exit(1)

if __name__ == '__main__':
    main()