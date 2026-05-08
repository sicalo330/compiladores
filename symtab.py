# symtab.py (ChainMap-backed, API-compatible)
from __future__ import annotations
from collections import ChainMap
from dataclasses import dataclass, field
from typing import Any, Optional, List

from rich.table   import Table
from rich.console import Console
from rich         import print

try:
	from model import Node
except Exception:
	class Node:
		def __init__(self, name): self.name = name
		
console = Console()

class Symtab:
	'''
	Tabla de símbolos con **misma interfaz** que la 
	versión previa, pero ahora respaldada internamente 
	por **ChainMap** para resolver sombras de forma 
	nativa y permitir inspección/depuración sencilla.
	
	API expuesta y compatible:
	- __init__(name: str, parent: Optional[Symtab] = None)
	- add(name: str, value: Any)           # define en el scope actual
	- get(name: str) -> Any | None         # busca con alcance léxico
	- print()                              # imprime esta tabla y sus hijas
	
	Extras NO disruptivos (opcionales):
	- entries -> dict del scope actual (alias a self._map)
	- cm -> ChainMap con cadena actual de scopes (solo lectura externa)
	- children: lista de Symtab hijas
	- parent: referencia a la tabla padre
	'''
	class SymbolDefinedError(Exception):
		pass
		
	class SymbolConflictError(Exception):
		pass
	
	def __init__(self, name: str, parent: Optional["Symtab"] = None):
		self.name: str = name
		self.parent: Optional["Symtab"] = parent
		self.children: List["Symtab"] = []
		
		self._map: dict[str, Any] = {}
		if parent is None: self.cm: ChainMap = ChainMap(self._map)
		else:
			self.cm: ChainMap = parent.cm.new_child(self._map)
			parent.children.append(self)
			
		self.entries = self._map
		
	#helpers privados
	
	def _type_of(self, obj: Any):
		try:
			return obj.type
		except Exception:
			return type(obj)
			
	
	def add(self, name: str, value: Any):
		if name in self._map:
			# chequeo de conflictos como el original
			existing = self._map[name]
			if self._type_of(existing) != self._type_of(value): raise Symtab.SymbolConflictError(f"Conflicto: '{name}' ya definido con tipo distinto en scope '{self.name}'")
			else: raise Symtab.SymbolDefinedError(f"Redefinición: '{name}' ya definido en scope '{self.name}'")
		self._map[name] = value
		return value
		
	def get(self, name: str):
		if name in self.cm:
			return self.cm[name]
		return None
		
	
	def print(self):
		'''
		Imprime esta tabla y recursivamente sus hijas (árbol de scopes).
		Muestra sólo el *scope actual* en cada nodo.
		'''
		table = Table(title=f"Symbol Table: '{self.name}'")
		table.add_column('key', style='cyan')
		table.add_column('value', style='bright_green')
		
		for k, v in self._map.items():
			if isinstance(v, Node): value = f"{v.__class__.__name__}({getattr(v, 'name', '?')})"
			else: value = f"{v}"
			table.add_row(k, value)
		print(table, '\n')
		
		for child in self.children: child.print()
			

	def merged_view(self) -> dict:
		"""Vista efectiva (dict) del scope actual (interno > padres)."""
		return dict(self.cm)
		
	def lineage(self) -> list[str]:
		"""Lista de nombres de scopes desde global hasta éste."""
		out = []
		node: Optional[Symtab] = self
		while node:
			out.append(node.name)
			node = node.parent
		return list(reversed(out))
		

if __name__ == "__main__":
	g = Symtab("global")
	g.add("x", 1)
	
	f = Symtab("function f", parent=g)
	f.add("x", 3)
	f.add("a", 10)
	
	b = Symtab("block", parent=f)
	b.add("t", True)
	
	assert b.get("t") is True
	assert b.get("a") == 10
	assert b.get("x") == 3
	assert g.get("x") == 1
	assert g.get("a") is None
	
	g.print()
	
	#print(b.merged_view())
 
