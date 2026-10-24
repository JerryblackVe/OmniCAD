# -*- coding: utf-8 -*-
"""MALLA › CREAR › Crear boceto de sección de malla (Fusion: MESH-CREATE-MESH-SECTION-SKETCH): boceto nuevo sobre el
plano con la línea de sección de la malla (fija, de construcción) y, opcional, las curvas cerradas ajustadas a ella
(Ajustar curvas a sección de malla, núcleo en `nucleo/malla_seccion.py`). El paso queda como un boceto más: doble clic
lo edita en el entorno de boceto."""
from ...nucleo import geometria as geo
from ...nucleo import malla_seccion as ms
from ...timeline.operaciones import OpBoceto
from ..comando import Comando, ErrorComando, Expresion, Opciones, Seleccion, exigir
from . import registrar
from .insertar import _InsertarArchivo2D, _plano_de_hit
from .malla import _mallas

_AJUSTES = {"ninguno": "No ajustar (solo la sección)", "lineas_arcos": "Líneas y arcos", "circulo": "Círculo",
            "elipse": "Elipse", "spline_cerrada": "Spline cerrada"}


class SeccionMalla(Comando):
    CLAVE, TITULO, ICONO = "seccion_malla", "Crear boceto de sección de malla", "cortar_plano"
    AYUDA = ("Boceto con la línea donde el plano corta la malla, para rehacerla como sólido. «Ajustar curvas» dibuja "
             "curvas cerradas que la siguen dentro de la desviación máxima.")
    verificar = staticmethod(_mallas)

    def campos(self, ctx):
        return [Seleccion("cuerpo", "Cuerpo de malla", {"cuerpo"}),
                Seleccion("plano", "Plano de sección", {"plano", "cara_plana"}),
                Expresion("distancia", "Distancia", "0 mm"),
                Opciones("ajuste", "Ajustar curvas", _AJUSTES, "ninguno"),
                Expresion("tolerancia", "Desviación máxima", "0.1 mm",
                          visible_si=lambda v: v.get("ajuste") != "ninguno")]

    def construir(self, v, ctx):
        cuerpo = ctx.estado.cuerpos.get(exigir(v, "cuerpo", "Seleccioná el cuerpo de malla.")[0]["ref"].get("cuerpo"))
        if cuerpo is None or getattr(cuerpo, "tipo", "") != "malla":
            raise ErrorComando("El cuerpo elegido no es una malla.")
        plano = _plano_de_hit(exigir(v, "plano", "Seleccioná el plano de sección.")[0])
        op = OpBoceto(ctx.doc.nuevo_id(), self.nombre_nuevo(ctx), desplazamiento=v["distancia"], **plano)
        tol = ctx.evaluar(v["tolerancia"]) if v["ajuste"] != "ninguno" else 0.1
        try:
            polilineas = ms.seccion(cuerpo.forma, op.plano(ctx.estado, ctx))
            op.boceto.agregar_proyeccion(ms.primitivas_seccion(polilineas), construccion=True)
            for P, cerrada in polilineas if v["ajuste"] != "ninguno" else ():
                if cerrada or v["ajuste"] == "lineas_arcos":
                    ms.agregar_curvas(op.boceto, ms.ajustar(P, cerrada, v["ajuste"], tolerancia=tol, desviacion=tol))
        except (geo.ErrorGeometria, ValueError) as e:
            raise ErrorComando(str(e)) from e
        return op

    nombre_nuevo = _InsertarArchivo2D.nombre_nuevo        # «BocetoN», como los demás bocetos nuevos


registrar(SeccionMalla)
