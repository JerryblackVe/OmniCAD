# -*- coding: utf-8 -*-
"""Identidad, transformación y organización de recursos vectoriales; API única de UI, CLI y MCP."""
from typing import Literal
from contextlib import contextmanager

from ..restricciones import objetos as ob
from ..restricciones.boceto import Texto
from ..timeline.parametros import ANGULO, ESCALAR, LONGITUD
from .errores import error
from .herramientas_boceto import _dibujar, boceto_activo
from .registro import Expr, herramienta

ALINEACIONES = {"left": "izquierda", "right": "derecha", "top": "arriba", "bottom": "abajo",
                "horizontal_center": "centro_h", "vertical_center": "centro_v", "origin": "origen",
                "distribute_horizontal": "distribuir_h", "distribute_vertical": "distribuir_v"}


def _exigir(b, ids):
    if not ids or any(i not in b.objetos for i in ids):
        raise error("ENTITY_NOT_FOUND", "Elegí ids de objetos existentes (get_vector_objects).")


def _exigir_unidades(b, ids, mensaje):
    """Solo objetos que el usuario maneja como pieza: raíces o miembros de un grupo personalizado."""
    unidades = {i for lista in ob.unidades(b).values() for i in lista}
    if any(i not in unidades for i in ids):
        raise error("INVALID_ARGUMENTS", mensaje)


@contextmanager
def textos_resueltos(b, valores):
    """Consulta/manipulación con la palabra visible; la receta conserva las plantillas originales."""
    from ..timeline.operaciones import _contenido_texto, texto_con_valores
    antes = {i: c.texto for i, c in b.curvas.items() if isinstance(c, Texto)}
    try:
        for i in antes:
            t = b.curvas[i]
            t.texto = texto_con_valores(_contenido_texto(t, valores), valores)
        yield
    finally:
        for i, texto in antes.items():
            if isinstance(b.curvas.get(i), Texto):
                b.curvas[i].texto = texto


def _editar(sesion, sketch, funcion):
    resultado = {}

    def cambiar(b):
        ob.evaluar(b, lambda v, k: sesion.doc.parametros.evaluar(
            v, ANGULO if k == "angulo" else ESCALAR if k in ("sx", "sy") else LONGITUD))
        with textos_resueltos(b, sesion.doc.parametros.valores()):
            resultado.update(funcion(b) or {})
    r = _dibujar(sesion, sketch, cambiar, desde_solver=True)
    r.update(resultado)
    return r


def info_objeto(b, oid, perfiles=()):
    o = b.objetos[oid]
    m = ob.acumulada(b, oid)
    import math
    import numpy as np
    cids = ob.curvas(b, [oid])
    x0, y0, x1, y1 = ob.caja(b, [oid])
    return {"id": oid, "name": o["nombre"], "children": list(o["entidades"]), "curves": cids,
            "matrix": m.tolist(), "position": [x0, y0], "width": x1 - x0, "height": y1 - y0,
            "angle": math.degrees(math.atan2(m[1, 0], m[0, 0])),
            "scale_x": float(np.linalg.norm(m[:2, 0])), "scale_y": float(np.linalg.norm(m[:2, 1])),
            "pivot": list(ob.pivote(b, oid)), "visible": o["visible"], "locked": o["bloqueado"],
            "in_profiles": o.get("perfiles", True), "category": ob.categoria(b, oid),
            "keep_proportions": o["proporciones"], "source_type": o.get("tipo_origen", "text" if
                any(isinstance(b.curvas[i], Texto) for i in cids) else "vector"),
            "editable_text": [i for i in cids if isinstance(b.curvas[i], Texto)],
            "profiles": [i for i, p in enumerate(perfiles) if p.firma and p.firma <= set(cids)]}


def regiones(b, plano, ids):
    """Regiones CAD del recurso, sin los huecos de letras ni los de relleno SVG."""
    from ..nucleo.perfiles import detectar_boceto, sin_huecos
    cids = set(ob.curvas(b, ids))
    todos = detectar_boceto(b, plano)
    utilizables = sin_huecos(todos, b)
    return todos, [p for p in utilizables if p.firma and p.firma <= cids]


