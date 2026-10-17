# -*- coding: utf-8 -*-
"""INSERTAR: archivos DXF y SVG como bocetos sobre un plano o una cara (Fusion: SLD-INS-DXF, SLD-INS-SVG)."""
from pathlib import Path

import numpy as np

from ...timeline.operaciones import OpBoceto
from ...timeline.ops_insertar import OpLienzo
from ...timeline.parametros import ANGULO, ESCALAR
from ..comando import Casilla, Comando, Entero, ErrorComando, Expresion, Porcentaje, Seleccion, Texto, exigir
from . import registrar


def _plano_de_hit(hit):
    """Parámetros `plano`/`marco`/`cara` de OpBoceto según lo elegido (en una cara, su referencia persistente)."""
    ref = hit["ref"]
    if ref["tipo"] == "plano":
        return {"plano": ref["id"], "marco": None, "cara": None}
    if ref["tipo"] == "cara" and hit.get("plano") is not None:
        return {"plano": "cara", "marco": hit["plano"].marco(), "cara": ref}
    raise ErrorComando("Elegí un plano o una cara plana.")


class _InsertarArchivo2D(Comando):
    EXTENSIONES = ()

    def campos(self, ctx):
        return [Seleccion("plano", "Plano/cara", {"plano", "cara_plana"}),
                Texto("archivo", "Archivo", ""), Expresion("escala", "Escala", "1", ESCALAR),
                Expresion("dx", "Desplazamiento X", "0 mm"), Expresion("dy", "Desplazamiento Y", "0 mm"),
                Expresion("angulo", "Ángulo", "0 deg", ANGULO),
                Casilla("voltear_h", "Volteo horizontal"), Casilla("voltear_v", "Volteo vertical")]

    def manipuladores(self, ctx, v):
        """Aro en la vista para arrastrar el dibujo por el plano (escribe Desplazamiento X / Y)."""
        from .. import manipuladores as mp
        from .comunes import evaluar_o_cero
        sel = v.get("plano") or []
        plano = sel[0].get("plano") if sel else None
        if plano is None:
            return []
        o, u, w = (np.asarray(x, float) for x in (plano.origen, plano.u, plano.v))
        dx, dy = evaluar_o_cero(ctx, v.get("dx")), evaluar_o_cero(ctx, v.get("dy"))

        def al_mover(q):
            d = np.asarray(q, float) - o
            return {"dx": float(d @ u), "dy": float(d @ w)}
        return [mp.Posicion("desplazamiento", o + u * dx + w * dy, plano.normal, al_mover)]

    def leer(self, ruta, v=None):
        raise NotImplementedError

    def clave_filtro(self, v):
        """Lo que, además del archivo, cambia las primitivas leídas (para no leer de nuevo en cada vista previa)."""
        return ()

    def transformacion(self, v, ctx):
        """Argumentos de `boceto_desde_primitivas` según el diálogo."""
        return {"escala": ctx.evaluar(v["escala"], ESCALAR),
                "desplazamiento": (ctx.evaluar(v["dx"]), ctx.evaluar(v["dy"])),
                "angulo": ctx.evaluar(v["angulo"], ANGULO),
                "voltear_h": bool(v.get("voltear_h")), "voltear_v": bool(v.get("voltear_v"))}

    def construir(self, v, ctx):
        from ...io_archivos.boceto_archivos import boceto_desde_primitivas
        plano = _plano_de_hit(exigir(v, "plano", "Elegí el plano o la cara donde va el dibujo.")[0])
        ruta = (v.get("archivo") or "").strip()
        if not ruta or not Path(ruta).is_file():
            raise ErrorComando("Elegí el archivo (Archivo › ruta completa).")
        clave = (ruta, Path(ruta).stat().st_mtime, self.clave_filtro(v))
        if getattr(self, "_clave", None) != clave:
            try:
                self._prims = self.leer(ruta, v)
            except (ValueError, OSError) as e:
                raise ErrorComando(f"No se pudo leer el archivo: {e}") from e
            self._clave = clave
        try:
            boceto = boceto_desde_primitivas(self._prims, **self.transformacion(v, ctx))
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

    def leer(self, ruta, v=None):
        from ...io_archivos.dxf import leer_dxf
        return leer_dxf(ruta)


def _lista(texto):
    return [t.strip() for t in str(texto or "").replace(";", ",").split(",") if t.strip()]


