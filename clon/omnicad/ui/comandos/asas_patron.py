# -*- coding: utf-8 -*-
"""Manipuladores y dibujo de la vista previa de los patrones de sólido (rectangular, circular, en trayectoria y en
puntos). Las posiciones salen de las mismas funciones que usa el cálculo (`solidos_crear.paso_angular`,
`recorrido_ruta`, `OpPatron.instancias`), así el asa, la vista previa y el resultado nunca discrepan."""
import numpy as np

from ...nucleo import geometria as geo
from ...nucleo import solidos_crear as sc
from ...timeline import entidades as ent
from ...timeline.operaciones import Contexto
from ...timeline.parametros import ANGULO
from ..comando import ErrorComando
from .asas_extra import _asa_cantidad, _centro_cuerpos, _direccion_de, _paso
from .comunes import evaluar_o_cero

MAX_CASILLAS = 400
VERDE_REFERENCIA = (0.1, 0.7, 0.3)
AZUL_DESTINO = (0.17, 0.49, 0.91)


def _mp():
    from .. import manipuladores as mp
    return mp


def _n(v, clave):
    try:
        return max(1, int(v.get(clave) or 1))
    except (TypeError, ValueError):
        return 1


def centro_del_objeto(ctx, v):
    """Punto que se copia: el centro de la caja de los cuerpos elegidos o de las herramientas de las operaciones; None
    con caras, componentes o geometría de construcción (ahí las copias se suprimen escribiendo su número)."""
    objeto = v.get("objeto", "cuerpos")
    if objeto == "cuerpos":
        return _centro_cuerpos(ctx, v)
    if objeto != "operaciones":
        return None
    from .crear import pasos_repetibles
    try:
        cajas = [geo.caja_envolvente(r[0]) for pid in pasos_repetibles(v.get("pasos"), ctx)
                 for r in ctx.estado.herramientas.get(pid) or []]
    except (ErrorComando, Exception):  # noqa: BLE001 — pasos a medio escribir o sin herramienta
        return None
    if not cajas:
        return None
    return (np.min([c[0] for c in cajas], axis=0) + np.max([c[1] for c in cajas], axis=0)) / 2


def _rectangular(ctx, v, centro):
    mp = _mp()
    if not v.get("dir1"):
        return []
    e1 = mp.entidad(v["dir1"][0], ctx.estado)
    d1 = mp.unitario(ent.direccion(e1))
    salida = []
    if _n(v, "n1") > 1:
        salida.append(mp.Flecha("d1", centro, d1))
    salida.append(_asa_cantidad("n1", centro, d1, _paso(v, "n1", "d1", ctx)))
    derivada = not v.get("dir2")
    d2 = mp.unitario(ent.direccion_perpendicular(e1)) if derivada else _direccion_de(ctx, v["dir2"][0])
    if d2 is None or np.linalg.norm(d2) < 1e-9:
        return salida
    if _n(v, "n2") > 1:
        salida.append(mp.Flecha("d2", centro, d2, color=(0.1, 0.62, 0.55) if derivada else mp.AZUL))
    salida.append(_asa_cantidad("n2", centro, d2, _paso(v, "n2", "d2", ctx)))
    return salida


def _circular(ctx, v, centro):
    mp = _mp()
    if not v.get("eje"):
        return []
    punto, d = ent.como_eje(mp.entidad(v["eje"][0], ctx.estado))
    d = mp.unitario(d)
    pie = np.asarray(punto, float) + d * float((centro - punto) @ d)
    radio = float(np.linalg.norm(centro - pie))
    modo, n0 = v.get("modo", "completo"), _n(v, "n")
    clave = "angulo_paso" if modo == "espaciado" else "angulo"
    salida = []
    if modo != "completo":
        salida.append(mp.Angulo(clave, pie, d, centro - pie, radio if radio > 1e-6 else None))
    if radio > 1e-6:
        total = 360.0 if modo == "completo" else evaluar_o_cero(ctx, v.get(clave), ANGULO)
        simetrico = modo == "simetrico" or (modo == "espaciado" and bool(v.get("simetrico_paso")))
        paso = sc.paso_angular(n0, total, "espaciado" if modo == "espaciado" else "completa", simetrico)
        u, signo = (centro - pie) / radio, (-1.0 if paso < 0 else 1.0)

        def posicion(n):
            a = np.radians(paso * (n - 1))
            p = pie + radio * (u * np.cos(a) + np.cross(d, u) * np.sin(a))
            return p, np.cross(d, (p - pie) / radio) * signo
        salida.append(mp.AsaCantidad("n", posicion, radio * abs(np.radians(paso)) or 10.0))
    return salida


def ruta_del_patron(ctx, v):
    """Las aristas de la ruta tal como las resuelve OpPatron (una cadena continua)."""
    from ...timeline.ops_solido import _aristas
    return _aristas([h["ref"] for h in v.get("ruta") or []], ctx.estado, "la ruta")[1]


