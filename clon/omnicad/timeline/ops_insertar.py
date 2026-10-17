# -*- coding: utf-8 -*-
"""
INSERTAR › Lienzo y Calcomanía de Fusion [SLD-INSERT-CANVAS, SLD-SCALE-CANVAS, SLD-INS-DECAL]: una imagen
(guardada dentro de la receta) apoyada sobre un plano o una cara plana, con posición, giro, ancho real
(calibración) y opacidad. El lienzo es una referencia para dibujar encima; la calcomanía se pega a la
cara del cuerpo y se ve opaca.

También Importar IGES (Archivo › Abrir de un .iges/.igs): como Importar STEP, el archivo va dentro de la receta.
"""
import logging

from ..nucleo import intercambio
from . import entidades as ent
from .operaciones import ANGULO, Contexto, ErrorOperacion, Operacion, _resolver, aplicar_resultado, registrar_operacion
from .parametros import ESCALAR

log = logging.getLogger(__name__)


class OpLienzo(Operacion):
    """Lienzo de Fusion (INSERTAR): imagen de referencia sobre un plano, con tamaño, desplazamiento, giro y
    opacidad; no crea geometría."""
    TIPO, ETIQUETA, ICONO = "lienzo", "Lienzo", "🖼"
    PARAMS = {"plano": None, "archivo": "", "imagen": "", "proporcion": 1.0, "ancho": "100 mm", "dx": "0 mm",
              "dy": "0 mm", "angulo": "0 deg", "opacidad": 50, "calcomania": False, "voltear": False,
              "alto": "100 mm", "mantener_proporcion": True, "voltear_v": False, "encadenar": False,
              "usar_opacidad": True, "centrada": False, "escala": "1"}
    EXPRESIONES = ("ancho", "alto", "dx", "dy", "angulo", "escala")

    def dependencias(self):
        return ent.dependencias_de(self.p["plano"]) - {self.id}

    def ejecutar(self, estado, ctx):
        if not self.p["imagen"]:
            raise ErrorOperacion("El lienzo no tiene imagen.")
        if not self.p["plano"]:
            raise ErrorOperacion("Elegí el plano o la cara del lienzo.")
        entidad = _resolver(self.p["plano"], estado)
        malla = None
        cuerpo = estado.cuerpos.get(entidad.cuerpo) if self.p["calcomania"] else None
        if self.p["calcomania"] and entidad.forma is not None:
            from ..nucleo.calcomanias import superficie
            malla = superficie(entidad.forma, cuerpo.forma if cuerpo else None, self.p["encadenar"], self.p["centrada"])
            plano = malla["plano"]
        else:
            plano = ent.como_plano(entidad)
        ancho = ctx.evaluar(self.p["ancho"])
        if ancho <= 0:
            raise ErrorOperacion("El ancho del lienzo tiene que ser positivo.")
        alto = (ancho * float(self.p.get("proporcion") or 1.0) if self.p["mantener_proporcion"]
                else ctx.evaluar(self.p["alto"]))
        if alto <= 0:
            raise ErrorOperacion("La altura de la calcomanía tiene que ser positiva.")
        escala = ctx.evaluar(self.p["escala"], ESCALAR)
        if escala <= 0:
            raise ErrorOperacion("El factor de escala debe ser positivo.")
        ancho, alto = ancho * escala, alto * escala
        estado.lienzos[self.id] = {"nombre": self.nombre, "plano": plano, "ancho": ancho,
                                   "alto": alto, "malla": malla,
                                   "dx": ctx.evaluar(self.p["dx"]), "dy": ctx.evaluar(self.p["dy"]),
                                   "angulo": ctx.evaluar(self.p["angulo"], ANGULO),
                                   "opacidad": (max(0, min(100, int(self.p["opacidad"]))) / 100.0
                                                if self.p["usar_opacidad"] else 1.0),
                                   "calcomania": bool(self.p["calcomania"]), "voltear": bool(self.p["voltear"]),
                                   "voltear_v": bool(self.p["voltear_v"]), "imagen": self.p["imagen"],
                                   # el cuerpo al que está pegada y su forma en este paso: la calcomanía se va con
                                   # él y, si el cuerpo cambia de lugar después, se vuelve a calcular (`vigentes`)
                                   "cuerpo": cuerpo.id if cuerpo is not None else None,
                                   "forma": cuerpo.forma if cuerpo is not None else None,
                                   "archivo": self.p["archivo"]}
        if malla is not None:
            from ..nucleo.calcomanias import textura
            d = estado.lienzos[self.id]
            malla["uv"] = textura(malla["coordenadas"], ancho, alto, d["dx"], d["dy"], d["angulo"],
                                  d["voltear"], d["voltear_v"])


