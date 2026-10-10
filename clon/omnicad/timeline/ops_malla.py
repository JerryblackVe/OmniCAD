# -*- coding: utf-8 -*-
"""
Operaciones del espacio MALLA de Fusion [Fusion-Mesh]: cuerpos de malla (`tipo="malla"`, la forma es un
`nucleo.malla.Malla`) que se insertan desde STL/OBJ/3MF/PLY, se preparan (reparar, grupos de caras),
se modifican (reducir, remallar, cortar, vaciar, combinar, suavizar…) y se convierten a B-rep.
La malla insertada viaja dentro de la receta (comprimida), así el proyecto es autónomo.
"""
import hashlib
import threading
import warnings

from ..nucleo import geometria as geo
from . import entidades as ent
from .operaciones import (ErrorOperacion, Operacion, ParametroMalFormado, _deps_objetivo, _resolver,
                          registrar_operacion)


def _ml():
    from ..nucleo import malla
    return malla


def _avisos_de_malla(registrados):
    """Textos de los AvisoMalla de `registrados` (warnings.catch_warnings(record=True)); los demás avisos (p. ej. de
    numpy) siguen su camino de siempre."""
    textos, otros = [], {}
    for a in registrados:
        if issubclass(a.category, _ml().AvisoMalla):
            textos.append(str(a.message))
        else:
            otros.setdefault((a.category, str(a.message), a.filename, a.lineno), a)     # una vez por lugar
    for a in otros.values():
        warnings.warn_explicit(a.message, a.category, a.filename, a.lineno)
    return textos


# Memoria de los pasos lentos (Reducir y Remallar: segundos con decenas de miles de triángulos), por contenido: el
# documento recalcula desde el paso tocado hasta el final (deshacer y rehacer, desde el primero), y la vista previa
# y Aceptar calculan lo mismo dos veces. Las mallas no se modifican en el lugar (Mover hace una copia), así que se
# devuelve el mismo objeto. Medido (botella de 74.252 triángulos): reducir a 18.562, 8,5 s; remallarla, 6,5 s.
_MEMORIA = {}                   # (función, opciones, huella de la entrada) → (malla resultado, textos de aviso)
_MEMORIA_MAX = 6
_CANDADO = threading.Lock()


def _huella(m):
    h = hashlib.blake2b(digest_size=16)
    for a in (m.vertices, m.caras, m.grupos):
        h.update(str(a.shape).encode())
        h.update(a.tobytes())
    return h.digest()


def _calcular(ctx, nombre, m, **opciones):
    """`malla.<nombre>(m, **opciones)` recordando los últimos _MEMORIA_MAX resultados; los avisos se repiten en
    cada uso (el paso los muestra aunque el resultado venga de la memoria). Los errores no se recuerdan."""
    clave = (nombre, tuple(sorted((k, repr(v)) for k, v in opciones.items())), _huella(m))
    with _CANDADO:
        guardado = _MEMORIA.pop(clave, None)
        if guardado is not None:
            _MEMORIA[clave] = guardado                          # el más reciente al final
    if guardado is None:
        with warnings.catch_warnings(record=True) as registrados:
            warnings.simplefilter("always")
            resultado = getattr(_ml(), nombre)(m, **opciones)
        guardado = (resultado, _avisos_de_malla(registrados))
        with _CANDADO:
            _MEMORIA[clave] = guardado
            while len(_MEMORIA) > _MEMORIA_MAX:
                del _MEMORIA[next(iter(_MEMORIA))]
    for texto in guardado[1]:
        ctx.aviso(texto)
    return guardado[0]


def _mallas(estado, ids):
    if not ids:
        raise ErrorOperacion("Elegí los cuerpos de malla.")
    salida = []
    for cid in ids:
        c = estado.cuerpo(cid)
        if getattr(c, "tipo", "solido") != "malla":
            raise ErrorOperacion(f"{c.nombre} no es un cuerpo de malla.")
        salida.append(c)
    return salida


