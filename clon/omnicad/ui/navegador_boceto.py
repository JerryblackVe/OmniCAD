# -*- coding: utf-8 -*-
"""Navegador del boceto en edición: categorías, grupos, selección sincronizada y menús del clic derecho.

Toda acción corre sobre el boceto del editor con `aplicar_cambio` (un paso de deshacer del boceto) y llama a las
mismas funciones de `restricciones/objetos.py` que usan las herramientas MCP/CLI del grupo «vectores».
"""
from PySide6.QtWidgets import QInputDialog, QMenu, QMessageBox

from ..restricciones import objetos as ob
from ..restricciones.boceto import Texto
from .navegador import ROL_CLAVE, ROL_TIPO

PREFIJOS = ("bk:", "bo:", "bc:", "bg:")


def _lienzo(v):
    mb = getattr(v, "modo_boceto", None)
    return mb.lienzo if mb is not None and mb.activo else None


def organizacion(v):
    """(id del boceto, organización) del boceto abierto, o None fuera del boceto."""
    lz, mb = _lienzo(v), v.modo_boceto
    op = (mb.datos or {}).get("op") if lz is not None else None
    if op is None:
        return None
    from ..api.herramientas_objetos_vectoriales import organizacion as datos
    return op.id, datos(lz.b)


def refrescar(v):
    """Rearma solo la rama del boceto si cambió su organización (nombres, banderas, contenido)."""
    actual = organizacion(v)
    if actual != v.navegador.boceto_edicion:
        v.navegador.actualizar_boceto(*(actual or ((v.navegador.boceto_edicion or (None,))[0], None)))


def id_de(clave):
    return int(clave.rsplit(":", 1)[1])


def claves_de(v, ids):
    """Filas del navegador de los objetos o curvas `ids` (un objeto dentro de un grupo aparece dos veces)."""
    nav = v.navegador
    return [k for k in nav._items if k.startswith(PREFIJOS[1:]) and id_de(k) in set(ids)]


def _objeto_de(clave):
    """Id del objeto arrastrado desde `bo:<oid>` o desde un miembro `bg:<gid>:<oid>`; None si no es objeto de boceto."""
    if not isinstance(clave, str):
        return None
    if clave.startswith("bg:"):
        return int(clave.split(":", 2)[2])
    if clave.startswith("bo:"):
        return int(clave[3:])
    return None


def _mover_desde_arbol(v, origen, destino):
    """Arrastrar una fila del árbol sobre un grupo del boceto: mueve el objeto al grupo (un paso de deshacer).

    Equivale a «Mover a grupo» del menú del navegador (reusa `ob.mover_a_grupo`). Devuelve True si cambió algo.
    """
    lz = _lienzo(v)
    if lz is None or not origen or not destino:
        return False
    oid = _objeto_de(origen)
    gid = id_de(destino) if destino.startswith("bo:") else (int(destino.split(":", 2)[1]) if destino.startswith("bg:") else None)
    if oid is None or gid is None or oid == gid:
        return False
    if ob.categoria(lz.b, oid) == "grupos":        # no se anidan grupos dentro de grupos
        return False
    if ob.categoria(lz.b, gid) != "grupos":         # el destino debe ser un grupo, no un objeto suelto
        return False
    return _cambiar(v, lambda b: ob.mover_a_grupo(b, [oid], gid))


def seleccion_editor(v):
    lz = _lienzo(v)
    if lz is None:
        return
    elegidos = [i for i in lz.seleccion if i in lz.b.objetos or i in lz.b.curvas]
    v.navegador.seleccionar(claves_de(v, elegidos), revelar=False)


def seleccionar(v, claves):
    """Clic (Ctrl, Mayús) en el navegador → la misma selección en el visor del boceto."""
    lz = _lienzo(v)
    ids = [id_de(k) for k in claves if k.startswith(PREFIJOS[1:])]
    if lz is None or not ids and claves:
        return                                 # una fila de cuerpo o de carpeta no borra lo elegido en el boceto
    ids = [i for i in dict.fromkeys(ids) if i in lz.b.curvas or (i in lz.b.objetos and lz.b.objetos[i]["visible"])]
    lz.objetos.modo_perfiles = False
    lz.perfiles_sel = []
    lz.seleccion = ids
    lz._notificar_seleccion()
    lz.update()


