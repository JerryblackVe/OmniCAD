# -*- coding: utf-8 -*-
"""
INSERTAR › Insertar SVG / Insertar DXF / Vectorizar imagen con un boceto ABIERTO (Fusion: SLD-INS-SVG y
SLD-INS-DXF dentro del entorno de boceto).

Fuera de un boceto, esos comandos (`comandos/insertar.py`) piden un plano o una cara y crean un boceto nuevo.
Con un boceto abierto, Fusion inserta el dibujo en ESE boceto, sin cambiar de plano. `InsertarEnBoceto`
envuelve al comando original: usa sus mismos campos (menos «Plano/cara»), su lectura del archivo y su
transformación (escala, desplazamiento, giro, volteos), muestra la vista previa sobre el plano del boceto y,
al aceptar, suma las curvas al boceto abierto en UN paso de deshacer del boceto (`Lienzo.aplicar_cambio`).
No agrega un paso al timeline: el boceto se guarda al terminarlo, como cualquier otro cambio del boceto.
"""
from pathlib import Path

import numpy as np

from ..comando import Comando, ErrorComando, Info
from .insertar import _InsertarArchivo2D

CAPA = "previa_insertar"
COLOR_PREVIA = (0.95, 0.55, 0.10)


def admite(comando):
    """¿El comando se puede usar dentro de un boceto abierto (archivo 2D → curvas del boceto)?"""
    return isinstance(comando, _InsertarArchivo2D)