def desfasar(b, plano, ids, distancia, esquinas="redondas"):
    """Offset exacto del objeto: genera otro objeto y conserva el recurso original."""
    from ..io_archivos.boceto_archivos import agregar_geometria
    from ..nucleo import geometria as geo, vectores
    _todos, perfiles = regiones(b, plano, ids)
    if not perfiles:
        raise ob._error("El objeto no tiene regiones cerradas utilizables para el desfase.")
    try:
        formas = vectores.desfase_caras([p.cara for p in perfiles], distancia, esquinas)
        if any(not geo.es_valida(f) for f in formas):
            raise geo.ErrorGeometria("El desfase produce contornos inválidos; probá una distancia menor.")
        curvas = agregar_geometria(b, vectores.primitivas_de_formas(formas, plano))
        nuevo = ob.crear(b, curvas, "Desfase")
        _todos, cerrados = regiones(b, plano, [nuevo])
        if not cerrados:
            raise geo.ErrorGeometria("El desfase no deja regiones cerradas válidas.")
    except geo.ErrorGeometria as e:
        raise ob._error(str(e)) from e
    return nuevo


def separar_regiones(b, plano, oid):
    """Separa letras/islas con sus agujeros; no expone nodos ni hace booleanas."""
    import copy
    o = b.objetos[oid]
    if oid not in ob.raices(b):
        raise ob._error("Desagrupá el grupo padre antes de separar sus regiones.")
    if o["bloqueado"]:
        raise ob._error("Desbloqueá el objeto antes de separar sus regiones.")
    _todos, perfiles = regiones(b, plano, [oid])
    if not perfiles:
        raise ob._error("El objeto no tiene regiones cerradas para separar.")
    # Cada isla lleva sus contornos interior y exterior; las firmas originales se conservan
    # siempre que una curva no forme parte de dos islas (perfiles partidos por intersecciones).
    conjuntos = [set(p.firma) for p in perfiles]
    if sum(map(len, conjuntos)) != len(set().union(*conjuntos)):
        raise ob._error("Las regiones comparten curvas: resolvé las intersecciones antes de separarlas.")
    hijos, actuales = [], set(ob.curvas(b, [oid]))
    originales, viejos = dict(b.objetos), set()

    def copiar(i, seleccion):
        if i in b.curvas:
            return i if i in seleccion else None
        viejo = originales[i]
        viejos.add(i)
        elementos = [k for h in viejo["entidades"] if (k := copiar(h, seleccion)) is not None]
        if not elementos:
            return None
        nuevo = b._nuevo_id()
        datos = copy.deepcopy(viejo)
        datos.update(id=nuevo, entidades=elementos)
        b.objetos[nuevo] = datos
        return nuevo

    usados = set().union(*conjuntos)
    if usados != actuales:
        conjuntos.append(actuales - usados)
    for n, conjunto in enumerate(conjuntos, 1):
        nuevo = copiar(oid, conjunto)
        b.objetos[nuevo]["nombre"] = f"{o['nombre']} · región {n}"
        hijos.append(nuevo)
    for i in viejos:
        del b.objetos[i]
    ob.invalidar(b)
    return hijos


def combinar(b, plano, ids, operacion="union"):
    """Booleana de perfiles, distinta de agrupar; conserva los originales como recursos ocultos."""
    from ..io_archivos.boceto_archivos import agregar_geometria
    from ..nucleo import geometria as geo, vectores
    grupos = [regiones(b, plano, [i])[1] for i in ids]
    if not grupos or any(not g for g in grupos):
        raise ob._error("Cada objeto debe tener al menos una región cerrada válida.")
    try:
        a = [p.cara for p in grupos[0]]
        herramientas = [p.cara for g in grupos[1:] for p in g]
        forma = vectores.booleana_caras(a, herramientas, operacion)
        if not geo.es_valida(forma):
            raise geo.ErrorGeometria("La combinación produce perfiles inválidos.")
        nuevas = agregar_geometria(b, vectores.primitivas_de_formas([forma], plano))
        nuevo = ob.crear(b, nuevas, "Perfiles combinados")
    except geo.ErrorGeometria as e:
        raise ob._error(str(e)) from e
    for i in ids:
        b.objetos[i]["visible"] = False
    return nuevo


