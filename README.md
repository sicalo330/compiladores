# Compilador Bminor++

## Integrantes
- Juan José Arcila  
- Jhonie Alejandro Tombe  
- Noah Narváez  

## Descripción

El compilador **Bminor++** busca ser una reimaginación de lo que fue el lenguaje Bminor clásico, incorporando algunas capas adicionales de complejidad y funcionalidades modernas.

Actualmente, el proyecto cuenta con los siguientes componentes:

- Gramática EBNF
- Lexer
- Parser
- Checker semántico
- Generador de representación intermedia
- Optimización O1 para la representación intermedia

Cabe aclarar lo siguiente, todo el proyecto funciona por estpas y si en alguna de ellas el compilador encuentra errores automáticamente se detendrá, es decir que si por ejemplo encuentra errores en el parser, generará los errores adecuados para el caso y no seguirá al checker y mucho menos va a generar la representación intermedia

## Como ejecutar el proyecto

Primero que todo es necesario estar en la raíz principal del proyecto
![alt text](/additions/img/rootProyect.png)

Para poder generar todas las fases del proyecto, es decir desde el lexer hasta el IR optimizado con O1 es necesario poner el comando python seguido del archivo main.py que es la unidad centrar de la lógica del compilador y justo después poner qué archivo se quiere testear o en este caso la ruta del archivo a testeas. Para poder generar la representación intermedia hace falta usar los sigiuentes comandos

```
python main.py test/IRO/test{numero}.bminor
python main.py test/IROptimizer/test{numero}.bminor
```

Si se quiere generar el IR con la optimización O1 es necesario poner exactamente el mismo comando pero con un -O1 al final

```
python main.py test/IRO/test{numero}.bminor
python main.py test/IROptimizer/test{numero}.bminor
```