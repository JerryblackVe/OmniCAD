# -*- coding: utf-8 -*-
"""
Herramientas del grupo "grafo": programación visual SIN ventana (tipo Grasshopper; GH8 de
`docs/brechas_grasshopper.md`, formato en `docs/grafo.md`).

Un grafo es un JSON con nodos (entradas, matemática, listas, árboles, vectores, curvas, sólidos y salidas) unidos por
cables. `run_graph` lo evalúa sin tocar el documento (y exporta los cuerpos a STEP/STL si se pide); `bake_graph` lo
hornea como UN paso «Grafo» del timeline que se reevalúa con los parámetros del documento; `list_graph_nodes` trae los
tipos de nodo y el formato. El motor guarda caché por nodo: correr de nuevo el mismo grafo con otra entrada recalcula
solo lo que cuelga de ella («hacé 20 variantes de este grafo» es barato).

Claves del grafo en español (las del formato nativo, como los parámetros de run_operation); nombres de herramientas,
argumentos y claves del resultado en inglés.
"""
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Literal

from ..grafo import CATEGORIAS, MODIFICADORES, MODOS_EMPAREJADO, ErrorGrafo, Grafo, catalogo, motor_para
from ..grafo.tipos import ACCESOS, TIPOS, Curva, Plano, es_forma
from ..io_archivos.exportar import exportar
from ..nucleo import geometria as geo
from ..timeline.parametros import ErrorExpresion
from .errores import error
from .registro import herramienta

_ESTADOS = {"ok": "ok", "aviso": "warning", "error": "error"}
_MAX_ITEMS = 200                 # ítems por salida que devuelve run_graph (con count dice cuántos hay)
_MAX_AVISOS = 8
_EXTENSIONES = (".step", ".stp", ".stl", ".obj", ".3mf", ".ply", ".iges", ".igs", ".brep", ".brp", ".glb", ".gltf")
_PISTA_NODOS = "list_graph_nodes lista los tipos de nodo, sus entradas y salidas, y el formato con un ejemplo."
Categoria = Literal["entrada", "matematica", "listas", "arboles", "vectores", "curvas", "solidos", "salida"]

# Ejemplo del formato (el mismo de ejemplos/agentes/grilla_cajas.grafo.json): 3 × 3 cajas en grilla, unidas.
EJEMPLO = {
    "formato": "omnicad.grafo", "version": 1,
    "nodos": [
        {"id": "lado", "tipo": "deslizador", "entradas": {"valor": 10, "minimo": 1, "maximo": 50}},
        {"id": "alto", "tipo": "numero", "entradas": {"valor": 5}},
        {"id": "filas", "tipo": "entero", "entradas": {"valor": 3}},
        {"id": "grilla", "tipo": "puntos_grilla",
         "entradas": {"cantidad_x": {"de": "filas"}, "cantidad_y": {"de": "filas"},
                      "paso_x": {"de": "lado"}, "paso_y": {"de": "lado"}}},
        {"id": "cajas", "tipo": "caja",
         "entradas": {"centro": {"de": "grilla.puntos"}, "ancho": {"de": "lado"}, "largo": {"de": "lado"},
                      "alto": {"de": "alto"}}},
        {"id": "union", "tipo": "unir", "entradas": {"cuerpos": {"de": "cajas"}}},
        {"id": "vol", "tipo": "volumen", "entradas": {"cuerpo": {"de": "union"}}},
        {"id": "pieza", "tipo": "salida", "entradas": {"valor": {"de": "union"}}},
        {"id": "volumen", "tipo": "salida", "entradas": {"valor": {"de": "vol"}}},
    ],
}
FORMATO = {
    "description": "Un grafo es {\"formato\": \"omnicad.grafo\", \"version\": 1, \"nodos\": [...]}. Cada nodo: "
                   "{\"id\", \"tipo\", \"entradas\"} y opcionales \"nombre\" (cómo se lo cita en inputs y outputs), "
                   "\"emparejado\" y \"posicion\" [x, y]. Las claves van en español.",
    "input_values": [
        "literal: 10, \"ancho / 2\" (expresión con parámetros del documento), true, \"texto\", [0, 0, 0] (un punto), "
        "\"XY\" (un plano), [1, 2, 3] en un puerto numérico (una lista de 3 números)",
        "cable: {\"de\": \"nodo\"} (su primera salida), {\"de\": \"nodo.salida\"} o {\"de\": [\"a\", \"b.x\"]} (se "
        "fusionan)",
        "árbol literal: {\"arbol\": {\"{0}\": [1, 2], \"{1}\": [3]}}",
        "con \"modificador\" (aplanar, injertar, simplificar, invertir) el árbol se transforma antes de usarlo: "
        "{\"de\": \"nodo\", \"modificador\": \"injertar\"}",
    ],
    "inputs_by_name": "inputs={\"lado\": 20} cambia el «valor» del nodo de entrada con ese nombre o id; "
                      "\"nodo.entrada\" cambia cualquier entrada de cualquier nodo.",
    "outputs": "Los nodos «salida» son el resultado: run_graph devuelve su valor y bake_graph hornea sus cuerpos.",
    "matching": MODOS_EMPAREJADO,
    "modifiers": MODIFICADORES,
    "types": TIPOS,
    "access": ACCESOS,
    "example": EJEMPLO,
    "example_inputs": {"lado": 12, "filas": 4},
}