class _OpMalla(Operacion):
    def dependencias(self):
        p = self.p
        return (_deps_objetivo(p.get("cuerpos")) | _deps_objetivo(p.get("objetivo")) |
                _deps_objetivo(p.get("herramientas")) | ent.dependencias_de(p.get("plano"))) - {self.id}


class OpInsertarMalla(_OpMalla):
    """INSERTAR › Insertar malla [MESH-INSERT-MESH]: el archivo se guarda en la receta."""
    TIPO, ETIQUETA, ICONO = "insertar_malla", "Insertar malla", "△"
    PARAMS = {"archivo": "", "datos": None}

    def ejecutar(self, estado, ctx):
        if not self.p["datos"]:
            raise ErrorOperacion("La inserción no tiene datos de malla.")
        if not isinstance(self.p["datos"], dict):
            raise ParametroMalFormado(self.p["datos"], 'se esperaba la malla guardada: un dict {"formato": '
                                                       '"omnicad.malla/1", …} (la arma insertar_malla al leer el archivo)')
        m = _ml().Malla.desde_dict(self.p["datos"])
        estado.nuevo_cuerpo(self.id, m, "malla", nombre=self.p["archivo"] or None)


class OpTeselar(_OpMalla):
    """MALLA › Malla de cuerpo B-Rep (teselar) [MESH-TESSELLATE]."""
    TIPO, ETIQUETA, ICONO = "teselar", "Teselar", "△"
    PARAMS = {"cuerpos": [], "refinamiento": "medio", "mantener": True}
    OPCIONES = {"refinamiento": ("bajo", "medio", "alto")}

    def ejecutar(self, estado, ctx):
        if not self.p["cuerpos"]:
            raise ErrorOperacion("Elegí los cuerpos a convertir en malla.")
        for cid in self.p["cuerpos"]:
            c = estado.cuerpo(cid)
            m = _ml().desde_brep(c.forma, refinamiento=self.p["refinamiento"])
            estado.nuevo_cuerpo(self.id, m, "malla", nombre=f"{c.nombre} (malla)", apariencia=c.apariencia)
            if not self.p["mantener"]:
                del estado.cuerpos[c.id]


class _OpMallaSimple(_OpMalla):
    """Base: aplica `transformar(malla, ctx)` a cada cuerpo de malla elegido; los AvisoMalla pasan al paso."""

    def transformar(self, m, ctx):
        raise NotImplementedError

    def ejecutar(self, estado, ctx):
        for c in _mallas(estado, self.p["cuerpos"]):
            with warnings.catch_warnings(record=True) as registrados:
                warnings.simplefilter("always")
                c.forma = self.transformar(c.forma, ctx)
            for texto in _avisos_de_malla(registrados):
                ctx.aviso(texto)


class OpRepararMalla(_OpMallaSimple):
    """PREPARAR › Reparar [MESH-REPAIR]."""
    TIPO, ETIQUETA, ICONO = "reparar_malla", "Reparar", "✚"
    PARAMS = {"cuerpos": [], "tipo": "cerrar_agujeros"}
    OPCIONES = {"tipo": ("cerrar_agujeros", "unir_vertices", "coser_y_quitar", "reconstruir")}

    def transformar(self, m, ctx):
        return _ml().reparar(m, tipo=self.p["tipo"])


class OpGruposCaras(_OpMallaSimple):
    """PREPARAR › Generar grupos de caras [MESH-GENERATE-FACE-GROUPS]."""
    TIPO, ETIQUETA, ICONO = "grupos_caras", "Grupos de caras", "◩"
    PARAMS = {"cuerpos": [], "angulo": "30 deg"}
    EXPRESIONES = ("angulo",)

    def transformar(self, m, ctx):
        return _ml().generar_grupos(m, angulo=ctx.evaluar(self.p["angulo"], "angulo"))


