# Diseño del agente

El agente debera estar diseñado para resolver el escenario `Emergency Control` como un
problema de búsqueda clásica.

El entorno es:

- totalmente observable;
- determinista;
- secuencial;
- estático durante la planificación;
- discreto;
- de agente único.

Por estas propiedades, el agente la estrategia a utilizar es el USC (Busqueda de costo uniforme) por el simple hecho que este algoritmo nos permite y nos ayuda a disminuir el costo por cada paso que haria nuestro robot no buscamos lllegar rapido a tal punto sino llegar gastando la menor cantidad de recursos posibles (batería, tiempo, esfuerzo) cada elemento cada paso tiene un costo y buscamos ahorrar la mayor cantidad de este mismo.

El archivo `scenario.json` es la fuente de verdad. El agente no debe asumir
ids, posiciones, costos, dependencias o cantidades específicas de una única
instancia.

---

## Estado

### Definición formal

El estado representa una fotografía completa del mundo en un instante:

```text
s = ⟨
    zona,
    bateria,
    payload_keys,
    payload_tools,
    payload_materials,
    doors_open,
    panels_ok,
    stations_on,
    ground_keys,
    ground_tools,
    ground_materials
⟩
```

Los componentes significan lo siguiente:

| Componente | Descripción |
|---|---|
| `zona` | Zona actual del robot. |
| `bateria` | Batería restante. |
| `payload_keys` | Llaves que se encuentran en el inventario. |
| `payload_tools` | Herramientas que se encuentran en el inventario. |
| `payload_materials` | Materiales en el inventario y sus cantidades. |
| `doors_open` | Puertas que ya fueron abiertas. |
| `panels_ok` | Paneles que ya fueron reparados. |
| `stations_on` | Estaciones que ya estan online. |
| `ground_keys` | Llaves que permanecen en el suelo y sus zonas. |
| `ground_tools` | Herramientas que permanecen en el suelo y sus zonas. |
| `ground_materials` | Materiales en el suelo, sus zonas y sus cantidades. |

La clase `Estado` implementa esta informacion. Las colecciones que forman parte
del estado se convierten en estructuras inmutables, principalmente mediante
`frozenset` (tuplas inmutables para que no cambien de orden en tiempo de ejecucion), para que el estado pueda utilizarse en `CLOSED` (es el conjunto de estados que el algortimo ya exploro lo agrega a closed si ya la visito) o en un conjunto
de estados visitados.

### Por qué cada variable es necesaria

Una variable pertenece al estado si puede cambiar las acciones legales futuras
o el resultado de alguna accion

#### Zona

La zona es necesaria porque determina:

- qué objetos puede recoger el robot;
- dónde puede soltar objetos;
- qué corredores puede utilizar;
- qué puertas puede abrir;
- qué paneles puede reparar;
- qué estaciones puede activar;
- qué cargadores puede utilizar.

Dos estados que solamente difieran en la zona pueden tener conjuntos de
acciones completamente diferentes.

#### Batería

La batería pertenece al estado porque cada acción consume energía y solo puede
ejecutarse cuando existe batería suficiente.

Dos estados con la misma zona, inventario y entorno, pero con diferente batería,
no necesariamente tienen las mismas acciones aplicables. Por ejemplo, uno puede
tener energía suficiente para recorrer un corredor y el otro no.

La acción `RECHARGE` también modifica este componente.

#### Inventario

El inventario es necesario porque determina qué acciones puede realizar el
robot:

- una llave permite abrir una puerta;
- una herramienta permite reparar paneles;
- un material es necesario para reparar un panel;
- los materiales se consumen al reparar;
- la capacidad de carga limita nuevas acciones `PICKUP`.

El inventario se divide en tres partes:

```text
payload_keys
payload_tools
payload_materials
```

Esta separación evita confundir ids de llaves y herramientas con tipos de
materiales.

#### Objetos en el suelo

La ubicación de los objetos debe formar parte del estado porque el robot puede
recogerlos y soltarlos.

La ubicación inicial proviene del escenario, pero después de una acción `DROP`
un objeto puede encontrarse en una zona diferente. Por tanto, la ubicación no
puede reconstruirse solamente a partir de `scenario.json`.

