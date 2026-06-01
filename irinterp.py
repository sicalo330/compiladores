from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional

class IRRuntimeError(RuntimeError):
	"""Generic IR interpreter error."""
		
class IRReturn(Exception):
	def __init__(self, value: Any):
		self.value = value

@dataclass
class IRFunction:
	"""
	Runtime function container.
	
	Compatible with several possible codegen layouts:
	- name, params, return_type, instructions
	- name, args, rettype, code
	"""
	name: str
	params: list[str] = field(default_factory=list)
	return_type: Any = None
	instructions: list[tuple] = field(default_factory=list)
	
@dataclass
class IRModule:
	globals: list[tuple] = field(default_factory=list)
	functions: list[Any] = field(default_factory=list)
	
@dataclass
class Frame:
	name: str
	instructions: list[tuple]
	params: list[str] = field(default_factory=list)
	locals: dict[str, Any] = field(default_factory=dict)
	scopes: list[dict[str, Any]] = field(default_factory=list)
	pc: int = 0
	stack: list[Any] = field(default_factory=list)
	labels: dict[str, int] = field(default_factory=dict)
	temps: dict[str, Any] = field(default_factory=dict)
	
	def __post_init__(self):
		if not self.scopes:
			self.scopes = [self.locals]
		else:
			self.locals = self.scopes[-1]
		self.labels = self._index_labels(self.instructions)
		
	@staticmethod
	def _index_labels(code: list[tuple]) -> dict[str, int]:
		labels: dict[str, int] = {}
		for i, inst in enumerate(code):
			if inst and inst[0] == "LABEL":
				if len(inst) != 2:
					raise IRRuntimeError(f"LABEL inválido: {inst}")
				labels[inst[1]] = i
		return labels
		
