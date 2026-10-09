# -*- coding: utf-8 -*-
"""Comandos de la pestaña CHAPA (Sheet Metal) con diálogo al estilo Fusion. Las medidas que «anulan la regla»
son campos de texto: vacíos = el valor de la regla del cuerpo."""
from pathlib import Path

import numpy as np

from ...nucleo import chapa as ch
from ...timeline.ops_chapa import (DIRECCIONES_CONTORNO, MODOS_DESGARRO, UBICACIONES_PATRON, OpConvertirChapa,
                                   OpDesgarro, OpDesplegar, OpDobladillo, OpPatronPlano, OpPestana, OpPlegar,
                                   OpUnirPlegando, es_chapa, exportar_dxf, modelo_actual)
from ...timeline.parametros import ANGULO, ESCALAR, LONGITUD
from ..comando import (Casilla, Comando, ErrorComando, Expresion, Info, Opciones, Seleccion, Texto, exigir,
                       hit_desde_ref, hits, refs)
from . import registrar

REGLAS = {n: n for n in ch.REGLAS}
CARA_PLANA = {"cara_plana"}


def _con_chapa(ctx):
    if any(es_chapa(c) for c in ctx.estado.cuerpos.values()):
        return None
    return "Primero creá un cuerpo de chapa (Pestaña base o de contorno, o Convertir a chapa)."


def _hit(ref, estado, punto=None):
    if not ref:
        return []
    h = hit_desde_ref(ref, estado)
    if punto is not None:
        h["punto"] = np.asarray(punto, float)
    return [h]


def _punto(h):
    p = h.get("punto")
    return None if p is None else [float(x) for x in np.asarray(p, float)]


def _cara_con_punto(v, clave, texto):
    h = exigir(v, clave, texto)[0]
    return h["ref"], _punto(h)


def _validar(ctx, v, claves, tipo=LONGITUD):
    for k in claves:
        if (v.get(k) or "").strip():
            ctx.evaluar(v[k], tipo)


def _cuerpo_de(v, clave="cuerpo"):
    sel = v.get(clave) or []
    return sel[0]["ref"].get("cuerpo") if sel else None


def _texto_regla(r):
    alivio = ch.FORMAS_ALIVIO[r["alivio_forma"]].lower()
    return (f"{r['nombre']}: espesor {r['espesor']:.4g} mm · radio {r['radio']:.4g} mm · K {r['k']:.3g}\n"
            f"alivio {alivio} {r['alivio_ancho']:.3g} × {r['alivio_profundidad']:.3g} mm · esquina "
            f"{ch.FORMAS_ESQUINA[r['esquina_forma']].lower()}")


def _texto_resumen(m):
    r = ch.resumen(m)
    return (f"Patrón plano {r['ancho']:.4g} × {r['alto']:.4g} mm · área {r['area']:.6g} mm²\n"
            f"{r['pliegues']} pliegue(s) · espesor {r['espesor']:.4g} mm")


