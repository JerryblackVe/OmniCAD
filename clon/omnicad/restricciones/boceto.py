# -*- coding: utf-8 -*-
"""
Modelo de datos del boceto 2D paramétrico.

Equivalencias con Fusion 360 (informe_analisis.md §3.2 y ayuda "Design: Sketch", SKT-*):
  - SketchPoint / SketchLine / SketchCircle / SketchArc / SketchEllipse / SketchEllipticalArc /
    SketchFittedSpline / SketchControlPointSpline / SketchConicCurve / SketchText  →  Punto, Linea,
    Circulo, Arco, Elipse, ArcoElipse, Spline (modo "ajuste" o "control"), Conica y Texto.
  - El rectángulo y la ranura NO son entidades: igual que en Fusion se arman con líneas y arcos que
    comparten vértices, más sus restricciones.
  - Tipo de línea (Paleta de boceto): normal, construcción (no forma perfiles) o eje / línea central
    (sí forma perfiles; se dibuja con trazo y punto).
  - Geometría proyectada (violeta en Fusion): curvas con `proyectada=True`, fijas para el solver.
  - GeometricConstraints → `TIPOS_RESTRICCION`. "Fijar" en Fusion es la propiedad `isFixed`; acá es
    la restricción 'fijo' (mismo efecto). 'desfase' y 'patron' son las restricciones internas que
    Fusion muestra como glifo de desfase / patrón.
  - SketchDimensions → `TIPOS_COTA`; cada cota guarda una EXPRESIÓN (puede usar parámetros).
  - Comandos de MODIFICAR (empalme, chaflán, recortar, alargar, partir, desfase, escala, mover/copiar,
    curva de fusión) y de CREAR (simetría, patrones, desglosar texto) son métodos del Boceto.

Coordenadas en milímetros, en el sistema (u, v) del plano del boceto.
"""
# ruff: noqa: F401 -- fachada compatible con los imports de boceto.
import bisect
import math
import copy
import re
from functools import lru_cache

import numpy as np

from .boceto_consultas import _Consultas
from .boceto_cortes import _Cortes
from .boceto_crear import (
    agregar_arco_tangente, agregar_circulo_puntos, agregar_estrella, agregar_linea_medio, agregar_poligono,
    agregar_rectangulo_3p, agregar_rectangulo_centro, _agrupar_estrella, aviso_radio_empalme, cambiar_radio,
    centro_arco_tangente, centro_poligono_arista, _Crear, proporcion_estrella, puntos_espiral, redondear_estrella,
    redondeos_estrella, validar_lados_poligono, validar_puntas_estrella, vertices_estrella, vertices_poligono,
    VUELTAS_MAX_ESPIRAL,
)
from .boceto_desfase import _Desfase
from .boceto_entidades import (
    ALTURA_MAXIMA_TEXTO, _antihorario_por, Arco, ArcoElipse, aviso_tangencias_fuera, _cambia_orientacion,
    CAMBIABLES, CIRCULARES, Circulo, circunferencia_3_puntos, CON_CENTRO, _CON_RADIO, Conica, Cota,
    _COTAS_ORIENTADAS, COTAS_POSITIVAS, _Curva, _CURVAS, distancia_con_circulo, distancia_punto_recta, _DOS_PI,
    Elipse, ELIPTICAS, ErrorBoceto, _es_numero, _exigir_radio_positivo, expresion_sin_signo, GEOMETRICAS,
    _invertir_curvatura, LARGO_EJE_VACIO, LIBRES, Linea, MAX_CARACTERES_TEXTO, MAX_COPIAS_PATRON,
    MAX_PUNTOS_PATRON, MEDIDA_MAXIMA, MEDIDA_MINIMA, MITAD_EJE_MINIMA, _numero, ORDEN_RESTRICCION, _ORIENTADAS,
    Punto, Restriccion, signos_cuadrante, Spline, Texto, TIPOS_COTA, TIPOS_RESTRICCION, _validar_cuadrante,
    validar_texto_boceto, validar_valor_cota,
)
from .boceto_esquinas import _Esquinas
from .boceto_geometria import (
    aviso_quitadas, _barrido, _base_derivada, caja_primitiva, _cantidad_muestras, _cruces_circulos,
    _cruces_recta_circulo, _ctrl_derivada, _de_boor, distancia_primitiva, dominio, evaluar_bspline,
    evaluar_primitiva, firma_primitiva, _funciones_base, _insertar_nudo, interpolar_spline, intersecciones,
    mas_cercano, _muestras, nudos_uniformes, parametro_elipse, parametros_cuerda, peine_curvatura,
    puntos_primitiva, recta_interseccion, _resolver_lineal, _rot, _tramo, tramo_bspline,
)
from .boceto_patrones import _Patrones
from .boceto_primitivas import (
    _CLAVES_TIPOGRAFIA, _contornos_camino, _contornos_texto, _derivadas_manijas, fraccion_en_camino, _kwargs_texto,
    lado_natural, _mapa_texto, _medidas_marco, _paradas_camino, paradas_cursor, polilinea_camino,
    primitivas_entidad, _TIPOGRAFIA_BASE, _tipografia_camino,
)
from .boceto_proyeccion import _Proyeccion
from .boceto_splines import _Splines
from .boceto_texto import (
    expresiones_de_texto, _FX, _partes_fx, _sumandos, sustituir_expresiones, _Texto, _validar_opciones_texto,
)
from .boceto_transformar import _Transformar


