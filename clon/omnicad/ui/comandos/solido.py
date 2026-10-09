# -*- coding: utf-8 -*-
"""Comandos de SÓLIDO › CREAR con diálogo al estilo Fusion: Extruir y Revolución."""
import numpy as np

from ...timeline.operaciones import DIRECCIONES, OpExtrusion, OpRevolucion
from ...timeline.parametros import ANGULO, LONGITUD
from ..comando import Casilla, Comando, ErrorComando, Expresion, Opciones, Seleccion, hit_desde_ref, hits, ref1
from . import registrar
from .comunes import (campo_objetivos, campo_operacion, evaluar_o_cero as _evaluar, objetivos, objetivos_desde_op,
                      perfiles_a_params, perfiles_desde_op)


EXTENSIONES = {"distancia": ("Distancia", "ext_distancia"), "objeto": ("Al objeto", "ext_objeto"),
               "todo": ("Todo", "ext_todo")}


class Extruir(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "extruir", "Extruir", "extruir", "E"
    AYUDA = "Agrega profundidad a perfiles de boceto o caras planas: cuerpo nuevo, unir, cortar o intersecar."
    CLASE_OP = OpExtrusion

    def verificar(self, ctx):
        if not ctx.estado.bocetos and not ctx.estado.cuerpos:
            return "Primero creá un boceto con un contorno cerrado (o elegí una cara plana de un cuerpo)."
        return None

    def campos(self, ctx):
        dos = lambda v: v.get("direccion") == "dos_lados"  # noqa: E731
        return [
            Opciones("tipo", "Tipo", {"solida": ("Extruir", "extruir"), "delgada": ("Extrusión delgada", "extruir")}),
            Seleccion("perfiles", "Perfiles", {"perfil", "cara_plana", "curva_boceto"}, maximo=None,
                      ayuda="Perfiles cerrados o caras planas; en la extrusión delgada también curvas abiertas."),
            Opciones("inicio", "Inicio", {"plano": "Plano del perfil", "desfase": "Desfase", "objeto": "Objeto"}),
            Expresion("desfase_inicio", "Desfase", "0 mm", visible_si=lambda v: v.get("inicio") == "desfase"),
            Seleccion("inicio_objeto", "Objeto", {"cara_plana", "plano"}, visible_si=lambda v: v.get("inicio") == "objeto"),
            Opciones("direccion", "Dirección", DIRECCIONES),
            Opciones("medida", "Medida", {"mitad": "Media longitud", "total": "Longitud total"},
                     visible_si=lambda v: v.get("direccion") == "simetrica"),
            Opciones("extension", "Tipo de extensión", EXTENSIONES),
            Expresion("distancia", "Distancia", "10 mm", visible_si=lambda v: v.get("extension") == "distancia"),
            Seleccion("hasta", "Objeto", {"cara", "plano", "cuerpo"}, visible_si=lambda v: v.get("extension") == "objeto"),
            Opciones("hasta_modo", "Extender", {"cara": "Hasta la cara seleccionada", "cuerpo": "Hasta el cuerpo",
                                                "a_traves": "A través del cuerpo"},
                     visible_si=lambda v: v.get("extension") == "objeto"),
            Expresion("desfase_hasta", "Desfase", "0 mm", visible_si=lambda v: v.get("extension") == "objeto"),
            Casilla("invertir", "Invertir dirección"),
            Expresion("conicidad", "Ángulo de conicidad", "0 deg", ANGULO),
            Expresion("distancia2", "Lado 2: distancia", "10 mm", visible_si=dos),
            Expresion("conicidad2", "Lado 2: conicidad", "0 deg", ANGULO, visible_si=dos),
            Expresion("espesor", "Grosor de pared", "1 mm", visible_si=lambda v: v.get("tipo") == "delgada"),
            Opciones("ubicacion", "Ubicación de pared", {"lado1": "Lado 1", "lado2": "Lado 2", "centro": "Centro"},
                     visible_si=lambda v: v.get("tipo") == "delgada"),
            campo_operacion(),
            campo_objetivos(),
        ]

    def construir(self, v, ctx):
        curvas = [h["ref"] for h in v.get("perfiles") or [] if h["ref"]["tipo"] == "curva_boceto"]
        resto = [h for h in v.get("perfiles") or [] if h["ref"]["tipo"] != "curva_boceto"]
        if curvas and v.get("tipo") != "delgada":
            raise ErrorComando("Las curvas abiertas solo se extruyen con «Extrusión delgada».")
        boceto, perfiles, caras = perfiles_a_params(resto) if resto or not curvas else ("", [], [])
        for clave, tipo in (("distancia", None), ("desfase_inicio", None), ("conicidad", ANGULO)):
            ctx.evaluar(v.get(clave) or "0", tipo or LONGITUD)
        if v.get("extension") == "objeto" and not v.get("hasta"):
            raise ErrorComando("Elegí el objeto hasta donde llega la extrusión.")
        params = {k: v.get(k) for k in ("tipo", "inicio", "desfase_inicio", "direccion", "medida", "extension",
                                         "distancia", "invertir", "conicidad", "distancia2", "conicidad2", "espesor",
                                         "ubicacion", "operacion", "hasta_modo", "desfase_hasta")}
        params.update(boceto=boceto, perfiles=perfiles, caras=caras, curvas=curvas, objetivos=objetivos(v),
                      objetivo="", inicio_objeto=ref1(v, "inicio_objeto"), hasta=ref1(v, "hasta"), simetrica=False)
        return self.crear_op(OpExtrusion, v, ctx, **params)

    def manipuladores(self, ctx, v):
        """Flecha de distancia desde el centro del perfil a lo largo de la normal (la del lado 2 en «Dos
        lados») y el asa de la conicidad en el borde del perfil, como Fusion."""
        from .. import manipuladores as mp
        if v.get("extension") != "distancia":
            return []
        base = mp.base_perfiles(v.get("perfiles"), ctx.estado)
        if base is None:
            return []
        centro, plano, formas = base
        n = mp.unitario(plano.normal) * (-1.0 if v.get("invertir") else 1.0)
        if v.get("inicio") == "desfase":
            centro = centro + n * _evaluar(ctx, v.get("desfase_inicio"))
        direccion = v.get("direccion")
        if direccion == "simetrica":
            return [mp.Flecha("distancia", centro, n, factor=1.0 if v.get("medida") != "total" else 0.5, minimo=0.0)]
        salida = [mp.Flecha("distancia", centro, n)]
        if direccion == "dos_lados":
            salida.append(mp.Flecha("distancia2", centro, -n, minimo=0.0))
        d = _evaluar(ctx, v.get("distancia"))
        lateral = mp.unitario(plano.u)
        borde = mp.punto_borde(formas, centro, lateral)
        borde = borde + n * float((centro - borde) @ n)          # a la altura del inicio (desfase)
        t = n * (-1.0 if d < 0 else 1.0)
        salida.append(mp.Angulo("conicidad", borde, np.cross(t, lateral), t, minimo=-89.0, maximo=89.0,
                                caja="arrastre"))
        return salida

    def previa_vista(self, ctx, v, op):
        """Con «Cortar», Fusion muestra en ROJO el volumen de la extrusión mientras el diálogo está abierto."""
        if op.p.get("operacion") != "cortar":
            return None
        import copy

        from .. import manipuladores as mp
        herramienta = copy.copy(op)
        herramienta.p = dict(op.p, operacion="nuevo", objetivos=[])
        estado, _avisos = ctx.doc.previsualizar(herramienta, ctx.indice)
        return mp.herramientas_rojas([c.forma for k, c in estado.cuerpos.items() if k not in ctx.estado.cuerpos])

    def desde_op(self, op, ctx):
        v = dict(op.p)
        if op.p.get("simetrica"):
            v.update(direccion="simetrica", medida="total")
        v["perfiles"] = perfiles_desde_op(op, ctx.estado) + hits(op.p.get("curvas") or [], ctx.estado)
        v["objetivos"] = objetivos_desde_op(op, ctx.estado)
        for clave in ("inicio_objeto", "hasta"):
            v[clave] = [hit_desde_ref(op.p[clave], ctx.estado)] if op.p.get(clave) else []
        return v


class Revolucion(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "revolucion", "Revolución", "revolucion", None
    AYUDA = "Gira perfiles de boceto o caras planas alrededor de un eje."
    CLASE_OP = OpRevolucion

    def verificar(self, ctx):
        return None if ctx.estado.bocetos or ctx.estado.cuerpos else "Primero creá un boceto con un contorno cerrado."

    def campos(self, ctx):
        return [
            Seleccion("perfiles", "Perfil", {"perfil", "cara_plana"}, maximo=None),
            Seleccion("eje", "Eje", {"eje"}),
            Opciones("extension", "Tipo", {"angulo": "Ángulo", "completa": "Completo"}),
            Opciones("direccion", "Dirección", DIRECCIONES, visible_si=lambda v: v.get("extension") != "completa"),
            Expresion("angulo", "Ángulo", "360 deg", ANGULO, visible_si=lambda v: v.get("extension") != "completa"),
            Expresion("angulo2", "Ángulo 2", "90 deg", ANGULO,
                      visible_si=lambda v: v.get("extension") != "completa" and v.get("direccion") == "dos_lados"),
            Casilla("invertir", "Invertir dirección"),
            campo_operacion(),
            campo_objetivos(),
        ]

    def construir(self, v, ctx):
        boceto, perfiles, caras = perfiles_a_params(v.get("perfiles"))
        eje = ref1(v, "eje")
        if eje is None and boceto:
            # Como Fusion: si el boceto tiene una línea central, es el eje por defecto.
            br = ctx.estado.bocetos.get(boceto)
            central = next((c.id for c in br.boceto.curvas.values() if getattr(c, "eje", False)
                            and c.tipo == "linea"), None) if br else None
            if central is not None:
                eje = {"tipo": "curva_boceto", "boceto": boceto, "curva": central}
        if eje is None:
            raise ErrorComando("Seleccioná el eje de revolución (una línea, arista o eje).")
        ctx.evaluar(v.get("angulo") or "0", ANGULO)
        params = {k: v.get(k) for k in ("extension", "direccion", "angulo", "angulo2", "invertir", "operacion")}
        params.update(boceto=boceto, perfiles=perfiles, caras=caras, eje_ref=eje, eje="v",
                      objetivos=objetivos(v), objetivo="")
        return self.crear_op(OpRevolucion, v, ctx, **params)

    def manipuladores(self, ctx, v):
        """Arco con asa alrededor del eje, a la distancia del centro del perfil (el segundo lado en «Dos
        lados»; en «Simétrica» el asa va a la mitad del ángulo, como el resultado)."""
        from .. import manipuladores as mp
        if v.get("extension") == "completa":
            return []
        base = mp.base_perfiles(v.get("perfiles"), ctx.estado)
        if base is None:
            return []
        try:
            op = self.construir(v, ctx)
            punto, d = op._eje(ctx.estado, base[1])
        except Exception:  # noqa: BLE001 — sin eje todavía no hay manipulador
            return []
        d = mp.unitario(d) * (-1.0 if v.get("invertir") else 1.0)
        if np.linalg.norm(d) < 1e-9:
            return []
        centro = base[0]
        pie = np.asarray(punto, float) + d * float((centro - punto) @ d)
        radio = float(np.linalg.norm(centro - pie))
        radio = radio if radio > 1e-6 else None
        if v.get("direccion") == "simetrica":
            return [mp.Angulo("angulo", pie, d, centro - pie, radio, factor=0.5)]
        salida = [mp.Angulo("angulo", pie, d, centro - pie, radio)]
        if v.get("direccion") == "dos_lados":
            salida.append(mp.Angulo("angulo2", pie, -d, centro - pie, radio))
        return salida

    def desde_op(self, op, ctx):
        v = dict(op.p)
        v["perfiles"] = perfiles_desde_op(op, ctx.estado)
        v["objetivos"] = objetivos_desde_op(op, ctx.estado)
        if op.p.get("eje_ref"):
            v["eje"] = [hit_desde_ref(op.p["eje_ref"], ctx.estado)]
        elif op.p.get("eje") not in ("u", "v", None):
            v["eje"] = [hit_desde_ref({"tipo": "curva_boceto", "boceto": op.p["boceto"], "curva": int(op.p["eje"])},
                                      ctx.estado)]
        else:
            br = ctx.estado.bocetos.get(op.p.get("boceto"))
            v["eje"] = []
            if br is not None:              # eje u/v del boceto: equivale al eje de origen paralelo (si pasa por 0)
                import numpy as np
                d = br.plano.u if op.p["eje"] == "u" else br.plano.v
                nombre = "XYZ"[int(np.argmax(np.abs(d)))]
                if np.allclose(br.plano.origen, 0):
                    v["eje"] = [hit_desde_ref({"tipo": "eje", "id": nombre}, ctx.estado)]
        return v



registrar(Extruir, Revolucion)