_VIGENTES = {}      # (id del dato del paso, id de la forma del cuerpo) → (dato, forma, dato recalculado o None)
MAX_COPIAS = 24     # shortcut: un patrón de cientos de copias recalcularía cientos de caras en cada cambio; llevan la calcomanía las primeras


def _recalculada(doc, estado, ident, d, cuerpo, op):
    """Lo que `op` (el paso de la calcomanía) da sobre `cuerpo` tal como está en `estado`, o None si su cara ya no se
    encuentra. Se guarda por (dato del paso, forma del cuerpo): el visor lo pide en cada refresco."""
    clave = (id(d), id(cuerpo.forma))
    if clave not in _VIGENTES:
        try:
            trabajo = estado.copia()
            op.ejecutar(trabajo, Contexto(doc.parametros.valores()))
            nuevo = trabajo.lienzos[ident]
        except Exception as e:  # noqa: BLE001 — una calcomanía que no se pudo volver a poner no tumba el refresco
            log.info("La calcomanía %s no se encuentra sobre %s: %s", ident, cuerpo.id, e)
            nuevo = None
        if len(_VIGENTES) > 64:
            _VIGENTES.clear()
        _VIGENTES[clave] = (d, cuerpo.forma, nuevo)      # retiene `d` y la forma: su id no se recicla mientras esté
    return _VIGENTES[clave][2]


def calcomanias_vigentes(doc, estado):
    """[(id, datos)] de lo que se dibuja de INSERTAR › Lienzo / Calcomanía con `estado`. Los lienzos, tal cual. Cada
    calcomanía va con su cuerpo, como la de Fusion: si el cuerpo ya no existe (borrado, unido a otro) se va con él; si
    cambió de lugar o de forma después del paso, se vuelve a poner sobre su cara (la referencia persistente la
    encuentra); y las copias del cuerpo (patrón, simetría, mover › copiar) llevan la suya (`id@copia`) cuando su
    cara se encuentra en la copia."""
    salida = []
    for ident, d in list(estado.lienzos.items()):
        cuerpo = estado.cuerpos.get(d.get("cuerpo")) if d.get("calcomania") else None
        if cuerpo is None:
            if not d.get("calcomania") or d.get("cuerpo") is None:
                salida.append((ident, d))          # lienzo, o calcomanía sobre algo que no es un cuerpo
            continue                               # calcomanía cuyo cuerpo ya no existe
        try:
            op = doc.operacion(ident)
        except Exception:  # noqa: BLE001 — vista previa de un paso que todavía no está en el documento
            op = None
        if op is None or cuerpo.forma is d.get("forma"):
            salida.append((ident, d))
        else:
            nuevo = _recalculada(doc, estado, ident, d, cuerpo, op)
            if nuevo is not None:
                salida.append((ident, nuevo))
        copias = [c for c in estado.cuerpos.values() if op is not None and d["cuerpo"] in getattr(c, "origen", ())]
        for copia in copias[:MAX_COPIAS]:
            ref = dict(op.p["plano"], cuerpo=copia.id)
            otra = OpLienzo(ident, op.nombre, False, **dict(op.p, plano=ref))
            nuevo = _recalculada(doc, estado, ident, d, copia, otra)
            if nuevo is not None:
                salida.append((f"{ident}@{copia.id}", nuevo))
    return salida


class OpImportarIGES(Operacion):
    """Importa un IGES como cuerpo(s) (Fusion lo abre con Abrir › Abrir desde mi equipo). El contenido se embebe
    en la receta para que el proyecto sea autónomo."""
    TIPO, ETIQUETA, ICONO = "importar_iges", "Importar IGES", "⇩"
    PARAMS = {"archivo": "", "contenido": ""}

    def ejecutar(self, estado, ctx):
        if not self.p["contenido"]:
            raise ErrorOperacion("La importación no tiene contenido IGES.")
        aplicar_resultado(estado, ctx, self.id, intercambio.leer_iges_texto(self.p["contenido"]), "nuevo")


registrar_operacion(OpLienzo, OpImportarIGES)