# ---------------------------------------------------------------- reglas
class ReglasChapa(Comando):
    """Reglas de chapa [SM-RULES-REF]: cambia la regla del cuerpo elegido (en la operación que lo creó, como
    cambiar la regla del componente en Fusion: se recalcula todo lo que sigue)."""
    CLAVE, TITULO, ICONO, ATAJO = "reglas_chapa", "Reglas de chapa", "reglas_chapa", None
    AYUDA = "Espesor, radio de plegado, factor K y alivios del cuerpo de chapa elegido."
    SIN_OP, PREVIA = True, False
    verificar = staticmethod(_con_chapa)
    NUMERICOS = ("espesor", "radio", "k", "alivio_ancho", "alivio_profundidad", "esquina_tam", "separacion")

    def campos(self, ctx):
        esquina = lambda v: v.get("esquina_forma") in ("redondo", "cuadrado")  # noqa: E731
        return [Seleccion("cuerpo", "Cuerpo de chapa", {"cuerpo"}),
                Info("actual", "Regla actual", self._actual),
                Opciones("regla", "Regla de la biblioteca", {"": "La actual", **REGLAS}),
                Texto("espesor", "Espesor (vacío = sin cambio)"), Texto("radio", "Radio de plegado"),
                Texto("k", "Factor K"),
                Opciones("alivio_forma", "Forma del alivio de plegado", {"": "Sin cambio", **ch.FORMAS_ALIVIO}),
                Texto("alivio_ancho", "Ancho del alivio"), Texto("alivio_profundidad", "Profundidad del alivio"),
                Opciones("esquina_forma", "Alivio de esquina (2 pliegues)", {"": "Sin cambio", **ch.FORMAS_ESQUINA}),
                Texto("esquina_tam", "Tamaño del alivio de esquina", visible_si=esquina),
                Texto("separacion", "Separación (desgarros)"),
                Casilla("restablecer", "Volver a los valores de la regla")]

    def _origen(self, v, ctx):
        cid = _cuerpo_de(v)
        if cid is None:
            raise ErrorComando("Elegí el cuerpo de chapa.")
        c = ctx.estado.cuerpos.get(cid)
        if c is None or not es_chapa(c):
            raise ErrorComando("El cuerpo elegido no es de chapa.")
        op_id = c.chapa.get("op_regla")
        try:
            return c, ctx.doc.operacion(op_id)
        except ValueError as e:
            raise ErrorComando("No se encontró la operación que tiene la regla de este cuerpo.") from e

    def _actual(self, v, ctx):
        if not v.get("cuerpo"):
            return "Elegí un cuerpo de chapa."
        return _texto_regla(self._origen(v, ctx)[0].chapa["regla"])

    def _nueva(self, v, ctx):
        c, op = self._origen(v, ctx)
        ajustes = {} if v.get("restablecer") else dict(op.p.get("ajustes") or {})
        for k in self.NUMERICOS + ("alivio_forma", "esquina_forma"):
            texto = (v.get(k) or "").strip()
            if texto:
                ajustes[k] = texto
        if op.TIPO == "convertir_chapa" and "espesor" in ajustes:
            raise ErrorComando("El espesor de una chapa convertida es el medido: no se puede cambiar.")
        nombre = v.get("regla") or op.p.get("regla") or ch.REGLA_DEFECTO
        valores = {k: x if k in ("alivio_forma", "esquina_forma") else
                   ctx.evaluar(x, ESCALAR if k == "k" else LONGITUD) for k, x in ajustes.items()}
        if op.TIPO == "convertir_chapa":
            valores["espesor"] = c.chapa["regla"]["espesor"]
        try:
            ch.regla(nombre, **valores)
        except RuntimeError as e:          # geo.ErrorGeometria: valores fuera de rango
            raise ErrorComando(str(e)) from e
        return op.__class__(op.id, op.nombre, op.suprimida, **dict(op.p, regla=nombre, ajustes=ajustes))

    def construir(self, v, ctx):
        return None

    def mostrar(self, v, ctx):
        if v.get("cuerpo"):
            self._nueva(v, ctx)

    def aplicar(self, v, ctx):
        nueva = self._nueva(v, ctx)
        if ctx.ventana is not None:
            ctx.ventana._reemplazar(nueva)
        else:
            ctx.doc.reemplazar(nueva.id, nueva)