# ---------------------------------------------------------------- utilidades
def _cargar(graph, inputs):
    """(datos del grafo, entradas). `graph`: el objeto, su texto JSON o la ruta a un .json con el grafo o con
    {"graph", "inputs"} (las entradas del archivo valen salvo las que llegan en `inputs`)."""
    entradas_archivo = {}
    datos = graph
    if isinstance(graph, str):
        texto = graph.strip()
        if texto.startswith("{"):
            try:
                datos = json.loads(texto)
            except ValueError as e:
                raise error("INVALID_ARGUMENTS", f"«graph» no es JSON válido: {e}", _PISTA_NODOS) from None
        else:
            ruta = Path(texto).expanduser()
            if not ruta.is_file():
                raise error("FILE_NOT_FOUND", f"No existe el archivo del grafo: {graph}",
                            "graph es el objeto JSON del grafo o la ruta a un archivo .json que lo tiene.")
            try:
                datos = json.loads(ruta.read_text(encoding="utf-8"))
            except (ValueError, UnicodeDecodeError) as e:
                raise error("INVALID_ARGUMENTS", f"El archivo {ruta.name} no es JSON válido: {e}") from None
            if isinstance(datos, dict) and "graph" in datos:
                entradas_archivo = datos.get("inputs") or {}
                datos = datos["graph"]
    if not isinstance(entradas_archivo, dict):
        raise error("INVALID_ARGUMENTS", "«inputs» del archivo tiene que ser un objeto {nombre: valor}.")
    entradas = dict(entradas_archivo)
    entradas.update(inputs or {})
    return datos, entradas


def _error_grafo(e):
    return error("INVALID_ARGUMENTS", f"Grafo inválido: {e.mensaje}", *e.pistas, _PISTA_NODOS)


def _motor(datos):
    """Motor con caché para el grafo (normalizado: el mismo grafo escrito distinto comparte la caché)."""
    try:
        return motor_para(Grafo.desde_json(datos).a_json())
    except ErrorGrafo as e:
        raise _error_grafo(e) from None


def _parametros(sesion):
    try:
        return sesion.doc.parametros.valores()
    except ErrorExpresion as e:
        sesion.avisar(f"Los parámetros del documento tienen un error y no se usan en el grafo: {e}")
        return {}


def _exigir_salidas(grafo, outputs):
    if not outputs:
        return None
    nombres = [n.publico for n in grafo.salidas_publicas()]
    faltan = [x for x in outputs if x not in nombres]
    if faltan:
        raise error("INVALID_ARGUMENTS", f"El grafo no tiene las salidas: {', '.join(faltan)}.",
                    f"Salidas del grafo: {', '.join(nombres) or '(ninguna: agregá nodos «salida»)'}.")
    return list(outputs)


def _r(x):
    return round(float(x), 6) + 0.0


def _caja(forma):
    caja = geo.caja_envolvente(forma)
    if not caja:
        return None
    p0, p1 = caja
    return {"min": [_r(v) for v in p0], "max": [_r(v) for v in p1],
            "size": [_r(b - a) for a, b in zip(p0, p1, strict=True)]}