def validar_objetos(b, plano, ids, tolerancia=1e-6):
    """Diagnóstico explícito: extremos abiertos, degeneradas, duplicadas, cruces y caras inválidas."""
    import math
    from ..nucleo import geometria as geo
    from ..restricciones.boceto import dominio, evaluar_primitiva, firma_primitiva, intersecciones
    prims = [p for i in ids for p in ob.primitivas(b, i)]
    extremos, vistas, duplicadas, degeneradas, cajas, puntas = {}, {}, [], [], [], []
    for p in prims:
        c = ob.limites_primitiva(p)
        cajas.append(c)
        if math.hypot(c[2] - c[0], c[3] - c[1]) < tolerancia:
            degeneradas.append(p[1])
        firma = firma_primitiva(p)
        if firma in vistas:
            duplicadas.append([vistas[firma], p[1]])
        vistas[firma] = p[1]
        t0, t1, _periodica = dominio(p)
        a, z = evaluar_primitiva(p, t0)[0], evaluar_primitiva(p, t1)[0]
        puntas.append((a, z))
        if math.dist(a, z) > tolerancia:
            for q in (a, z):
                clave = tuple(round(v / tolerancia) for v in q)
                extremos.setdefault(clave, []).append(p[1])
    cruces = []
    for i, a in enumerate(prims):
        for j in range(i + 1, len(prims)):
            c, d = cajas[i], cajas[j]
            if c[2] < d[0] - tolerancia or d[2] < c[0] - tolerancia or c[3] < d[1] - tolerancia or d[3] < c[1] - tolerancia:
                continue
            for q in intersecciones(a, prims[j], tolerancia):
                punto = q[-1] if len(q) == 3 else q
                if not any(math.dist(punto, p) <= tolerancia * 2 for p in puntas[i]) or not any(
                        math.dist(punto, p) <= tolerancia * 2 for p in puntas[j]):
                    cruces.append([a[1], prims[j][1]])
                    break
    todos, utilizables = regiones(b, plano, ids)
    cids = set(ob.curvas(b, ids))
    abiertas = sorted({i for lista in extremos.values() if len(lista) % 2 for i in lista})
    invalidos = [i for i, p in enumerate(todos) if p.firma <= cids and not geo.es_valida(p.cara)]
    return {"valid": not (abiertas or degeneradas or duplicadas or cruces or invalidos),
            "open_curves": abiertas, "degenerate_curves": degeneradas, "duplicate_curves": duplicadas,
            "intersections": cruces, "invalid_profiles": invalidos,
            "usable_profiles": [i for i, p in enumerate(todos) if p in utilizables],
            "messages": (["Hay contornos abiertos: uní sus extremos antes de extruir."] if abiertas else [])
                        + (["Hay cruces interiores: separá o combiná los perfiles antes de extruir."] if cruces else [])
                        + (["Hay perfiles duplicados o geometría degenerada."] if duplicadas or degeneradas else [])}


@herramienta("get_vector_objects", "vectores", "Consulta objetos, grupos, matrices, pivotes y perfiles CAD por id estable.")
def get_vector_objects(sesion, sketch: str | None = None):
    """
    sketch: id o nombre del boceto; vacío = último boceto activo.
    """
    op, br = boceto_activo(sesion, sketch)
    return {"sketch": op.id, "roots": ob.raices(br.boceto),
            "objects": [info_objeto(br.boceto, i, br.perfiles) for i in br.boceto.objetos]}


@herramienta("create_vector_object", "vectores", "Convierte curvas o texto de un boceto antiguo en un objeto rígido sin perder sus ids ni sus perfiles.", modifica=True)
def create_vector_object(sesion, entities: list[int], name: str = "Objeto vectorial", sketch: str | None = None):
    """
    entities: ids de curvas o textos libres (get_sketch); también admite objetos raíz para agrupar.
    name: nombre editable del objeto o grupo.
    sketch: id o nombre del boceto; vacío = último boceto activo.
    """
    return _editar(sesion, sketch, lambda b: {"object_id": ob.crear(b, entities, name)})


@herramienta("group_vector_objects", "vectores", "Agrupa objetos lógicamente, incluso grupos anidados; no une perfiles ni cambia geometría.", modifica=True)
def group_vector_objects(sesion, objects: list[int], name: str = "Grupo", sketch: str | None = None):
    """
    objects: ids de objetos raíz a agrupar.
    name: nombre del grupo.
    sketch: id o nombre del boceto.
    """
    def agrupar(b):
        _exigir(b, objects)
        return {"object_id": ob.crear(b, objects, name)}
    return _editar(sesion, sketch, agrupar)


