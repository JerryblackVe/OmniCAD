# -*- coding: utf-8 -*-
"""
Operaciones de SÓLIDO › MODIFICAR que se guardan en el timeline (además de Combinar, que vive en
`operaciones.py`): Mover/copiar, Quitar y las que usan el núcleo de `solidos_modificar`.
"""
import math

import numpy as np

from ..nucleo import geometria as geo
from . import entidades as ent
from .operaciones import (ANGULO, ErrorOperacion, Operacion, _deps_objetivo, _resolver, _resolver_todas,
                          atributos_copia, registrar_operacion)


def _sm():
    from ..nucleo import solidos_modificar
    return solidos_modificar


def _por_cuerpo(refs, estado, que="aristas"):
    """{id de cuerpo: [subformas]} a partir de referencias a caras o aristas (pueden ser de varios cuerpos)."""
    grupos = {}
    for e in _resolver_todas(refs, estado, ("arista",) if que == "aristas" else ("cara",)):
        if e.cuerpo is None:
            raise ErrorOperacion(f"Solo se pueden usar {que} de cuerpos.")
        grupos.setdefault(e.cuerpo, []).append(e.forma)
    if not grupos:
        raise ErrorOperacion(f"Elegí las {que}.")
    return grupos


def _deps_refs(*listas):
    return ent.dependencias_de(*listas)


def _matriz_traslacion(v):
    m = np.identity(4)
    m[:3, 3] = v
    return m


def _matriz_rotacion(punto, eje, angulo_grados):
    eje = np.asarray(eje, float)
    eje = eje / (np.linalg.norm(eje) or 1.0)
    a = math.radians(angulo_grados)
    x, y, z = eje
    c, s = math.cos(a), math.sin(a)
    k = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    r = np.identity(3) + s * k + (1 - c) * (k @ k)
    m = np.identity(4)
    m[:3, :3] = r
    m[:3, 3] = np.asarray(punto, float) - r @ np.asarray(punto, float)
    return m


TIPOS_MOVIMIENTO = {"libre": "Movimiento libre", "traslacion": "Trasladar", "rotacion": "Girar",
                    "punto_a_punto": "Punto a punto", "punto_a_posicion": "Punto a posición"}


