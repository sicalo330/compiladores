from lexer import Lexer
from parser import Parser
from checker import Checker
from ircode_starter import IRCodeGen
from irinterp import IRInterpreter

with open("additions/testIR.txt", "r", encoding="utf-8") as f:
    code = f.read()

lexer = Lexer()
parser = Parser()

ast = parser.parse(lexer.tokenize(code))

checker = Checker()
checker.check(ast)

ir = IRCodeGen.generate(ast)
print(ir.format())

interp = IRInterpreter(ir, trace=True)
#Este es el que se encarga de llamar la función main
interp.run("main")



#Podemos usar la función main como un label
