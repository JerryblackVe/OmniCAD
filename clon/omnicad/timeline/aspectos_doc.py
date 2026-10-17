# -*- coding: utf-8 -*-
"""
Los aspectos de un diseño («En este diseño» del panel Aspecto de Fusion).

Cada diseño guarda su lista de aspectos en `Documento.propiedades["__aspectos__"]["lista"]` (como el navegador guarda
sus grupos en «__navegador__»): entran en deshacer y viajan con el proyecto. Un aspecto del diseño es la ficha de
`nucleo.aspectos` más un `id` («asp1»). Al asignarlo, cada cuerpo (o cara) recibe además su color y su acabado
(`apariencia`, `acabado`: lo que ya leen el visor, el render y la exportación) y el `id` del aspecto, así editar el
aspecto del diseño los pone al día a todos a la vez.

  propiedades[cuerpo] = {"apariencia": [r, g, b], "acabado": {...}, "aspecto": "asp1",
                         "caras": [{"ref": <referencia persistente de la cara>, "apariencia", "acabado", "aspecto"}]}

Las funciones de acá modifican el documento con UNA instantánea de deshacer (`Documento.set_propiedades`).
"""
import copy

from ..nucleo import aspectos as asp
from ..nucleo import geometria as geo
from . import entidades as ent

CLAVE = "__aspectos__"


def lista(doc):
    """Los aspectos del diseño, con su id (copia: modificarla no cambia el documento)."""
    datos = doc.propiedades.get(CLAVE, {}).get("lista", [])
    return copy.deepcopy(datos) if isinstance(datos, list) else []


def buscar(doc, ref):
    """El aspecto del diseño con ese id o ese nombre (sin distinguir mayúsculas), o None."""
    texto = str(ref).strip().casefold()
    todos = lista(doc)
    return next((a for a in todos if a["id"].casefold() == texto), None) or \
        next((a for a in todos if a["nombre"].casefold() == texto), None)


def usos(doc, aid):
    """({ids de cuerpos con ese aspecto}, [(id de cuerpo, referencia de cara)]) en todo el diseño."""
    cuerpos, caras = [], []
    for cid, props in doc.propiedades.items():
        if cid == CLAVE or not isinstance(props, dict):
            continue
        if props.get("aspecto") == aid:
            cuerpos.append(cid)
        caras += [(cid, c["ref"]) for c in props.get("caras", []) if isinstance(c, dict) and c.get("aspecto") == aid]
    return cuerpos, caras


def _id_nuevo(todos):
    usados = {a["id"] for a in todos}
    n = 1
    while f"asp{n}" in usados:
        n += 1
    return f"asp{n}"


def nombre_unico(todos, nombre, ignorar=None):
    """«X», o «X (1)», «X (2)»… si ya hay uno con ese nombre (como «ABS (blanco) (1)» de Fusion)."""
    usados = {a["nombre"].casefold() for a in todos if a["id"] != ignorar}
    if nombre.casefold() not in usados:
        return nombre
    n = 1
    while f"{nombre} ({n})".casefold() in usados:
        n += 1
    return f"{nombre} ({n})"


def _contenido(a):
    return {k: v for k, v in a.items() if k not in ("id", "origen")}


def _por_cuerpo(caras):
    """{id de cuerpo: [referencias de sus caras]} de una lista de (id de cuerpo, referencia)."""
    salida = {}
    for cid, ref in caras:
        salida.setdefault(cid, []).append(ref)
    return salida


def _con_aspecto(entrada):
    return {"apariencia": list(entrada["color"]), "acabado": asp.acabado_de(entrada), "aspecto": entrada["id"]}


def entrada_para(doc, aspecto, origen=None):
    """(lista nueva, entrada) para usar `aspecto` en este diseño: si ya está (mismo nombre y mismo contenido) se
    reusa; si no, se suma con un id nuevo y un nombre que no choque."""
    todos = lista(doc)
    a = asp.normalizar(aspecto)
    for existente in todos:
        if existente["nombre"] == a["nombre"] and _contenido(existente) == _contenido(a):
            return todos, existente
    entrada = dict(a, id=_id_nuevo(todos), nombre=nombre_unico(todos, a["nombre"]))
    if origen:
        entrada["origen"] = origen
    todos.append(entrada)
    return todos, entrada


def _cambios_de_cuerpo(doc, cid):
    return doc.propiedades.get(cid, {})


def asignar(doc, aspecto, cuerpos=(), caras=(), origen=None):
    """Pone `aspecto` (un dict de `nucleo.aspectos`, o el de «En este diseño») en los cuerpos y en las caras
    (lista de (id de cuerpo, referencia de cara)). Devuelve la entrada del diseño."""
    todos, entrada = entrada_para(doc, aspecto, origen)
    cambios = {CLAVE: {"lista": todos}}
    for cid in cuerpos:
        cambios.setdefault(cid, {}).update(_con_aspecto(entrada))
    for cid, refs in _por_cuerpo(caras).items():
        actuales = [c for c in _cambios_de_cuerpo(doc, cid).get("caras", []) if c["ref"] not in refs]
        cambios.setdefault(cid, {})["caras"] = actuales + [dict(_con_aspecto(entrada), ref=ref) for ref in refs]
    doc.set_propiedades(cambios)
    return entrada


