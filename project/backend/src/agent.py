"""Agente racional para Emergency Control — búsqueda UCS (Costo Uniforme)."""

from __future__ import annotations

import heapq
import itertools


class Estado:
    __slots__ = (
        "zona", "bateria",
        "payload_keys", "payload_tools", "payload_materials",
        "ground_keys", "ground_tools", "ground_materials",
        "doors_open", "panels_ok", "stations_on",
    )

    def __init__(self, zona, bateria,
                 payload_keys, payload_tools, payload_materials,
                 ground_keys, ground_tools, ground_materials,
                 doors_open, panels_ok, stations_on):
        self.zona = zona
        self.bateria = bateria
        self.payload_keys = frozenset(payload_keys)
        self.payload_tools = frozenset(payload_tools)
        self.payload_materials = frozenset(payload_materials.items())
        self.ground_keys = frozenset(ground_keys.items())
        self.ground_tools = frozenset(ground_tools.items())
        self.ground_materials = frozenset(
            (t, z, c) for t, (z, c) in ground_materials.items()
        )
        self.doors_open = frozenset(doors_open)
        self.panels_ok = frozenset(panels_ok)
        self.stations_on = frozenset(stations_on)

    def _tupla(self):
        return (self.zona, self.bateria, self.payload_keys, self.payload_tools,
                self.payload_materials, self.ground_keys, self.ground_tools,
                self.ground_materials, self.doors_open, self.panels_ok,
                self.stations_on)

    def _mundo(self):
        t = self._tupla()
        return t[:1] + t[2:]

    def __eq__(self, otro):
        return isinstance(otro, Estado) and self._tupla() == otro._tupla()

    def __hash__(self):
        return hash(self._tupla())

    def dict_ground_keys(self):
        return dict(self.ground_keys)

    def dict_ground_tools(self):
        return dict(self.ground_tools)

    def dict_ground_materials(self):
        return {t: (z, c) for t, z, c in self.ground_materials}

    def dict_payload_materials(self):
        return dict(self.payload_materials)

    def peso_actual(self, pesos):
        total = 0
        for kid in self.payload_keys:
            total += pesos["keys"].get(kid, 1)
        for tid in self.payload_tools:
            total += pesos["tools"].get(tid, 1)
        for mtype, cnt in self.payload_materials:
            total += pesos["materials"].get(mtype, 1) * cnt
        return total


def estado_inicial(scenario):
    ground_keys = {k["id"]: k["zone"] for k in scenario["keys"]}
    ground_tools = {t["id"]: t["zone"] for t in scenario["tools"]}
    ground_materials = {m["type"]: (m["zone"], m["count"]) for m in scenario["materials"]}
    return Estado(
        zona=scenario["robot"]["start"],
        bateria=scenario["robot"]["battery_start"],
        payload_keys=set(), payload_tools=set(), payload_materials={},
        ground_keys=ground_keys, ground_tools=ground_tools, ground_materials=ground_materials,
        doors_open=set(), panels_ok=set(), stations_on=set(),
    )


def _construir_indices(scenario):
    idx = {}
    idx["corridors"] = scenario["corridors"]
    idx["doors"] = {d["id"]: d for d in scenario["doors"]}
    idx["panels"] = {p["id"]: p for p in scenario["panels"]}
    idx["stations"] = {s["id"]: s for s in scenario["stations"]}
    idx["chargers"] = scenario.get("chargers", [])
    idx["capacity"] = scenario["robot"]["cargo_capacity"]
    idx["battery_max"] = scenario["robot"]["battery_max"]
    costs = scenario.get("action_costs", {})
    idx["c_pickup"] = costs.get("pickup", 1)
    idx["c_drop"] = costs.get("drop", 1)
    idx["c_interact"] = costs.get("interact", 2)
    idx["c_recharge"] = costs.get("recharge", 3)
    idx["pesos"] = {
        "keys": {k["id"]: k.get("weight", 1) for k in scenario["keys"]},
        "tools": {t["id"]: t.get("weight", 1) for t in scenario["tools"]},
        "materials": {m["type"]: m.get("weight", 1) for m in scenario["materials"]},
    }
    key_to_doors = {}
    for d in scenario["doors"]:
        key_to_doors.setdefault(d["key"], []).append(d["id"])
    idx["key_to_doors"] = key_to_doors
    tool_to_panels = {}
    for p in scenario["panels"]:
        tool_to_panels.setdefault(p["requires"]["tool"], []).append(p["id"])
    idx["tool_to_panels"] = tool_to_panels
    return idx