class InsertarEnBoceto(Comando):
    """El comando de insertar archivo 2D, apuntado al boceto abierto (`lienzo`, el editor del boceto)."""
    SIN_OP = True
    EN_BOCETO_ABIERTO = True        # la ventana lo cierra si el boceto se termina con el panel abierto

    def __init__(self, base, lienzo):
        self.base, self.lienzo = base, lienzo
        self.CLAVE, self.TITULO, self.ICONO = base.CLAVE, base.TITULO, base.ICONO
        self.AYUDA = base.AYUDA
        self._clave, self._prims = None, None
        self._muestras_clave, self._muestras, self._caja = None, None, None

    # ------------------------------------------------------------ campos
    def campos(self, ctx):
        return [c for c in self.base.campos(ctx) if c.clave != "plano"] + [
            Info("destino", "Boceto", lambda _v, _c: "Se suma al boceto abierto (en su plano).")]

    def manipuladores(self, ctx, v):
        """El boceto abierto ya fija el plano: las asas no dependen de un campo de selección inexistente."""
        from .. import manipuladores as mp
        from .comunes import evaluar_o_cero
        return mp.asas_imagen(self.lienzo.plano, evaluar_o_cero(ctx, v.get("dx")),
                             evaluar_o_cero(ctx, v.get("dy")), escala="escala" in v,
                             volteo=("voltear_h", "voltear_v"))

    # ------------------------------------------------------------ datos
    def primitivas(self, v):
        """Primitivas del archivo, leídas una sola vez mientras no cambien el archivo ni el filtro."""
        ruta = (v.get("archivo") or "").strip()
        if not ruta or not Path(ruta).is_file():
            raise ErrorComando("Elegí el archivo (Archivo › ruta completa).")
        clave = (ruta, Path(ruta).stat().st_mtime, self.base.clave_filtro(v))
        if self._clave != clave:
            try:
                self._prims = self.base.leer(ruta, v)
            except (ValueError, OSError) as e:
                raise ErrorComando(f"No se pudo leer el archivo: {e}") from e
            self._clave = clave
        return self._prims

    def boceto_previo(self, v, ctx):
        """Boceto suelto con lo que se va a insertar (en coordenadas del boceto abierto)."""
        from ...io_archivos.boceto_archivos import boceto_desde_primitivas
        from ...api.herramientas_boceto import _exigir_tamano
        prims = self.primitivas(v)
        try:
            b = boceto_desde_primitivas(prims, **self.base.transformacion(v, ctx))
            _exigir_tamano(b)
            return b
        except ValueError as e:
            raise ErrorComando(str(e)) from e

    def segmentos_previa(self, v, ctx):
        """Muestras cacheadas y una matriz visual; mover un asa no reconstruye bocetos ni perfiles OCC."""
        from ...io_archivos.boceto_archivos import boceto_desde_primitivas, caja_primitivas, _transformacion
        from ...restricciones.boceto import puntos_primitiva
        from ..visor3d import _segmentos
        prims = self.primitivas(v)
        if self._muestras_clave != self._clave:
            b = boceto_desde_primitivas(prims)
            self._muestras = _segmentos([np.asarray(puntos_primitiva(p, 32), float)
                                       for p in b.geometria(incluir_construccion=True)]).astype(float)[:, :2]
            self._caja = caja_primitivas(prims)
            self._muestras_clave = self._clave
        tr = self.base.transformacion(v, ctx)
        escala = tr.get("escala", 1.)
        if tr.get("ancho") is not None:
            if self._caja is None or self._caja[1][0] - self._caja[0][0] <= 1e-12 or tr["ancho"] <= 0:
                raise ErrorComando("El ancho tiene que ser positivo y el dibujo debe tener ancho.")
            escala = tr["ancho"] / (self._caja[1][0] - self._caja[0][0])
        if escala <= 0:
            raise ErrorComando("La escala tiene que ser positiva.")
        centro = tuple((a + b) / 2 for a, b in zip(*self._caja, strict=True)) if self._caja else (0., 0.)
        f = _transformacion(escala, tr["desplazamiento"], tr["angulo"],
                           (tr.get("voltear_h", False), tr.get("voltear_v", False)), centro)
        origen = np.asarray(f((0., 0.)))
        matriz = np.column_stack((np.asarray(f((1., 0.))) - origen, np.asarray(f((0., 1.))) - origen))
        uv = self._muestras @ matriz.T + origen
        if not np.isfinite(uv).all() or abs(uv).max(initial=0) > 1e6:
            raise ErrorComando("El dibujo transformado supera 1 km desde el origen del boceto.")
        plano = self.lienzo.plano
        return plano.origen + uv[:, :1] * plano.u + uv[:, 1:] * plano.v

    # ------------------------------------------------------------ panel (comando sin paso propio)
    def construir(self, v, ctx):
        return None

    def mostrar(self, v, ctx):
        visor = getattr(ctx.ventana, "visor", None)
        if visor is None:
            self.boceto_previo(v, ctx)          # sin ventana: solo valida
            return
        try:
            segs = self.segmentos_previa(v, ctx)
        except (ErrorComando, ValueError):
            visor.set_capa(CAPA, None)
            raise
        visor.set_capa(CAPA, [("lineas", segs, COLOR_PREVIA, 1.5)] if len(segs) else None)

    def aplicar(self, v, ctx):
        """Suma el dibujo al boceto abierto, en un solo paso de deshacer del boceto."""
        from ...io_archivos.boceto_archivos import boceto_desde_primitivas
        lz = self.lienzo
        prims = self.primitivas(v)
        transformacion = self.base.transformacion(v, ctx)
        self.boceto_previo(v, ctx)               # valida antes de tocar el boceto (escala, archivo sin geometría)
        antes = len(lz.b.curvas)
        objetos_antes = set(lz.b.objetos)
        eje, lz.eje = lz.eje, False              # «línea central» activa no convierte el dibujo en ejes
        try:
            ok = lz.aplicar_cambio(lambda: boceto_desde_primitivas(prims, destino=lz.b, **transformacion),
                                   anclar=not getattr(prims, "como_objeto", False))
        finally:
            lz.eje = eje
        if not ok:
            raise ErrorComando("No se pudo sumar el dibujo al boceto (entra en conflicto con sus restricciones).")
        self.agregadas = len(lz.b.curvas) - antes
        from ...restricciones import objetos
        nuevos = [i for i in objetos.raices(lz.b) if i not in objetos_antes]
        if nuevos:
            lz.seleccion = nuevos
            lz._notificar_seleccion()
            lz.update()

    def al_cerrar(self, ctx):
        visor = getattr(ctx.ventana, "visor", None)
        if visor is not None:
            visor.set_capa(CAPA, None)