@herramienta("ungroup_vector_object", "vectores", "Desagrupa un nivel conservando las matrices, los ids de las curvas y los grupos interiores. "
             "Un objeto hoja (una forma del SVG) no se separa: sus curvas quedan juntas para no romper el contorno ni el relleno.",
             modifica=True)
def ungroup_vector_object(sesion, object: int, sketch: str | None = None):
    """
    object: id del grupo a desagrupar. Si es una hoja (sus entidades son curvas), queda igual y se devuelve su id.
    sketch: id o nombre del boceto.
    """
    def separar(b):
        _exigir(b, [object])
        return {"object_ids": ob.desagrupar(b, object)}
    return _editar(sesion, sketch, separar)


@herramienta("transform_vector_objects", "vectores", "Mueve, rota, escala y refleja (escala -1) objetos completos en un solo deshacer. Las expresiones quedan paramétricas; el recálculo actualiza las extrusiones dependientes.", modifica=True)
def transform_vector_objects(sesion, objects: list[int], dx: Expr = 0, dy: Expr = 0, angle: Expr = 0,
                             scale_x: Expr = 1, scale_y: Expr | None = None, pivot: list[float] | None = None,
                             sketch: str | None = None):
    """
    objects: ids de objetos o grupos completos; también un objeto dentro de un grupo personalizado.
    dx: desplazamiento horizontal en mm, número o expresión.
    dy: desplazamiento vertical en mm, número o expresión.
    angle: rotación en grados, número o expresión.
    scale_x: factor horizontal, número o expresión (1 = igual; -1 refleja respecto del pivote).
    scale_y: factor vertical; vacío = proporcional a scale_x (-1 con scale_x=1 refleja en vertical).
    pivot: centro común [x, y] en mm; vacío = pivote propio (uno) o centro de la selección (varios).
    sketch: id o nombre del boceto.
    """
    def cambiar(b):
        _exigir(b, objects)
        _exigir_unidades(b, objects, "Transformá el SVG, el DXF o el texto completo, no una pieza interna.")
        if pivot is not None and len(pivot) != 2:
            raise error("INVALID_ARGUMENTS", "pivot es [x, y] en milímetros.")
        x0, y0, x1, y1 = ob.caja(b, objects)
        p = pivot if pivot is not None else (ob.pivote(b, objects[0]) if len(objects) == 1 else
                                             ((x0 + x1) / 2, (y0 + y1) / 2))
        datos = {"dx": dx, "dy": dy, "angulo": angle, "sx": scale_x,
                 "sy": scale_x if scale_y is None else scale_y, "pivote": list(p)}
        valores = {k: v if k == "pivote" else sesion.doc.parametros.evaluar(
            v, ANGULO if k == "angulo" else ESCALAR if k in ("sx", "sy") else LONGITUD) for k, v in datos.items()}
        # La historia paramétrica se reproduce en coordenadas del boceto: solo vale para objetos raíz. Dentro de un
        # grupo el valor queda fijo (exacto, sin fórmula).
        raices = set(ob.raices(b))
        ob.transformar(b, objects, ob.afin(**valores), parametros=datos if raices.issuperset(objects) else None)
        return {"object_ids": objects}
    return _editar(sesion, sketch, cambiar)


@herramienta("set_vector_object", "vectores", "Cambia nombre, visibilidad, bloqueo, participación en perfiles, proporciones o pivote; "
             "las tres primeras son independientes y cambiar el pivote no mueve el objeto.", modifica=True)
def set_vector_object(sesion, object: int, name: str | None = None, visible: bool | None = None,
                      locked: bool | None = None, keep_proportions: bool | None = None,
                      pivot: list[float] | None = None, sketch: str | None = None, reset_transform: bool = False,
                      in_profiles: bool | None = None):
    """
    object: id estable del objeto.
    name: nuevo nombre; vacío conserva el actual.
    visible: false oculta la representación; los perfiles CAD conservan su geometría.
    locked: true impide seleccionar y transformar accidentalmente.
    in_profiles: false saca sus curvas (y las de lo que contiene) de los perfiles CAD sin ocultarlo; true las devuelve.
    keep_proportions: bloqueo de proporciones para la interacción gráfica.
    pivot: nuevo centro de transformación [x, y] en mm del boceto.
    sketch: id o nombre del boceto.
    reset_transform: true restablece matriz y pivote a la importación, sin cambiar los ids ni reabrir el archivo.
    """
    def cambiar(b):
        _exigir(b, [object])
        if reset_transform:
            ob.restablecer(b, [object])
        if name is not None and not name.strip():
            raise error("INVALID_ARGUMENTS", "El nombre no puede quedar vacío.")
        for k, v in (("nombre", name and name.strip()), ("visible", visible), ("bloqueado", locked),
                     ("proporciones", keep_proportions), ("perfiles", in_profiles)):
            if v is not None:
                b.objetos[object][k] = v
        if pivot is not None:
            if len(pivot) != 2:
                raise error("INVALID_ARGUMENTS", "pivot es [x, y] en milímetros.")
            ob.poner_pivote(b, object, pivot)
        return {"object_id": object}
    return _editar(sesion, sketch, cambiar)


