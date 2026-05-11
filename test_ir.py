from lexer import Lexer
from parser import Parser
from checker import Checker
from ircode_starter import IRCodeGen
from irinterp import IRInterpreter

# code = """
# main : function void () = {
#     a : integer = 2;
#     b : integer = 3;
#     c : integer = 0;
    
#     c = a + b;
#     print c;
    
#     if (c > 4) {
#         print 100;
#     } else {
#         print 200;
#     }
    
#     while (a < 10) {
#         a = a + 1;
#         print a;
#     }
# }
# """

code = """
is_prime: function boolean (n: integer) = {
    i: integer;
    
    if (n <= 1) {
    	return false;
    }
    if (n == 2) {
    	return true;
    }
    if (n % 2 == 0) {
    	return false; 
    }
    for(i = 3; i*i <= n; i += 2) {
    	if (n % i == 0) {
    		return false;
    	}
    }
    return true;
}

main: function integer () = {
    n: integer = 2;
    limit: integer = 100;
    count: integer = 0;
    sum: integer = 0;

    print "Primos hasta: ";
    print limit;
    print "----------------";

    while (n <= limit) {
        if (is_prime(n)) {
            print n;
            count = count + 1;
            sum = sum + n;
        } 

        n = n + 1;
    }

    print "----------------";
    print "Cantidad de primos:";
    print count;

    print "Suma de primos:";
    print sum;

    return 0;
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
#Este es el que se encarga de llamar la función main
interp.run("main")