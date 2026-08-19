# Emergency Control — Agente racional con UCS

Proyecto de un agente racional para el escenario `Emergency Control`.

El agente utiliza **Uniform Cost Search (UCS)** para encontrar un plan legal de
costo mínimo. El plan se valida mediante el simulador oficial y luego se
ejecuta visualmente en el frontend.

## Estructura del proyecto

```text
project/
├── backend/
│   ├── requirements.txt
│   ├── src/
│   │   ├── agent.py
│   │   ├── main.py
│   │   └── simulator.py
│   └── tests/
│       └── test_agent_plan.py
├── frontend/
├── scenarios/
│   └── scenario.json
├── CONTRATO.md
├── design.md
└── README.md
```

### Archivos principales

- `backend/src/agent.py`: implementación del agente UCS.
- `backend/src/main.py`: API FastAPI.
- `backend/src/simulator.py`: simulador y validador oficial.
- `backend/tests/test_agent_plan.py`: pruebas del agente.
- `scenarios/scenario.json`: escenario y costos oficiales.
- `CONTRATO.md`: reglas que debe cumplir el plan.
- `design.md`: diseño formal del estado, acciones y búsqueda.
- `frontend/`: interfaz visual para ejecutar el plan.

## Requisitos

Se necesita tener instalado:

- Python 3.11 o una versión compatible;
- Node.js y npm;
- Git, si el repositorio se descarga desde GitHub.

Para comprobar las instalaciones:

```powershell
python --version
node --version
npm --version
```

## Iniciar el backend

El backend debe iniciarse desde la carpeta `backend`.

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --app-dir src --port 8000
```

Si el backend inicia correctamente, quedará disponible en:

```text
http://127.0.0.1:8000
```

### Comprobar el backend

En otra terminal se puede comprobar el endpoint de salud:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

La respuesta esperada es:

```json
{
  "status": "ok"
}
```

También se puede abrir directamente en el navegador:

```text
http://127.0.0.1:8000/api/health
```

El endpoint que calcula el plan es:

```text
POST http://127.0.0.1:8000/api/solve
```

El backend no debe cerrarse mientras se esté utilizando el frontend.

## Iniciar el frontend

Con el backend ejecutándose, se abre una segunda terminal.

Desde la carpeta raíz del proyecto:

```powershell
cd frontend
npm run dev
```

Vite mostrará una dirección parecida a:

```text
http://localhost:5173
```

La dirección exacta debe ser la que aparezca en la terminal.

Abrir esa dirección en el navegador.

El frontend se comunica con el backend mediante:

```text
POST /api/solve
```

El proxy del frontend redirige esa solicitud al backend que está ejecutándose
en el puerto `8000`.

## Ejecutar el agente directamente

Para ejecutar el agente UCS sin utilizar el frontend, se debe abrir una
terminal en la carpeta `backend`, activar el entorno virtual y ejecutar
`agent.py`:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python src/agent.py
```

El agente lee el escenario desde:

```text
scenarios/scenario.json
```

y muestra en la terminal el resultado en formato JSON.

Una solución exitosa tiene una estructura similar a esta:

```json
{
  "solution_found": true,
  "total_cost": 82,
  "steps": [
    {
      "op": "PICKUP",
      "item": "KEY1",
      "cost": 1
    }
  ],
  "message": "UCS agent"
}
```

El plan puede tardar porque UCS explora diferentes configuraciones del mundo.
Mientras busca, el agente muestra mensajes de progreso, por ejemplo:

```text
... explorando, nodos vistos: 20000, frontera: 15000
```

Ese mensaje significa que la búsqueda continúa explorando estados.

## Ejecutar las pruebas del agente

Las pruebas deben ejecutarse desde la carpeta `backend`.

Primero se activa el entorno virtual:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
```

Después se ejecuta:

```powershell
python tests/test_agent_plan.py
```

El archivo de pruebas verifica que:

1. UCS encuentre una solución;
2. el plan tenga pasos;
3. el plan sea ejecutable por el simulador oficial;
4. la misión llegue a la meta;
5. las operaciones utilizadas sean legales;
6. las acciones `INTERACT` sean válidas;
7. los costos individuales sean correctos;
8. `total_cost` sea igual a la suma de los costos de todos los pasos.

Si todas las pruebas pasan, aparecerá:

```text
All UCS agent tests passed.
```

Este mensaje significa que todas las comprobaciones incluidas en
`test_agent_plan.py` terminaron correctamente.

Si alguna prueba falla, Python mostrará un error indicando qué validación no se
cumplió.

## Probar una misión visualmente

Para probar la misión desde el frontend:

### 1. Iniciar el backend

En la primera terminal:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --app-dir src --port 8000
```

