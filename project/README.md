# Proyecto — Emergency Control

Frontend 3D del profesor + API demo (sin IA). El enunciado está en el `README.MD` de la raíz.

## Estructura

```text
project/
├── frontend/          # React + R3F — simulación 3D voxel
├── backend/           # FastAPI — POST /api/solve (plan demo)
├── scenarios/         # scenario.json — fuente de verdad
├── design.md
└── README.md
```

## Cómo levantar (tú)

Abre **dos terminales**.

### Terminal 1 — Backend

```bash
cd project/backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --app-dir src --port 8000
```

Comprobar: http://127.0.0.1:8000/api/health

### Terminal 2 — Frontend

```bash
cd project/frontend
npm install
npm run dev
```

Abrir: http://localhost:5173

Pulsa **EXECUTE PLAN**. El frontend llama a `/api/solve` (proxy Vite → puerto 8000) y reproduce el plan casilla a casilla.

### Tests del plan demo

```bash
cd project/backend
.\.venv\Scripts\activate
python tests/test_demo_plan.py
```

## Contrato visual vs agente (importante)

La versión oficial y completa de este contrato (esquema JSON, acciones de `INTERACT`, reglas del mundo y costos) está en `../CONTRATO.md`, que forma parte del enunciado.

El enunciado fija **4 operaciones visuales** que el frontend entiende:

```text
MOVE | PICKUP | DROP | INTERACT
```

`REPAIR`, `ACTIVATE`, `OPEN_DOOR`, `RECHARGE` **no son ops del plan de alto nivel**: son el campo `action` dentro de un paso `INTERACT`.

Ejemplo de lo que debe devolver `/api/solve`:

```json
{ "op": "INTERACT", "target": "PANEL_A", "action": "REPAIR", "consumes": "FUSE", "cost": 2 }
```

- **Agente (estudiante):** puede modelar acciones internas (`REPAIR_PANEL_A`, etc.) y luego **traducirlas** a `MOVE`/`PICKUP`/`DROP`/`INTERACT`.
- **Frontend / banco de pruebas:** solo ejecuta esas 4 ops. El log muestra `INTERACT REPAIR ...` para dejar claro el `op` + el `action`.

Así no hay contradicción: la capa visual no define la IA; solo anima el plan ya traducido.