class OpMover(Operacion):
    """Mover/copiar de Fusion [SLD-USE-MOVE-COPY] para cuerpos: movimiento libre (X/Y/Z y giros alrededor
    del pivote), trasladar (ejes del diseño o una dirección elegida), girar alrededor de un eje, punto a
    punto y punto a posición. «Crear copia» deja el original y agrega cuerpos nuevos."""
    TIPO, ETIQUETA, ICONO = "mover", "Mover", "✥"
    PARAMS = {"cuerpos": [], "tipo": "libre", "dx": "0 mm", "dy": "0 mm", "dz": "0 mm", "rx": "0 deg",
              "ry": "0 deg", "rz": "0 deg", "pivote": None, "direccion": None, "distancia": "10 mm", "eje": None,
              "angulo": "90 deg", "origen": None, "destino": None, "x": "0 mm", "y": "0 mm", "z": "0 mm",
              "copiar": False}
    EXPRESIONES = ("dx", "dy", "dz", "rx", "ry", "rz", "distancia", "angulo", "x", "y", "z")
    OPCIONES = {"tipo": TIPOS_MOVIMIENTO}

    def dependencias(self):
        p = self.p
        return (_deps_objetivo(p["cuerpos"]) | ent.dependencias_de(p.get("pivote"), p.get("direccion"),
                                                                   p.get("eje"), p.get("origen"), p.get("destino"))
                ) - {self.id}

    def matriz(self, estado, ctx, formas):
        p, t = self.p, self.p["tipo"]
        L = lambda k: ctx.evaluar(p[k])  # noqa: E731
        A = lambda k: ctx.evaluar(p[k], ANGULO)  # noqa: E731
        if t == "libre":
            if p.get("pivote"):
                piv = ent.como_punto(_resolver(p["pivote"], estado))
            else:                                   # pivote por defecto: centro de la selección
                cajas = [geo.caja_envolvente(f) for f in formas]
                piv = np.mean([(np.array(a) + np.array(b)) / 2 for a, b in cajas if a], axis=0)
            m = np.identity(4)
            for eje, k in ((0, "rx"), (1, "ry"), (2, "rz")):
                ang = A(k)
                if abs(ang) > 1e-12:
                    m = _matriz_rotacion(piv, np.identity(3)[eje], ang) @ m
            return _matriz_traslacion((L("dx"), L("dy"), L("dz"))) @ m
        if t == "traslacion":
            if p.get("direccion"):
                return _matriz_traslacion(ent.direccion(_resolver(p["direccion"], estado)) * L("distancia"))
            return _matriz_traslacion((L("dx"), L("dy"), L("dz")))
        if t == "rotacion":
            if not p.get("eje"):
                raise ErrorOperacion("Elegí el eje de giro.")
            punto, eje = ent.como_eje(_resolver(p["eje"], estado))
            return _matriz_rotacion(punto, eje, A("angulo"))
        if t in ("punto_a_punto", "punto_a_posicion"):
            if not p.get("origen"):
                raise ErrorOperacion("Elegí el punto de origen.")
            a = ent.como_punto(_resolver(p["origen"], estado))
            if t == "punto_a_posicion":
                return _matriz_traslacion(np.array([L("x"), L("y"), L("z")]) - a)
            if not p.get("destino"):
                raise ErrorOperacion("Elegí el punto de destino.")
            return _matriz_traslacion(ent.como_punto(_resolver(p["destino"], estado)) - a)
        raise ErrorOperacion(f"Tipo de movimiento desconocido: {t}")

    def ejecutar(self, estado, ctx):
        if not self.p["cuerpos"]:
            raise ErrorOperacion("Elegí los cuerpos a mover.")
        cuerpos = [estado.cuerpo(c) for c in self.p["cuerpos"]]
        m = self.matriz(estado, ctx, [c.forma for c in cuerpos])
        for c in cuerpos:
            if getattr(c, "tipo", "solido") == "malla":
                nueva = c.forma.copia()
                nueva.vertices = (np.c_[nueva.vertices, np.ones(len(nueva.vertices))] @ m.T)[:, :3]
            else:
                nueva = geo.transformar(c.forma, m)
            if self.p.get("copiar"):
                estado.nuevo_cuerpo(self.id, nueva, c.tipo, nombre=f"{c.nombre} (copia)",
                                    **atributos_copia(c))
            else:
                c.forma = nueva


class OpQuitar(Operacion):
    """Quitar de Fusion [SLD-REMOVE]: saca cuerpos del diseño pero deja el paso en el timeline
    (suprimiéndolo, los cuerpos vuelven)."""
    TIPO, ETIQUETA, ICONO = "quitar", "Quitar", "✖"
    PARAMS = {"cuerpos": []}

    def dependencias(self):
        return _deps_objetivo(self.p["cuerpos"]) - {self.id}

    def ejecutar(self, estado, ctx):
        if not self.p["cuerpos"]:
            raise ErrorOperacion("Elegí los cuerpos a quitar.")
        for cid in self.p["cuerpos"]:
            del estado.cuerpos[estado.cuerpo(cid).id]