def valor_json(v):
    """Un valor del grafo como JSON: puntos [x, y, z], planos y curvas como objetos, cuerpos con sus medidas."""
    if v is None or isinstance(v, (bool, int, str)):
        return v
    if isinstance(v, float):
        return _r(v) if math.isfinite(v) else None
    if isinstance(v, Plano):
        return {"kind": "plane", "origin": [_r(c) for c in v.origen], "x_axis": [_r(c) for c in v.x],
                "y_axis": [_r(c) for c in v.y], "normal": [_r(c) for c in v.z]}
    if isinstance(v, Curva):
        return {"kind": "curve", "description": v.descripcion, "closed": v.cerrada}
    if es_forma(v):
        solidos = geo.solidos(v)
        return {"kind": "body", "solids": len(solidos), "volume": _r(geo.volumen(v)) if solidos else None,
                "area": _r(geo.area(v)), "bounding_box": _caja(v)}
    if isinstance(v, (list, tuple)):
        return [valor_json(x) for x in v]
    return str(v)


def _salidas_json(resultado, nombres):
    salida = {}
    for nombre, arbol in resultado.salidas.items():
        if nombres and nombre not in nombres:
            continue
        ramas, n, truncado = {}, 0, False
        for ruta, items in arbol.ramas():
            if n >= _MAX_ITEMS:
                truncado = True
                break
            tomar = items[:_MAX_ITEMS - n]
            truncado = truncado or len(tomar) < len(items)
            ramas[str(ruta)] = [valor_json(x) for x in tomar]
            n += len(tomar)
        info = {"count": len(arbol), "branches": ramas, "truncated": truncado}
        if len(arbol) == 1:
            info["value"] = next(v for items in ramas.values() for v in items)
        salida[nombre] = info
    return salida


def _entradas_json(grafo, entradas):
    """Las entradas públicas del grafo con el valor que se usó."""
    cambios = grafo.resolver_entradas(entradas)
    salida = []
    for n in grafo.entradas_publicas():
        valor = cambios.get((n.id, "valor"), n.entradas.get("valor"))
        if valor is None:
            from ..grafo import definicion
            valor = valor_json(definicion(n.tipo).entrada("valor").defecto)
        salida.append({"name": n.publico, "node": n.id, "type": n.tipo, "value": valor})
    return salida


def _nodos_json(resultado):
    return [{"id": i.id, "type": i.tipo, "name": i.nombre or None, "status": _ESTADOS[i.estado], "messages": i.mensajes,
             "ms": round(i.duracion * 1000, 3), "computed": i.ejecutado,
             "items": {s: len(a) for s, a in i.salidas.items()}} for i in (resultado.nodos[x] for x in resultado.orden)]


def _avisar_nodos(sesion, resultado):
    lista = resultado.errores + resultado.avisos
    for nid, m in lista[:_MAX_AVISOS]:
        tipo = "error" if (nid, m) in resultado.errores else "aviso"
        sesion.avisar(f"Nodo «{nid}» ({tipo}): {m}")
    if len(lista) > _MAX_AVISOS:
        sesion.avisar(f"… y {len(lista) - _MAX_AVISOS} mensaje(s) más de los nodos (ver nodes).")


def _preparar_export(export, overwrite):
    ruta = Path(export).expanduser()
    if ruta.suffix.lower() not in _EXTENSIONES:
        raise error("INVALID_FORMAT", f"El grafo se exporta a {', '.join(_EXTENSIONES)}; llegó «{ruta.suffix or '(sin extensión)'}».")
    if ruta.name in ("", ".."):
        raise error("INVALID_ARGUMENTS", f"La ruta «{export}» no tiene nombre de archivo.")
    if ruta.exists() and not overwrite:
        raise error("FILE_EXISTS", f"Ya existe el archivo: {ruta}")
    if not ruta.parent.is_dir():
        raise error("FILE_NOT_FOUND", f"No existe la carpeta: {ruta.parent}")
    return ruta


# ---------------------------------------------------------------- herramientas
@herramienta("list_graph_nodes", "grafo",
             "Lista los tipos de nodo para armar grafos de programación visual (tipo Grasshopper) que corren sin "
             "ventana con run_graph y se hornean con bake_graph: tipo, categoría, descripción y cada entrada y salida "
             "con su tipo de dato, acceso (item, lista o árbol), unidad y valor por defecto. Trae también el formato "
             "JSON del grafo con un ejemplo.")