def asignar_color(doc, rgb, cuerpos=(), caras=()):
    """Un color suelto (sin aspecto del diseño): los cuerpos y caras toman el color y pierden su acabado."""
    suelto = {"apariencia": list(rgb), "acabado": None, "aspecto": None}
    cambios = {cid: dict(suelto) for cid in cuerpos}
    for cid, refs in _por_cuerpo(caras).items():
        actuales = [c for c in _cambios_de_cuerpo(doc, cid).get("caras", []) if c["ref"] not in refs]
        cambios.setdefault(cid, {})["caras"] = actuales + [dict(suelto, ref=ref) for ref in refs]
    doc.set_propiedades(cambios)


def quitar(doc, cuerpos=(), caras=()):
    """Saca el aspecto de los cuerpos (queda el color de su material) y de las caras (vuelven al del cuerpo)."""
    cambios = {}
    for cid in cuerpos:
        cambios.setdefault(cid, {}).update({"apariencia": None, "acabado": None, "aspecto": None})
    for cid, refs in _por_cuerpo(caras).items():
        resto = [c for c in _cambios_de_cuerpo(doc, cid).get("caras", []) if c["ref"] not in refs]
        cambios.setdefault(cid, {})["caras"] = resto or None
    if cambios:
        doc.set_propiedades(cambios)


def _repartir(doc, entradas):
    """Cambios de propiedades que ponen al día a quienes usan alguna de las `entradas` (cuerpos y caras), en una sola
    pasada: un cuerpo con caras de dos aspectos editados recibe las dos novedades juntas."""
    por_id = {e["id"]: e for e in entradas}
    cambios = {}
    for cid, props in doc.propiedades.items():
        if cid == CLAVE or not isinstance(props, dict):
            continue
        if props.get("aspecto") in por_id:
            cambios[cid] = _con_aspecto(por_id[props["aspecto"]])
        caras = props.get("caras")
        if caras and any(c.get("aspecto") in por_id for c in caras):
            cambios.setdefault(cid, {})["caras"] = [
                dict(c, **_con_aspecto(por_id[c["aspecto"]])) if c.get("aspecto") in por_id else c for c in caras]
    return cambios


def editar(doc, ref, cambios_aspecto):
    """Cambia propiedades de un aspecto del diseño; todos los cuerpos y caras que lo usan se ven con el cambio."""
    todos = lista(doc)
    anterior = buscar(doc, ref)
    if anterior is None:
        raise geo.ErrorGeometria(f"El diseño no tiene un aspecto «{ref}».")
    entrada = dict(asp.normalizar(asp.mezclar(anterior, cambios_aspecto)), id=anterior["id"])
    if "origen" in anterior:
        entrada["origen"] = anterior["origen"]
    entrada["nombre"] = nombre_unico(todos, entrada["nombre"], ignorar=anterior["id"])
    nueva = [entrada if a["id"] == entrada["id"] else a for a in todos]
    cambios = {CLAVE: {"lista": nueva}, **_repartir(doc, [entrada])}
    doc.set_propiedades(cambios)
    return entrada


def agregar(doc, aspecto, origen=None):
    """Suma `aspecto` al diseño con un id nuevo y un nombre libre, sin asignarlo a nada. Devuelve la entrada."""
    todos = lista(doc)
    entrada = dict(asp.normalizar(aspecto), id=_id_nuevo(todos))
    entrada["nombre"] = nombre_unico(todos, entrada["nombre"])
    if origen:
        entrada["origen"] = origen
    todos.append(entrada)
    doc.set_propiedades({CLAVE: {"lista": todos}})
    return entrada


def duplicar(doc, ref, nombre=None):
    todos = lista(doc)
    anterior = buscar(doc, ref)
    if anterior is None:
        raise geo.ErrorGeometria(f"El diseño no tiene un aspecto «{ref}».")
    entrada = dict(anterior, id=_id_nuevo(todos), nombre=nombre_unico(todos, nombre or anterior["nombre"]))
    todos.append(entrada)
    doc.set_propiedades({CLAVE: {"lista": todos}})
    return entrada