class InsertarSVG(_InsertarArchivo2D):
    CLAVE, TITULO, ICONO = "insertar_svg", "Insertar SVG", "insertar_svg"
    AYUDA = ("Trae un dibujo SVG a un boceto nuevo (las curvas pasan a splines). Con Capas o Colores se importa "
             "solo esa parte del archivo.")
    EXTENSIONES = ("svg",)

    def campos(self, ctx):
        return super().campos(ctx) + [Texto("capas", "Capas (coma)", ""), Texto("colores", "Colores #rrggbb (coma)", "")]

    def clave_filtro(self, v):
        return (tuple(_lista(v.get("capas"))), tuple(_lista(v.get("colores"))))

    def leer(self, ruta, v=None):
        from ...io_archivos.svg import leer_svg
        v = v or {}
        return leer_svg(ruta, capas=_lista(v.get("capas")) or None, colores=_lista(v.get("colores")) or None)


class VectorizarImagen(_InsertarArchivo2D):
    """INSERTAR › Vectorizar imagen: PNG/JPG a contornos cerrados en un boceto (no existe en Fusion)."""
    CLAVE, TITULO, ICONO = "vectorizar_imagen", "Vectorizar imagen", "vectorizar_imagen"
    AYUDA = ("Convierte una imagen (logo, silueta, dibujo en blanco y negro) en contornos cerrados de un boceto. "
             "Umbral 0 = automático.")
    EXTENSIONES = ("png", "jpg", "jpeg", "bmp", "gif", "webp")

    def campos(self, ctx):
        return [Seleccion("plano", "Plano/cara", {"plano", "cara_plana"}), Texto("archivo", "Imagen", ""),
                Expresion("ancho", "Ancho final", "100 mm"),
                Entero("umbral", "Umbral (0 = auto)", 0, 0, 254), Casilla("invertir", "Tinta clara (invertir)"),
                Entero("suavizado", "Suavizado (px)", 1, 0, 10), Casilla("curvas", "Curvas suaves (splines)"),
                Expresion("dx", "Desplazamiento X", "0 mm"), Expresion("dy", "Desplazamiento Y", "0 mm"),
                Expresion("angulo", "Ángulo", "0 deg", ANGULO),
                Casilla("voltear_h", "Volteo horizontal"), Casilla("voltear_v", "Volteo vertical")]

    def clave_filtro(self, v):
        return (v.get("umbral"), bool(v.get("invertir")), v.get("suavizado"), bool(v.get("curvas")))

    def leer(self, ruta, v=None):
        from ...io_archivos.vectorizar import vectorizar_imagen
        v = v or {}
        return vectorizar_imagen(ruta, umbral=(v.get("umbral") or None), invertir=bool(v.get("invertir")),
                                 suavizado=float(v.get("suavizado", 1)), curvas=bool(v.get("curvas")))

    def transformacion(self, v, ctx):
        return {"ancho": ctx.evaluar(v["ancho"]), "desplazamiento": (ctx.evaluar(v["dx"]), ctx.evaluar(v["dy"])),
                "angulo": ctx.evaluar(v["angulo"], ANGULO),
                "voltear_h": bool(v.get("voltear_h")), "voltear_v": bool(v.get("voltear_v"))}


class Lienzo(Comando):
    """INSERTAR › Lienzo [SLD-INSERT-CANVAS]: imagen de referencia sobre un plano o una cara. El ancho es la
    medida real (lo que en Fusion se ajusta con «Calibrar»)."""
    CLAVE, TITULO, ICONO = "lienzo", "Lienzo", "lienzo"
    CLASE_OP = OpLienzo
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
            if Path(ruta).stat().st_size > 32 * 1024 * 1024:
                raise ErrorComando("La imagen supera 32 MB.")
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
        propio = Path(getattr(self, "_ruta", None) or "").stem
        if self.CALCOMANIA and propio:                  # como Fusion: la calcomanía se llama como su imagen
            candidato, n = propio, 2
            while candidato in usados:
                candidato, n = f"{propio} ({n})", n + 1
            return candidato
        n = 1
        while f"{base}{n}" in usados:
            n += 1
        return f"{base}{n}"


