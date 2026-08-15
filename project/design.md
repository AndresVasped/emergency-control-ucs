# Diseño del agente

Este documento debe completarse antes de la implementación principal del agente.

Use sus propias palabras y notación. No reemplace este archivo por una transcripción del enunciado.

## Estado

Defina formalmente qué información representa un estado.

Explique:

- qué variables forman parte del estado
- por qué cada una es necesaria
- qué información puede derivarse de otras variables
- qué información pertenece al historial de búsqueda pero no al estado físico
- cuándo dos configuraciones deben considerarse el mismo estado

(completar)

## Acciones

Defina las acciones que puede realizar el agente.

Para cada acción indique:

- precondiciones
- efectos
- costo

(completar)

## Modelo de transición

Explique cómo una acción legal transforma un estado en el siguiente y qué información del mundo puede cambiar como consecuencia.

```text
s -> s'
```

(completar)

## Prueba de meta

Defina formalmente `Goal(s)` y explique por qué representa la condición real de éxito de la misión.

(completar)

## Función de costo

Defina `g(n)` como el costo acumulado desde el estado inicial hasta el nodo actual.

Explique por qué su función de costo representa correctamente qué significa para este agente encontrar una solución mejor.

(completar)

## Estrategia de búsqueda

Seleccione una estrategia de búsqueda estudiada en clase y justifique su elección considerando las propiedades del problema.

La justificación debe discutir, cuando corresponda:

- completitud
- optimalidad
- costo de camino
- tiempo
- espacio
- condiciones bajo las cuales las garantías de la estrategia dejan de cumplirse

(completar)