Los materiales se identifican por tipo y cantidad, no por ids individuales,
porque el contrato los referencia por tipos como `FUSE`, `CHIP` o `CABLE`.

#### Puertas abiertas

Las puertas abiertas forman parte del estado porque una puerta abierta permite
utilizar corredores que antes estaban bloqueados.

Además, las puertas son monotónicas: una vez abiertas, no vuelven a cerrarse.

#### Paneles reparados

Los paneles reparados forman parte del estado porque:

- un panel reparado no puede repararse nuevamente;
- una estación puede exigir que ciertos paneles estén reparados.

#### Estaciones activadas

Las estaciones online forman parte del estado porque:

- algunas estaciones pueden depender de otras estaciones;
- la meta se expresa en términos de estaciones online.

---

### Qué información se deriva y NO se almacena

No se almacenan como componentes independientes del estado los datos que ya
están en el escenario o que pueden calcularse a partir de él y del estado.

Por ejemplo:

- el grafo de corredores;
- los costos oficiales;
- la capacidad máxima;
- la batería máxima;
- el peso de los objetos;
- la herramienta requerida por cada panel;
- el material requerido por cada panel;
- las dependencias de cada estación;
- el peso total actual del inventario.

El peso de la carga se calcula con la función `payload_weight`, utilizando los
pesos declarados en `scenario.json`.

Esta decisión evita duplicar información y evita que dos variables del estado
se contradigan.

---

### Qué pertenece al historial de búsqueda y no al estado físico

La información del historial de búsqueda no representa una propiedad física del
mundo.

No forma parte de `Estado`:

- `g(n)`, el costo acumulado del camino;
- el estado padre;
- la acción que llevó al estado actual;
- el contador usado para desempatar nodos;
- el orden de descubrimiento;
- la posición del nodo dentro de la frontera.

Esta información se guarda en las estructuras de UCS y se utiliza para
reconstruir el plan cuando se encuentra una solución.

Dos caminos diferentes pueden llegar a la misma configuración física. Por eso
el historial no debe incluirse dentro del estado; de lo contrario, `CLOSED`
consideraría diferentes dos situaciones físicamente iguales.

---

### Cuándo dos configuraciones son el mismo estado

Dos configuraciones son el mismo estado cuando tienen exactamente los mismos
valores físicos en todos los componentes relevantes:

```text
(zona, bateria, inventario, objetos_en_el_suelo,
 puertas_abiertas, paneles_reparados, estaciones_activadas)
```

El orden de las colecciones no tiene significado físico. Por esto se utilizan
representaciones canónicas:

- `frozenset` para conjuntos de ids;
- pares `(id, zona)` para objetos en el suelo;
- pares `(tipo, cantidad)` para materiales en el inventario;
- tuplas `(tipo, zona, cantidad)` para materiales en el suelo.

Por ejemplo, los inventarios:

```text
{KEY1, KEY2}
```

y

```text
{KEY2, KEY1}
```

representan el mismo inventario.

La clase `Estado` implementa `__eq__` y `__hash__` a partir de una tupla
canónica. Esto permite que el algoritmo reconozca estados equivalentes aunque
se hayan alcanzado por caminos diferentes.

---

### Relevancia: objetos que ya no cambian el futuro

Los cambios del entorno son monotónicos:

- una puerta abierta no vuelve a cerrarse;
- un panel reparado no necesita repararse otra vez;
- una estación online permanece online.

Por eso algunos objetos dejan de ser útiles después de cumplir su función.

El agente aplica estas reglas:

1. Una llave solamente se puede soltar después de que la puerta asociada ya
   esté abierta.
2. Una herramienta solamente se puede soltar cuando ya no es necesaria para
   ningún panel pendiente.
3. Los materiales no se generan como acciones `DROP`, porque se recogen para
   ser consumidos durante una reparación.
4. No se generan acciones para volver a abrir una puerta, reparar un panel ya
   reparado o activar una estación ya online.

Estas restricciones reducen estados que únicamente se diferencian por la
posición de objetos que ya no pueden producir progreso.

La poda es segura porque soltar una llave antes de abrir su puerta o soltar una
herramienta antes de terminar sus reparaciones puede obligar al robot a
recogerla otra vez, agregando costo sin producir progreso.