def _cambiar(v, funcion):
    lz = _lienzo(v)
    if lz is None or not lz.aplicar_cambio(lambda: funcion(lz.b)):
        return False
    lz.objetos._firma = None
    lz.seleccion = [i for i in lz.seleccion if i in lz.b.objetos or i in lz.b.curvas]
    lz._notificar_seleccion()
    lz.update()
    refrescar(v)
    return True


def alternar_visible(v, clave):
    oid = id_de(clave)
    _cambiar(v, lambda b: b.objetos[oid].update(visible=not b.objetos[oid]["visible"]))


def renombrar(v, clave, nombre):
    oid = id_de(clave)
    _cambiar(v, lambda b: b.objetos[oid].update(nombre=nombre))


def _bandera(v, ids, clave, valor):
    _cambiar(v, lambda b: [b.objetos[i].update({clave: valor}) for i in ids])


def _reflejar(v, ids, horizontal):
    def cambiar(b):
        x0, y0, x1, y1 = ob.caja(b, ids)
        ob.transformar(b, ids, ob.afin(sx=-1 if horizontal else 1, sy=1 if horizontal else -1,
                                       pivote=((x0 + x1) / 2, (y0 + y1) / 2)))
    _cambiar(v, cambiar)


def _duplicar(v, ids):
    nuevos = []
    if _cambiar(v, lambda b: nuevos.extend(ob.duplicar(b, ids))):
        seleccionar(v, [f"bo:{i}" for i in nuevos])


def _agrupar(v, ids):
    nombre, ok = QInputDialog.getText(v, "Agrupar", "Nombre del grupo:", text="Grupo")
    if ok and nombre.strip():
        _cambiar(v, lambda b: ob.crear(b, ids, nombre.strip()))


def _renombrar_dialogo(v, oid):
    lz = _lienzo(v)
    nombre, ok = QInputDialog.getText(v, "Renombrar", "Nombre:", text=lz.b.objetos[oid]["nombre"])
    if ok and nombre.strip():
        renombrar(v, f"bo:{oid}", nombre.strip())