# ---------------------------------------------------------------- pestaña
class Pestana(Comando):
    """Pestaña [SM-REF-BASE-EDGE-CONTOUR-FLANGE]: base (perfiles cerrados), de arista (aristas de chapa) o de
    contorno (perfil abierto)."""
    CLAVE, TITULO, ICONO, ATAJO = "pestana", "Pestaña", "pestana", None
    AYUDA = "Crea chapa desde un perfil cerrado (base) o abierto (contorno), o agrega pestañas en aristas de chapa."
    CLASE_OP = OpPestana
    TIPO_DEFECTO = None

    def campos(self, ctx):
        def es(*tipos):
            return lambda v: v.get("tipo") in tipos

        def arista_y(clave, *valores):
            return lambda v: v.get("tipo") == "arista" and v.get(clave) in valores

        def anula(*tipos):
            return lambda v: v.get("tipo") in tipos and bool(v.get("anular"))
        defecto = self.TIPO_DEFECTO or ("arista" if _con_chapa(ctx) is None else "base")
        return [
            Opciones("tipo", "Tipo", {"base": ("Pestaña base", "pestana"), "arista": ("Pestaña de arista", "pestana"),
                                      "contorno": ("Pestaña de contorno", "pestana_contorno")}, defecto),
            Seleccion("perfiles", "Perfiles", {"perfil"}, maximo=None, visible_si=es("base")),
            Seleccion("curvas", "Perfil abierto", {"curva_boceto"}, maximo=None, visible_si=es("contorno"),
                      ayuda="Líneas y arcos tangentes de un boceto, en cadena abierta."),
            Seleccion("aristas", "Aristas", {"arista_lineal"}, maximo=None, visible_si=es("arista"),
                      ayuda="Aristas rectas del borde de la cara de arriba o de abajo de la chapa."),
            Expresion("distancia", "Distancia", "20 mm", visible_si=es("contorno")),
            Opciones("direccion", "Dirección", DIRECCIONES_CONTORNO, visible_si=es("contorno")),
            Expresion("distancia2", "Distancia 2", "10 mm",
                      visible_si=lambda v: v.get("tipo") == "contorno" and v.get("direccion") == "dos_lados"),
            Opciones("orientacion", "Orientación", ch.ORIENTACIONES, visible_si=es("base", "contorno")),
            Expresion("altura", "Altura", "20 mm", visible_si=es("arista")),
            Expresion("angulo", "Ángulo", "90 deg", ANGULO, visible_si=es("arista")),
            Opciones("referencia", "Referencia de altura", ch.REFERENCIAS_ALTURA, visible_si=es("arista")),
            Opciones("posicion", "Posición del pliegue", ch.POSICIONES, visible_si=es("arista")),
            Opciones("ancho", "Tipo de ancho", ch.TIPOS_ANCHO, visible_si=es("arista")),
            Expresion("ancho_distancia", "Ancho", "20 mm", visible_si=arista_y("ancho", "simetrico")),
            Expresion("ancho1", "Distancia 1", "10 mm", visible_si=arista_y("ancho", "dos_lados")),
            Expresion("ancho2", "Distancia 2", "10 mm", visible_si=arista_y("ancho", "dos_lados")),
            Casilla("invertir", "Invertir", visible_si=es("arista")),
            Opciones("regla", "Regla de chapa", REGLAS, ch.REGLA_DEFECTO, visible_si=es("base", "contorno")),
            Casilla("anular", "Anular reglas"),
            Texto("espesor", "Espesor (vacío = regla)", visible_si=anula("base", "contorno")),
            Texto("k", "Factor K (vacío = regla)", visible_si=anula("base", "contorno")),
            Texto("radio", "Radio de plegado (vacío = regla)", visible_si=anula("base", "contorno", "arista")),
            Opciones("alivio_forma", "Forma del alivio", {"": "Según la regla", **ch.FORMAS_ALIVIO},
                     visible_si=anula("arista")),
            Texto("alivio_ancho", "Ancho del alivio (vacío = regla)", visible_si=anula("arista")),
            Texto("alivio_profundidad", "Profundidad del alivio (vacío = regla)", visible_si=anula("arista")),
        ]

    def construir(self, v, ctx):
        tipo = v.get("tipo") or "base"
        anular = bool(v.get("anular"))
        p = {"tipo": tipo, "anular": anular}
        if tipo == "base":
            p["perfiles"] = refs(v, "perfiles") or exigir(v, "perfiles", "Seleccioná uno o más perfiles cerrados.")
        elif tipo == "contorno":
            p["curvas"] = refs(v, "curvas") or exigir(v, "curvas", "Seleccioná las curvas del perfil abierto.")
            ctx.evaluar(v["distancia"])
            p.update(distancia=v["distancia"], direccion=v["direccion"], distancia2=v["distancia2"])
        else:
            p["aristas"] = refs(v, "aristas") or exigir(v, "aristas", "Seleccioná las aristas de chapa.")
            ctx.evaluar(v["altura"])
            ctx.evaluar(v["angulo"], ANGULO)
            p.update({k: v[k] for k in ("altura", "angulo", "referencia", "posicion", "ancho", "ancho_distancia",
                                        "ancho1", "ancho2", "invertir")})
            if anular:
                _validar(ctx, v, ("radio", "alivio_ancho", "alivio_profundidad"))
                p.update({k: (v.get(k) or "").strip() for k in ("radio", "alivio_forma", "alivio_ancho",
                                                                "alivio_profundidad")})
        if tipo in ("base", "contorno"):
            p.update(orientacion=v["orientacion"], regla=v["regla"])
            if anular:
                _validar(ctx, v, ("espesor", "radio"))
                _validar(ctx, v, ("k",), ESCALAR)
                p["ajustes"] = {k: v[k].strip() for k in ("espesor", "radio", "k") if (v.get(k) or "").strip()}
        return self.crear_op(OpPestana, v, ctx, **p)

    def desde_op(self, op, ctx):
        v = dict(op.p, perfiles=hits(op.p.get("perfiles"), ctx.estado), curvas=hits(op.p.get("curvas"), ctx.estado),
                 aristas=hits(op.p.get("aristas"), ctx.estado))
        if op.p.get("tipo") in ("base", "contorno"):
            ajustes = op.p.get("ajustes") or {}
            v.update(espesor=ajustes.get("espesor", ""), radio=ajustes.get("radio", ""), k=ajustes.get("k", ""),
                     anular=bool(ajustes))
        return v