---

## Acciones

Las acciones siguientes son acciones internas del agente. Antes de enviarlas al
frontend se traducen al formato externo definido por el contrato.

Toda acción requiere además:

```text
bateria >= costo_de_la_accion
```

| Acción | Precondiciones | Efectos | Costo |
|---|---|---|---|
| `MOVE(zona_origen, zona_destino)` | Existe un corredor entre las zonas; si tiene puerta, la puerta está abierta; existe batería suficiente. | Cambia la zona y disminuye la batería. | Costo del corredor. |
| `PICKUP_KEY(id)` | La llave está en el suelo de la zona actual; hay capacidad disponible; hay batería suficiente. | La llave pasa del suelo al inventario. | `action_costs.pickup`. |
| `PICKUP_TOOL(id)` | La herramienta está en el suelo de la zona actual; hay capacidad disponible; hay batería suficiente. | La herramienta pasa del suelo al inventario. | `action_costs.pickup`. |
| `PICKUP_MATERIAL(tipo)` | Existe una unidad del material en la zona actual; hay capacidad disponible; hay batería suficiente. | Disminuye la cantidad del material en el suelo y aumenta la cantidad en el inventario. | `action_costs.pickup`. |
| `DROP_KEY(id)` | La llave está en el inventario, su puerta ya está abierta y hay batería suficiente. | La llave pasa al suelo de la zona actual. | `action_costs.drop`. |
| `DROP_TOOL(id)` | La herramienta está en el inventario, ya no es necesaria para paneles pendientes y hay batería suficiente. | La herramienta pasa al suelo de la zona actual. | `action_costs.drop`. |
| `OPEN_DOOR(id)` | El robot está junto a la puerta; está cerrada; la llave correspondiente está en el inventario; hay batería suficiente. | La puerta pasa a `OPEN` y disminuye la batería. | `action_costs.interact`. |
| `REPAIR(panel, material)` | El robot está en la zona del panel; el panel está dañado; tiene la herramienta requerida; tiene el material requerido; hay batería suficiente. | El panel pasa a `OK`, se consume una unidad del material y disminuye la batería. | `action_costs.interact`. |
| `ACTIVATE(station)` | El robot está en la zona de la estación; está offline; se cumplen sus dependencias; hay batería suficiente. | La estación pasa a `ONLINE` y disminuye la batería. | `action_costs.interact`. |
| `RECHARGE(charger)` | El robot está en la zona del cargador; la batería no está llena; puede pagar el costo de recarga. | La batería se establece en `battery_max`. | `action_costs.recharge`. |

---


### `Applicable` interno vs legalidad del contrato

El simulador define las acciones físicamente legales. El agente, además, puede
restringir las acciones que genera cuando una acción legal nunca puede formar
parte de un plan óptimo.

La principal restricción se aplica a `DROP`.

El contrato permite soltar un objeto en cualquier zona si el objeto está en el
inventario. Sin embargo, generar todos los `DROP` posibles produce muchas
combinaciones de posiciones de objetos y aumenta innecesariamente el espacio
de búsqueda.

El agente solamente genera:

- `DROP_KEY` cuando la puerta asociada ya está abierta;
- `DROP_TOOL` cuando la herramienta ya no es necesaria;
- no genera `DROP_MATERIAL`.

La justificación es la siguiente:

- soltar una llave antes de abrir su puerta no ayuda y puede obligar a
  recogerla de nuevo;
- soltar una herramienta antes de terminar los paneles que la requieren puede
  obligar a recogerla de nuevo;
- un material que todavía no se necesita puede quedarse en el suelo;
- un material necesario se recoge y se consume directamente al reparar;
- recoger y soltar un material sin utilizarlo añade costo y no produce
  progreso.

La restricción conserva las soluciones óptimas porque elimina acciones que
agregan costo sin habilitar una acción nueva.

---

## Modelo de transición

```text
s  --a-->  s'     solo si a ∈ Applicable(s)
```

El modelo de transición es determinista y parcial:

- determinista porque una acción aplicada a un estado produce un único estado;
- parcial porque una acción no se puede aplicar si no cumple sus
  precondiciones.

### Cambios posibles

Una acción puede modificar:

- la zona del robot;
- la batería;
- el inventario;
- la ubicación de objetos en el suelo;
- las puertas abiertas;
- los paneles reparados;
- las estaciones activadas.

### Propiedades que se preservan

La transición conserva:

- el escenario;
- los corredores declarados;
- los costos oficiales;
- la capacidad;
- la batería máxima;
- las propiedades de los objetos;
- las dependencias de paneles y estaciones.

### Representación canónica

Después de cada acción se construye un nuevo objeto `Estado`. Las colecciones
se almacenan de forma inmutable y canónica:

- `frozenset` para conjuntos;
- pares para ids y zonas;
- pares para tipos y cantidades;
- tuplas para el hash del estado completo.

Esto garantiza que estados físicamente equivalentes tengan la misma igualdad y
el mismo hash.

---

## Prueba de meta

```text
Goal(s) ⟺
todas las estaciones indicadas en goal.stations_online
pertenecen a s.stations_on
```

En Python, la prueba se implementa conceptualmente como:

```python
all(
    station_id in estado.stations_on
    for station_id in scenario["goal"]["stations_online"]
)
```

Las puertas y los paneles no son la meta principal. Son medios necesarios para
llegar a ella:

- las puertas abiertas permiten desplazarse;
- los paneles reparados pueden ser dependencias;
- las estaciones online satisfacen la misión.

La meta se comprueba cuando el nodo se extrae de la frontera de UCS. No se
comprueba únicamente al generar un sucesor, porque el primer nodo meta extraído
es el que tiene el menor costo acumulado.

---

## Función de costo

```text
g(n) = Σ costo(aᵢ)
```

El costo acumulado es la suma de los costos oficiales de todas las acciones
desde el estado inicial hasta el nodo actual.

Los costos se obtienen del escenario:

- `MOVE`: costo del corredor utilizado;
- `PICKUP`: costo de recoger;
- `DROP`: costo de soltar;
- `INTERACT` con `OPEN_DOOR`, `REPAIR` o `ACTIVATE`: costo de interactuar;
- `INTERACT` con `RECHARGE`: costo de recargar.

El costo total del plan es:

```text
total_cost = sum(step["cost"] for step in steps)
```

Minimizar la cantidad de pasos no es lo mismo que minimizar el costo. Un plan
con menos pasos puede utilizar corredores o acciones más costosas que un plan
con más pasos.

Por esa razón se utiliza UCS y se ordena la frontera por el costo acumulado,
no por la cantidad de acciones.

---

## Estrategia de búsqueda
## Uniform Cost Search

Se utiliza Uniform Cost Search porque:

- los costos de las acciones son diferentes;
- todos los costos oficiales son positivos;
- se busca un plan de costo total mínimo;
- el espacio es discreto;
- el entorno es determinista;
- el plan puede reconstruirse a partir de estados padre.

La frontera se implementa con un `heapq`. Cada elemento contiene:

```text
(costo_acumulado, contador, estado)
```

El contador se utiliza únicamente para desempatar nodos que tengan el mismo
costo y evitar que Python compare directamente objetos `Estado`.


### Funcionamiento

El algoritmo realiza estos pasos:

1. Construye el estado inicial a partir de `scenario.json`.
2. Inserta el estado inicial en la frontera con costo cero.
3. Extrae el estado de menor costo acumulado.
4. Comprueba si el estado satisface la meta.
5. Si ya fue visitado, lo descarta.
6. Lo agrega a `CLOSED`.
7. Genera sus sucesores aplicables.
8. Calcula el nuevo costo de cada sucesor.
9. Inserta los sucesores en la frontera.
10. Repite hasta hallar la meta o hasta vaciar la frontera.

### Completitud

UCS es completo bajo estas condiciones:

- el espacio de estados es finito;
- cada estado genera un número finito de sucesores;
- los costos son positivos;
- las podas no eliminan acciones necesarias para alcanzar la solución.

El escenario tiene un número finito de zonas, objetos, puertas, paneles,
estaciones y cantidades de materiales. Por tanto, utilizando una
representación canónica y evitando ciclos inútiles, el espacio es finito.

### Optimalidad