def sucesores(estado, idx):
    out = []
    zona = estado.zona
    bateria = estado.bateria
    peso_actual = estado.peso_actual(idx["pesos"])
    capacidad = idx["capacity"]

    ground_keys = estado.dict_ground_keys()
    ground_tools = estado.dict_ground_tools()
    ground_materials = estado.dict_ground_materials()
    payload_materials = estado.dict_payload_materials()

    # --- MOVE ---
    for c in idx["corridors"]:
        if c["from"] != zona:
            continue
        costo = c["cost"]
        if bateria < costo:
            continue
        if c.get("door") is not None and c["door"] not in estado.doors_open:
            continue
        nuevo = Estado(
            zona=c["to"], bateria=bateria - costo,
            payload_keys=estado.payload_keys, payload_tools=estado.payload_tools,
            payload_materials=payload_materials,
            ground_keys=ground_keys, ground_tools=ground_tools,
            ground_materials=ground_materials,
            doors_open=estado.doors_open, panels_ok=estado.panels_ok,
            stations_on=estado.stations_on,
        )
        out.append((costo, nuevo, [{"op": "MOVE", "from": zona, "to": c["to"], "cost": costo}]))

    c_pickup = idx["c_pickup"]
    c_drop = idx["c_drop"]

    # --- PICKUP (con DROP acoplado solo si hace falta liberar capacidad) ---
    def generar_pickup(oid, peso_obj, zona_obj, aplicar_pickup):
        if zona_obj != zona:
            return
        if bateria < c_pickup:
            return
        if peso_actual + peso_obj <= capacidad:
            nuevo, pasos = aplicar_pickup(None, None, None, None, None, None)
            out.append((c_pickup, nuevo, pasos))
            return
        # sin espacio: probar soltar cada objeto propio vivo para hacer hueco
        candidatos = list(estado.payload_keys) + list(estado.payload_tools) + \
            [m for m, cnt in payload_materials.items() for _ in range(cnt)]
        vistos = set()
        for cand in candidatos:
            if cand in vistos:
                continue
            vistos.add(cand)
            costo_total = c_drop + c_pickup
            if bateria < costo_total:
                continue
            gk2, gt2, gm2 = dict(ground_keys), dict(ground_tools), dict(ground_materials)
            pk2, pt2, pm2 = set(estado.payload_keys), set(estado.payload_tools), dict(payload_materials)
            if cand in pk2:
                pk2.discard(cand); gk2[cand] = zona
            elif cand in pt2:
                pt2.discard(cand); gt2[cand] = zona
            else:
                pm2[cand] -= 1
                if pm2[cand] == 0:
                    del pm2[cand]
                z0, c0 = gm2.get(cand, (zona, 0))
                gm2[cand] = (zona, c0 + 1)
            peso_liberado = idx["pesos"]["keys"].get(cand,
                idx["pesos"]["tools"].get(cand, idx["pesos"]["materials"].get(cand, 1)))
            if peso_actual - peso_liberado + peso_obj > capacidad:
                continue  # ese único drop no basta
            paso_drop = {"op": "DROP", "item": cand, "cost": c_drop}
            nuevo, pasos_pickup = aplicar_pickup(gk2, gt2, gm2, pk2, pt2, pm2)
            out.append((costo_total, nuevo, [paso_drop] + pasos_pickup))

    for kid, kzone in ground_keys.items():
        peso_obj = idx["pesos"]["keys"].get(kid, 1)
        def aplicar(gk2, gt2, gm2, pk2, pt2, pm2, kid=kid):
            gk_ = dict(gk2) if gk2 is not None else dict(ground_keys)
            gt_ = dict(gt2) if gt2 is not None else dict(ground_tools)
            gm_ = dict(gm2) if gm2 is not None else dict(ground_materials)
            pk_ = set(pk2) if pk2 is not None else set(estado.payload_keys)
            pt_ = set(pt2) if pt2 is not None else set(estado.payload_tools)
            pm_ = dict(pm2) if pm2 is not None else dict(payload_materials)
            del gk_[kid]; pk_.add(kid)
            nuevo = Estado(zona=zona, bateria=bateria - c_pickup,
                            payload_keys=pk_, payload_tools=pt_, payload_materials=pm_,
                            ground_keys=gk_, ground_tools=gt_, ground_materials=gm_,
                            doors_open=estado.doors_open, panels_ok=estado.panels_ok,
                            stations_on=estado.stations_on)
            return nuevo, [{"op": "PICKUP", "item": kid, "cost": c_pickup}]
        generar_pickup(kid, peso_obj, kzone, aplicar)

    for tid, tzone in ground_tools.items():
        peso_obj = idx["pesos"]["tools"].get(tid, 1)
        def aplicar(gk2, gt2, gm2, pk2, pt2, pm2, tid=tid):
            gk_ = dict(gk2) if gk2 is not None else dict(ground_keys)
            gt_ = dict(gt2) if gt2 is not None else dict(ground_tools)
            gm_ = dict(gm2) if gm2 is not None else dict(ground_materials)
            pk_ = set(pk2) if pk2 is not None else set(estado.payload_keys)
            pt_ = set(pt2) if pt2 is not None else set(estado.payload_tools)
            pm_ = dict(pm2) if pm2 is not None else dict(payload_materials)
            del gt_[tid]; pt_.add(tid)
            nuevo = Estado(zona=zona, bateria=bateria - c_pickup,
                            payload_keys=pk_, payload_tools=pt_, payload_materials=pm_,
                            ground_keys=gk_, ground_tools=gt_, ground_materials=gm_,
                            doors_open=estado.doors_open, panels_ok=estado.panels_ok,
                            stations_on=estado.stations_on)
            return nuevo, [{"op": "PICKUP", "item": tid, "cost": c_pickup}]
        generar_pickup(tid, peso_obj, tzone, aplicar)

    for mtype, (mzone, mcount) in ground_materials.items():
        if mcount <= 0:
            continue
        peso_obj = idx["pesos"]["materials"].get(mtype, 1)
        def aplicar(gk2, gt2, gm2, pk2, pt2, pm2, mtype=mtype):
            gk_ = dict(gk2) if gk2 is not None else dict(ground_keys)
            gt_ = dict(gt2) if gt2 is not None else dict(ground_tools)
            gm_ = dict(gm2) if gm2 is not None else dict(ground_materials)
            pk_ = set(pk2) if pk2 is not None else set(estado.payload_keys)
            pt_ = set(pt2) if pt2 is not None else set(estado.payload_tools)
            pm_ = dict(pm2) if pm2 is not None else dict(payload_materials)
            z0, c0 = gm_.get(mtype, (zona, 0))
            gm_[mtype] = (z0, c0 - 1)
            pm_[mtype] = pm_.get(mtype, 0) + 1
            nuevo = Estado(zona=zona, bateria=bateria - c_pickup,
                            payload_keys=pk_, payload_tools=pt_, payload_materials=pm_,
                            ground_keys=gk_, ground_tools=gt_, ground_materials=gm_,
                            doors_open=estado.doors_open, panels_ok=estado.panels_ok,
                            stations_on=estado.stations_on)
            return nuevo, [{"op": "PICKUP", "item": mtype, "cost": c_pickup}]
        generar_pickup(mtype, peso_obj, mzone, aplicar)

    # --- INTERACT: OPEN_DOOR (con drop automático si la llave muere) ---
    costo_i = idx["c_interact"]
    for did, door in idx["doors"].items():
        if did in estado.doors_open:
            continue
        if zona not in door["between"]:
            continue
        kid = door["key"]
        if kid not in estado.payload_keys:
            continue
        if bateria < costo_i:
            continue
        pasos = [{"op": "INTERACT", "target": did, "action": "OPEN_DOOR", "cost": costo_i}]
        nuevo_doors = estado.doors_open | {did}
        nuevo_payload_keys = estado.payload_keys - {kid}
        costo_total = costo_i
        puertas_de_la_llave = idx["key_to_doors"].get(kid, [])
        sigue_viva = any(d != did and d not in nuevo_doors for d in puertas_de_la_llave)
        gk = dict(ground_keys)
        if sigue_viva:
            nuevo_payload_keys = estado.payload_keys
        else:
            costo_total += c_drop
            pasos.append({"op": "DROP", "item": kid, "cost": c_drop})
        if bateria < costo_total:
            continue
        nuevo = Estado(
            zona=zona, bateria=bateria - costo_total,
            payload_keys=nuevo_payload_keys, payload_tools=estado.payload_tools,
            payload_materials=payload_materials,
            ground_keys=gk, ground_tools=ground_tools, ground_materials=ground_materials,
            doors_open=nuevo_doors, panels_ok=estado.panels_ok,
            stations_on=estado.stations_on,
        )
        out.append((costo_total, nuevo, pasos))

    # --- INTERACT: REPAIR (con drop automático si la herramienta muere) ---
    for pid, panel in idx["panels"].items():
        if pid in estado.panels_ok:
            continue
        if panel["zone"] != zona:
            continue
        req_tool = panel["requires"]["tool"]
        req_mat = panel["requires"]["material"]
        if req_tool not in estado.payload_tools:
            continue
        if payload_materials.get(req_mat, 0) <= 0:
            continue
        if bateria < costo_i:
            continue
        pasos = [{"op": "INTERACT", "target": pid, "action": "REPAIR", "consumes": req_mat, "cost": costo_i}]
        costo_total = costo_i
        nuevo_panels = estado.panels_ok | {pid}
        pm = dict(payload_materials)
        pm[req_mat] -= 1
        if pm[req_mat] == 0:
            del pm[req_mat]
        nuevo_payload_tools = estado.payload_tools
        paneles_de_la_tool = idx["tool_to_panels"].get(req_tool, [])
        sigue_viva = any(p != pid and p not in nuevo_panels for p in paneles_de_la_tool)
        if not sigue_viva:
            costo_total += c_drop
            pasos.append({"op": "DROP", "item": req_tool, "cost": c_drop})
            nuevo_payload_tools = estado.payload_tools - {req_tool}
        if bateria < costo_total:
            continue
        nuevo = Estado(
            zona=zona, bateria=bateria - costo_total,
            payload_keys=estado.payload_keys, payload_tools=nuevo_payload_tools,
            payload_materials=pm,
            ground_keys=ground_keys, ground_tools=ground_tools, ground_materials=ground_materials,
            doors_open=estado.doors_open, panels_ok=nuevo_panels,
            stations_on=estado.stations_on,
        )
        out.append((costo_total, nuevo, pasos))

    # --- INTERACT: ACTIVATE ---
    for sid, station in idx["stations"].items():
        if sid in estado.stations_on:
            continue
        if station["zone"] != zona:
            continue
        req = station.get("requires", {})
        if not all(p in estado.panels_ok for p in req.get("panels_ok", [])):
            continue
        if not all(s in estado.stations_on for s in req.get("stations_online", [])):
            continue
        if bateria < costo_i:
            continue
        nuevo = Estado(
            zona=zona, bateria=bateria - costo_i,
            payload_keys=estado.payload_keys, payload_tools=estado.payload_tools,
            payload_materials=payload_materials,
            ground_keys=ground_keys, ground_tools=ground_tools, ground_materials=ground_materials,
            doors_open=estado.doors_open, panels_ok=estado.panels_ok,
            stations_on=estado.stations_on | {sid},
        )
        out.append((costo_i, nuevo, [{"op": "INTERACT", "target": sid, "action": "ACTIVATE", "cost": costo_i}]))

    # --- INTERACT: RECHARGE ---
    costo_r = idx["c_recharge"]
    for charger in idx["chargers"]:
        if charger["zone"] != zona:
            continue
        if bateria == idx["battery_max"]:
            continue
        if bateria < costo_r:
            continue
        nuevo = Estado(
            zona=zona, bateria=idx["battery_max"],
            payload_keys=estado.payload_keys, payload_tools=estado.payload_tools,
            payload_materials=payload_materials,
            ground_keys=ground_keys, ground_tools=ground_tools, ground_materials=ground_materials,
            doors_open=estado.doors_open, panels_ok=estado.panels_ok,
            stations_on=estado.stations_on,
        )
        out.append((costo_r, nuevo, [{"op": "INTERACT", "target": charger["id"], "action": "RECHARGE", "cost": costo_r}]))

    return out