class IRInterpreter:
	"""
	Intérprete para un IR estilo máquina de pila inspirado en el material de Dabeaz.
	
	Soporta:
	- enteros, flotantes y bytes
	- variables globales y locales
	- operaciones sobre pila
	- IF/ELSE/ENDIF
	- LOOP/CBREAK/CONTINUE/ENDLOOP
	- LABEL/BRANCH/CBRANCH
	- CALL/RET
	- memoria lineal con PEEK/POKE/GROW
	
	Convenciones:
	- bool se representa con enteros 0/1
	- byte se trunca con & 0xFF
	- las funciones reciben argumentos ya evaluados
	- LOAD/STORE buscan primero en locales y luego en globals
	"""
	
	def __init__(self, module_or_functions: Any = None, memory_size: int = 65536, trace: bool = False):
		self.trace = trace
		self.memory = bytearray(memory_size)
		self.globals: dict[str, Any] = {}
		self.functions: dict[str, Frame | Any] = {}
		self.call_depth = 0
		
		if module_or_functions is not None:
			self.load(module_or_functions)
	
	#Esta función toma el IR del ircodestarter y lo guarda en este interp.py
	def load(self, module_or_functions: Any) -> None:
		self.functions.clear()
		
		if hasattr(module_or_functions, "functions"):
			module = module_or_functions
			if hasattr(module, "globals"):
				self._execute_global_inits(getattr(module, "globals"))
			for fn in getattr(module, "functions"):
				self._register_function(fn)
			return
			
		if isinstance(module_or_functions, dict):
			for name, fn in module_or_functions.items():
				self.functions[name] = fn
			return
			
		if isinstance(module_or_functions, list):
			for fn in module_or_functions:
				self._register_function(fn)
			return
			
		raise IRRuntimeError(f"No puedo cargar funciones desde {type(module_or_functions).__name__}")
	
	#Esta función siempre entrará de primero
	def run(self, name: str = "main", *args):
		return self.call(name, list(args))
		
	def call(self, name: str, args: list[Any]):
		#name en este caso es la función que piden que se ejecute que por default es main,
		#si este no está en la pila de funciones que mandó ircode_starter entonces no hay función main, 
		#por lo tanto no se va a ejectura
		if name not in self.functions:
			raise IRRuntimeError(f"Función no encontrada: {name}")
			
		fn = self.functions[name]
		
		if callable(fn) and not hasattr(fn, "instructions") and not hasattr(fn, "code"):
			return fn(*args)
			
		frame = self._make_frame(fn, args)
		return self._execute_frame(frame)
	
	def _register_function(self, fn: Any) -> None:
		name = getattr(fn, "name", None)
		if not name:
			raise IRRuntimeError(f"Función sin nombre: {fn}")
		self.functions[name] = fn
	
	#Make frame se llama cada vez que hay una funcion, si hay dos funciones se llama dos veces, si hay tres, tres...
	#Deja un diccionario para poder ir guardando todas las pilas de instrucciones posteriores
	def _make_frame(self, fn: Any, args: list[Any]) -> Frame:
		instructions = self._extract_code(fn)
		param_names = self._extract_param_names(fn)
		
		if len(args) != len(param_names):
			raise IRRuntimeError(
				f"La función {getattr(fn, 'name', '<anon>')} esperaba {len(param_names)} args y recibió {len(args)}"
			)
			
		locals_: dict[str, Any] = {}
		for name, value in zip(param_names, args):
			locals_[name] = value
			
		return Frame(
			name=getattr(fn, "name", "<anon>"),
			instructions=instructions,
			params=param_names,
			locals=locals_,
			scopes=[locals_],
		)
		
	def _extract_code(self, fn: Any) -> list[tuple]:
		if hasattr(fn, "instructions"):
			return list(getattr(fn, "instructions"))
		if hasattr(fn, "code"):
			return list(getattr(fn, "code"))
		raise IRRuntimeError(f"No encuentro instrucciones en {fn}")
		
	def _extract_param_names(self, fn: Any) -> list[str]:
		if hasattr(fn, "params"):
			params = getattr(fn, "params")
			out = []
			for p in params:
				if isinstance(p, tuple):
					out.append(p[0])
				else:
					out.append(str(p))
			return out
		if hasattr(fn, "args"):
			return [str(x) for x in getattr(fn, "args")]
		return []
	
	#Esta función ejecuta las varaibles globales, es decir fuera de la función
	def _execute_global_inits(self, code: list[tuple]) -> None:
		"""
		Ejecuta una secuencia simple de inicialización global.
		Usa un frame sintético llamado _globals.
		"""
		if not code:
			return
		frame = Frame(name="_globals", instructions=list(code))
		self._execute_frame(frame)
	
	#Aquí ocurre lo que es la ejecución del IR en sí gracias al while
	def _execute_frame(self, frame: Frame):
		self.call_depth += 1
		try:
			while frame.pc < len(frame.instructions):
				inst = frame.instructions[frame.pc]
				self._trace(frame, inst)
				jumped = self._dispatch(frame, inst)
				if not jumped:
					frame.pc += 1
		except IRReturn as ret:
			return ret.value
		finally:
			self.call_depth -= 1
		return None
		
	def _dispatch(self, frame: Frame, inst: tuple) -> bool:
		op = inst[0]
		args = inst[1:]

		if op == "LABEL":
			return False

		if op == "ENTER":
			frame.scopes.append({})
			frame.locals = frame.scopes[-1]
			return False

		if op == "EXIT":
			if len(frame.scopes) <= 1:
				raise IRRuntimeError("EXIT fuera de scope")
			frame.scopes.pop()
			frame.locals = frame.scopes[-1]
			return False

		if op == "ALLOC":
			name = args[0]
			if frame.name == "_globals":
				self.globals.setdefault(name, 0)
			else:
				frame.locals.setdefault(name, 0)
			return False

		if op == "MOVI":
			value = int(args[0])
			temp = args[1]
			frame.temps[temp] = value
			return False
		if op == "MOVF":
			value = float(args[0])
			temp = args[1]
			frame.temps[temp] = value
			return False
		if op == "MOVB":
			value = int(args[0]) & 0xFF
			temp = args[1]
			frame.temps[temp] = value
			return False
		if op == "MOVS":
			value = args[0]
			temp = args[1]
			frame.temps[temp] = value
			return False

		if op == "ADD":
			left = args[0]
			right = args[1]
			out = args[2]
			left_val = self._get_operand(frame, left)
			right_val = self._get_operand(frame, right)
			frame.temps[out] = left_val + right_val
			return False
		if op == "SUB":
			left = args[0]
			right = args[1]
			out = args[2]
			left_val = self._get_operand(frame, left)
			right_val = self._get_operand(frame, right)
			frame.temps[out] = left_val - right_val
			return False
		if op == "MUL":
			left = args[0]
			right = args[1]
			out = args[2]
			left_val = self._get_operand(frame, left)
			right_val = self._get_operand(frame, right)
			frame.temps[out] = left_val * right_val
			return False
		if op == "DIV":
			left = args[0]
			right = args[1]
			out = args[2]
			left_val = self._get_operand(frame, left)
			right_val = self._get_operand(frame, right)
			if right_val == 0:
				raise IRRuntimeError("División por cero")
			frame.temps[out] = int(left_val / right_val)
			return False
		if op == "REM":
			left = args[0]
			right = args[1]
			out = args[2]
			left_val = self._get_operand(frame, left)
			right_val = self._get_operand(frame, right)
			if right_val == 0:
				raise IRRuntimeError("División por cero")
			frame.temps[out] = left_val % right_val
			return False
			
		if op == "NEG":
			operand = args[0]
			out = args[1]
			val = self._get_operand(frame, operand)
			frame.temps[out] = -val
			return False
		if op == "NOT":
			operand = args[0]
			out = args[1]
			val = self._get_operand(frame, operand)
			frame.temps[out] = 0 if val else 1
			return False

		if op == "CMP":
			cmpop = args[0]
			left = args[1]
			right = args[2]
			out = args[3]
			left_val = self._get_operand(frame, left)
			right_val = self._get_operand(frame, right)
			result = self._compare_symbol(cmpop, left_val, right_val)
			frame.temps[out] = 1 if result else 0
			return False

		if op == "AND":
			left = args[0]
			right = args[1]
			out = args[2]
			left_val = self._get_operand(frame, left)
			right_val = self._get_operand(frame, right)
			frame.temps[out] = 1 if (left_val and right_val) else 0
			return False

		if op == "OR":
			left = args[0]
			right = args[1]
			out = args[2]
			left_val = self._get_operand(frame, left)
			right_val = self._get_operand(frame, right)
			frame.temps[out] = 1 if (left_val or right_val) else 0
			return False

		if op == "PRINT":
			operand = args[0]
			val = self._get_operand(frame, operand)
			print(val, end="")
			return False
		if op == "PRINTS":
			operand = args[0]
			val = self._get_operand(frame, operand)
			print(val, end="")
			return False
		if op == "PRINTI":
			operand = args[0] if args else None
			if operand:
				val = self._get_operand(frame, operand)
			else:
				val = int(self._pop(frame))
			print(val)
			return False
		if op == "PRINTB":
			operand = args[0] if args else None
			if operand:
				val = self._get_operand(frame, operand)
			else:
				val = int(self._pop(frame))
			print(chr(int(val) & 0xFF), end="")
			return False
		if op == "PRINTF":
			operand = args[0] if args else None
			if operand:
				val = self._get_operand(frame, operand)
			else:
				val = float(self._pop(frame))
			print(val)
			return False
			
		if op == "CONSTI":
			self._push(frame, int(args[0]))
			return False
		if op == "CONSTF":
			self._push(frame, float(args[0]))
			return False
		if op == "CONSTB":
			self._push(frame, int(args[0]) & 0xFF)
			return False

		if op in {"GLOBALI", "GLOBALF", "GLOBALB"}:
			name = args[0]
			self.globals.setdefault(name, 0)
			return False
			
		if op in {"LOCALI", "LOCALF", "LOCALB"}:
			name = args[0]
			frame.locals.setdefault(name, 0)
			return False

		if op == "LOAD":
			name = args[0]
			self._push(frame, self._load_var(frame, name))
			return False

		if op in {"LOADI", "LOADF", "LOADB", "LOADS"}:
			name = args[0]
			if len(args) > 1:
				temp = args[1]
				frame.temps[temp] = self._load_var(frame, name)
			else:
				self._push(frame, self._load_var(frame, name))
			return False

		if op == "PUSH":
			operand = args[0]
			value = self._get_operand(frame, operand)
			self._push(frame, value)
			return False

		if op == "POP":
			temp = args[0]
			value = self._pop(frame)
			frame.temps[temp] = value
			return False
		
		if op == "STORE":
			source = args[0]
			name = args[1]
			value = self._get_operand(frame, source)
			self._store_var(frame, name, value)
			return False
		
		if op == "STOREA":
			# STOREA value array_name index
			source = args[0]
			name = args[1]
			index = int(self._get_operand(frame, args[2]))
			value = self._get_operand(frame, source)
			# Get or create array
			arr = self._load_var(frame, name)
			if not isinstance(arr, list):
				arr = []
				self._store_var(frame, name, arr)
			# Extend array if necessary
			while len(arr) <= index:
				arr.append(0)
			arr[index] = value
			return False
		
		if op == "LOADA":
			# LOADA dest array_name index
			dest = args[0]
			name = args[1]
			index = int(self._get_operand(frame, args[2]))
			arr = self._load_var(frame, name)
			if not isinstance(arr, list) or index >= len(arr):
				value = 0  # Default for out of bounds
			else:
				value = arr[index]
			frame.temps[dest] = value
			return False
			
		if op in {"STOREI", "STOREF", "STOREB", "STORES"}:
			if len(args) == 2:
				source = args[0]
				name = args[1]
				value = self._get_operand(frame, source)
			else:
				name = args[0]
				value = self._pop(frame)
			if op == "STOREB":
				value &= 0xFF
			self._store_var(frame, name, value)
			return False

		if op in {"ADDI", "SUBI", "MULI", "DIVI", "ANDI", "ORI", "XORI"}:
			b = int(self._pop(frame))
			a = int(self._pop(frame))
			if op == "ADDI":
				self._push(frame, a + b)
			elif op == "SUBI":
				self._push(frame, a - b)
			elif op == "MULI":
				self._push(frame, a * b)
			elif op == "DIVI":
				if b == 0:
					raise IRRuntimeError("División por cero en DIVI")
				self._push(frame, int(a / b))
			elif op == "ANDI":
				self._push(frame, a & b)
			elif op == "ORI":
				self._push(frame, a | b)
			else:
				self._push(frame, a ^ b)
			return False
			
		if op in {"ADDF", "SUBF", "MULF", "DIVF"}:
			b = float(self._pop(frame))
			a = float(self._pop(frame))
			if op == "ADDF":
				self._push(frame, a + b)
			elif op == "SUBF":
				self._push(frame, a - b)
			elif op == "MULF":
				self._push(frame, a * b)
			else:
				if b == 0.0:
					raise IRRuntimeError("División por cero en DIVF")
				self._push(frame, a / b)
			return False

		if op in {"LTI", "LEI", "GTI", "GEI", "EQI", "NEI"}:
			b = int(self._pop(frame))
			a = int(self._pop(frame))
			self._push(frame, int(self._compare(op, a, b)))
			return False
			
		if op in {"LTF", "LEF", "GTF", "GEF", "EQF", "NEF"}:
			b = float(self._pop(frame))
			a = float(self._pop(frame))
			self._push(frame, int(self._compare(op, a, b)))
			return False
			
		if op == "CMPF":
			cmpop = args[0]
			b = float(self._pop(frame))
			a = float(self._pop(frame))
			self._push(frame, int(self._compare_symbol(cmpop, a, b)))
			return False
			
		if op == "CMPI":
			cmpop = args[0]
			b = int(self._pop(frame))
			a = int(self._pop(frame))
			self._push(frame, int(self._compare_symbol(cmpop, a, b)))
			return False
			
		if op == "CMPB":
			cmpop = args[0]
			b = int(self._pop(frame)) & 0xFF
			a = int(self._pop(frame)) & 0xFF
			self._push(frame, int(self._compare_symbol(cmpop, a, b)))
			return False
			
		if op == "PRINTI":
			# print(int(self._pop(frame)))
			return False
		if op == "PRINTF":
			# print(float(self._pop(frame)))
			return False
		if op == "PRINTB":
			# print(chr(int(self._pop(frame)) & 0xFF), end="")
			return False
			
		if op == "ITOF":
			self._push(frame, float(int(self._pop(frame))))
			return False
		if op == "FTOI":
			self._push(frame, int(float(self._pop(frame))))
			return False
		if op == "ITOB":
			self._push(frame, int(self._pop(frame)) & 0xFF)
			return False
		if op == "BTOI":
			self._push(frame, int(self._pop(frame)) & 0xFF)
			return False

		if op == "GROW":
			nbytes = int(self._pop(frame))
			if nbytes < 0:
				raise IRRuntimeError("GROW con tamaño negativo")
			self.memory.extend(b"\x00" * nbytes)
			self._push(frame, len(self.memory))
			return False
			
		if op == "PEEKI":
			addr = int(self._pop(frame))
			self._push(frame, self._mem_read_int(addr))
			return False
			
		if op == "POKEI":
			value = int(self._pop(frame))
			addr = int(self._pop(frame))
			self._mem_write_int(addr, value)
			return False
			
		if op == "PEEKF":
			import struct
			addr = int(self._pop(frame))
			self._ensure_mem(addr, 8)
			self._push(frame, struct.unpack("<d", self.memory[addr:addr + 8])[0])
			return False
			
		if op == "POKEF":
			import struct
			value = float(self._pop(frame))
			addr = int(self._pop(frame))
			self._ensure_mem(addr, 8)
			self.memory[addr:addr + 8] = struct.pack("<d", value)
			return False
			
		if op == "PEEKB":
			addr = int(self._pop(frame))
			self._ensure_mem(addr, 1)
			self._push(frame, self.memory[addr])
			return False
			
		if op == "POKEB":
			value = int(self._pop(frame)) & 0xFF
			addr = int(self._pop(frame))
			self._ensure_mem(addr, 1)
			self.memory[addr] = value
			return False
			
		if op == "IF":
			test = self._pop(frame)
			if test:
				return False
			frame.pc = self._find_else_or_endif(frame.instructions, frame.pc)
			return True
			
		if op == "ELSE":
			frame.pc = self._find_matching_endif(frame.instructions, frame.pc)
			return True
			
		if op == "ENDIF":
			return False
			
		if op == "LOOP":
			return False
			
		if op == "CBREAK":
			test = self._pop(frame)
			if test:
				frame.pc = self._find_matching_endloop(frame.instructions, frame.pc)
				return True
			return False
			
		if op == "CONTINUE":
			frame.pc = self._find_loop_start(frame.instructions, frame.pc)
			return True
			
		if op == "ENDLOOP":
			frame.pc = self._find_loop_start(frame.instructions, frame.pc)
			return True
		
		if op == "BRANCH":
			label = args[0]
			#Entra a la función jump to label para saber si hay algún L1 o L2...
			#De ser así devolvería un true para jump
			#Y si es true entonces hay saltos
			frame.pc = self._jump_to_label(frame, label)
			return True
			
		if op == "CBRANCH":
			if len(args) == 3:
				test_operand = args[0]
				label_true = args[1]
				label_false = args[2]
				test = self._get_operand(frame, test_operand)
			else:
				test = self._pop(frame)
				label_true = args[0]
				label_false = args[1]
			frame.pc = self._jump_to_label(frame, label_true if test else label_false)
			return True
		
		if op == "CALL":
			name = args[0]
			argc = int(args[1]) if len(args) > 1 else 0
			call_args = [self._pop(frame) for _ in range(argc)]
			call_args.reverse()
			result = self.call(name, call_args)
			if result is not None:
				self._push(frame, result)
			return False
			
		if op == "RET":
			if args:
				value = self._get_operand(frame, args[0])
			else:
				value = None
			raise IRReturn(value)
			
		raise IRRuntimeError(f"Opcode no soportado: {op}")
	
	#Esta función general los logs
	def _trace(self, frame: Frame, inst: tuple) -> None:
		if not self.trace:
			return
		indent = "  " * max(0, self.call_depth - 1)
		print(f"{indent}[{frame.name} pc={frame.pc}] {inst} stack={frame.stack} locals={frame.locals}")
		
	def _push(self, frame: Frame, value: Any) -> None:
		frame.stack.append(value)
		
	def _pop(self, frame: Frame) -> Any:
		if not frame.stack:
			raise IRRuntimeError("Stack underflow")
		return frame.stack.pop()
		
	def _load_var(self, frame: Frame, name: str) -> Any:
		# Buscar desde el scope más interno al más externo
		for scope in reversed(frame.scopes):
			if name in scope:
				return scope[name]

		# Si no está en scopes locales, buscar en globals
		if name in self.globals:
			return self.globals[name]

		raise IRRuntimeError(f"Variable no definida: {name}")
	
	def _get_operand(self, frame: Frame, operand: str | int) -> Any:
		"""
		Get the value of an operand.
		Can be:
		- A temporary register (R1, R2, ...)
		- A variable name (from locals or globals)
		- A literal integer or value
		"""
		if isinstance(operand, (int, float)):
			return operand
		operand_str = str(operand)
		if operand_str.startswith("R"):
			if operand_str in frame.temps:
				return frame.temps[operand_str]
			raise IRRuntimeError(f"Temporal no inicializado: {operand_str}")
		for scope in reversed(frame.scopes):
			if operand_str in scope:
				return scope[operand_str]
		if operand_str in self.globals:
			return self.globals[operand_str]
		try:
			return int(operand_str)
		except ValueError:
			raise IRRuntimeError(f"Operando no resuelto: {operand_str}")
		
	def _store_var(self, frame: Frame, name: str, value: Any) -> None:
		# Buscar la variable desde el scope más interno al más externo.
		for scope in reversed(frame.scopes):
			if name in scope:
				scope[name] = value
				return
		# Si no está en ningún scope local, actualizar globals si existe.
		if name in self.globals:
			self.globals[name] = value
			return
		# Fallback: crear en el scope actual.
		frame.locals[name] = value
		
	def _jump_to_label(self, frame: Frame, label: str) -> int:
		if label not in frame.labels:
			raise IRRuntimeError(f"Label no encontrado: {label}")
		return frame.labels[label]
		
	def _ensure_mem(self, addr: int, size: int) -> None:
		if addr < 0:
			raise IRRuntimeError("Dirección de memoria negativa")
		if addr + size > len(self.memory):
			raise IRRuntimeError("Acceso de memoria fuera de rango")
			
	def _mem_read_int(self, addr: int) -> int:
		import struct
		self._ensure_mem(addr, 8)
		return struct.unpack("<q", self.memory[addr:addr + 8])[0]
		
	def _mem_write_int(self, addr: int, value: int) -> None:
		import struct
		self._ensure_mem(addr, 8)
		self.memory[addr:addr + 8] = struct.pack("<q", int(value))
		
	@staticmethod
	def _compare(op: str, a: Any, b: Any) -> bool:
		if op in {"LTI", "LTF"}:
			return a < b
		if op in {"LEI", "LEF"}:
			return a <= b
		if op in {"GTI", "GTF"}:
			return a > b
		if op in {"GEI", "GEF"}:
			return a >= b
		if op in {"EQI", "EQF"}:
			return a == b
		if op in {"NEI", "NEF"}:
			return a != b
		raise IRRuntimeError(f"Comparación desconocida: {op}")
		
	@staticmethod
	def _compare_symbol(op: str, a: Any, b: Any) -> bool:
		if op == "<":
			return a < b
		if op == "<=":
			return a <= b
		if op == ">":
			return a > b
		if op == ">=":
			return a >= b
		if op == "==":
			return a == b
		if op == "!=":
			return a != b
		raise IRRuntimeError(f"Operador de comparación desconocido: {op}")
	
	@staticmethod
	def _find_else_or_endif(code: list[tuple], start: int) -> int:
		depth = 0
		for i in range(start + 1, len(code)):
			op = code[i][0]
			if op == "IF":
				depth += 1
			elif op == "ENDIF":
				if depth == 0:
					return i
				depth -= 1
			elif op == "ELSE" and depth == 0:
				return i
		raise IRRuntimeError("No se encontró ELSE/ENDIF correspondiente")
		
	@staticmethod
	def _find_matching_endif(code: list[tuple], start: int) -> int:
		depth = 0
		for i in range(start + 1, len(code)):
			op = code[i][0]
			if op == "IF":
				depth += 1
			elif op == "ENDIF":
				if depth == 0:
					return i
				depth -= 1
		raise IRRuntimeError("No se encontró ENDIF correspondiente")
		
	@staticmethod
	def _find_matching_endloop(code: list[tuple], start: int) -> int:
		depth = 0
		for i in range(start + 1, len(code)):
			op = code[i][0]
			if op == "LOOP":
				depth += 1
			elif op == "ENDLOOP":
				if depth == 0:
					return i
				depth -= 1
		raise IRRuntimeError("No se encontró ENDLOOP correspondiente")
		
	@staticmethod
	def _find_loop_start(code: list[tuple], start: int) -> int:
		depth = 0
		for i in range(start - 1, -1, -1):
			op = code[i][0]
			if op == "ENDLOOP":
				depth += 1
			elif op == "LOOP":
				if depth == 0:
					return i
				depth -= 1
		raise IRRuntimeError("No se encontró LOOP correspondiente")

# def _demo_module() -> IRModule:
# 	"""
# 	Programa demo:
# 	x: integer = 1;
# 	while x <= 5 {
# 		print x;
# 		x = x + 1;
# 	}
# 	return x;
# 	"""
# 	main = IRFunction(
# 		name="main",
# 		params=[],
# 		return_type="I",
# 		instructions=[
# 			("LOCALI", "x"),
# 			("CONSTI", 1),
# 			("STORE", "x"),
			
# 			("LOOP",),
# 				("LOAD", "x"),
# 				("CONSTI", 5),
# 				("LEI",),
# 				("CONSTI", 0),
# 				("EQI",),
# 				("CBREAK",),
			
# 				("LOAD", "x"),
# 				("PRINTI",),
			
# 				("LOAD", "x"),
# 				("CONSTI", 1),
# 				("ADDI",),
# 				("STORE", "x"),
# 			("ENDLOOP",),
			
# 			("LOAD", "x"),
# 			("RET",),
# 		],
# 	)
# 	return IRModule(functions=[main])
	
	
# if __name__ == "__main__":
# 	interp = IRInterpreter(_demo_module(), trace=False)
# 	result = interp.run("main")
# 	# print("\nreturn =", result)