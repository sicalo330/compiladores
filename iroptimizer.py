from __future__ import annotations

from typing import Any, Optional

from ircode_starter import IRProgram, IRFunction, Instruction


class IROptimizer:
    def __init__(self, level: int = 0):
        self.level = level

    @classmethod
    def optimize(cls, program: IRProgram, level: int = 0) -> IRProgram:
        return cls(level).visit_program(program)

    def visit_program(self, program: IRProgram) -> IRProgram:
        if self.level <= 0:
            return program

        new_globals = list(program.globals)
        new_functions: list[IRFunction] = []

        # Pre-poblar var_const con los valores globales conocidos
        # para que los LOADI dentro de funciones los puedan resolver
        global_var_const: dict = {}
        global_reg_const: dict = {}
        for inst in program.globals:
            op = inst[0]
            if op in {"MOVI", "MOVF", "MOVB"} and len(inst) == 3:
                global_reg_const[inst[2]] = inst[1]
            elif op in {"STORE", "STOREI", "STOREF"} and len(inst) == 3:
                src, var_name = inst[1], inst[2]
                src_val = global_reg_const.get(src) if isinstance(src, str) and src.startswith("R") else None
                if src_val is not None:
                    global_var_const[var_name] = src_val

        for fn in program.functions:
            new_insts = self.optimize_instruction_list(fn.instructions, initial_var_const=dict(global_var_const))
            new_functions.append(
                IRFunction(
                    name=fn.name,
                    params=list(fn.params),
                    return_type=fn.return_type,
                    instructions=new_insts,
                )
            )

        return IRProgram(globals=new_globals, functions=new_functions)

    def optimize_instruction_list(self, instructions: list[Instruction], initial_var_const: dict = None) -> list[Instruction]:
        insts = list(instructions)

        if self.level >= 1:
            insts = self.constant_fold_and_simplify(insts, initial_var_const=initial_var_const or {})
            insts = self.remove_unreachable(insts)
            insts = self.remove_branch_to_next_label(insts)

        if self.level >= 2:
            insts = self.remove_unused_temp_definitions(insts)

        return insts

    # -------------------------------------------------
    # Nivel O1
    # -------------------------------------------------

    def constant_fold_and_simplify(self, instructions: list[Instruction], initial_var_const: dict = None) -> list[Instruction]:
        const: dict[str, Any] = {}
        var_const: dict[str, Any] = dict(initial_var_const) if initial_var_const else {}
        scope_stack: list[dict] = []  # Para ENTER/EXIT: guarda snapshots del scope
        out: list[Instruction] = []

        for inst in instructions:
            op = inst[0]

            # Al encontrar un LABEL, invalidar const y var_const
            # porque el label puede ser destino de un salto hacia atrás (loop)
            if op == "LABEL":
                const.clear()
                var_const.clear()
                out.append(inst)
                continue

            if op in {"MOVI", "MOVF", "MOVB"} and len(inst) == 3:
                value, dst = inst[1], inst[2]
                const[dst] = value
                out.append(inst)
                continue

            if op in {"LOADI", "LOADF", "LOADB", "LOADS", "LOADV", "LOAD"} and len(inst) == 3:
                var_name, dst = inst[1], inst[2]
                if var_name in var_const:
                    value = var_const[var_name]
                    if isinstance(value, float):
                        mov_op = "MOVF"
                    elif isinstance(value, bool) or op == "LOADB":
                        mov_op = "MOVB"
                    elif isinstance(value, str) or op == "LOADS":
                        mov_op = "MOVS"
                    else:
                        mov_op = "MOVI"
                    out.append((mov_op, value, dst))
                    const[dst] = value
                else:
                    const.pop(dst, None)
                    out.append(inst)
                continue

            if op in {"STORE", "STOREF", "STOREI", "STOREB", "STORES", "STOREV"} and len(inst) == 3:
                src, var_name = inst[1], inst[2]
                src_val = const.get(src) if isinstance(src, str) and src.startswith("R") else (src if not isinstance(src, str) else None)
                if src_val is not None:
                    var_const[var_name] = src_val
                else:
                    var_const.pop(var_name, None)
                out.append(inst)
                continue

            if op in {"ADDI", "SUBI", "MULI", "DIVI", "ADDF", "SUBF", "MULF", "DIVF", "ADD", "SUB", "MUL", "DIV"} and len(inst) == 4:
                a, b, dst = inst[1], inst[2], inst[3]

                a_val = const.get(a) if isinstance(a, str) and a.startswith("R") else (a if not isinstance(a, str) else None)
                b_val = const.get(b) if isinstance(b, str) and b.startswith("R") else (b if not isinstance(b, str) else None)

                folded = False
                if a_val is not None and b_val is not None:
                    if (op.endswith("DIV") or op.endswith("DIVI") or op.endswith("DIVF") or op == "DIV") and b_val == 0:
                        pass
                    else:
                        try:
                            res = self.eval_binop(op, a_val, b_val)
                            mov = "MOVF" if isinstance(res, float) and not isinstance(res, bool) else "MOVI"
                            out.append((mov, res, dst))
                            const[dst] = res
                            folded = True
                        except Exception:
                            folded = False

                if folded:
                    continue

                simplified = False
                if a_val is not None or b_val is not None:
                    if op.startswith("ADD") or op == "ADD":
                        if a_val == 0 and b_val is not None:
                            out.append(("MOVI" if isinstance(b_val, int) else "MOVF", b_val, dst))
                            const[dst] = b_val
                            simplified = True
                        elif b_val == 0 and a_val is not None:
                            out.append(("MOVI" if isinstance(a_val, int) else "MOVF", a_val, dst))
                            const[dst] = a_val
                            simplified = True

                    if not simplified and (op.startswith("SUB") or op == "SUB"):
                        if b_val == 0 and a_val is not None:
                            out.append(("MOVI" if isinstance(a_val, int) else "MOVF", a_val, dst))
                            const[dst] = a_val
                            simplified = True

                    if not simplified and (op.startswith("MUL") or op == "MUL"):
                        if a_val == 1 and b_val is not None:
                            out.append(("MOVI" if isinstance(b_val, int) else "MOVF", b_val, dst))
                            const[dst] = b_val
                            simplified = True
                        elif b_val == 1 and a_val is not None:
                            out.append(("MOVI" if isinstance(a_val, int) else "MOVF", a_val, dst))
                            const[dst] = a_val
                            simplified = True
                        elif a_val == 0:
                            out.append(("MOVI", 0, dst))
                            const[dst] = 0
                            simplified = True
                        elif b_val == 0:
                            out.append(("MOVI", 0, dst))
                            const[dst] = 0
                            simplified = True

                    if not simplified and (op.startswith("DIV") or op == "DIV"):
                        if b_val == 1 and a_val is not None:
                            out.append(("MOVI" if isinstance(a_val, int) else "MOVF", a_val, dst))
                            const[dst] = a_val
                            simplified = True

                if simplified:
                    continue

                const.pop(dst, None)
                out.append(inst)
                continue

            if op in {"CMPI", "CMPF", "CMPB", "CMP"} and len(inst) >= 4:
                # CMPI cmp_oper, a, b, dst  OR CMP cmp_oper, a, b, dst
                if op == "CMP":
                    cmp_oper, a, b, dst = inst[1], inst[2], inst[3], inst[4] if len(inst) >= 5 else (inst[3] if len(inst) == 4 else None)
                else:
                    cmp_oper, a, b, dst = inst[1], inst[2], inst[3], inst[4]

                a_val = const.get(a) if isinstance(a, str) and a.startswith("R") else (a if not isinstance(a, str) else None)
                b_val = const.get(b) if isinstance(b, str) and b.startswith("R") else (b if not isinstance(b, str) else None)

                if a_val is not None and b_val is not None:
                    res = 1 if self.eval_cmp(cmp_oper, a_val, b_val) else 0
                    out.append(("MOVI", res, dst))
                    const[dst] = res
                    continue

                const.pop(dst, None)
                out.append(inst)
                continue

            if op == "CBRANCH" and len(inst) == 4:
                test, true_label, false_label = inst[1], inst[2], inst[3]
                test_val = const.get(test) if isinstance(test, str) and test.startswith("R") else (test if not isinstance(test, str) else None)

                if test_val is not None:
                    if test_val == 1:
                        out.append(("BRANCH", true_label))
                        continue
                    elif test_val == 0:
                        out.append(("BRANCH", false_label))
                        continue

                out.append(inst)
                continue

            # Manejo de scopes: ENTER guarda snapshot, EXIT lo restaura
            if op == "ENTER":
                scope_stack.append((dict(const), dict(var_const)))
                out.append(inst)
                continue

            if op == "EXIT":
                if scope_stack:
                    saved_const, saved_var_const = scope_stack.pop()
                    # Eliminar registros/vars locales que no existían antes del bloque
                    for k in list(const.keys()):
                        if k not in saved_const:
                            del const[k]
                    for k in list(var_const.keys()):
                        if k not in saved_var_const:
                            del var_const[k]
                    # Restaurar valores que el bloque pudo haber pisado
                    const.update(saved_const)
                    var_const.update(saved_var_const)
                out.append(inst)
                continue

            # Instrucciones conservadoras: si definen un registro, quitar su const
            if len(inst) >= 2 and isinstance(inst[-1], str) and inst[-1].startswith("R"):
                const.pop(inst[-1], None)

            out.append(inst)

        return out

    def remove_unreachable(self, instructions: list[Instruction]) -> list[Instruction]:
        out: list[Instruction] = []
        unreachable = False

        for inst in instructions:
            op = inst[0]

            if op == "LABEL":
                unreachable = False
                out.append(inst)
                continue

            if unreachable:
                # drop until next label
                continue

            out.append(inst)

            if op == "BRANCH" or op == "RET":
                unreachable = True

        return out

    def remove_branch_to_next_label(self, instructions: list[Instruction]) -> list[Instruction]:
        out: list[Instruction] = []
        i = 0

        while i < len(instructions):
            inst = instructions[i]
            if inst[0] == "BRANCH" and i + 1 < len(instructions):
                nxt = instructions[i + 1]
                if nxt[0] == "LABEL" and len(inst) >= 2 and inst[1] == nxt[1]:
                    # skip branch
                    i += 1
                    continue

            out.append(inst)
            i += 1

        return out

    # -------------------------------------------------
    # Nivel O2
    # -------------------------------------------------

    def remove_unused_temp_definitions(self, instructions: list[Instruction]) -> list[Instruction]:
        used: set[str] = set()
        result_reversed: list[Instruction] = []

        for inst in reversed(instructions):
            dst = self.defined_temp(inst)
            args = self.used_temps(inst)

            if dst is not None and dst not in used and self.is_pure_definition(inst):
                # instruction is dead, drop it
                continue

            if dst is not None:
                # definition kills previous uses of dst
                if dst in used:
                    used.discard(dst)

            used.update(args)
            result_reversed.append(inst)

        return list(reversed(result_reversed))

    def defined_temp(self, inst: Instruction) -> Optional[str]:
        op = inst[0]

        if op in {"MOVI", "MOVF", "MOVB", "ADDR"} and len(inst) == 3:
            return inst[2] if isinstance(inst[2], str) and inst[2].startswith("R") else None

        if op in {"ADDI", "SUBI", "MULI", "DIVI", "ADDF", "SUBF", "MULF", "DIVF", "AND", "OR", "XOR", "ADD", "SUB", "MUL", "DIV"} and len(inst) == 4:
            return inst[3] if isinstance(inst[3], str) and inst[3].startswith("R") else None

        if op in {"CMPI", "CMPF", "CMPB", "CMP"} and len(inst) >= 4:
            # CMP may have different arity (CMP oper a b dst)
            if op == "CMP":
                return inst[4] if len(inst) >= 5 and isinstance(inst[4], str) and inst[4].startswith("R") else None
            return inst[4] if isinstance(inst[4], str) and inst[4].startswith("R") else None

        if op.startswith("LOAD") and len(inst) >= 3:
            return inst[-1] if isinstance(inst[-1], str) and inst[-1].startswith("R") else None

        return None

    def used_temps(self, inst: Instruction) -> set[str]:
        op = inst[0]

        if op in {"MOVI", "MOVF", "MOVB", "LABEL", "BRANCH", "DATAS", "ADDR", "ENTER", "EXIT"}:
            return set()

        if op.startswith("STORE"):
            return self.temps_in(inst[1:2])

        if op.startswith("PRINT") or op in {"PRINT", "PRINTB", "PRINTS", "PRINTF"}:
            return self.temps_in(inst[1:])

        if op == "CBRANCH":
            return self.temps_in(inst[1:2])

        if op == "RET":
            return self.temps_in(inst[1:])

        if op in {"ADDI", "SUBI", "MULI", "DIVI", "ADDF", "SUBF", "MULF", "DIVF", "AND", "OR", "XOR", "ADD", "SUB", "MUL", "DIV"}:
            return self.temps_in(inst[1:3])

        if op in {"CMPI", "CMPF", "CMPB", "CMP"}:
            if op == "CMP":
                return self.temps_in(inst[2:4]) if len(inst) >= 5 else self.temps_in(inst[1:3])
            return self.temps_in(inst[2:4])

        return self.temps_in(inst[1:])

    def temps_in(self, values) -> set[str]:
        return {x for x in values if isinstance(x, str) and x.startswith("R")}

    def is_pure_definition(self, inst: Instruction) -> bool:
        op = inst[0]
        return (
            op in {
                "MOVI", "MOVF", "MOVB", "ADDR",
                "ADDI", "SUBI", "MULI", "DIVI",
                "ADDF", "SUBF", "MULF", "DIVF",
                "AND", "OR", "XOR",
                "CMPI", "CMPF", "CMPB", "CMP",
            }
            or op.startswith("LOAD")
        )

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    def eval_cmp(self, oper: str, a: Any, b: Any) -> bool:
        if oper == "==":
            return a == b
        if oper == "!=":
            return a != b
        if oper == "<":
            return a < b
        if oper == "<=":
            return a <= b
        if oper == ">":
            return a > b
        if oper == ">=":
            return a >= b
        raise NotImplementedError(f"Comparador no soportado: {oper}")

    def eval_binop(self, op: str, a: Any, b: Any) -> Any:
        # support both suffixed and plain ops
        core = op
        if op.endswith("I") or op.endswith("F"):
            core = op[:-1]

        if core in {"ADDI", "ADD", "ADD"}:
            return a + b
        if core in {"SUBI", "SUB", "SUB"}:
            return a - b
        if core in {"MULI", "MUL", "MUL"}:
            return a * b
        if core in {"DIVI", "DIV", "DIV"}:
            # integer division if both ints
            if isinstance(a, int) and isinstance(b, int):
                return a // b
            return a / b
        if core in {"AND"}:
            return int(bool(a) and bool(b))
        if core in {"OR"}:
            return int(bool(a) or bool(b))
        if core in {"XOR"}:
            return int(bool(a) ^ bool(b))

        raise NotImplementedError(f"Operación binaria no soportada: {op}")