@herramienta("align_vector_objects", "vectores", "Alinea o distribuye objetos por sus cajas exactas, respecto de selección, origen u objeto de referencia.", modifica=True)
def align_vector_objects(sesion, objects: list[int], mode: Literal["left", "right", "top", "bottom", "horizontal_center", "vertical_center", "origin", "distribute_horizontal", "distribute_vertical"],
                         reference: Literal["selection", "origin", "object"] = "selection",
                         reference_object: int | None = None, gap: Expr | None = None, sketch: str | None = None):
    """
    objects: ids de los objetos a alinear o distribuir.
    mode: borde o centro a alinear; distribute_horizontal/vertical reparte las separaciones.
    reference: selection, origin u object.
    reference_object: id del objeto de referencia (con reference=object).
    gap: separación exacta en mm al distribuir; vacío = huecos iguales entre los extremos actuales.
    sketch: id o nombre del boceto.
    """
    def cambiar(b):
        _exigir(b, objects)
        if reference == "object":
            _exigir(b, [reference_object])
        distancia = None if gap is None else sesion.doc.parametros.evaluar(gap)
        ob.alinear(b, objects, ALINEACIONES[mode], {"selection": "seleccion", "origin": "origen", "object": "objeto"}[reference],
                   reference_object, distancia)
        return {"object_ids": objects}
    return _editar(sesion, sketch, cambiar)


@herramienta("duplicate_vector_objects", "vectores", "Duplica objetos con nuevos ids, sus textos editables y sus grupos interiores, en un solo deshacer.", modifica=True)
def duplicate_vector_objects(sesion, objects: list[int], dx: float = 10, dy: float = 0, sketch: str | None = None):
    """
    objects: ids de objetos raíz a duplicar.
    dx: desplazamiento horizontal de las copias, en mm.
    dy: desplazamiento vertical de las copias, en mm.
    sketch: id o nombre del boceto.
    """
    def copiar(b):
        _exigir(b, objects)
        from .herramientas_boceto import ligar_parametro_texto
        from ..timeline.operaciones import _contenido_texto, texto_con_valores
        nuevos = ob.duplicar(b, objects, dx, dy)
        valores = sesion.doc.parametros.valores()
        for i in ob.curvas(b, nuevos):
            t = b.curvas[i]
            if isinstance(t, Texto):
                contenido = texto_con_valores(_contenido_texto(t, valores), valores)
                t.parametro_texto = t.parametro_altura = t.altura_expr = None
                ligar_parametro_texto(sesion.doc, t, contenido)
        return {"object_ids": nuevos}
    return _editar(sesion, sketch, copiar)


@herramienta("get_vector_regions", "vectores", "Lista las regiones cerradas utilizables del objeto, excluidos los agujeros; extrude acepta profile='object:<id>'.")
def get_vector_regions(sesion, objects: list[int], sketch: str | None = None):
    """
    objects: ids de los objetos a consultar.
    sketch: id o nombre del boceto.
    """
    op, br = boceto_activo(sesion, sketch)
    _exigir(br.boceto, objects)
    todos, utiles = regiones(br.boceto, br.plano, objects)
    return {"sketch": op.id, "profiles": [{"index": i, "area": p.area, "curves": sorted(p.firma),
                                           "centroid": list(p.centroide_uv)} for i, p in enumerate(todos) if p in utiles]}