UCS es óptimo cuando todos los costos son no negativos y la meta se comprueba
al extraer el nodo de menor costo de la frontera.

En este agente, el costo de un sucesor se calcula como:

```text
nuevo_costo = costo_actual + costo_accion
```

La meta se prueba al extraer el nodo, no al generarlo. Por lo tanto, el primer
estado meta extraído es el de menor costo entre las soluciones representadas
por el modelo.

Las garantías de completitud u optimalidad podrían romperse si:

- se utilizaran costos negativos;
- se alteraran los costos oficiales;
- se incluyera el historial dentro del estado;
- los estados no fueran canónicos;
- se podaran estados que no estén realmente dominados;
- se detuviera UCS antes de extraer correctamente un estado meta;
- se ignorara la batería;
- se modificara artificialmente el escenario.

### `CLOSED`

`CLOSED` almacena estados físicos canónicos ya procesados.

Gracias a `__eq__` y `__hash__`, dos caminos que llegan a la misma
configuración física se reconocen como el mismo estado. Así se evita expandir
repetidamente la misma situación.

---

### Batería como recurso

La batería sí pertenece al estado porque puede impedir que una acción sea
legal.

Antes de generar una acción se comprueba:

```text
bateria >= costo
```

Para una acción normal:

```text
bateria_nueva = bateria_actual - costo
```

Para `RECHARGE`:

1. se verifica que haya batería suficiente para pagar la recarga;
2. se paga el costo;
3. la batería se establece en `battery_max`.

La recarga no se genera cuando la batería ya está llena.

### Dominancia

La batería puede producir varios estados con el mismo mundo físico pero
diferente energía restante.

Sea `m` la configuración física sin considerar la batería. Un estado `A`
domina a otro estado `B` si:

```text
m(A) = m(B)
costo(A) <= costo(B)
bateria(A) >= bateria(B)
```

Si `A` domina a `B`, cualquier continuación posible desde `B` también puede
realizarse desde `A`, porque `A` tiene al menos la misma batería y no costó más
llegar a esa configuración.

Por tanto, un estado dominado puede descartarse sin perder una solución óptima.

La comparación debe considerar simultáneamente:

- la misma configuración física;
- el costo acumulado;
- la batería restante.

No es correcto descartar un estado únicamente porque tenga menos batería si
llegó con un costo menor. Una implementación completa debe mantener etiquetas
no dominadas por cada configuración física.

---

## Formulación y tamaño del espacio (obligatorio)

### 1. Por qué el espacio puede generar millones de nodos

Aunque el mapa tenga pocas zonas, el estado completo combina muchas variables:

- posición del robot;
- batería restante;
- objetos del inventario;
- objetos en el suelo;
- puertas abiertas;
- paneles reparados;
- estaciones online;
- cantidades de materiales.

Con aproximadamente diez objetos y capacidad limitada, cada objeto puede estar
en distintas zonas, en el inventario o haber sido consumido. Además, cada
puerta, panel y estación puede tener diferentes estados.

El producto de todas esas posibilidades puede generar millones de estados,
aunque visualmente el mapa solo tenga unas pocas zonas.

### 2. Papel de `DROP`

`DROP` es una de las principales causas de explosión combinatoria.

Si se genera un `DROP` arbitrario en cada zona, cada objeto del inventario puede
quedar en varios lugares. Después, el algoritmo puede volver a recogerlo y
soltarlo en otra zona, generando permutaciones que no aportan progreso.

Por esta razón, el agente no genera todos los `DROP` permitidos por el
simulador, sino solamente los que pueden ser necesarios para liberar capacidad
después de cumplir una función.

### 3. Podas y abstracciones aplicadas

El agente aplica las siguientes medidas:

1. Representa los estados con estructuras canónicas e inmutables.
2. Utiliza `CLOSED` para evitar reexpandir estados equivalentes.
3. No genera movimientos a través de puertas cerradas.
4. No genera acciones sin batería suficiente.
5. No permite recoger objetos si se excede la capacidad.
6. Solo permite soltar una llave después de abrir su puerta.
7. Solo permite soltar una herramienta cuando ya no se necesita.
8. No genera `DROP` de materiales.
9. No repite reparaciones, activaciones o aperturas ya realizadas.
10. No recarga una batería que ya está llena.
11. Puede descartar estados dominados cuando se verifica la comparación
    completa entre mundo, costo y batería.

