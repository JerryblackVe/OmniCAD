# -*- coding: utf-8 -*-
"""
INSERTAR › Lienzo y Calcomanía de Fusion [SLD-INSERT-CANVAS, SLD-SCALE-CANVAS, SLD-INS-DECAL]: una imagen
(guardada dentro de la receta) apoyada sobre un plano o una cara plana, con posición, giro, ancho real
(calibración) y opacidad. El lienzo es una referencia para dibujar encima; la calcomanía se pega a la
cara del cuerpo y se ve opaca.

También Importar IGES (Archivo › Abrir de un .iges/.igs): como Importar STEP, el archivo va dentro de la receta.
"""
from ..nucleo import intercambio
from . import entidades as ent
from .operaciones import ANGULO, ErrorOperacion, Operacion, _resolver, aplicar_resultado, registrar_operacion


class OpLienzo(Operacion):
    """Lienzo de Fusion (INSERTAR): imagen de referencia sobre un plano, con tamaño, desplazamiento, giro y
    opacidad; no crea geometría."""
    TIPO, ETIQUETA, ICONO = "lienzo", "Lienzo", "🖼"
    PARAMS = {"plano": None, "archivo": "", "imagen": "", "proporcion": 1.0, "ancho": "100 mm", "dx": "0 mm",
              "dy": "0 mm", "angulo": "0 deg", "opacidad": 50, "calcomania": False, "voltear": False}
    EXPRESIONES = ("ancho", "dx", "dy", "angulo")

    def dependencias(self):
        return ent.dependencias_de(self.p["plano"]) - {self.id}

    def ejecutar(self, estado, ctx):
        if not self.p["imagen"]:
            raise ErrorOperacion("El lienzo no tiene imagen.")
        if not self.p["plano"]:
            raise ErrorOperacion("Elegí el plano o la cara del lienzo.")
        plano = ent.como_plano(_resolver(self.p["plano"], estado))
        ancho = ctx.evaluar(self.p["ancho"])
        if ancho <= 0:
            raise ErrorOperacion("El ancho del lienzo tiene que ser positivo.")
        estado.lienzos[self.id] = {"nombre": self.nombre, "plano": plano, "ancho": ancho,
                                   "alto": ancho * float(self.p.get("proporcion") or 1.0),
                                   "dx": ctx.evaluar(self.p["dx"]), "dy": ctx.evaluar(self.p["dy"]),
                                   "angulo": ctx.evaluar(self.p["angulo"], ANGULO),
                                   "opacidad": max(0, min(100, int(self.p["opacidad"]))) / 100.0,
                                   "calcomania": bool(self.p["calcomania"]), "voltear": bool(self.p["voltear"]),
                                   "imagen": self.p["imagen"]}


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