def parse_opt_level(value: str) -> int:
    text = str(value).strip()

    #Por si acaso ponen O1 a secas en vez de -O1
    if text.startswith("-O"):
        text = text[2:]
    elif text.startswith("O"):
        text = text[1:]

    if not text.isdigit():
        raise ValueError(f"Nivel de optimización inválido: {value!r}")

    level = int(text)

    #Solo se hará el O1
    #if level < 0 or level > 4:
     #   raise ValueError("El nivel de optimización debe estar entre 0 y 4")

    if level != 1:
        raise ValueError("El nivel de optimización debe estar entre 0 y 4")

    return level


if __name__ == "__main__":
    import sys
    from ircode_starter import IRCodeGen

    if len(sys.argv) < 2:
        print("Uso: python iroptimizer.py archivo.bminor -O1")
        sys.exit(1)

    src = sys.argv[1]
    level = 0
    if len(sys.argv) >= 3:
        try:
            level = parse_opt_level(sys.argv[2])
        except Exception:
            try:
                level = int(sys.argv[2])
            except Exception:
                level = 0

    # For convenience, if input is a .bminor source, run through parser -> ircode
    try:
        with open(src, "r", encoding="utf-8") as f:
            code = f.read()
        # try to generate IR from source using existing pipeline
        from lexer import Lexer
        from parser import Parser
        from checker import Checker

        lexer = Lexer()
        parser = Parser()
        ast = parser.parse(lexer.tokenize(code))
        checker = Checker()
        checker.check(ast)
        ir = IRCodeGen.generate(ast)
    except Exception:
        # fallback: try to load a pickled IRProgram
        try:
            import pickle

            with open(src, "rb") as f:
                ir = pickle.load(f)
        except Exception as e:
            print("No se pudo leer el archivo como .bminor ni como IR pickled:", e)
            raise

    opt = IROptimizer(level)
    new_ir = opt.optimize(ir, level=level)
    print(new_ir.format())