class OpEmpalme(Operacion):
    """Empalme de Fusion [SLD-FILLET-SOLID]: tipo Empalme (radio constante, de cuerda o variable entre
    inicio y fin) o Empalme de reglas (todas las aristas de unas caras o las que están entre dos grupos de
    caras, con redondeos, empalmes o ambos). La cadena tangente suma las aristas tangentes."""
    TIPO, ETIQUETA, ICONO = "empalme", "Empalme", "◜"
    PARAMS = {"tipo": "empalme", "aristas": [], "tipo_radio": "constante", "radio": "1 mm", "radio_fin": "2 mm",
              "cuerda": "1 mm", "cadena_tangente": True, "caras_a": [], "caras_b": [], "regla": "todas",
              "redondeos": "ambos"}
    EXPRESIONES = ("radio", "radio_fin", "cuerda")
    OPCIONES = {"tipo": ("empalme", "reglas"), "tipo_radio": ("constante", "cuerda", "variable"),
                "regla": ("todas", "entre"), "redondeos": ("ambos", "redondeos", "empalmes")}

    def dependencias(self):
        return _deps_refs(self.p["aristas"], self.p["caras_a"], self.p["caras_b"]) - {self.id}

    def ejecutar(self, estado, ctx):
        p, sm = self.p, _sm()
        r = ctx.evaluar(p["radio"])
        if p["tipo"] == "reglas":
            otras = _por_cuerpo(p["caras_b"], estado, "caras") if p["regla"] == "entre" else {}
            for cid, caras in _por_cuerpo(p["caras_a"], estado, "caras").items():
                c = estado.cuerpo(cid)
                c.forma = sm.empalme_reglas(c.forma, caras, otras.get(cid) if p["regla"] == "entre" else None,
                                            radio=r, tipo=p["regla"], redondeos=p["redondeos"])
            return
        grupo = {"tipo": p["tipo_radio"], "radio": r, "cuerda": ctx.evaluar(p["cuerda"]),
                 "radios": [(0.0, r), (1.0, ctx.evaluar(p["radio_fin"]))]}
        for cid, aristas in _por_cuerpo(p["aristas"], estado).items():
            c = estado.cuerpo(cid)
            c.forma = sm.empalme(c.forma, [dict(grupo, aristas=aristas)], cadena_tangente=p["cadena_tangente"])


class OpChaflan(Operacion):
    """Chaflán de Fusion [SLD-CHAMFER-SOLID]: distancia igual, dos distancias o distancia y ángulo, con
    «Voltear» para pasar la primera distancia a la otra cara."""
    TIPO, ETIQUETA, ICONO = "chaflan", "Chaflán", "◸"
    PARAMS = {"aristas": [], "tipo": "distancia_igual", "distancia": "1 mm", "distancia2": "1 mm",
              "angulo": "45 deg", "voltear": False, "cadena_tangente": True}
    EXPRESIONES = ("distancia", "distancia2", "angulo")
    OPCIONES = {"tipo": ("distancia_igual", "dos_distancias", "distancia_angulo")}

    def dependencias(self):
        return _deps_refs(self.p["aristas"]) - {self.id}

    def ejecutar(self, estado, ctx):
        p, sm = self.p, _sm()
        grupo = {"tipo": p["tipo"], "distancia": ctx.evaluar(p["distancia"]),
                 "distancia2": ctx.evaluar(p["distancia2"]), "angulo": ctx.evaluar(p["angulo"], ANGULO),
                 "voltear": p["voltear"]}
        for cid, aristas in _por_cuerpo(p["aristas"], estado).items():
            c = estado.cuerpo(cid)
            c.forma = sm.chaflan(c.forma, [dict(grupo, aristas=aristas)], cadena_tangente=p["cadena_tangente"])


class OpVaciado(Operacion):
    """Vaciado de Fusion [GUID-83A14252]: caras a quitar (o un cuerpo entero: queda hueco), espesor
    interior/exterior, dirección y cadena tangente."""
    TIPO, ETIQUETA, ICONO = "vaciado", "Vaciado", "▢"
    PARAMS = {"caras": [], "cuerpos": [], "espesor_interior": "1 mm", "espesor_exterior": "1 mm",
              "direccion": "interior", "tangente": True, "tipo": "afilado"}
    EXPRESIONES = ("espesor_interior", "espesor_exterior")
    OPCIONES = {"direccion": ("interior", "exterior", "ambos"), "tipo": ("afilado", "redondeado")}

    def dependencias(self):
        return (_deps_refs(self.p["caras"]) | _deps_objetivo(self.p["cuerpos"])) - {self.id}

    def ejecutar(self, estado, ctx):
        p, sm = self.p, _sm()
        grupos = _por_cuerpo(p["caras"], estado, "caras") if p["caras"] else {}
        for cid in p["cuerpos"]:
            grupos.setdefault(estado.cuerpo(cid).id, [])
        if not grupos:
            raise ErrorOperacion("Elegí caras a quitar o un cuerpo para vaciar.")
        for cid, caras in grupos.items():
            c = estado.cuerpo(cid)
            c.forma = sm.vaciado(c.forma, caras, espesor_interior=ctx.evaluar(p["espesor_interior"]),
                                 espesor_exterior=ctx.evaluar(p["espesor_exterior"]), direccion=p["direccion"],
                                 tangente=p["tangente"], tipo=p["tipo"])


