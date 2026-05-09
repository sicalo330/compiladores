# errors.py
'''
Gestión de errores del compilador.

Una de las partes más importantes (y molestas) de escribir un compilador
es la notificación fiable de mensajes de error al usuario. Este archivo
debería consolidar algunas funciones básicas de gestión de errores en un solo lugar.
Facilitar la notificación de errores. Facilitar la detección de errores.

Podría ampliarse para que sea más potente posteriormente.

Variable global que indica si se ha producido algún error. El compilador puede 
consultar esto posteriormente para decidir si debe detenerse.
'''
from rich import print

_errors_detected = 0
_compiler_failed = False
_errors = []

#Stage se pone en general por si no viene de alguna fase del compilador dando a entender que es un error cualquiera
#No sé como explicarlo mejor o no sé son las 2 de la mañana
def error(message, lineno=None, stage="GENERAL"):
    #Registra un error con su fase correspondiente con la fase correspondiente'LEXER', 'PARSER', 'CHECKER', 'IR'
    global _errors
    _errors.append({
        "message": message,
        "lineno": lineno,
        "stage": stage.upper()
    })

    #Visualización con colores según la fase
    colors = {
        "LEXER": "red",
        "PARSER": "magenta",
        "CHECKER": "yellow",
        "IR": "blue",
        "GENERAL": "white"
    }
    color = colors.get(stage.upper(), "white")
    
    print(f"[bold {color}][{stage.upper()} ERROR][/bold {color}] "
          f"[cyan]Linea {lineno if lineno else '?'}:[/cyan] {message}")
	
def errors_detected():
	return _errors_detected > 0
	
def clearErrors():
    _errors.clear()

def report_by_stage(stage):
    return [e for e in _errors if e['stage'] == stage.upper()]

def has_errors(stage=None):
    if stage:
        return any(e['stage'] == stage.upper() for e in _errors)
    return len(_errors) > 0

def get_errors():
    return _errors

def compilation_failed():
	return _compiler_failed

def report():
	return _errors

#Creo que puse demasiados helpers