_PERFILES = {}                 # (estado, referencias de la ruta) → (aristas, RecorridoRuta): arrastrar un asa no la rearma cada vez


def _recorrido(ctx, v):
    clave = (id(ctx.estado), repr([h["ref"] for h in v["ruta"]]))
    if clave not in _PERFILES:
        if len(_PERFILES) > 8:
            _PERFILES.clear()
        ruta = ruta_del_patron(ctx, v)
        _PERFILES[clave] = (ruta, _mp().RecorridoRuta(*sc.perfil_ruta(ruta)), ctx.estado)   # el estado evita reusar un id viejo
    return _PERFILES[clave][:2]


def _ruta(ctx, v):
    mp = _mp()
    if not v.get("ruta"):
        return []
    ruta, rec = _recorrido(ctx, v)
    puntos, arco = rec.puntos, rec.arco
    n = _n(v, "rn")
    inicio = min(1.0, max(0.0, evaluar_o_cero(ctx, v.get("inicio"), "escalar")))
    distancia = evaluar_o_cero(ctx, v.get("rd"))
    distribucion = v.get("distribucion", "extension")
    _largo, _cerrada, s0, paso = sc.recorrido_ruta(ruta, n, distancia, inicio=inicio, distribucion=distribucion)
    salida = [mp.AsaRuta("inicio", arco / rec.largo, puntos)]
    if n > 1:
        salida.append(mp.AsaRecorrido("rd", rec, s0, (n - 1) if distribucion == "espaciado" else 1.0))
    signo = -1.0 if paso < 0 else 1.0
    salida.append(mp.AsaCantidad("rn", lambda m: (rec.punto(s0 + paso * (m - 1)), rec.tangente(s0 + paso * (m - 1)) * signo),
                                 abs(paso) or 10.0))
    return salida


def _casillas(comando, ctx, v, centro):
    """La casilla de supresión sobre cada copia (las que existen y las ya suprimidas)."""
    from ...timeline.operaciones import ErrorOperacion
    from ...timeline.parametros import ErrorExpresion
    from .crear import suprimir_a_texto, texto_a_suprimir
    try:
        op = comando.construir(v, ctx)
        instancias = op.instancias(ctx.estado, Contexto(ctx.doc.parametros.valores()))
    except (ErrorComando, ErrorExpresion, ErrorOperacion, ent.ErrorReferencia, geo.ErrorGeometria):
        return None
    forma = op.p["forma_patron"]
    if len(instancias) > MAX_CASILLAS:                   # con miles de copias las casillas tapan todo: se suprime por número
        return None
    items = []
    for ident, t, estado in instancias:
        if t is not None:
            m = sc.a_matriz(t)
            items.append((ident, m[:3, :3] @ centro + m[:3, 3], estado))

    def alternar(ident):
        clave = list(ident) if isinstance(ident, tuple) else ident
        actuales = texto_a_suprimir(forma, v.get("suprimir"))
        actuales.remove(clave) if clave in actuales else actuales.append(clave)
        return {"suprimir": suprimir_a_texto(forma, actuales)}

    return _mp().CasillasCopias(items, alternar, originales={(0, 0) if forma == "rectangular" else 0})


def manipuladores(comando, ctx, v):
    forma = v.get("forma")
    centro = centro_del_objeto(ctx, v)
    salida = []
    try:
        if forma == "ruta":                                  # las asas siguen a la ruta, no al cuerpo
            salida = _ruta(ctx, v)
        elif centro is not None and forma == "rectangular":
            salida = _rectangular(ctx, v, centro)
        elif centro is not None and forma == "circular":
            salida = _circular(ctx, v, centro)
    except (ent.ErrorReferencia, geo.ErrorGeometria, ErrorComando, ValueError):
        salida = []
    if v.get("ver_casillas") and centro is not None:
        casillas = _casillas(comando, ctx, v, centro)
        if casillas is not None:
            salida.insert(0, casillas)
    return salida


def previa_vista(comando, ctx, v, op):
    """Patrón en puntos: la referencia (cruz verde), los destinos (cruces azules) y una línea de la referencia a cada
    destino: así se ve qué punto se lleva a dónde."""
    if op.p.get("forma_patron") != "puntos":
        return None
    puntos, ref = op.puntos_patron(ctx.estado, Contexto(ctx.doc.parametros.valores()))
    destinos = np.array(puntos, float)
    lineas = np.stack([np.tile(ref, (len(destinos), 1)), destinos], axis=1).reshape(-1, 3)
    return [("lineas", lineas, AZUL_DESTINO, 1.4), ("puntos", destinos, AZUL_DESTINO, 10),
            ("puntos", np.array([ref], float), VERDE_REFERENCIA, 13)]