class OpDesmoldeo(Operacion):
    """Desmoldeo de Fusion [GUID-83C650C2]: plano fijo (da la dirección de extracción y el plano neutro),
    caras a inclinar, ángulo, un lado / dos lados / simétrico y voltear la dirección."""
    TIPO, ETIQUETA, ICONO = "desmoldeo", "Desmoldeo", "◿"
    PARAMS = {"plano": None, "caras": [], "angulo": "3 deg", "lados": "uno", "angulo2": "3 deg", "voltear": False}
    EXPRESIONES = ("angulo", "angulo2")
    OPCIONES = {"lados": ("uno", "dos", "simetrico")}

    def dependencias(self):
        return _deps_refs(self.p["plano"], self.p["caras"]) - {self.id}

    def ejecutar(self, estado, ctx):
        p, sm = self.p, _sm()
        if not p["plano"]:
            raise ErrorOperacion("Elegí el plano fijo (una cara plana o un plano).")
        e = _resolver(p["plano"], estado)
        plano = ent.como_plano(e)
        # Con una cara, la extracción va hacia afuera del material que esa cara limita (al revés de su
        # normal exterior): el cuerpo se angosta alejándose de la cara fija, como en Fusion.
        direccion = -plano.normal if e.tipo == "cara" else plano.normal
        direccion = -direccion if p["voltear"] else direccion
        for cid, caras in _por_cuerpo(p["caras"], estado, "caras").items():
            c = estado.cuerpo(cid)
            c.forma = sm.desmoldeo(c.forma, caras, direccion, ctx.evaluar(p["angulo"], ANGULO), plano,
                                   lados=p["lados"], angulo2=ctx.evaluar(p["angulo2"], ANGULO))


class OpEscala(Operacion):
    """Escala de Fusion [GUID-D3F6F79B]: cuerpos, punto base, uniforme o no uniforme (X, Y, Z)."""
    TIPO, ETIQUETA, ICONO = "escala", "Escala", "⤢"
    PARAMS = {"cuerpos": [], "punto": None, "tipo": "uniforme", "factor": "1", "fx": "1", "fy": "1", "fz": "1"}
    EXPRESIONES = ("factor", "fx", "fy", "fz")
    OPCIONES = {"tipo": ("uniforme", "no_uniforme")}

    def dependencias(self):
        return (_deps_objetivo(self.p["cuerpos"]) | _deps_refs(self.p["punto"])) - {self.id}

    def ejecutar(self, estado, ctx):
        p, sm = self.p, _sm()
        if not p["cuerpos"]:
            raise ErrorOperacion("Elegí los cuerpos a escalar.")
        punto = ent.como_punto(_resolver(p["punto"], estado)) if p["punto"] else np.zeros(3)
        E = lambda k: ctx.evaluar(p[k], "escalar")  # noqa: E731
        for cid in p["cuerpos"]:
            c = estado.cuerpo(cid)
            if p["tipo"] == "uniforme":
                c.forma = sm.escalar(c.forma, punto, factor=E("factor"))
            else:
                c.forma = sm.escalar(c.forma, punto, factores=(E("fx"), E("fy"), E("fz")))
            if getattr(c, "tipo", "solido") == "solido" and geo.sin_volumen(c.forma):
                raise ErrorOperacion(f"«{c.nombre}» queda sin volumen con esa escala: el factor es demasiado chico.")


