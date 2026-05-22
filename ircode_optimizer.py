import pickle
from rich.table import Table
from rich.console import Console
from ircode_starter import Instruction, IRFunction, IRProgram

def makeNewInst(origInst: Instruction, changes: list[tuple[str, int]]) -> Instruction: # changes se organiza como (cambio, índice)
    newInst = list(origInst)
    for change in changes:
        newInst[change[1]] = change[0]
    return tuple(newInst)

def eitherIsFloat(x, y) -> bool:
    return isinstance(x, float) or isinstance(y, float)

class IROptimizer:
    def __init__(self, priority: int):
        self.priority: int = priority
        self.const: dict = {}
        self.alias: dict = {}

    def traverseIR(self, IR: IRProgram) -> tuple[IRProgram, dict, dict]:
        # PLAN    
        # 1. Por cada función, preparar la nueva lista de instrucciones
        # 2. Cada optimización debe eliminar las instrucciones que se están optimizando
        # y añadir las instrucciones optimizadas a la lista de nuevas instrucciones
        # 3. Asignar la nueva lista de instrucciones a la función
        # 4. Una vez terminado eso, añadir la función a la nueva lista de funciones 
        # 5. Una vez terminado eso, añadir la nueva lista de funciones al programa
        # 6. Retornar el programa optimizado

        # Para tratar la lista de instrucciones como una pila, se invierte y se usa pop u append

        # Guardo todas las constantes para que la optimización sea directa
        self.const["R0"] = 0
        newInstList: list[IRFunction] = [] # Aquí se almacenan las nuevas listas de instrucciones
        for g in IR.globals:
            newG = self.handleInst(g)
            newInstList.append(newG)
        IR.globals = newInstList
        print(self.const)

        newFuncList: list[IRFunction] = []
        MOVs: set[str] = {"MOVI", "MOVF", "MOVB", 'MOVS'}

        for f in IR.functions: # Por cada función en IR
            funcConst: list[str] = []
            newInstList = []

            # Iterar por las instrucciones
            for inst in f.instructions:# Por cada instrucción en la función
                newInst = self.handleInst(inst)
                newInstList.append(newInst)
                # if newInst[0] in MOVs: funcConst.append(newInst[2]) # Esto necesita un arreglo porque no considera algunas cosas, ´por eso está desactivado

            # añadir las instrucciones procesadas a la nueva lista
            f.instructions = newInstList
            newFuncList.append(f)

            # Eliminar las constantes de cada función para que no se trasladen a las demás funciones
            # for r in funcConst: # r de registro
            #     if r in self.const.keys(): self.const.pop(r)

        IR.functions = newFuncList
        return IR, self.const, self.alias

    def handleInst(self, inst: Instruction) -> Instruction:
        '''
        Se encarga de tomar la instrucción actual, extraerle información, y decidir si requiere optimización o no
        '''

        # Aplicar cambios de alias de ser necesario
        newInst: list = list(inst)
        for i in range(len(inst[1:])):
            if inst[i] in self.alias.keys():
                newInst[i] = self.alias[inst[i]]
        inst = tuple(newInst)

        needsHandling: bool = True
        while needsHandling: # Un ciclo porque tras convertir una instrucción a otra, puede resultar en una instrucción aún más optimizable y el ciclo hace esas optimizaciones extra
            needsHandling = False
            # Extracción de datos a const y alias
            if inst[0] in {"MOVI", "MOVF"}:
                if inst[1] == 0: self.alias[inst[2]] = "R0"
                else: self.const[inst[2]] = inst[1]
            elif inst[0] in {"MOVB", 'MOVS'}: self.const[inst[2]] = inst[1]
            elif inst[0] in {"STORE", "STOREI", "STOREF", "STOREB", "STORES", "STOREV"}: self.const[inst[2]] = self.const[inst[1]]
            elif inst[0] == "STOREA":
                if isinstance(inst[3], int): self.const[inst[2] + str(inst[3])] = self.const[inst[1]]
                else: self.const[inst[2] + str(self.const[inst[3]])] = self.const[inst[1]]
            elif inst[0] in {"LOAD", "LOADI", "LOADF", "LOADB", "LOADS", "LOADV"}: self.const[inst[2]] = self.const[inst[1]]
            elif inst[0] == "LOADA":
                if isinstance(inst[3], int): self.const[inst[1]] = self.const[inst[2] + str(inst[3])]
                else: self.const[inst[1]] = self.const[inst[2] + str(self.const[inst[3]])]
            
            # Constant folding
            elif self.needsConstantFolding(inst):
                instType: str = ''
                res: int | float | float = 0
                arithOps = {'ADD', 'SUB','MUL','DIV','REM'}
                if inst[0] in arithOps:
                    instType = 'MOVF' if eitherIsFloat(self.const.inst[1], self.const.inst[2]) else 'MOVI'
                    match inst[0]:
                        case 'ADD': res = self.const.inst[1] + self.const.inst[2]
                        case 'SUB': res = self.const.inst[1] - self.const.inst[2]
                        case 'MUL': res = self.const.inst[1] * self.const.inst[2]
                        case 'DIV': res = self.const.inst[1] / self.const.inst[2] if instType == 'MOVF' else self.const.inst[1] // self.const.inst[2]
                        case 'REM': res = self.const.inst[1] % self.const.inst[2]
                else:
                    instType = 'MOVB'
                    if inst[0] == "CMP":
                        match inst[1]:
                            case '<': res = self.const.inst[2] < self.const.inst[3]
                            case '<=': res = self.const.inst[2] <= self.const.inst[3]
                            case '>': res = self.const.inst[2] > self.const.inst[3]
                            case '>=': res = self.const.inst[2] >= self.const.inst[3]
                            case '==': res = self.const.inst[2] == self.const.inst[3]
                            case '!=': res = self.const.inst[2] != self.const.inst[3]
                    else: res = (self.const.inst[1] and self.const.inst[2]) if inst[0] == 'AND' else (self.const.inst[1] or self.const.inst[2])
                    res = int(res)
                inst = (instType, res, inst[-1])
                needsHandling = True # Para chequear por más optimizaciones posibles
            
            # Algebraic simplification
            elif self.needsAlgebraicSimplification(inst):
                pass

        return inst

    # Métodos de apoyo
    def needsConstantFolding(self, inst: Instruction) -> bool:
        validOps: set[str] = {'ADD', 'SUB', 'MUL', 'DIV', 'REM', 'CMP', 'AND', 'OR'}
        if inst[0] in validOps:
            if inst[0] != "CMP": return self.areInConst(inst[1], inst[2])
            else: return self.areInConst(inst[2], inst[3])
    
    def needsAlgebraicSimplification(self, inst: Instruction) -> bool:
        validOps: set[str] = {"ADD", "SUB", "MUL", "DIV", "REM"}
        res: bool = False
        if inst[0] in validOps:
            if self.eitherIsInConst(self.const[inst[1]], self.const[inst[2]]):
                match inst[0]:
                    case "ADD": res = self.const.inst[1] == 0 or self.const.inst[2] == 0
                    case "SUB": res = self.const.inst[2] == 0
                    case "MUL": res = self.const.inst[1] == 1 or self.const.inst[2] == 1
                    case "DIV": res = self.const.inst[2] == 1
                    case "REM": res = self.const.inst[2] % 1 == 0
        # Es posible añadir simplificación para and y or, pero no es un requisito, tons no lo añado (aún)
        return res
    

    # def needsAliasPropagation(instruction: Instruction, alias: dict):
    #     if instruction[0] == "PRINT":
    #         if instruction[1] in alias.keys():
    #             pass # TODO
    
    # # 6
    # def needsDeadTemporaryElimination(instruction: Instruction):
    #     pass
    
    def areInConst(self, x: str, y: str) -> bool:
        return x in self.const.keys() and y in self.const.keys()
    
    def eitherIsInConst(self, x: str, y: str) -> bool:
        return x in self.const.keys() or y in self.const.keys()

if __name__ == "__main__":
    IROptimizerTest: IROptimizer = IROptimizer(1)
    with open("test/IR/IRToOptimize.pickle", "rb") as f:
        IRCode: IRProgram = pickle.load(f)
    
    # Prueba de guardado correcto del archivo - Hecho
    print(IRCode.format())

    comparativeTable: Table = Table(title="comparative table")



    IRCodeOptimized, consts, aliases = IROptimizerTest.traverseIR(IRCode)
    print(IRCodeOptimized.format())
    print("")
    print(consts)
    print("")
    print(aliases)