class OpReducirMalla(_OpMallaSimple):
    """MODIFICAR › Reducir [MESH-REDUCE]."""
    TIPO, ETIQUETA, ICONO = "reducir_malla", "Reducir", "▽"
    PARAMS = {"cuerpos": [], "tipo": "proporcion", "proporcion": "0.5", "caras": 1000, "tolerancia": "0.1 mm"}
    EXPRESIONES = ("proporcion", "tolerancia")
    OPCIONES = {"tipo": ("proporcion", "caras", "tolerancia")}

    def transformar(self, m, ctx):
        t = self.p["tipo"]
        if t == "caras":
            return _calcular(ctx, "reducir", m, objetivo_caras=self.entero("caras", minimo=None))
        if t == "tolerancia":
            return _calcular(ctx, "reducir", m, tolerancia=ctx.evaluar(self.p["tolerancia"]))
        return _calcular(ctx, "reducir", m, proporcion=ctx.evaluar(self.p["proporcion"], "escalar"))


class OpRemallar(_OpMallaSimple):
    """MODIFICAR › Remallar [MESH-REMESH]."""
    TIPO, ETIQUETA, ICONO = "remallar", "Remallar", "▦"
    PARAMS = {"cuerpos": [], "densidad": "1", "preservar_bordes": True, "preservar_aristas_vivas": True}
    EXPRESIONES = ("densidad",)

    def transformar(self, m, ctx):
        return _calcular(ctx, "remallar", m, densidad=ctx.evaluar(self.p["densidad"], "escalar"),
                         preservar_bordes=self.p["preservar_bordes"],
                         preservar_aristas_vivas=self.p["preservar_aristas_vivas"])


class OpCortarPlanoMalla(_OpMalla):
    """MODIFICAR › Cortar con plano [MESH-PLANE-CUT]: recortar (con o sin relleno) o partir en dos."""
    TIPO, ETIQUETA, ICONO = "cortar_plano", "Corte de plano", "⊖"
    PARAMS = {"cuerpos": [], "plano": None, "tipo": "recortar", "rellenar": True, "invertir": False}
    OPCIONES = {"tipo": ("recortar", "partir", "partir_caras")}

    def ejecutar(self, estado, ctx):
        if not self.p["plano"]:
            raise ErrorOperacion("Elegí el plano de corte.")
        plano = ent.como_plano(_resolver(self.p["plano"], estado))
        for c in _mallas(estado, self.p["cuerpos"]):
            r = _ml().cortar_plano(c.forma, plano.origen, plano.normal, tipo=self.p["tipo"],
                                   rellenar=self.p["rellenar"], invertir=self.p["invertir"])
            partes = list(r) if isinstance(r, (list, tuple)) else [r]
            c.forma = partes[0]
            for parte in partes[1:]:
                estado.nuevo_cuerpo(self.id, parte, "malla", apariencia=c.apariencia)


class OpVaciadoMalla(_OpMallaSimple):
    """MODIFICAR › Vaciado de malla [MESH-SHELL]."""
    TIPO, ETIQUETA, ICONO = "vaciado_malla", "Vaciado de malla", "▢"
    PARAMS = {"cuerpos": [], "espesor": "2 mm"}
    EXPRESIONES = ("espesor",)

    def transformar(self, m, ctx):
        return _ml().vaciar(m, ctx.evaluar(self.p["espesor"]))


class OpCombinarMallas(_OpMalla):
    """MODIFICAR › Combinar mallas [MESH-COMBINE]: unir, cortar, intersecar o fusionar."""
    TIPO, ETIQUETA, ICONO = "combinar_mallas", "Combinar mallas", "⊕"
    PARAMS = {"objetivo": "", "herramientas": [], "operacion": "unir", "mantener": False}
    OPCIONES = {"operacion": ("unir", "cortar", "intersecar", "fusionar")}

    def ejecutar(self, estado, ctx):
        (obj,) = _mallas(estado, [self.p["objetivo"]] if self.p["objetivo"] else [])
        herramientas = _mallas(estado, self.p["herramientas"])
        obj.forma = _ml().combinar([obj.forma] + [h.forma for h in herramientas], operacion=self.p["operacion"])
        if not self.p["mantener"]:
            for h in herramientas:
                del estado.cuerpos[h.id]


