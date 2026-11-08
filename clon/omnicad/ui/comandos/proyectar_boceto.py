# -*- coding: utf-8 -*-
"""Proyectar a superficie y Curva de intersección dentro del boceto abierto."""
from ...nucleo import geometria as geo
from ...restricciones import boceto3d as b3
from ...timeline import entidades as ent
from ...timeline.operaciones import BocetoResuelto, aristas_de_origen
from ..comando import Comando, ErrorComando, Opciones, Seleccion
from . import registrar


class _CurvasEnBoceto(Comando):
    SIN_OP = True
    EN_BOCETO_ABIERTO = True

    def verificar(self, ctx):
        if ctx.ventana is None or not ctx.ventana.modo_boceto.activo:
            return "Abrí un boceto para usar este comando."
        return None

    def preparar_panel(self, panel):
        modo = panel.ctx.ventana.modo_boceto
        lz = modo.lienzo
        op = modo.datos.get("op")
        if op is None and "id" not in modo.datos:
            modo.datos["id"] = panel.ctx.doc.nuevo_id()
        bid = op.id if op is not None else modo.datos["id"]
        estado = panel.ctx.ventana._estado_visible().copia()
        estado.bocetos[bid] = BocetoResuelto(bid, "Boceto abierto", lz.b.copia(), lz.plano, [], lz.resultado)
        panel.ctx.estado = estado
        visor = panel.visor
        visor.set_modelo(estado, visor._ocultos - {bid}, tuple(i for i in visor._excluir_bocetos if i != bid))

    def campos(self, ctx):
        return [Seleccion("curvas", "Curvas", {"curva_boceto"}, maximo=None),
                Seleccion("caras", "Caras", {"cara"}, maximo=None)]

    def construir(self, v, ctx):
        if not v.get("curvas") or not v.get("caras"):
            raise ErrorComando("Elegí las curvas del boceto y las caras de destino.")
        origen = {"tool": self.HERRAMIENTA, "refs": [h["ref"] for h in v["caras"]],
                  "curves": [h["ref"] for h in v["curvas"]]}
        if self.HERRAMIENTA == "project_to_surface":
            modo = v.get("tipo", "closest")
            if modo not in ("closest", "vector"):
                raise ErrorComando("Elegí Punto más cercano o A lo largo de un vector.")
            origen.update(mode=modo, direction=None)
            if modo == "vector":
                if not v.get("direccion"):
                    raise ErrorComando("Elegí un eje o una arista recta como dirección de proyección.")
                try:
                    direccion = ent.como_eje(ent.resolver(v["direccion"][0]["ref"], ctx.estado))[1]
                except ent.ErrorReferencia as e:
                    raise ErrorComando(str(e)) from e
                origen["direction"] = [float(x) for x in direccion]
        try:
            curvas = aristas_de_origen(origen, ctx.estado)
        except (geo.ErrorGeometria, ent.ErrorReferencia) as e:
            raise ErrorComando(str(e)) from e
        if not curvas:
            raise ErrorComando("La selección no deja ninguna curva (no se cortan o no cae sobre la cara).")
        return curvas, origen

    def mostrar(self, v, ctx):
        self.construir(v, ctx)

    def aplicar(self, v, ctx):
        curvas, origen = self.construir(v, ctx)
        lz = ctx.ventana.modo_boceto.lienzo

        def agregar():
            for i, curva in enumerate(curvas):
                b3.agregar_desde_mundo(lz.b, curva, lz.plano, lz.construccion, {**origen, "index": i})
        if not lz.aplicar_cambio(agregar, anclar=False):
            raise ErrorComando("No se pudieron agregar las curvas: entran en conflicto con el boceto.")


class ProyectarSuperficie(_CurvasEnBoceto):
    CLAVE = "sk_proyectar_superficie"
    TITULO = "Proyectar a superficie"
    ICONO = "proyectar_superficie"
    HERRAMIENTA = "project_to_surface"
    AYUDA = "Proyecta curvas de boceto sobre caras y crea curvas 3D vinculadas al modelo."

    def campos(self, ctx):
        return super().campos(ctx) + [
            Opciones("tipo", "Tipo de proyección", {"closest": "Punto más cercano", "vector": "A lo largo de un vector"}),
            Seleccion("direccion", "Dirección", {"eje", "arista_lineal"},
                      visible_si=lambda v: v.get("tipo") == "vector")]


class CurvaInterseccion(_CurvasEnBoceto):
    CLAVE = "sk_curva_interseccion"
    TITULO = "Curva de intersección"
    ICONO = "curva_interseccion"
    HERRAMIENTA = "intersection_curve"
    AYUDA = "Interseca la extrusión normal de las curvas elegidas con las caras y crea curvas 3D vinculadas."


registrar(ProyectarSuperficie, CurvaInterseccion)