### 2. Iniciar el frontend

En la segunda terminal:

```powershell
cd frontend
npm run dev
```

### 3. Abrir la aplicación

Abrir en el navegador la dirección mostrada por Vite, normalmente:

```text
http://localhost:5173
```

### 4. Ejecutar la misión

En la interfaz:

1. cargar o utilizar el escenario predeterminado;
2. pulsar el botón `EXECUTE PLAN`;
3. esperar la respuesta de `/api/solve`;
4. observar la ejecución paso a paso del robot.

El frontend debe mostrar el plan recibido y ejecutar las operaciones:

```text
MOVE
PICKUP
DROP
INTERACT
```

Las acciones como `OPEN_DOOR`, `REPAIR`, `ACTIVATE` y `RECHARGE` aparecen
dentro de `INTERACT`.

Por ejemplo:

```json
{
  "op": "INTERACT",
  "target": "PANEL_A",
  "action": "REPAIR",
  "consumes": "FUSE",
  "cost": 2
}
```

## Interpretación del resultado

### Misión exitosa

Una respuesta exitosa contiene:

```json
{
  "solution_found": true,
  "total_cost": 82,
  "steps": [...]
}
```

Esto significa que:

- el agente encontró un plan;
- el plan contiene acciones;
- el costo total fue calculado;
- las acciones cumplen el contrato;
- el plan puede ser validado por el simulador;
- la misión llega a las estaciones objetivo.

El campo `total_cost` es la suma de los costos de todos los pasos:

```text
total_cost = suma de los costos individuales
```

El costo no representa necesariamente la cantidad de pasos. UCS minimiza el
costo total, no la longitud del plan.

### Misión no encontrada

Una respuesta como:

```json
{
  "solution_found": false,
  "total_cost": 0,
  "steps": [],
  "message": "No solution found (UCS)"
}
```

significa que el agente no encontró una solución dentro de las condiciones de
búsqueda.

Las posibles causas son:

- el escenario no tiene solución;
- no hay batería suficiente;
- faltan llaves, herramientas o materiales;
- una dependencia de una estación no puede cumplirse;
- se alcanzó el tiempo máximo de búsqueda.

## Contrato de operaciones

El frontend solamente ejecuta estas cuatro operaciones principales:

```text
MOVE
PICKUP
DROP
INTERACT
```

Las acciones siguientes no son operaciones principales independientes. Son
valores del campo `action` dentro de un paso `INTERACT`:

```text
OPEN_DOOR
REPAIR
ACTIVATE
RECHARGE
```

Ejemplo:

```json
{
  "op": "INTERACT",
  "target": "DOOR1",
  "action": "OPEN_DOOR",
  "cost": 2
}
```

El agente puede utilizar acciones internas con otros nombres durante la
búsqueda, pero antes de devolver el resultado debe traducirlas al formato
definido en `CONTRATO.md`.

## Relación entre los archivos

- `scenario.json` define las zonas, objetos, costos y dependencias.
- `CONTRATO.md` define las operaciones y reglas legales.
- `agent.py` busca un plan de costo mínimo respetando el escenario.
- `simulator.py` valida que el plan sea legal.
- `main.py` expone el agente mediante la API.
- El frontend anima visualmente el plan retornado por la API.
- `design.md` explica y justifica las decisiones del agente.

## Resultado validado

Durante la validación del escenario utilizado, el agente encontró una solución
UCS con:

```text
solution_found: true
total_cost: 82
```

El resultado debe considerarse válido cuando:

1. `solution_found` es `true`;
2. el plan tiene pasos;
3. el simulador ejecuta todos los pasos;
4. las estaciones objetivo terminan en `ONLINE`;
5. las pruebas muestran:

```text
All UCS agent tests passed.
```