Estas podas son `sound` porque eliminan acciones que no producen progreso, que
solamente agregan costo o que pueden reemplazarse por una secuencia igual o
mejor.

### 4. Por qué no se debe modificar artificialmente el escenario

No es una solución:

- aumentar la capacidad de carga;
- ignorar la batería;
- eliminar estaciones;
- eliminar puertas;
- reducir los costos;
- utilizar únicamente el plan de demostración;
- codificar los ids y posiciones de una sola instancia.

El profe puede ejecutar el agente con otro escenario. Por eso el agente debe
leer todas las propiedades desde `scenario.json` y respetar el contrato.

La dificultad debe resolverse mediante una representación correcta del estado,
sucesores relevantes, canonicalización y búsqueda UCS.

---

## Traducción al contrato externo

El agente puede utilizar nombres internos como:

```text
MOVE
PICKUP_KEY
PICKUP_TOOL
PICKUP_MATERIAL
DROP_KEY
DROP_TOOL
OPEN_DOOR
REPAIR
ACTIVATE
RECHARGE
```

Sin embargo, el frontend solamente acepta las siguientes operaciones externas:

```text
MOVE
PICKUP
DROP
INTERACT
```

La función `_traducir` convierte las acciones internas al formato exigido por
el contrato.

Las correspondencias son:

| Acción interna | Acción externa |
|---|---|
| `MOVE` | `MOVE` |
| `PICKUP_KEY` | `PICKUP` |
| `PICKUP_TOOL` | `PICKUP` |
| `PICKUP_MATERIAL` | `PICKUP` |
| `DROP_KEY` | `DROP` |
| `DROP_TOOL` | `DROP` |
| `OPEN_DOOR` | `INTERACT` con `action: OPEN_DOOR` |
| `REPAIR` | `INTERACT` con `action: REPAIR` |
| `ACTIVATE` | `INTERACT` con `action: ACTIVATE` |
| `RECHARGE` | `INTERACT` con `action: RECHARGE` |

Por ejemplo, una reparación interna se traduce a:

```json
{
  "op": "INTERACT",
  "target": "PANEL_A",
  "action": "REPAIR",
  "consumes": "FUSE",
  "cost": 2
}
```

El frontend no ejecuta directamente las acciones internas. Ejecuta el plan
traducido y vuelve a comprobar sus pasos contra el simulador oficial.

---

## Correspondencia entre diseño e implementación

La implementación de `agent.py` contiene:

- la clase `Estado`;
- la construcción del estado inicial;
- el cálculo del peso del inventario;
- la generación de sucesores;
- la validación de precondiciones;
- la búsqueda UCS;
- la reconstrucción del plan;
- la traducción al formato del contrato;
- la respuesta de `solve_scenario`.

La respuesta del agente tiene la estructura:

```json
{
  "solution_found": true,
  "total_cost": 82,
  "steps": [],
  "message": "UCS agent"
}
```

Los ids, costos, zonas, pesos y dependencias se obtienen del escenario y no se
deben fijar directamente dentro del algoritmo.

---

## 4.1. Estado

El estado representa una configuración instantánea y completa del simulador que contiene toda la información necesaria para determinar qué acciones futuras son válidas.

Formalmente, un estado $s$ se define como una tupla:


$$s = \langle z, b, P_k, P_t, P_m, G_k, G_t, G_m, D, R, S \rangle$$

Donde las variables necesarias son:

* $z$: La zona actual donde se encuentra el robot.
* $b$: El nivel de batería actual del robot.
* $P_k, P_t, P_m$: Los conjuntos de llaves (keys), herramientas (tools) y materiales (materials) que actualmente están cargados en el inventario (payload) del robot.
* $G_k, G_t, G_m$: La distribución en el entorno (ground) de las llaves, herramientas y materiales, mapeando cada objeto a la zona donde se encuentra tirado o disponible.
* $D$: El conjunto de puertas (`doors_open`) que ya han sido abiertas.
* $R$: El conjunto de paneles (`panels_ok`) que ya han sido reparados.
* $S$: El conjunto de estaciones de emergencia (`stations_on`) que ya han sido activadas.