def list_graph_nodes(sesion, category: Categoria | None = None, query: str | None = None, include_format: bool = True):
    """
    category: categoría de nodos: entrada, matematica, listas, arboles, vectores, curvas, solidos o salida; vacío = todas.
    query: texto a buscar en el tipo, el título o la descripción (sin distinguir mayúsculas); vacío = todos.
    include_format: true para incluir el formato JSON del grafo, las reglas de emparejado y un ejemplo.
    """
    q = (query or "").strip().casefold()
    nodos = [d.a_json() for d in catalogo().values()
             if (category is None or d.categoria == category)
             and (not q or q in f"{d.tipo} {d.titulo} {d.descripcion}".casefold())]
    resultado = {"count": len(nodos), "categories": CATEGORIAS, "nodes": nodos}
    if include_format:
        resultado["graph_format"] = FORMATO
    return resultado


@herramienta("run_graph", "grafo",
             "Evalúa un grafo de nodos (programación visual tipo Grasshopper: flujo de datos con listas y árboles) SIN "
             "tocar el documento. Devuelve el valor de cada nodo «salida» (los cuerpos con volumen, área y caja), las "
             "entradas usadas y el estado y el tiempo de cada nodo; con export guarda los cuerpos de las salidas "
             "(.step, .stl, .3mf, .obj…). Las entradas se cambian por nombre en inputs (también con expresiones de "
             "parámetros del documento). Llamar de nuevo con el mismo grafo recalcula solo los nodos que dependen de "
             "lo que cambió. list_graph_nodes trae los nodos y el formato.")
def run_graph(sesion, graph: dict | str, inputs: dict | None = None, outputs: list[str] | None = None,
              export: str | None = None, overwrite: bool = False, include_nodes: bool = True):
    """
    graph: el grafo (objeto con "nodos"; ver list_graph_nodes), su texto JSON o la ruta a un archivo .json con el grafo
        o con {"graph", "inputs"}.
    inputs: valores de entrada por nombre, p. ej. {"lado": 20, "alto": "espesor * 2"}: el nombre (o id) de un nodo de
        entrada cambia su valor; "nodo.entrada" cambia cualquier entrada de un nodo. Acepta números, expresiones con
        parámetros del documento, listas y puntos [x, y, z].
    outputs: nombres de las salidas a devolver y exportar; vacío = todas.
    export: ruta del archivo donde guardar los cuerpos de las salidas (.step/.stp, .stl, .obj, .3mf, .ply, .iges/.igs,
        .brep); vacío = no exporta.
    overwrite: true para reemplazar el archivo de export si ya existe.
    include_nodes: true para incluir el estado, los mensajes y el tiempo de cada nodo.
    """
    datos, entradas = _cargar(graph, inputs)
    ruta = _preparar_export(export, overwrite) if export else None
    motor = _motor(datos)
    nombres = _exigir_salidas(motor.grafo, outputs)
    try:
        resultado = motor.evaluar(entradas, _parametros(sesion))
        usadas = _entradas_json(motor.grafo, entradas)
    except ErrorGrafo as e:
        raise _error_grafo(e) from None
    _avisar_nodos(sesion, resultado)
    if not motor.grafo.salidas_publicas():
        sesion.avisar("El grafo no tiene nodos «salida»: no devuelve resultados (agregá uno conectado a lo que querés ver).")
    estado = "error" if resultado.errores else "warning" if resultado.avisos else "ok"
    respuesta = {"status": estado, "outputs": _salidas_json(resultado, nombres), "inputs": usadas,
                 "computed_nodes": len(resultado.ejecutados), "cached_nodes": len(resultado.orden) - len(resultado.ejecutados),
                 "total_ms": round(resultado.duracion * 1000, 3)}
    if include_nodes:
        respuesta["nodes"] = _nodos_json(resultado)
    if ruta is not None:
        formas = [f for _n, f in resultado.cuerpos(nombres)]
        if not formas:
            raise error("NOTHING_TO_EXPORT", "Las salidas del grafo no tienen cuerpos para exportar.",
                        "Conectá un nodo de sólidos (caja, unir…) a un nodo «salida».")
        n = exportar([SimpleNamespace(forma=f) for f in formas], ruta)
        respuesta["export"] = {"path": str(ruta.resolve()), "format": ruta.suffix.lower().lstrip("."),
                               "bodies": len(formas), "size_bytes": ruta.stat().st_size}
        if isinstance(n, int):
            respuesta["export"]["triangles"] = n
    return respuesta