class Calcomania(Lienzo):
    CLAVE, TITULO, ICONO = "calcomania", "Calcomanía", "calcomania"
    AYUDA = "Pega una imagen sobre una cara plana o curva, con tamaño, giro, opacidad y volteos."
    CALCOMANIA = True
    VARIANTE = ("calcomania", True)

    def campos(self, ctx):
        return [Texto("archivo", "Imagen"), Seleccion("plano", "Cara", {"cara"}),
                Casilla("encadenar", "Encadenar caras", True), Porcentaje("opacidad", "Opacidad"),
                Casilla("mantener_proporcion", "Mantener relación de aspecto", True),
                Expresion("ancho", "Anchura", "0 mm"), Expresion("alto", "Altura", "0 mm"),
                Expresion("escala", "Factor de escala", "1.00", ESCALAR),
                Expresion("dx", "Distancia X", "0 mm"), Expresion("dy", "Distancia Y", "0 mm"),
                Expresion("angulo", "Ángulo Z", "0 deg", ANGULO),
                Casilla("voltear", "Volteo horizontal"), Casilla("voltear_v", "Volteo vertical")]

    def preparar_panel(self, panel):
        self._panel = panel
        self._sincronizando = False
        if panel.ctx.op is not None:
            panel.widgets["archivo"].setPlaceholderText(panel.ctx.op.p["archivo"])
            panel.widgets["archivo"].setToolTip("Imagen embebida; escribí una ruta para reemplazarla.")
        panel.valores["plano"] = [dict(h, dibujo=[]) for h in panel.valores.get("plano", [])]
        panel._refrescar_seleccion()
        for clave in ("ancho", "alto"):
            panel.widgets[clave].textChanged.connect(lambda _t, k=clave: self._proporcion(k))
        panel.widgets["mantener_proporcion"].toggled.connect(lambda activa: self._proporcion("ancho") if activa else None)

    def ajustar_hit(self, campo, hit, ctx, visor):
        return dict(hit, dibujo=[])

    def _proporcion(self, clave):
        p = self._panel
        if self._sincronizando or not p.valores.get("mantener_proporcion") or not getattr(self, "_prop", None):
            return
        try:
            valor = p.ctx.evaluar(p.valores[clave])
        except ValueError:
            return
        self._sincronizando = True
        try:
            p.set_valor("alto" if clave == "ancho" else "ancho",
                        f"{valor * self._prop if clave == 'ancho' else valor / self._prop:.12g} mm")
        finally:
            self._sincronizando = False

    def construir(self, v, ctx):
        from ...nucleo.calcomanias import superficie
        from ...timeline import entidades
        proporcion_anterior = getattr(self, "_prop", None)
        op = super().construir(v, ctx)
        if self._prop != proporcion_anterior and getattr(self, "_panel", None) is not None:
            self._proporcion("ancho")
        e = entidades.resolver(op.p["plano"], ctx.estado)
        malla = superficie(e.forma, centrada=ctx.op.p.get("centrada", False) if ctx.op else True)
        ancho = ctx.evaluar(v["ancho"])
        if ancho == 0:
            ancho = min(malla["tamano"][0], malla["tamano"][1] / self._prop) * 0.9
            if getattr(self, "_panel", None) is not None:
                self._panel.set_valor("ancho", f"{ancho:.12g} mm")
        op.p.update(ancho=f"{ancho:.12g} mm", alto=v["alto"], encadenar=v["encadenar"],
                    escala=v["escala"],
                    mantener_proporcion=v["mantener_proporcion"], voltear_v=v["voltear_v"],
                    usar_opacidad=v.get("usar_opacidad", True),
                    centrada=ctx.op.p.get("centrada", False) if ctx.op else True)
        return op

    def desde_op(self, op, ctx):
        self._b64, self._prop = op.p["imagen"], op.p["proporcion"]
        valores = super().desde_op(op, ctx)
        valores["alto"] = (f"{ctx.evaluar(op.p['ancho']) * self._prop:.12g} mm"
                           if op.p["mantener_proporcion"] else op.p["alto"])
        return valores

    def manipuladores(self, ctx, v):
        from .. import manipuladores as mp
        from ...nucleo.calcomanias import superficie
        from ...timeline import entidades
        if not v.get("plano"):
            return []
        e = entidades.resolver(v["plano"][0]["ref"], ctx.estado)
        pl = superficie(e.forma, centrada=ctx.op.p.get("centrada", False) if ctx.op else True)["plano"]
        dx, dy = ctx.evaluar(v["dx"]), ctx.evaluar(v["dy"])
        o = pl.a_3d(dx, dy)
        return [mp.PosicionCalcomania(o, pl),
                mp.FlechaCalcomania("dx", o, pl.u, pl.v),
                mp.FlechaCalcomania("dy", o, pl.u, pl.v),
                mp.GiroCalcomania("angulo", o, pl.normal, pl.v, caja=True),
                mp.EscalaCalcomania(o, pl.u, pl.v),
                mp.Volteo("voltear", o, pl.u, pl.v), mp.Volteo("voltear_v", o, pl.u, pl.v)]


registrar(InsertarDXF, InsertarSVG, VectorizarImagen, Lienzo, Calcomania)