class OpSuavizarMalla(_OpMallaSimple):
    """MODIFICAR › Suavizar [MESH-SMOOTH]."""
    TIPO, ETIQUETA, ICONO = "suavizar_malla", "Suavizar", "∿"
    PARAMS = {"cuerpos": [], "intensidad": "0.5", "iteraciones": 10}
    EXPRESIONES = ("intensidad",)

    def transformar(self, m, ctx):
        return _ml().suavizar(m, intensidad=ctx.evaluar(self.p["intensidad"], "escalar"),
                              iteraciones=self.entero("iteraciones", minimo=None))


class OpInvertirNormalMalla(_OpMallaSimple):
    """MODIFICAR › Invertir normal [MESH-REVERSE-NORMAL]."""
    TIPO, ETIQUETA, ICONO = "invertir_normal_malla", "Invertir normal de malla", "⇅"
    PARAMS = {"cuerpos": []}

    def transformar(self, m, ctx):
        return _ml().invertir_normales(m)


class OpSepararMalla(_OpMalla):
    """MODIFICAR › Separar [MESH-SEPARATE]: cada cáscara (o grupo de caras) pasa a ser un cuerpo."""
    TIPO, ETIQUETA, ICONO = "separar_malla", "Separar", "⊞"
    PARAMS = {"cuerpos": [], "tipo": "cascaras"}
    OPCIONES = {"tipo": ("cascaras", "grupos")}

    def ejecutar(self, estado, ctx):
        for c in _mallas(estado, self.p["cuerpos"]):
            partes = _ml().separar(c.forma, tipo=self.p["tipo"])
            if len(partes) < 2:
                ctx.aviso(f"{c.nombre} tiene una sola parte.")
            c.forma = partes[0]
            for parte in partes[1:]:
                estado.nuevo_cuerpo(self.id, parte, "malla", apariencia=c.apariencia)


class OpEscalarMalla(_OpMallaSimple):
    """MODIFICAR › Escalar malla [MESH-SCALE-MESH]."""
    TIPO, ETIQUETA, ICONO = "escalar_malla", "Escalar malla", "⤢"
    PARAMS = {"cuerpos": [], "fx": "1", "fy": "1", "fz": "1"}
    EXPRESIONES = ("fx", "fy", "fz")

    def transformar(self, m, ctx):
        E = lambda k: ctx.evaluar(self.p[k], "escalar")  # noqa: E731
        return _ml().escalar(m, E("fx"), E("fy"), E("fz"))


class OpConvertirMalla(_OpMalla):
    """MODIFICAR › Convertir malla [MESH-CONVERT-TO-SOLID]: facetado o prismático; sólido si es cerrada."""
    TIPO, ETIQUETA, ICONO = "convertir_malla", "Convertir malla", "■"
    PARAMS = {"cuerpos": [], "metodo": "facetado", "mantener": False}
    OPCIONES = {"metodo": ("facetado", "prismatico")}

    def ejecutar(self, estado, ctx):
        for c in _mallas(estado, self.p["cuerpos"]):
            forma = _ml().a_brep(c.forma, metodo=self.p["metodo"])
            tipo = "solido" if geo.solidos(forma) else "superficie"
            estado.nuevo_cuerpo(self.id, forma, tipo, nombre=f"{c.nombre} (B-rep)", apariencia=c.apariencia)
            if not self.p["mantener"]:
                del estado.cuerpos[c.id]


registrar_operacion(OpInsertarMalla, OpTeselar, OpRepararMalla, OpGruposCaras, OpReducirMalla, OpRemallar,
                    OpCortarPlanoMalla, OpVaciadoMalla, OpCombinarMallas, OpSuavizarMalla, OpInvertirNormalMalla,
                    OpSepararMalla, OpEscalarMalla, OpConvertirMalla)
