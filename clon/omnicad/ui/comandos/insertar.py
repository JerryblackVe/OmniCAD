# -*- coding: utf-8 -*-
"""INSERTAR: archivos DXF y SVG como bocetos sobre un plano o una cara (Fusion: SLD-INS-DXF, SLD-INS-SVG)."""
from pathlib import Path

from ...timeline.operaciones import OpBoceto
from ...timeline.parametros import ANGULO, ESCALAR
from ..comando import Casilla, Comando, Entero, ErrorComando, Expresion, Seleccion, Texto, exigir
from . import registrar


def _plano_de_hit(hit):
    """Parámetros `plano`/`marco` de OpBoceto según lo elegido."""
    ref = hit["ref"]
    if ref["tipo"] == "plano":
        return {"plano": ref["id"], "marco": None}
    if ref["tipo"] == "cara" and hit.get("plano") is not None:
        return {"plano": "cara", "marco": hit["plano"].marco()}
    raise ErrorComando("Elegí un plano o una cara plana.")


class _InsertarArchivo2D(Comando):
    EXTENSIONES = ()

    def campos(self, ctx):
        return [Seleccion("plano", "Plano/cara", {"plano", "cara_plana"}),
                Texto("archivo", "Archivo", ""), Expresion("escala", "Escala", "1", ESCALAR),
                Expresion("dx", "Desplazamiento X", "0 mm"), Expresion("dy", "Desplazamiento Y", "0 mm"),
                Expresion("angulo", "Ángulo", "0 deg", ANGULO)]

    def leer(self, ruta):
        raise NotImplementedError

    def construir(self, v, ctx):
        from ...io_archivos.boceto_archivos import boceto_desde_primitivas
        plano = _plano_de_hit(exigir(v, "plano", "Elegí el plano o la cara donde va el dibujo.")[0])
        ruta = (v.get("archivo") or "").strip()
        if not ruta or not Path(ruta).is_file():
            raise ErrorComando("Elegí el archivo (Archivo › ruta completa).")
        clave = (ruta, Path(ruta).stat().st_mtime)
        if getattr(self, "_clave", None) != clave:
            try:
                self._prims = self.leer(ruta)
            except (ValueError, OSError) as e:
                raise ErrorComando(f"No se pudo leer el archivo: {e}") from e
            self._clave = clave
        try:
            boceto = boceto_desde_primitivas(self._prims, escala=ctx.evaluar(v["escala"], ESCALAR),
                                             desplazamiento=(ctx.evaluar(v["dx"]), ctx.evaluar(v["dy"])),
                                             angulo=ctx.evaluar(v["angulo"], ANGULO))
        except ValueError as e:
            raise ErrorComando(str(e)) from e
        if ctx.op is not None:
            return OpBoceto(ctx.op.id, ctx.op.nombre, ctx.op.suprimida, boceto=boceto, **plano)
        return OpBoceto(ctx.doc.nuevo_id(), self.nombre_nuevo(ctx), boceto=boceto, **plano)

    def nombre_nuevo(self, ctx):
        usados = {o.nombre for o in ctx.doc.operaciones}
        n = 1
        while f"Boceto{n}" in usados:
            n += 1
        return f"Boceto{n}"


class InsertarDXF(_InsertarArchivo2D):
    CLAVE, TITULO, ICONO = "insertar_dxf", "Insertar DXF", "insertar_dxf"
    AYUDA = "Trae la geometría 2D de un archivo DXF a un boceto nuevo sobre un plano o una cara."
    EXTENSIONES = ("dxf",)

    def leer(self, ruta):
        from ...io_archivos.dxf import leer_dxf
        return leer_dxf(ruta)


class InsertarSVG(_InsertarArchivo2D):
    CLAVE, TITULO, ICONO = "insertar_svg", "Insertar SVG", "insertar_svg"
    AYUDA = "Trae un dibujo SVG a un boceto nuevo (las curvas pasan a splines)."
    EXTENSIONES = ("svg",)

    def leer(self, ruta):
        from ...io_archivos.svg import leer_svg
        return leer_svg(ruta)


class Lienzo(Comando):
    """INSERTAR › Lienzo [SLD-INSERT-CANVAS]: imagen de referencia sobre un plano o una cara. El ancho es la
    medida real (lo que en Fusion se ajusta con «Calibrar»)."""
    CLAVE, TITULO, ICONO = "lienzo", "Lienzo", "lienzo"
    AYUDA = "Pone una imagen de referencia sobre un plano o una cara (para dibujar encima)."
    EXTENSIONES = ("png", "jpg", "jpeg", "bmp")
    CALCOMANIA = False

    def campos(self, ctx):
        filtros = {"cara_plana"} if self.CALCOMANIA else {"plano", "cara_plana"}
        return [Seleccion("plano", "Cara" if self.CALCOMANIA else "Plano/cara", filtros),
                Texto("archivo", "Imagen", ""), Expresion("ancho", "Ancho real", "100 mm"),
                Expresion("dx", "Desplazamiento X", "0 mm"), Expresion("dy", "Desplazamiento Y", "0 mm"),
                Expresion("angulo", "Ángulo", "0 deg", ANGULO),
                Entero("opacidad", "Opacidad (%)", 100 if self.CALCOMANIA else 50, 0, 100),
                Casilla("voltear", "Voltear horizontal")]

    def construir(self, v, ctx):
        import base64

        from PySide6.QtGui import QImage

        from ...timeline.ops_insertar import OpLienzo
        hit = exigir(v, "plano", "Elegí el plano o la cara.")[0]
        ruta = (v.get("archivo") or "").strip()
        if ruta and getattr(self, "_ruta", None) != ruta:
            if not Path(ruta).is_file():
                raise ErrorComando("No encuentro la imagen.")
            datos = Path(ruta).read_bytes()
            img = QImage.fromData(datos)
            if img.isNull():
                raise ErrorComando("No se pudo leer la imagen (PNG, JPG o BMP).")
            self._ruta, self._b64, self._prop = ruta, base64.b64encode(datos).decode("ascii"), img.height() / img.width()
        if not getattr(self, "_b64", None):
            if ctx.op is not None:
                self._b64, self._prop = ctx.op.p["imagen"], ctx.op.p["proporcion"]
            else:
                raise ErrorComando("Elegí la imagen.")
        ctx.evaluar(v["ancho"])
        params = {"plano": hit["ref"], "archivo": Path(ruta).name if ruta else (ctx.op.p["archivo"] if ctx.op else ""),
                  "imagen": self._b64, "proporcion": self._prop, "calcomania": self.CALCOMANIA,
                  **{k: v[k] for k in ("ancho", "dx", "dy", "angulo", "opacidad", "voltear")}}
        return self.crear_op(OpLienzo, v, ctx, **params)

    def desde_op(self, op, ctx):
        from ..comando import hit_desde_ref
        return dict(op.p, plano=[hit_desde_ref(op.p["plano"], ctx.estado)] if op.p.get("plano") else [], archivo="")

    def nombre_nuevo(self, ctx):
        base = "Calcomanía" if self.CALCOMANIA else "Lienzo"
        usados = {o.nombre for o in ctx.doc.operaciones}
        n = 1
        while f"{base}{n}" in usados:
            n += 1
        return f"{base}{n}"


class Calcomania(Lienzo):
    CLAVE, TITULO, ICONO = "calcomania", "Calcomanía", "calcomania"
    AYUDA = "Pega una imagen sobre una cara plana del cuerpo."
    CALCOMANIA = True
    VARIANTE = ("calcomania", True)


registrar(InsertarDXF, InsertarSVG, Lienzo, Calcomania)