# ---------------------------------------------------------------- boceto
class Boceto(_Texto, _Crear, _Proyeccion, _Consultas, _Cortes, _Esquinas, _Desfase, _Transformar,
             _Patrones, _Splines):
    ORIGEN = 0
    EJE_X = -1
    EJE_Y = -2

    def __init__(self):
        self.puntos = {}
        self.curvas = {}
        self.objetos = {}              # jerarquía vectorial; curvas originales + matrices, sin duplicar geometría
        self.props_curvas = {}         # H-69: nombre, visible, bloqueado o perfiles de una curva (solo lo cambiado)
        self.restricciones = {}
        self.cotas = {}
        self.proyecciones = []
        self.patrones = []             # patrones de boceto editables (ver `_patron`)
        self.ultimo_patron = None
        self.geo3d = {}                # geometría fuera del plano (Boceto 3D de Fusion): ver restricciones.boceto3d
        self._siguiente = 1

    # ------------------------------------------------------------ ids
    def _nuevo_id(self):
        i = self._siguiente
        self._siguiente += 1
        return i

    def entidad(self, id):
        if id in self.puntos:
            return self.puntos[id]
        if id in self.curvas:
            return self.curvas[id]
        raise ErrorBoceto(f"No existe la entidad {id}.")

    def copia(self):
        """Copia independiente. Más rápida que deepcopy: los puntos y las curvas solo tienen números, textos y
        listas de números (lo que se copia aparte)."""
        b = copy.copy(self)
        b.puntos = {k: copy.copy(p) for k, p in self.puntos.items()}
        b.curvas = {}
        for k, c in self.curvas.items():
            n = copy.copy(c)
            for a, v in vars(c).items():
                if isinstance(v, (list, dict, set)):
                    setattr(n, a, copy.deepcopy(v))
            b.curvas[k] = n
        b.restricciones = copy.deepcopy(self.restricciones)
        b.cotas = copy.deepcopy(self.cotas)
        for a, v in vars(self).items():
            if a not in ("puntos", "curvas", "restricciones", "cotas") and isinstance(v, (list, dict, set)):
                setattr(b, a, copy.deepcopy(v))
        return b

    def reproyectar(self, registro, primitivas, puntos) -> bool:
        """Actualiza Proyectar / Intersecar de Fusion conservando ids; si cambia la topología, no toca nada."""
        derivadas = self.derivar_proyeccion(registro, primitivas)
        huecos = set(registro.get("huecos", ()))
        for unir in (True, False):         # False: el registro es anterior a unir arcos, elipses y splines
            nuevo = Boceto()
            ids = nuevo.agregar_proyeccion(derivadas, puntos, registro["construccion"], unir=unir)
            ids = [i for k, i in enumerate(ids) if k not in huecos]
            if len(ids) == len(registro["ids"]):
                break
        else:
            return False
        coordenadas, curvas = {}, []
        for anterior_id, nuevo_id in zip(registro["ids"], ids, strict=True):
            anterior = self.curvas.get(anterior_id, self.puntos.get(anterior_id))
            actual = nuevo.entidad(nuevo_id)
            if anterior is None or type(anterior) is not type(actual):
                return False
            if isinstance(anterior, Punto):
                anteriores, actuales = [anterior.id], [actual.id]
            else:
                anteriores, actuales = anterior.puntos(), actual.puntos()
                curvas.append((anterior, actual))
            if len(anteriores) != len(actuales) or any(p not in self.puntos for p in anteriores):
                return False
            for pid, qid in zip(anteriores, actuales, strict=True):
                xy = nuevo.coords(qid)
                if pid in coordenadas and math.dist(coordenadas[pid], xy) > 1e-6:
                    return False
                coordenadas[pid] = xy
        for pid, xy in coordenadas.items():
            self.puntos[pid].x, self.puntos[pid].y = xy
        for anterior, actual in curvas:
            for atributo in type(anterior).DATOS:
                setattr(anterior, atributo, copy.deepcopy(getattr(actual, atributo)))
        return True

    # ------------------------------------------------------------ borrado
    def eliminar(self, id):
        """Borra una entidad, restricción o cota, y en cascada lo que dependa de ella."""
        if id <= 0:
            raise ErrorBoceto("El origen y los ejes no se pueden borrar.")
        self.exigir_desbloqueadas([id], "borrarla")
        if id in self.restricciones:
            del self.restricciones[id]
            return
        if id in self.cotas:
            borrada = self.cotas.pop(id)
            for k in self.cotas.values():      # chaflán ligado (BOC-25): la que la citaba hereda su expresión
                if borrada.nombre and k.expresion == borrada.nombre:
                    k.expresion = borrada.expresion
            return
        if id in self.curvas:
            curva = self.curvas.pop(id)
            pts = curva.puntos()
            if isinstance(curva, Linea):             # borrar la línea de una manija la desactiva
                for s in self.curvas.values():
                    if isinstance(s, Spline):
                        s.manijas = [m for m in s.manijas if {m[0], m[1]} != {curva.p1, curva.p2}]
            for lid in self._lineas_auxiliares(curva):   # las manijas y el marco se van con su curva
                pts += self.curvas.pop(lid).puntos()
            for p in pts:
                if not self._punto_en_uso(p):
                    self.puntos.pop(p, None)
        elif id in self.puntos:
            for cid in [c.id for c in self.curvas.values() if id in c.puntos()
                        and not (isinstance(c, Spline) and id in [m[1] for m in c.manijas])]:
                self.curvas.pop(cid)
            del self.puntos[id]
        else:
            raise ErrorBoceto(f"No existe el elemento {id}.")
        self._quitar_huerfanas()

    def _lineas_auxiliares(self, c):
        """Ids de las líneas de las manijas de una spline o del marco de un texto (las que unen sus puntos)."""
        if isinstance(c, Spline):
            pares = [{a, b} for a, b, _k in c.manijas]
        elif isinstance(c, Texto) and c.marco:
            esquinas = set(c.puntos())
            lineas = [l for l in self.curvas.values() if isinstance(l, Linea) and l.construccion]
            vecinos = [{p for l in lineas if esquina in l.puntos() for p in l.puntos()} for esquina in c.marco]
            # El texto guarda tres esquinas; la cuarta une los dos lados opuestos al ancla.
            esquinas |= vecinos[0] & vecinos[1]
            pares = [{l.p1, l.p2} for l in lineas if {l.p1, l.p2} <= esquinas]
        else:
            return []
        return [l.id for l in self.curvas.values() if isinstance(l, Linea) and {l.p1, l.p2} in pares]

    def _quitar_huerfanas(self):
        for cid in [k for k in self.props_curvas if k not in self.curvas]:
            del self.props_curvas[cid]
        if self.objetos:
            from . import objetos
            cambio = True
            while cambio:
                cambio = False
                vivos_obj = set(self.curvas) | set(self.objetos)
                for oid, o in list(self.objetos.items()):
                    o["entidades"] = [i for i in o["entidades"] if i in vivos_obj]
                    if not o["entidades"]:
                        del self.objetos[oid]
                        cambio = True
            objetos.invalidar(self)
        vivos = set(self.puntos) | set(self.curvas)
        for c in self.curvas.values():
            if isinstance(c, Texto) and c.camino is not None and c.camino not in self.curvas:
                c.camino = None                            # se borró su curva: vuelve a ser texto recto
            if isinstance(c, Spline) and c.manijas:        # se borró la punta de una manija
                c.manijas = [m for m in c.manijas if m[0] in self.puntos and m[1] in self.puntos]
        for tabla in (self.restricciones, self.cotas):
            for k in [k for k, v in tabla.items() if not set(v.entidades) <= vivos]:
                del tabla[k]

    def _depurar(self, puntos_viejos=()):
        """Tras modificar geometría: borra los puntos viejos que quedaron sueltos y las restricciones o
        cotas que ya no aplican al nuevo tipo de las entidades."""
        for p in puntos_viejos:
            if p in self.puntos and not self._punto_en_uso(p) and not self._punto_referenciado(p):
                del self.puntos[p]
        self._quitar_huerfanas()
        for rid in list(self.restricciones):
            r = self.restricciones[rid]
            try:
                self._validar_restriccion(r.tipo, r.entidades)
            except ErrorBoceto:
                del self.restricciones[rid]
        for kid in list(self.cotas):
            k = self.cotas[kid]
            try:
                self._validar_cota(k.tipo, k.entidades)
            except ErrorBoceto:
                del self.cotas[kid]

    def _punto_en_uso(self, pid):
        return any(pid in c.puntos() for c in self.curvas.values())

    def _punto_referenciado(self, pid):
        return any(pid in r.entidades for r in self.restricciones.values()) or \
            any(pid in k.entidades for k in self.cotas.values())

    # ------------------------------------------------------------ serialización
    def a_dict(self):
        d = {"siguiente_id": self._siguiente,
             "puntos": [p.a_dict() for p in self.puntos.values()],
             "curvas": [c.a_dict() for c in self.curvas.values()],
             "restricciones": [r.a_dict() for r in self.restricciones.values()],
             "cotas": [c.a_dict() for c in self.cotas.values()]}
        if self.proyecciones:
            d["proyecciones"] = copy.deepcopy(self.proyecciones)
        if self.patrones:
            d["patrones"] = copy.deepcopy(self.patrones)
        if self.objetos:
            d["objetos"] = copy.deepcopy(list(self.objetos.values()))
        if self.props_curvas:
            d["props_curvas"] = [{"id": k, **v} for k, v in self.props_curvas.items()]
        if any(self.geo3d.values()):
            from . import boceto3d
            d["geo3d"] = boceto3d.a_dict(self.geo3d)
        return d

    @classmethod
    def desde_dict(cls, d):
        b = cls()
        b._siguiente = d.get("siguiente_id", 1)
        b.proyecciones = copy.deepcopy(d.get("proyecciones", []))
        for n, r in enumerate(b.proyecciones, 1):          # los proyectos viejos no numeraban sus proyecciones
            r.setdefault("id", n)
        b.patrones = copy.deepcopy(d.get("patrones", []))
        b.objetos = {o["id"]: copy.deepcopy(o) for o in d.get("objetos", [])}
        if len(b.objetos) != len(d.get("objetos", [])):
            raise ErrorBoceto("Identificadores de objetos repetidos.")
        b.props_curvas = {p["id"]: {k: v for k, v in p.items() if k != "id"} for p in d.get("props_curvas", [])}
        for p in d.get("puntos", []):
            b.puntos[p["id"]] = Punto(p["id"], p["x"], p["y"], p.get("proyectado", False))
        for c in d.get("curvas", []):
            datos = {k: v for k, v in c.items() if k != "tipo"}
            b.curvas[c["id"]] = _CURVAS[c["tipo"]](**datos)
        for r in d.get("restricciones", []):
            b.restricciones[r["id"]] = Restriccion(r["id"], r["tipo"], r["entidades"], r.get("datos"))
        for c in d.get("cotas", []):
            b.cotas[c["id"]] = Cota(c["id"], c["tipo"], c["entidades"], c["expresion"], c.get("datos"), c.get("nombre", ""),
                                   c.get("referencia", False))
        if d.get("geo3d"):
            from . import boceto3d
            b.geo3d = boceto3d.desde_dict(d["geo3d"])
        if b.objetos:
            from . import objetos
            objetos.validar(b)
        todos = list(b.puntos) + list(b.curvas) + list(b.restricciones) + list(b.cotas) + list(b.objetos)
        todos += [i for tabla in b.geo3d.values() for i in tabla]
        b._siguiente = max([b._siguiente] + [i + 1 for i in todos])
        b._depurar()          # un .omnicad es un archivo de otro: lo que cita algo inexistente o ya no aplica, se descarta
        return b