class OpDesfaseCara(Operacion):
    """Cara de desfase / Pulsar-tirar de Fusion [SLD-OFFSET-FACES]: mueve caras a lo largo de su normal."""
    TIPO, ETIQUETA, ICONO = "desfase_cara", "Desfase de cara", "⇱"
    PARAMS = {"caras": [], "distancia": "1 mm", "tangente": True}
    EXPRESIONES = ("distancia",)

    def dependencias(self):
        return _deps_refs(self.p["caras"]) - {self.id}

    def ejecutar(self, estado, ctx):
        for cid, caras in _por_cuerpo(self.p["caras"], estado, "caras").items():
            c = estado.cuerpo(cid)
            c.forma = _sm().desfasar_caras(c.forma, caras, ctx.evaluar(self.p["distancia"]),
                                           tangente=self.p["tangente"])


class OpReemplazarCara(Operacion):
    """Reemplazar cara de Fusion [GUID-CA081251]: lleva caras del cuerpo hasta una cara o plano destino."""
    TIPO, ETIQUETA, ICONO = "reemplazar_cara", "Reemplazar cara", "⇥"
    PARAMS = {"caras": [], "destino": None}

    def dependencias(self):
        return _deps_refs(self.p["caras"], self.p["destino"]) - {self.id}

    def ejecutar(self, estado, ctx):
        if not self.p["destino"]:
            raise ErrorOperacion("Elegí la cara o el plano destino.")
        e = _resolver(self.p["destino"], estado)
        destino = e.forma if e.tipo == "cara" else ent.como_plano(e)
        for cid, caras in _por_cuerpo(self.p["caras"], estado, "caras").items():
            c = estado.cuerpo(cid)
            c.forma = _sm().reemplazar_cara(c.forma, caras, destino)


def _herramienta(ref, estado):
    """Herramienta de corte: cara, plano (geo.Plano), cuerpo o arista."""
    e = _resolver(ref, estado)
    if e.tipo in ("plano", "boceto"):
        return ent.como_plano(e)
    return e.forma


class OpDividirCara(Operacion):
    """Dividir cara de Fusion [GUID-BA98BF29]: parte caras con una cara, un plano o aristas."""
    TIPO, ETIQUETA, ICONO = "dividir_cara", "Dividir cara", "⊟"
    PARAMS = {"caras": [], "herramienta": None, "extender": True}

    def dependencias(self):
        return _deps_refs(self.p["caras"], self.p["herramienta"]) - {self.id}

    def ejecutar(self, estado, ctx):
        if not self.p["herramienta"]:
            raise ErrorOperacion("Elegí la herramienta de división.")
        herramienta = _herramienta(self.p["herramienta"], estado)
        for cid, caras in _por_cuerpo(self.p["caras"], estado, "caras").items():
            c = estado.cuerpo(cid)
            c.forma = _sm().dividir_cara(c.forma, caras, herramienta, extender=self.p["extender"])


class OpDividirCuerpo(Operacion):
    """Dividir cuerpo de Fusion [SLD-SPLIT-BODY-SOLID]: el cuerpo queda partido en varios cuerpos."""
    TIPO, ETIQUETA, ICONO = "dividir_cuerpo", "Dividir cuerpo", "⊘"
    PARAMS = {"cuerpo": "", "herramienta": None, "extender": True}

    def dependencias(self):
        return (_deps_objetivo(self.p["cuerpo"]) | _deps_refs(self.p["herramienta"])) - {self.id}

    def ejecutar(self, estado, ctx):
        if not self.p["cuerpo"] or not self.p["herramienta"]:
            raise ErrorOperacion("Elegí el cuerpo a dividir y la herramienta.")
        c = estado.cuerpo(self.p["cuerpo"])
        partes = _sm().dividir_cuerpo(c.forma, _herramienta(self.p["herramienta"], estado),
                                      extender=self.p["extender"])
        if len(partes) < 2:
            ctx.aviso("La herramienta no divide el cuerpo.")
        c.forma = partes[0]
        for parte in partes[1:]:
            estado.nuevo_cuerpo(self.id, parte, c.tipo, **atributos_copia(c))