**Justificación de las variables:**
Cada variable es estrictamente necesaria para validar precondiciones. La zona $z$ restringe el movimiento y las interacciones locales. La batería $b$ limita cualquier acción. Los inventarios $P$ y $G$ determinan si es posible hacer un `PICKUP`, un `DROP` o interacciones de consumo. Los conjuntos de progreso $D, R, S$ evitan repetir acciones inútiles (como abrir una puerta abierta) y validan las dependencias en cadena requeridas para ganar el juego.

**Información derivada:**
El peso actual de la carga no es una variable de estado intrínseca. Se deriva matemáticamente sumando el peso constante de los elementos presentes en $P_k$, $P_t$ y $P_m$ consultando el diccionario estático de propiedades del escenario.

**Información excluida del estado:**
El costo acumulado hasta el momento $g(n)$, el nodo padre y la secuencia de pasos ejecutados pertenecen a la estructura del **nodo de búsqueda** (historial), pero no al **estado físico**.

**Equivalencia de estados:**
Dos configuraciones se consideran el mismo estado si y solo si todos los elementos de la tupla coinciden exactamente (implementado mediante sobrecarga de `__eq__` y `__hash__` usando colecciones inmutables `frozenset`). Llegar a la misma disposición de objetos y batería en un mismo cuarto constituye el mismo estado, sin importar el orden temporal en que se recogieron los objetos.

---
## 4.2. Acciones

El agente dispone de un conjunto finito de acciones legales que transforman el entorno. Cada acción tiene precondiciones, efectos y un costo oficial definido en el escenario.

* **MOVE(to):**
* *Precondiciones:* Existe un corredor entre la zona actual $z$ y la zona destino, la puerta (si existe) está abierta (pertenece al conjunto $D$), y la batería $b$ es mayor o igual al costo del movimiento.


* *Efectos:* La zona actual del robot se actualiza y la batería disminuye.
* *Costo:* Costo específico del corredor utilizado.




* **PICKUP(item):**
* *Precondiciones:* El objeto está en el suelo de la zona actual, hay batería suficiente, y el peso actual del inventario más el del nuevo objeto no excede la capacidad máxima de carga del robot.


* *Efectos:* El objeto se elimina del entorno ($G$) y se añade al inventario ($P$).
* *Costo:* Costo oficial definido en `action_costs.pickup`.




* **INTERACT(target, action):**
* *Precondiciones:* Varían según la operación (`OPEN_DOOR`, `REPAIR`, `ACTIVATE`, `RECHARGE`). Requieren estar en la zona correcta, tener batería suficiente, y poseer las llaves, herramientas o materiales necesarios en el inventario. Para activar estaciones, deben cumplirse las dependencias previas (paneles y estaciones requeridas).


* *Efectos:* Modifican el estado del mundo ($D$, $R$, o $S$). Los materiales utilizados en reparaciones se consumen (se eliminan de $P$) y las recargas restauran la batería $b$ a su máximo.


* *Costo:* Costo oficial de interactuar o recargar.




* **DROP(item):**
* *Justificación de Diseño (Restricción algorítmica):* Aunque el simulador físico permite dejar objetos libremente en cualquier zona, el agente **no** expone esta acción de forma independiente como un sucesor libre. Hacerlo convertiría el espacio de estados en un problema combinatorio sobre la ubicación de cada objeto, colapsando la búsqueda. El agente asegura la completitud y el óptimo restringiendo el `DROP` a dos escenarios donde es lógicamente indispensable:


1. Para liberar espacio acoplado a un `PICKUP` cuando el robot excede su capacidad.
2. Como descarte automático tras un `INTERACT` si la herramienta o llave utilizada ya no tiene ningún objetivo útil restante en el mapa.





## 4.3. Modelo de Transición

El modelo de transición determina cómo el mundo cambia al aplicar una acción legal $a$ en un estado $s$, generando un nuevo estado $s'$.

