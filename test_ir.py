from lexer import Lexer
from parser import Parser
from checker import Checker
from ircode_starter import IRCodeGen
from irinterp import IRInterpreter

code = """
main : function void () = {
    a : integer = 2;
    b : integer = 3;
    c : integer = 0;
    
    c = a + b;
    print c;
    
    if (c > 4) {
        print 100;
    } else {
        print 200;
    }
    
    while (a < 10) {
        a = a + 1;
        print a;
    }
}
"""

lexer = Lexer()
parser = Parser()

ast = parser.parse(lexer.tokenize(code))

checker = Checker()
checker.check(ast)

ir = IRCodeGen.generate(ast)
print(ir.format())

interp = IRInterpreter(ir, trace=True)
interp.run("main")