def suprimir(doc, ref, quitar_usos=False):
    """Saca un aspecto del diseño. Si lo usan cuerpos o caras, falla salvo `quitar_usos` (se los saca también)."""
    anterior = buscar(doc, ref)
    if anterior is None:
        raise geo.ErrorGeometria(f"El diseño no tiene un aspecto «{ref}».")
    cuerpos, caras = usos(doc, anterior["id"])
    if (cuerpos or caras) and not quitar_usos:
        raise geo.ErrorGeometria(f"«{anterior['nombre']}» lo usan {len(cuerpos)} cuerpo(s) y {len(caras)} cara(s): "
                                 "quitáselo primero o pedí que se quite de todos.")
    cambios = {CLAVE: {"lista": [a for a in lista(doc) if a["id"] != anterior["id"]]}}
    doc.set_propiedades(cambios)
    if cuerpos or caras:
        quitar(doc, cuerpos, caras)
    return anterior, cuerpos, caras


def reemplazar_lista(doc, nueva):
    """Escribe la lista de «En este diseño» que armó el panel Aspecto: los aspectos nuevos (id «nuevoN», duplicados) reciben
    su id definitivo, los que cambiaron ponen al día a sus cuerpos y caras, y uno que se sacó y todavía se usa es un
    error. Devuelve {id provisorio: id definitivo}."""
    actual = lista(doc)
    conocidos = {a["id"]: a for a in actual}
    destino, mapa = [], {}
    for a in nueva:
        entrada = dict(asp.normalizar(a), id=a["id"])
        if "origen" in a:
            entrada["origen"] = a["origen"]
        if entrada["id"] not in conocidos:
            mapa[entrada["id"]] = entrada["id"] = _id_nuevo(actual + destino)
        destino.append(entrada)
    for anterior in actual:
        if anterior["id"] not in {e["id"] for e in destino} and any(usos(doc, anterior["id"])):
            raise geo.ErrorGeometria(f"«{anterior['nombre']}» todavía se usa: no se puede sacar del diseño.")
    cambiaron = [e for e in destino if e["id"] in conocidos and _contenido(conocidos[e["id"]]) != _contenido(e)]
    doc.set_propiedades({CLAVE: {"lista": destino}, **_repartir(doc, cambiaron)})
    return mapa


def renombrar(doc, ref, nombre):
    return editar(doc, ref, {"nombre": nombre})


def propiedades_con(doc, nueva):
    """Las propiedades del documento como quedarían al escribir `nueva` («En este diseño» editado en un panel): la vista
    previa de Render, que muestra los cambios sin tocar el documento. Sin cambios devuelve las propiedades tal cual."""
    actual = {a["id"]: a for a in lista(doc)}
    cambiaron = [dict(asp.normalizar(a), id=a["id"]) for a in nueva
                 if a["id"] in actual and _contenido(actual[a["id"]]) != _contenido(a)]
    if not cambiaron:
        return doc.propiedades
    salida = {k: dict(v) if isinstance(v, dict) else v for k, v in doc.propiedades.items()}
    for cid, claves in _repartir(doc, cambiaron).items():
        salida.setdefault(cid, {}).update(claves)
    return salida


def aplicar_panel(doc, diseno, elegido=None, cuerpos=(), caras=(), rgb=None):
    """Lo que escribe el panel Aspecto al aplicar (Aceptar en Diseño, aplicar en Render): la lista editada de «En este
    diseño» (`diseno`, None = sin tocarla) y después el color suelto `rgb` o el aspecto `elegido` en los cuerpos y las
    caras. Devuelve {id provisorio: id definitivo} de los aspectos nuevos. Pensada para correr en una transacción."""
    mapa = reemplazar_lista(doc, diseno) if diseno is not None and diseno != lista(doc) else {}
    if rgb is not None:
        asignar_color(doc, rgb, cuerpos, caras)
    elif elegido is not None:
        origen = None if "id" in elegido else ("mis" if elegido["nombre"] in asp.cargar_usuario()["mis"] else "biblioteca")
        asignar(doc, elegido, cuerpos, caras, origen)
    return mapa


def cara_de(estado, ref):
    """La cara OCC a la que apunta `ref`, o None si ya no existe (la geometría cambió demasiado)."""
    try:
        return ent.resolver(ref, estado).forma
    except ent.ErrorReferencia:
        return None


def caras_propias(props):
    """[(referencia, propiedades)] de las caras con aspecto propio de un cuerpo (`props`: sus propiedades en el documento)."""
    return [(c["ref"], c) for c in props.get("caras") or [] if isinstance(c, dict) and c.get("ref") and c.get("apariencia")]


def caras_con_aspecto(doc, estado):
    """[(id de cuerpo, referencia de cara, color [r, g, b])] de las caras pintadas de los cuerpos que existen."""
    salida = []
    for cid, props in doc.propiedades.items():
        if cid == CLAVE or cid not in estado.cuerpos or not isinstance(props, dict):
            continue
        for c in props.get("caras", []):
            if isinstance(c, dict) and c.get("ref") and c.get("apariencia"):
                salida.append((cid, c["ref"], list(c["apariencia"])))
    return salida
