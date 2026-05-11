from pathlib import Path
from lexer import Lexer
from parser import Parser
from ircode_starter import IRCodeGen
from irinterp import IRInterpreter

text = Path('additions/IR/test4.txt').read_text(encoding='utf-8')
ast = Parser().parse(Lexer().tokenize(text))
ir = IRCodeGen.generate(ast)
interp = IRInterpreter(ir, trace=False)
frame = interp._make_frame(ir.functions[0], [])
print('instructions', frame.instructions)
print('start')
while frame.pc < len(frame.instructions):
    inst = frame.instructions[frame.pc]
    print('pc', frame.pc, inst)
    jumped = interp._dispatch(frame, inst)
    print('jumped', jumped, 'stack', frame.stack, 'locals', frame.locals, 'globals', interp.globals)
    if not jumped:
        frame.pc += 1
print('done')