@herramienta("bake_graph", "grafo",
             "Hornea un grafo en el documento: agrega UN paso «Grafo» al timeline que guarda el grafo y sus entradas y "
             "lo vuelve a evaluar en cada recálculo (paramétrico: una entrada como \"ancho / 2\" o un nodo «parametro» "
             "siguen a los parámetros del documento, y el paso se edita con edit_feature). Los cuerpos salen de los "
             "nodos «salida»; operation los aplica como cuerpo nuevo, unir, cortar o intersecar. Con fixed=true deja "
             "cuerpos fijos (operación base, sin el grafo).", modifica=True)
def bake_graph(sesion, graph: dict | str, inputs: dict | None = None, outputs: list[str] | None = None,
               operation: Literal["new_body", "join", "cut", "intersect"] = "new_body",
               target: str | list[str] | None = None, name: str | None = None, fixed: bool = False):
    """
    graph: el grafo (objeto con "nodos"; ver list_graph_nodes), su texto JSON o la ruta a un archivo .json con el grafo
        o con {"graph", "inputs"}.
    inputs: valores de entrada por nombre (como en run_graph); las expresiones con parámetros del documento quedan
        enlazadas: al cambiar el parámetro, el paso se recalcula.
    outputs: nombres de las salidas cuyos cuerpos se hornean; vacío = todas.
    operation: "new_body", "join", "cut" o "intersect" (con fixed=true, solo new_body).
    target: cuerpo(s) para join, cut o intersect (id o nombre); vacío = los sólidos que toca.
    name: nombre del paso en el timeline; vacío = el automático.
    fixed: true para hornear cuerpos fijos (operación base) en vez del grafo paramétrico.
    """
    from ..nucleo import intercambio
    from ..timeline.operaciones import OpOperacionBase
    from ..timeline.ops_grafo import OpGrafo, cuerpos_de_salida, mensajes_de_nodos, nombres_de_cuerpos
    from .herramientas_solido import OPERACIONES, _agregar, _objetivos
    datos, entradas = _cargar(graph, inputs)
    motor = _motor(datos)
    nombres = _exigir_salidas(motor.grafo, outputs)
    try:
        motor.grafo.resolver_entradas(entradas)
    except ErrorGrafo as e:
        raise _error_grafo(e) from None
    doc = sesion.doc
    if fixed:
        if operation != "new_body":
            raise error("INVALID_ARGUMENTS", "Con fixed=true el grafo se hornea como cuerpos nuevos (operation=new_body).",
                        "Para unir o cortar con el resultado, horneá el grafo paramétrico (fixed=false).")
        resultado = motor.evaluar(entradas, _parametros(sesion))
        if resultado.errores:
            raise error("OPERATION_FAILED", f"El grafo tiene nodos con error: {mensajes_de_nodos(resultado.errores)}.",
                        "run_graph muestra el estado y los mensajes de cada nodo.")
        piezas = cuerpos_de_salida(resultado, nombres)
        if not piezas:
            raise error("OPERATION_FAILED", "El grafo no dio cuerpos: ninguna salida tiene un cuerpo.",
                        "Conectá un nodo de sólidos (caja, unir…) a un nodo «salida».")
        congelados = [{"id": f"grafo.{i}", "nombre": nombre, "tipo": tipo, "apariencia": None,
                       "brep": intercambio.brep_a_texto(forma)}
                      for i, ((_n, forma, tipo), nombre) in enumerate(zip(piezas, nombres_de_cuerpos(piezas), strict=True), 1)]
        op = OpOperacionBase(doc.nuevo_id(), name or None, cuerpos=congelados)
    else:
        objetivo = _objetivos(sesion, operation, target)
        op = OpGrafo(doc.nuevo_id(), name or None, grafo=motor.grafo.a_json(), entradas=entradas,
                     salidas=nombres or [], operacion=OPERACIONES[operation], objetivo=objetivo or "")
    informe = _agregar(sesion, op, combina=operation != "new_body")
    informe["inputs"] = entradas
    informe["parametric"] = not fixed
    return informe