class OpDivisionSilueta(Operacion):
    """División de silueta de Fusion [SLD-REF-SILHOUETTE-SPLIT]: parte las caras por su silueta vista
    desde una dirección (modo «solo caras»)."""
    TIPO, ETIQUETA, ICONO = "division_silueta", "División de silueta", "◐"
    PARAMS = {"cuerpo": "", "direccion": None}

    def dependencias(self):
        return (_deps_objetivo(self.p["cuerpo"]) | _deps_refs(self.p["direccion"])) - {self.id}

    def ejecutar(self, estado, ctx):
        if not self.p["cuerpo"] or not self.p["direccion"]:
            raise ErrorOperacion("Elegí el cuerpo y la dirección de vista.")
        c = estado.cuerpo(self.p["cuerpo"])
        c.forma = _sm().division_silueta(c.forma, ent.direccion(_resolver(self.p["direccion"], estado)))


class OpAlinear(Operacion):
    """Alinear de Fusion [SLD-ALIGN-CMD]: lleva una referencia de los cuerpos (punto, plano o eje) sobre
    otra; planos enfrentados, ejes coincidentes; «Voltear» gira 180°."""
    TIPO, ETIQUETA, ICONO = "alinear", "Alinear", "⇶"
    PARAMS = {"cuerpos": [], "origen": None, "destino": None, "voltear": False, "copiar": False}

    def dependencias(self):
        return (_deps_objetivo(self.p["cuerpos"]) | _deps_refs(self.p["origen"], self.p["destino"])) - {self.id}

    @staticmethod
    def _dato(e):
        if e.tipo in ("vertice", "punto", "punto_boceto"):
            return {"tipo": "punto", "punto": ent.como_punto(e)}
        if e.tipo == "eje" or (e.tipo in ("arista", "curva_boceto") and e.eje is not None):
            p, d = ent.como_eje(e)
            return {"tipo": "eje", "punto": p, "direccion": d}
        if e.plano is not None:
            return {"tipo": "plano", "plano": e.plano}
        if e.tipo == "cara":
            p, d = ent.como_eje(e)
            return {"tipo": "eje", "punto": p, "direccion": d}
        raise ErrorOperacion("La referencia de alineación tiene que ser un punto, un plano o un eje.")

    def ejecutar(self, estado, ctx):
        p = self.p
        if not p["cuerpos"] or not p["origen"] or not p["destino"]:
            raise ErrorOperacion("Elegí los cuerpos, la referencia de origen y la de destino.")
        _, m = _sm().alinear(None, self._dato(_resolver(p["origen"], estado)),
                             self._dato(_resolver(p["destino"], estado)), voltear=p["voltear"])
        for cid in p["cuerpos"]:
            c = estado.cuerpo(cid)
            nueva = geo.transformar(c.forma, m)
            if p["copiar"]:
                estado.nuevo_cuerpo(self.id, nueva, c.tipo, nombre=f"{c.nombre} (copia)",
                                    **atributos_copia(c))
            else:
                c.forma = nueva


class OpBorrarCaras(Operacion):
    """Borrar caras (Suprimir de Fusion sobre caras [SLD-DELETE]): quita caras y cierra el hueco
    extendiendo las vecinas (defeaturing)."""
    TIPO, ETIQUETA, ICONO = "borrar_caras", "Borrar caras", "⌫"
    PARAMS = {"caras": []}

    def dependencias(self):
        return _deps_refs(self.p["caras"]) - {self.id}

    def ejecutar(self, estado, ctx):
        for cid, caras in _por_cuerpo(self.p["caras"], estado, "caras").items():
            c = estado.cuerpo(cid)
            c.forma = _sm().quitar_caras(c.forma, caras)


registrar_operacion(OpMover, OpQuitar, OpEmpalme, OpChaflan, OpVaciado, OpDesmoldeo, OpEscala, OpDesfaseCara,
                    OpReemplazarCara, OpDividirCara, OpDividirCuerpo, OpDivisionSilueta, OpAlinear, OpBorrarCaras)