class PestanaContorno(Pestana):
    """Pestaña de contorno [Contour Flange]: el mismo comando Pestaña, con el tipo contorno elegido."""
    CLAVE, TITULO, ICONO = "pestana_contorno", "Pestaña de contorno", "pestana_contorno"
    AYUDA = "Chapa plegada a partir de un perfil abierto de líneas y arcos, con el radio de la regla en las esquinas."
    TIPO_DEFECTO = "contorno"
    VARIANTE = ("tipo", "contorno")


# ---------------------------------------------------------------- dobladillo, plegar, desplegar
class Dobladillo(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "dobladillo", "Dobladillo", "dobladillo", None
    AYUDA = "Dobla el borde de la chapa sobre sí mismo: plano, abierto o en lágrima."
    CLASE_OP = OpDobladillo
    verificar = staticmethod(_con_chapa)

    def campos(self, ctx):
        return [Seleccion("aristas", "Aristas", {"arista_lineal"}, maximo=None),
                Opciones("tipo", "Tipo", ch.TIPOS_DOBLADILLO),
                Expresion("longitud", "Longitud", "10 mm"),
                Texto("separacion", "Separación (vacío = regla)",
                      visible_si=lambda v: v.get("tipo") in ("abierto", "lagrima")),
                Texto("radio", "Radio (vacío = regla)", visible_si=lambda v: v.get("tipo") == "lagrima"),
                Opciones("posicion", "Posición", {"adyacente": "Adyacente", "tangente": "Tangente"}),
                Casilla("invertir", "Invertir")]

    def construir(self, v, ctx):
        exigir(v, "aristas", "Seleccioná las aristas de chapa.")
        ctx.evaluar(v["longitud"])
        _validar(ctx, v, ("separacion", "radio"))
        return self.crear_op(OpDobladillo, v, ctx, aristas=refs(v, "aristas"), tipo=v["tipo"], longitud=v["longitud"],
                             separacion=(v.get("separacion") or "").strip(), radio=(v.get("radio") or "").strip(),
                             posicion=v["posicion"], invertir=v["invertir"])

    def desde_op(self, op, ctx):
        return dict(op.p, aristas=hits(op.p["aristas"], ctx.estado))


class Plegar(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "plegar", "Plegar", "plegar", None
    AYUDA = "Pliega la chapa por líneas rectas de un boceto dibujado sobre la cara (el lado del clic queda fijo)."
    CLASE_OP = OpPlegar
    verificar = staticmethod(_con_chapa)

    def campos(self, ctx):
        return [Seleccion("cara", "Cara estacionaria", CARA_PLANA,
                          ayuda="Hacé clic del lado de la línea que tiene que quedar quieto."),
                Seleccion("lineas", "Líneas de plegado", {"curva_boceto"}, maximo=None),
                Expresion("angulo", "Ángulo de plegado", "90 deg", ANGULO),
                Opciones("posicion", "Posición de la línea", ch.POSICIONES_LINEA, "centro"),
                Casilla("invertir", "Invertir"), Casilla("anular", "Anular reglas"),
                Texto("radio", "Radio de plegado (vacío = regla)", visible_si=lambda v: bool(v.get("anular")))]

    def construir(self, v, ctx):
        cara, punto = _cara_con_punto(v, "cara", "Seleccioná la cara estacionaria.")
        exigir(v, "lineas", "Seleccioná las líneas de plegado.")
        ctx.evaluar(v["angulo"], ANGULO)
        _validar(ctx, v, ("radio",))
        return self.crear_op(OpPlegar, v, ctx, cara=cara, punto=punto, lineas=refs(v, "lineas"), angulo=v["angulo"],
                             posicion=v["posicion"], invertir=v["invertir"], anular=bool(v.get("anular")),
                             radio=(v.get("radio") or "").strip())

    def desde_op(self, op, ctx):
        return dict(op.p, cara=_hit(op.p["cara"], ctx.estado, op.p.get("punto")),
                    lineas=hits(op.p["lineas"], ctx.estado))


class Desplegar(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "desplegar", "Desplegar", "desplegar", None
    AYUDA = "Endereza pliegues de la chapa (todos o los elegidos); la cara estacionaria queda quieta."
    CLASE_OP = OpDesplegar
    VARIANTE = ("modo", "desplegar")
    verificar = staticmethod(_con_chapa)

    def campos(self, ctx):
        return [Seleccion("cara", "Cara estacionaria", CARA_PLANA),
                Casilla("todos", "Seleccionar todos los pliegues", True),
                Seleccion("pliegues", "Pliegues", {"cara"}, minimo=0, maximo=None,
                          visible_si=lambda v: not v.get("todos"), ayuda="Caras curvas de los pliegues.")]

    def construir(self, v, ctx):
        cara, punto = _cara_con_punto(v, "cara", "Seleccioná la cara estacionaria.")
        if not v.get("todos"):
            exigir(v, "pliegues", "Seleccioná los pliegues a desplegar (o marcá «todos»).")
        return self.crear_op(OpDesplegar, v, ctx, modo="desplegar", cara=cara, punto=punto,
                             todos=bool(v.get("todos")), pliegues=[] if v.get("todos") else refs(v, "pliegues"))

    def desde_op(self, op, ctx):
        return dict(op.p, cara=_hit(op.p["cara"], ctx.estado, op.p.get("punto")),
                    pliegues=hits(op.p.get("pliegues"), ctx.estado))


class Replegar(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "replegar", "Volver a plegar", "plegar", None
    AYUDA = "Vuelve a plegar los pliegues desplegados."
    CLASE_OP = OpDesplegar
    VARIANTE = ("modo", "replegar")
    verificar = staticmethod(_con_chapa)

    def campos(self, ctx):
        return [Seleccion("cuerpo", "Cuerpo de chapa", {"cuerpo"}),
                Seleccion("cara", "Cara estacionaria", CARA_PLANA, minimo=0,
                          ayuda="Opcional: sin cara queda fija la misma que al desplegar.")]

    def nombre_nuevo(self, ctx):
        usados = {o.nombre for o in ctx.doc.operaciones}
        n = 1
        while f"Replegado{n}" in usados:
            n += 1
        return f"Replegado{n}"

    def construir(self, v, ctx):
        cid = _cuerpo_de(v)
        if cid is None:
            raise ErrorComando("Seleccioná el cuerpo de chapa.")
        sel = v.get("cara") or []
        return self.crear_op(OpDesplegar, v, ctx, modo="replegar", cuerpo=cid, cara=sel[0]["ref"] if sel else None,
                             punto=_punto(sel[0]) if sel else None)

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpo=hits([{"tipo": "cuerpo", "cuerpo": op.p["cuerpo"]}] if op.p.get("cuerpo") else [],
                                      ctx.estado),
                    cara=_hit(op.p.get("cara"), ctx.estado, op.p.get("punto")))


# ---------------------------------------------------------------- patrón plano y DXF
class PatronPlano(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "patron_plano", "Crear patrón plano", "patron_plano", None
    AYUDA = "Crea el patrón plano de la chapa (desarrollo exacto con el factor K) como un cuerpo aparte."
    CLASE_OP = OpPatronPlano
    verificar = staticmethod(_con_chapa)

    def campos(self, ctx):
        return [Seleccion("cara", "Cara estacionaria", CARA_PLANA),
                Opciones("ubicacion", "Ubicación", UBICACIONES_PATRON),
                Info("resumen", "Desarrollo", self._resumen)]

    def _resumen(self, v, ctx):
        if not v.get("cara"):
            return "Elegí la cara estacionaria."
        c = ctx.estado.cuerpos.get(v["cara"][0]["ref"].get("cuerpo"))
        return _texto_resumen(modelo_actual(c)) if c is not None and es_chapa(c) else "No es un cuerpo de chapa."

    def construir(self, v, ctx):
        cara, punto = _cara_con_punto(v, "cara", "Seleccioná la cara estacionaria.")
        return self.crear_op(OpPatronPlano, v, ctx, cara=cara, punto=punto, ubicacion=v["ubicacion"])

    def desde_op(self, op, ctx):
        return dict(op.p, cara=_hit(op.p["cara"], ctx.estado, op.p.get("punto")))


class ExportarDXFPatron(Comando):
    """Exportar el patrón plano como DXF [GUID-9C211F95]: contorno exterior, contornos interiores y líneas de
    pliegue (centro y extensión) en capas separadas, en mm."""
    CLAVE, TITULO, ICONO, ATAJO = "exportar_dxf_chapa", "Exportar DXF del patrón plano", "patron_plano", None
    AYUDA = "Guarda el patrón plano de un cuerpo de chapa como DXF para corte láser o plegadora."
    SIN_OP, PREVIA, TEXTO_ACEPTAR = True, False, "Exportar"
    verificar = staticmethod(_con_chapa)

    def campos(self, ctx):
        return [Seleccion("cuerpo", "Cuerpo de chapa o patrón plano", {"cuerpo"}),
                Texto("archivo", "Archivo (vacío = elegir)"),
                Casilla("centros", "Líneas de centro de pliegue", True),
                Casilla("extensiones", "Líneas de extensión de pliegue", False),
                Info("resumen", "Desarrollo", self._resumen)]

    def _cuerpo(self, v, ctx):
        cid = _cuerpo_de(v)
        c = ctx.estado.cuerpos.get(cid) if cid else None
        if c is None or getattr(c, "chapa", None) is None:
            raise ErrorComando("Elegí un cuerpo de chapa (o su patrón plano).")
        return c

    def _resumen(self, v, ctx):
        return _texto_resumen(modelo_actual(self._cuerpo(v, ctx))) if v.get("cuerpo") else "Elegí el cuerpo."

    def construir(self, v, ctx):
        return None

    def mostrar(self, v, ctx):
        if v.get("cuerpo"):
            self._cuerpo(v, ctx)

    def aplicar(self, v, ctx):
        c = self._cuerpo(v, ctx)
        ruta = (v.get("archivo") or "").strip()
        if not ruta:
            from PySide6.QtWidgets import QFileDialog
            ruta, _ = QFileDialog.getSaveFileName(ctx.ventana, "Exportar patrón plano", f"{c.nombre}.dxf",
                                                  "DXF (*.dxf)")
            if not ruta:
                raise ErrorComando("Elegí dónde guardar el DXF.")
        if Path(ruta).suffix.lower() != ".dxf":
            ruta += ".dxf"
        exportar_dxf(ctx.estado, c.id, ruta, bool(v.get("centros")), bool(v.get("extensiones")))


# ---------------------------------------------------------------- convertir, desgarro, unir plegando
class ConvertirChapa(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "convertir_chapa", "Convertir a chapa", "convertir_chapa", None
    AYUDA = "Convierte una placa plana de espesor constante en un cuerpo de chapa (el espesor se mide)."
    CLASE_OP = OpConvertirChapa

    def campos(self, ctx):
        return [Seleccion("cara", "Cara", CARA_PLANA, ayuda="Una cara ancha y plana de la placa."),
                Info("espesor", "Espesor (detectado)", self._espesor),
                Opciones("regla", "Regla plantilla", REGLAS, ch.REGLA_DEFECTO)]

    def _espesor(self, v, ctx):
        if not v.get("cara"):
            return "Elegí una cara."
        h = v["cara"][0]
        c = ctx.estado.cuerpos.get(h["ref"].get("cuerpo"))
        if c is None or h.get("forma") is None:
            return "—"
        return f"{ch.detectar_espesor(c.forma, h['forma']):.4g} mm"

    def construir(self, v, ctx):
        h = exigir(v, "cara", "Seleccioná una cara plana ancha del cuerpo.")[0]
        return self.crear_op(OpConvertirChapa, v, ctx, cara=h["ref"], regla=v["regla"])

    def desde_op(self, op, ctx):
        return dict(op.p, cara=_hit(op.p["cara"], ctx.estado))


class Desgarro(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "desgarro", "Desgarro", "desgarro", None
    AYUDA = "Quita una cara de la chapa (un pliegue o una parte plana) o la corta entre dos puntos del borde."
    CLASE_OP = OpDesgarro
    verificar = staticmethod(_con_chapa)

    def campos(self, ctx):
        puntos = lambda v: v.get("modo") == "puntos"  # noqa: E731
        return [Opciones("modo", "Selección", MODOS_DESGARRO),
                Seleccion("cara", "Cara", {"cara"}, ayuda="En «Puntos», la cara cuyo borde tiene los dos puntos."),
                Seleccion("puntos", "Puntos", {"vertice", "punto", "punto_boceto"}, minimo=2, maximo=2,
                          visible_si=puntos),
                Opciones("lado", "Orientación", ch.ORIENTACIONES, "centro", visible_si=puntos),
                Texto("separacion", "Separación (vacío = regla)", visible_si=puntos)]

    def construir(self, v, ctx):
        cara = exigir(v, "cara", "Seleccioná la cara.")[0]["ref"]
        p = {"modo": v["modo"], "cara": cara}
        if v["modo"] == "puntos":
            if len(v.get("puntos") or []) != 2:
                raise ErrorComando("Seleccioná dos puntos del borde de la cara.")
            _validar(ctx, v, ("separacion",))
            p.update(puntos=refs(v, "puntos"), lado=v["lado"], separacion=(v.get("separacion") or "").strip())
        return self.crear_op(OpDesgarro, v, ctx, **p)

    def desde_op(self, op, ctx):
        return dict(op.p, cara=_hit(op.p["cara"], ctx.estado), puntos=hits(op.p.get("puntos"), ctx.estado))


class UnirPlegando(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "unir_plegando", "Unir plegando", "unir_plegando", None
    AYUDA = "Une dos cuerpos de chapa del mismo espesor con un pliegue entre dos aristas paralelas."
    CLASE_OP = OpUnirPlegando
    verificar = staticmethod(_con_chapa)

    def campos(self, ctx):
        return [Seleccion("aristas", "Aristas", {"arista_lineal"}, minimo=2, maximo=2,
                          ayuda="Una arista de cada cuerpo, del borde de la cara de arriba o de abajo."),
                Casilla("anular", "Anular reglas"),
                Texto("radio", "Radio de plegado (vacío = regla)", visible_si=lambda v: bool(v.get("anular")))]

    def construir(self, v, ctx):
        if len(v.get("aristas") or []) != 2:
            raise ErrorComando("Seleccioná dos aristas, una de cada cuerpo de chapa.")
        _validar(ctx, v, ("radio",))
        return self.crear_op(OpUnirPlegando, v, ctx, aristas=refs(v, "aristas"), anular=bool(v.get("anular")),
                             radio=(v.get("radio") or "").strip())

    def desde_op(self, op, ctx):
        return dict(op.p, aristas=hits(op.p["aristas"], ctx.estado))


registrar(ReglasChapa, Pestana, PestanaContorno, Dobladillo, Plegar, Desplegar, Replegar, PatronPlano,
          ExportarDXFPatron, ConvertirChapa, Desgarro, UnirPlegando)