Dado el estado $s = \langle z, b, P, G, D, R, S \rangle$, la función de transición (implementada como la generación de `sucesores`) aplica los efectos descritos en la sección de acciones. Por ejemplo, si $a = \text{INTERACT}(\text{target}, \text{REPAIR})$, entonces $s'$ heredará todas las propiedades de $s$, pero tendrá una batería $b' = b - \text{costo}$, el material consumido desaparecerá del inventario $P'$, y el identificador del panel reparado se añadirá al conjunto $R'$. El modelo asume un entorno determinista.

## 4.4. Prueba de Meta

La prueba de meta $Goal(s)$ no se basa en verificar si se ejecutó una lista secuencial de tareas, sino en constatar una condición física final en el mundo.

Sea $S_{goal}$ el conjunto de estaciones de emergencia que el escenario exige activar. Un estado $s$ satisface la meta si y solo si todas las estaciones objetivo están incluidas en el conjunto de estaciones encendidas del estado actual:


$$S_{goal} \subseteq s.S$$

## 4.5. Función de Costo

La función de costo $g(n)$ representa el esfuerzo o gasto acumulado desde el estado inicial hasta el nodo de búsqueda actual $n$. Se define de manera aditiva:


$$g(n) = g(n_{padre}) + c(n_{padre}, a, n)$$

Donde el costo de la transición $c$ corresponde estrictamente a los valores oficiales estipulados por el contrato del simulador. Dado que todos los costos oficiales son no negativos, la función $g(n)$ garantiza un crecimiento monótono, condición matemática necesaria para la correcta aplicación y optimalidad del algoritmo UCS.

---

## 4.6. Estrategia de Búsqueda

Para resolver este problema, se ha implementado el algoritmo de **Búsqueda de Costo Uniforme (UCS / Uniform Cost Search)**.

**Justificación de la elección:**
El entorno "Emergency Control" asocia un costo no negativo distinto a cada operación (por ejemplo, moverse por distintos pasillos cuesta diferente cantidad de energía). Como la misión requiere encontrar el plan que minimice el costo acumulado total $g(n)$, algoritmos como BFS (que minimizan la cantidad de pasos) son incorrectos. UCS garantiza la expansión mediante contornos de costo creciente, asegurando la resolución óptima.

**Completitud y Optimalidad:**
UCS es completo y óptimo siempre que el costo de cada acción sea estrictamente mayor que cero (o al menos no negativo) y el factor de ramificación sea finito. En este diseño, todas las acciones consumen costos positivos oficiales definidos en `scenario.json`, lo que garantiza que el algoritmo no quedará atrapado en bucles infinitos intentando acumular pasos de costo cero.

**Manejo del Tiempo y Espacio (Optimización de Pareto):**
La complejidad temporal y espacial de UCS depende críticamente del factor de ramificación. Si bien el simulador permite soltar objetos (`DROP`) en cualquier momento, el agente restringe esta acción algorítmicamente para evitar una explosión combinatoria inmanejable.
Adicionalmente, para optimizar la memoria (Lista de Cerrados), el algoritmo emplea un **filtro de dominancia de Pareto**. Si se descubre una ruta hacia un mundo físico idéntico $\langle z, P, G, D, R, S \rangle$, pero con un costo $g(n)$ mayor y un nivel de batería $b$ menor que una ruta previamente explorada, ese nuevo estado es descartado inmediatamente porque está lógicamente "dominado" y nunca podrá generar un plan futuro mejor.

---

## Validación

La prueba de integración del agente comprueba:

1. que UCS encuentre una solución;
2. que el plan no esté vacío;
3. que el simulador oficial pueda ejecutar todos los pasos;
4. que se alcance la meta;
5. que solo se utilicen `MOVE`, `PICKUP`, `DROP` e `INTERACT`;
6. que las acciones de `INTERACT` sean válidas;
7. que cada paso tenga el costo oficial;
8. que `total_cost` sea la suma de los costos de los pasos.

El comando utilizado para ejecutar la prueba es:

```powershell
cd project/backend
python tests\test_agent_plan.py
```

El mensaje:

```text
All UCS agent tests passed.
```

indica que las comprobaciones implementadas en la prueba terminaron sin errores.

En el escenario utilizado durante la validación, el agente produce un plan
ejecutable con costo total:

```text
82
```


La prueba valida la correspondencia del plan con el contrato y con el
simulador. La justificación de la búsqueda de menor costo se encuentra en la
sección de UCS.
```