def es_meta(estado, scenario):
    objetivo = scenario["goal"]["stations_online"]
    return all(s in estado.stations_on for s in objetivo)


def buscar_plan(scenario, max_nodos=1_500_000, progreso_cada=50_000):
    idx = _construir_indices(scenario)
    inicio = estado_inicial(scenario)

    contador = itertools.count()
    heap = [(0, next(contador), inicio)]
    costo_final = {inicio: 0}
    pareto = {inicio._mundo(): [(0, inicio.bateria)]}
    padres = {inicio: (None, None)}
    cerrados = set()
    nodos_explorados = 0

    while heap:
        g, _, actual = heapq.heappop(heap)
        if actual in cerrados:
            continue
        if g > costo_final.get(actual, float("inf")):
            continue
        cerrados.add(actual)
        nodos_explorados += 1

        if nodos_explorados % progreso_cada == 0:
            print(f"... explorando, nodos vistos: {nodos_explorados}, frontera: {len(heap)}")

        if nodos_explorados > max_nodos:
            print("Límite de seguridad de nodos alcanzado sin solución.")
            return {"solution_found": False, "total_cost": 0, "steps": [],
                    "message": "Se excedió el límite de nodos explorados."}

        if es_meta(actual, scenario):
            pasos = _reconstruir(actual, padres)
            return {"solution_found": True, "total_cost": g, "steps": pasos, "message": ""}

        for costo_t, hijo, pasos_t in sucesores(actual, idx):
            g_hijo = g + costo_t
            mundo_h = hijo._mundo()
            frontera = pareto.get(mundo_h, [])
            dominado = any(c <= g_hijo and b >= hijo.bateria for c, b in frontera)
            if dominado:
                continue
            frontera = [(c, b) for c, b in frontera if not (g_hijo <= c and hijo.bateria >= b)]
            frontera.append((g_hijo, hijo.bateria))
            pareto[mundo_h] = frontera

            if g_hijo < costo_final.get(hijo, float("inf")):
                costo_final[hijo] = g_hijo
                padres[hijo] = (actual, pasos_t)
                heapq.heappush(heap, (g_hijo, next(contador), hijo))

    return {"solution_found": False, "total_cost": 0, "steps": [],
            "message": "No existe un plan que cumpla la meta."}


def _reconstruir(estado_final, padres):
    pasos = []
    actual = estado_final
    while True:
        prev, pasos_t = padres[actual]
        if prev is None:
            break
        pasos = pasos_t + pasos
        actual = prev
    return pasos


def solve_scenario(scenario):
    return buscar_plan(scenario)


if __name__ == "__main__":
    import json
    from pathlib import Path

    ruta = Path(__file__).resolve().parents[2] / "scenarios" / "scenario.json"
    with ruta.open(encoding="utf-8") as f:
        escenario = json.load(f)

    resultado = buscar_plan(escenario)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))