@herramienta("validate_vector_objects", "vectores", "Valida los contornos del objeto y comunica extremos abiertos, duplicados, degeneradas, cruces y regiones CAD inválidas.")
def validate_vector_objects(sesion, objects: list[int], tolerance: float = 1e-6, sketch: str | None = None):
    """
    objects: ids de objetos a validar.
    tolerance: tolerancia de coincidencia e intersección, en mm (0 < tolerance <= 1).
    sketch: id o nombre del boceto.
    """
    import math
    if not math.isfinite(tolerance) or not 0 < tolerance <= 1:
        raise error("INVALID_ARGUMENTS", "tolerance debe ser positiva y no superar 1 mm.")
    _op, br = boceto_activo(sesion, sketch)
    _exigir(br.boceto, objects)
    return validar_objetos(br.boceto, br.plano, objects, tolerance)


@herramienta("offset_vector_objects", "vectores", "Genera otro objeto con offset exacto de sus perfiles y agujeros. Positivo agranda el material, negativo lo reduce.", modifica=True)
def offset_vector_objects(sesion, objects: list[int], distance: Expr,
                          corners: Literal["round", "sharp"] = "round", sketch: str | None = None):
    """
    objects: ids de los objetos con perfiles cerrados.
    distance: distancia exacta en mm, número o expresión.
    corners: round redondea las esquinas, sharp las prolonga.
    sketch: id o nombre del boceto.
    """
    _op, br = boceto_activo(sesion, sketch)
    def cambiar(b):
        _exigir(b, objects)
        return {"object_id": desfasar(b, br.plano, objects, sesion.doc.parametros.evaluar(distance),
                                     "redondas" if corners == "round" else "vivas")}
    return _editar(sesion, sketch, cambiar)


@herramienta("combine_vector_objects", "vectores", "Une, resta o interseca perfiles en un objeto nuevo; agrupar es otra herramienta. Conserva los recursos originales ocultos.", modifica=True)
def combine_vector_objects(sesion, objects: list[int], operation: Literal["union", "subtract", "intersect"] = "union",
                           sketch: str | None = None):
    """
    objects: ids de los objetos; el primero es el objetivo al restar o intersecar.
    operation: union, subtract o intersect.
    sketch: id o nombre del boceto.
    """
    _op, br = boceto_activo(sesion, sketch)
    def cambiar(b):
        _exigir(b, objects)
        return {"object_id": combinar(b, br.plano, objects,
                                      {"union": "union", "subtract": "resta", "intersect": "interseccion"}[operation])}
    return _editar(sesion, sketch, cambiar)


@herramienta("separate_vector_regions", "vectores", "Separa islas o letras convertidas en objetos independientes, con sus agujeros y sus transformaciones. Un texto editable debe convertirse primero con explode_text.", modifica=True)
def separate_vector_regions(sesion, object: int, sketch: str | None = None):
    """
    object: id del objeto raíz que contiene regiones independientes.
    sketch: id o nombre del boceto.
    """
    _op, br = boceto_activo(sesion, sketch)
    def cambiar(b):
        _exigir(b, [object])
        return {"object_ids": separar_regiones(b, br.plano, object)}
    return _editar(sesion, sketch, cambiar)


@herramienta("simplify_vector_object", "vectores", "Simplificación conservadora opcional: quita líneas duplicadas y tramos colineales, conserva Bézier, cierres y agujeros e informa el desvío medido y su cota.", modifica=True)
def simplify_vector_object(sesion, object: int, tolerance: float = 0.01, sketch: str | None = None):
    """
    object: id del objeto a simplificar.
    tolerance: cota máxima acumulada en mm (0 < tolerance <= 1); no es una orden de aproximar curvas.
    sketch: id o nombre del boceto.
    """
    def cambiar(b):
        _exigir(b, [object])
        return ob.simplificar(b, object, tolerance)
    return _editar(sesion, sketch, cambiar)


@herramienta("select_vector_objects", "vectores", "Selecciona objetos por id en la ventana, en el editor o en el visor principal. La selección es exclusivamente visual; para transformar sin ventana usá transform_vector_objects.")
def select_vector_objects(sesion, objects: list[int], mode: Literal["replace", "add", "remove"] = "replace",
                          sketch: str | None = None):
    """
    objects: ids de objetos raíz del boceto.
    mode: replace reemplaza la selección; add suma objetos; remove los quita.
    sketch: boceto del visor principal; vacío = boceto abierto o último boceto.
    """
    elegir = getattr(sesion, "seleccionar_objetos_vectoriales", None)
    if elegir is None:
        raise error("APP_NOT_RUNNING", "La selección visual necesita la ventana con un boceto abierto.")
    return elegir(objects, mode, sketch)