def _eliminar(v, ids, contenido):
    lz = _lienzo(v)
    curvas = len(ob.curvas(lz.b, ids))
    if contenido and QMessageBox.question(
            v, "Eliminar", f"Se borran {len(ids)} objeto(s) con sus {curvas} curvas. Se puede deshacer con Ctrl+Z.",
            QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
        return
    _cambiar(v, lambda b: ob.eliminar(b, ids, contenido))


def _editar(v, oid):
    lz = _lienzo(v)
    textos = [i for i in ob.curvas(lz.b, [oid]) if isinstance(lz.b.curvas[i], Texto)]
    seleccionar(v, [f"bo:{oid}"])
    if textos and lz.b.objetos[oid].get("texto_automatico") is not None:
        lz.editar_texto(textos[0], lz.a_px(*ob.pivote(lz.b, oid)))


def _accion(m, texto, funcion, habilitada=True, ayuda=""):
    a = m.addAction(texto, funcion)
    a.setEnabled(habilitada)
    if ayuda:
        a.setToolTip(ayuda)
    return a


def _menu_objetos(v, m, ids):
    """Clic derecho sobre uno o varios objetos (o un grupo): acciones según su tipo y su estado."""
    b = _lienzo(v).b
    uno = ids[0] if len(ids) == 1 else None
    es_grupo = uno is not None and ob.categoria(b, uno) == "grupos"
    bloqueados = any(b.objetos[i]["bloqueado"] for i in ids)
    traba = "Desbloqueá el objeto para cambiarlo." if bloqueados else ""
    arriba = ob.padres(b)
    grupos = [g for g in ob.unidades(b)["grupos"] if g not in ids]
    if uno is not None:
        if es_grupo:
            _accion(m, "Renombrar grupo…", lambda: _renombrar_dialogo(v, uno))
            _accion(m, "Seleccionar contenido", lambda: seleccionar(v, [f"bo:{i}" for i in b.objetos[uno]["entidades"]
                                                                           if i in b.objetos]))
        else:
            _accion(m, "Editar", lambda: _editar(v, uno),
                    ayuda="Un texto abre su edición; los demás objetos quedan elegidos con su marco.")
            _accion(m, "Renombrar…", lambda: _renombrar_dialogo(v, uno))
        m.addSeparator()
    sufijo = " grupo" if es_grupo else ""
    _accion(m, f"Mover / Rotar{sufijo}", lambda: seleccionar(v, [f"bo:{i}" for i in ids]), not bloqueados,
            traba or "Elige el objeto: arrastralo o usá la manija de giro y los campos del panel.")
    _accion(m, f"Escalar{sufijo}", lambda: seleccionar(v, [f"bo:{i}" for i in ids]), not bloqueados,
            traba or "Elige el objeto: usá las manijas de las esquinas o el ancho y el alto del panel.")
    if not es_grupo:
        reflejar = m.addMenu("Reflejar")
        reflejar.setEnabled(not bloqueados)
        reflejar.addAction("Horizontal", lambda: _reflejar(v, ids, True))
        reflejar.addAction("Vertical", lambda: _reflejar(v, ids, False))
        _accion(m, "Duplicar", lambda: _duplicar(v, ids), all(i in ob.raices(b) for i in ids),
                "Para duplicar un objeto de un grupo, sacalo del grupo o duplicá el grupo.")
    m.addSeparator()
    if es_grupo:
        _accion(m, "Agregar objetos…", lambda: _agregar_a_grupo(v, uno))
        _accion(m, "Desagrupar", lambda: _cambiar(v, lambda b: ob.desagrupar(b, uno)), not bloqueados, traba)
    else:
        _accion(m, "Agrupar", lambda: _agrupar(v, ids), all(i in ob.raices(b) for i in ids),
                "Para agrupar objetos que ya están en un grupo, usá «Mover a grupo».")
        mover = m.addMenu("Mover a grupo")
        mover.setEnabled(not bloqueados)
        for g in grupos:
            mover.addAction(b.objetos[g]["nombre"], lambda _=False, g=g: _cambiar(v, lambda b: ob.mover_a_grupo(b, ids, g)))
        sacar = mover.addAction("Fuera de grupos", lambda: _cambiar(v, lambda b: ob.mover_a_grupo(b, ids, None)))
        sacar.setEnabled(any(arriba.get(i) is not None for i in ids))
    m.addSeparator()
    visibles = all(b.objetos[i]["visible"] for i in ids)
    _accion(m, ("Ocultar" if visibles else "Mostrar") + (" contenido" if es_grupo else ""),
            lambda: _bandera(v, ids, "visible", not visibles))
    _accion(m, "Aislar" + sufijo, lambda: _cambiar(v, lambda b: ob.aislar(b, ids)))
    _accion(m, "Desbloquear" if bloqueados else "Bloquear", lambda: _bandera(v, ids, "bloqueado", not bloqueados))
    en_perfiles = all(b.objetos[i].get("perfiles", True) for i in ids)
    a = _accion(m, "Participar en perfiles", lambda: _bandera(v, ids, "perfiles", not en_perfiles),
                ayuda="Apagado, sus curvas no forman perfiles CAD aunque se vean.")
    a.setCheckable(True)
    a.setChecked(en_perfiles)
    m.addSeparator()
    if uno is not None and not es_grupo:
        _accion(m, "Propiedades", lambda: seleccionar(v, [f"bo:{uno}"]),
                ayuda="Elige el objeto: el panel muestra su posición, tamaño, ángulo y opciones.")
    if es_grupo:
        _accion(m, "Eliminar grupo (conservar objetos)", lambda: _eliminar(v, ids, False), not bloqueados, traba)
        _accion(m, "Eliminar grupo y su contenido…", lambda: _eliminar(v, ids, True), not bloqueados, traba)
    else:
        _accion(m, "Eliminar…", lambda: _eliminar(v, ids, True), not bloqueados, traba)


def _agregar_a_grupo(v, gid):
    """Suma al grupo los objetos elegidos en el visor (o pide elegirlos)."""
    lz = _lienzo(v)
    ids = [i for i in lz.objetos.seleccion() if i != gid]
    if not ids:
        v.mensaje("Elegí en el visor los objetos que querés sumar al grupo y repetí «Agregar objetos…».", 7000)
        return
    _cambiar(v, lambda b: ob.mover_a_grupo(b, ids, gid))


def _menu_categoria(v, m, cat):
    b = _lienzo(v).b
    ids = ob.unidades(b)[cat]
    curvas = ob.geometria_suelta(b) if cat == "geometrias" else []
    nada = "La categoría está vacía." if not ids and not curvas else ""
    _accion(m, "Crear grupo", lambda: _agrupar(v, [i for i in ids if i in ob.raices(b)]),
            any(i in ob.raices(b) for i in ids), "Agrupa los objetos de la categoría que no están en otro grupo.")
    _accion(m, "Seleccionar contenido", lambda: seleccionar(v, [f"bo:{i}" for i in ids] + [f"bc:{i}" for i in curvas]),
            not nada, nada)
    _accion(m, "Mostrar todo", lambda: _bandera(v, ids, "visible", True), bool(ids), nada)
    _accion(m, "Ocultar todo", lambda: _bandera(v, ids, "visible", False), bool(ids),
            nada or "La geometría suelta se oculta solo al aislar.")
    _accion(m, "Aislar categoría", lambda: _cambiar(v, lambda b: ob.aislar(b, ids)), bool(ids),
            nada or "Solo la geometría suelta: agrupala en un objeto para aislarla.")
    m.addSeparator()
    it = v.navegador.item(f"bk:{cat}")
    _accion(m, "Contraer" if it is not None and it.isExpanded() else "Expandir",
            lambda: it.setExpanded(not it.isExpanded()), it is not None)


def _menu_vacio(v, m):
    b = _lienzo(v).b
    elegidos = [i for i in _lienzo(v).objetos.seleccion() if i in ob.raices(b)]
    _accion(m, "Crear grupo", lambda: _agrupar(v, elegidos), bool(elegidos),
            "Elegí en el visor o en el navegador los objetos que va a contener.")
    _accion(m, "Expandir todo", lambda: _plegar(v, True))
    _accion(m, "Contraer todo", lambda: _plegar(v, False))
    _accion(m, "Mostrar todos los objetos", lambda: _bandera(v, list(b.objetos), "visible", True), bool(b.objetos))
    _accion(m, "Restaurar aislamiento", lambda: _cambiar(v, ob.restaurar_aislamiento), ob.aislamiento_activo(b),
            "No hay ningún objeto aislado.")


def _plegar(v, abrir):
    nav = v.navegador
    for k, it in nav._items.items():
        if k.startswith(PREFIJOS) and it.childCount():
            it.setExpanded(abrir)
    nav.ajustar_alto()


def menu(v, item):
    """Menú del clic derecho de la organización del boceto: objeto, grupo, curva suelta, categoría o área vacía."""
    lz = _lienzo(v)
    if lz is None:
        return None
    m = QMenu(v.navegador)
    m.setToolTipsVisible(True)
    if item is None:
        _menu_vacio(v, m)
        return m
    tipo, clave = item.data(0, ROL_TIPO), item.data(0, ROL_CLAVE)
    if tipo == "categoria_boceto":
        _menu_categoria(v, m, clave[3:])
    elif tipo == "objeto_boceto":
        elegidas = [it.data(0, ROL_CLAVE) for it in v.navegador.arbol.selectedItems()
                    if it.data(0, ROL_TIPO) == "objeto_boceto"]
        ids = list(dict.fromkeys(id_de(k) for k in (elegidas if clave in elegidas else [clave])))
        _menu_objetos(v, m, [i for i in ids if i in lz.b.objetos])
    elif tipo == "curva_boceto":
        cid = id_de(clave)
        _accion(m, "Seleccionar", lambda: seleccionar(v, [clave]))
        _accion(m, "Convertir en objeto", lambda: _cambiar(v, lambda b: ob.crear(b, [cid], ob.nombre_curva(b, cid))),
                ayuda="Pasa a ser un objeto rígido: se puede renombrar, ocultar, bloquear y sacar de los perfiles.")
        m.addSeparator()
        _accion(m, "Eliminar", lambda: _cambiar(v, lambda b: b.eliminar(cid)))
    return m