def organizacion(b):
    """Lo que muestra el navegador al editar el boceto: categorías con sus piezas, grupos y geometría suelta."""
    from ..restricciones.objetos import CATEGORIAS
    arriba = ob.padres(b)

    def fila(oid):
        o = b.objetos[oid]
        hijos = [i for i in o["entidades"] if i in b.objetos]
        return {"id": oid, "name": o["nombre"], "category": ob.categoria(b, oid), "source": o.get("tipo_origen"),
                "visible": o["visible"],
                "locked": o["bloqueado"], "in_profiles": o.get("perfiles", True), "parent": arriba.get(oid),
                "children": hijos if ob.categoria(b, oid) == "grupos" else [],
                "parts": len(hijos) if ob.categoria(b, oid) != "grupos" else 0, "curves": len(ob.curvas(b, [oid]))}
    unidades = ob.unidades(b)
    sueltas = [{"id": i, "name": ob.nombre_curva(b, i), "type": b.curvas[i].tipo,
                "construction": b.curvas[i].construccion} for i in ob.geometria_suelta(b)]
    categorias = {}
    for clave, titulo in CATEGORIAS.items():
        filas = [fila(i) for i in unidades[clave]]
        extra = sueltas if clave == "geometrias" else []
        categorias[clave] = {"title": titulo, "count": len(filas) + len(extra), "objects": filas, "curves": extra}
    return {"categories": categorias, "isolation_active": ob.aislamiento_activo(b)}


@herramienta("get_sketch_organization", "vectores", "Consulta la organización del boceto como la ve el navegador al editarlo: "
             "Geometrías, Textos, SVG / DXF y Grupos personalizados, con ids, nombres, visible, bloqueado y en perfiles.")
def get_sketch_organization(sesion, sketch: str | None = None):
    """
    sketch: id o nombre del boceto; vacío = último boceto activo.
    """
    op, br = boceto_activo(sesion, sketch)
    return {"sketch": op.id, **organizacion(br.boceto)}


@herramienta("isolate_vector_objects", "vectores", "Aísla objetos: oculta todo lo demás (también la geometría suelta) hasta restaurar. "
             "Sin objetos termina el aislamiento y devuelve la visibilidad que había.", modifica=True)
def isolate_vector_objects(sesion, objects: list[int] | None = None, sketch: str | None = None):
    """
    objects: ids de los objetos que quedan a la vista; vacío = restaurar el aislamiento.
    sketch: id o nombre del boceto.
    """
    def cambiar(b):
        if objects:
            _exigir(b, objects)
            ob.aislar(b, objects)
        else:
            ob.restaurar_aislamiento(b)
        return {"isolation_active": ob.aislamiento_activo(b)}
    return _editar(sesion, sketch, cambiar)


@herramienta("move_vector_objects_to_group", "vectores", "Cambia la pertenencia de objetos a un grupo personalizado sin moverlos en pantalla; "
             "sin grupo los saca a la raíz. Un grupo que queda vacío desaparece.", modifica=True)
def move_vector_objects_to_group(sesion, objects: list[int], group: int | None = None, sketch: str | None = None):
    """
    objects: ids de objetos (textos, SVG/DXF, geometrías o grupos).
    group: id del grupo personalizado de destino; vacío = sacarlos del grupo.
    sketch: id o nombre del boceto.
    """
    def cambiar(b):
        _exigir(b, objects)
        ob.mover_a_grupo(b, objects, group)
        return {"object_ids": objects, "group": group}
    return _editar(sesion, sketch, cambiar)


@herramienta("delete_vector_objects", "vectores", "Elimina objetos con sus curvas, o solo el contenedor de un grupo personalizado "
             "(keep_contents) dejando sus objetos donde estaban. Se deshace con undo.", modifica=True)
def delete_vector_objects(sesion, objects: list[int], keep_contents: bool = False, sketch: str | None = None):
    """
    objects: ids de los objetos o grupos a eliminar.
    keep_contents: true quita solo el grupo y conserva su contenido; false borra también las curvas.
    sketch: id o nombre del boceto.
    """
    def cambiar(b):
        _exigir(b, objects)
        ob.eliminar(b, objects, keep_contents is False)
        return {"deleted": objects}
    return _editar(sesion, sketch, cambiar)
