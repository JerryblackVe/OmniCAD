# -*- coding: utf-8 -*-
"""SÓLIDO › CREAR › Engranaje (engranaje recto o helicoidal, par que engrana, cremallera y rueda de cadena) y Eje
(eje escalonado por tramos) con diálogo. Operaciones en `timeline/ops_engranaje.py`; núcleo en
`nucleo/engranajes.py`."""
from ...nucleo import engranajes as en
from ...timeline.operaciones import ErrorOperacion
from ...timeline.ops_engranaje import PERSONALIZADA, TIPOS, TRAMO, OpEje, OpEngranaje, agregar_ensamblaje
from ...timeline.parametros import ANGULO, ESCALAR
from ..comando import Casilla, Comando, Entero, Expresion, Info, Opciones, Seleccion, hit_desde_ref, ref1
from . import registrar
from .comunes import campo_objetivos, campo_operacion, objetivos, objetivos_desde_op

_CLAVES_ENGRANAJE = [k for k in OpEngranaje.PARAMS if k not in ("plano", "centro")]
_CADENAS = {PERSONALIZADA: "Personalizada (paso y rodillo)",
            **{k: f"{k} — paso {p:g} mm, rodillo Ø{d1:g} mm" for k, (p, d1, _b1) in en.CADENAS.items()}}


def _h1(ref, estado):
    return [hit_desde_ref(ref, estado)] if ref else []


def _es(*tipos):
    return lambda v: (v.get("tipo") or "engranaje") in tipos


def _par(v):
    return _es("engranaje")(v) and bool(v.get("par"))


def _cadena_propia(v):
    return _es("rueda_cadena")(v) and v.get("cadena") == PERSONALIZADA


def _params(v):
    """Valores del diálogo → parámetros de OpEngranaje (los que no muestra, como x e y, se conservan)."""
    params = {k: v[k] for k in _CLAVES_ENGRANAJE if k in v and v[k] is not None}
    params.update(plano=ref1(v, "plano"), centro=ref1(v, "centro"), par=bool(v.get("par")) and _es("engranaje")(v))
    return params


def _f(x):
    return f"{x:.4g}"


def _medidas(v, ctx):
    """Texto del campo «Medidas»: diámetros, paso y, en el par, la distancia entre centros (lo que calcula el
    complemento «Spur Gear» de Fusion antes de crear)."""
    op = OpEngranaje("tmp", **_params(v))
    m = op.medidas(ctx)
    tipo = v.get("tipo") or "engranaje"
    if tipo == "rueda_cadena":
        d = en.datos_rueda_cadena(m["paso"], m["rodillo"], m["dientes"])
        texto = (f"Ø primitivo {_f(d['diametro_primitivo'])} · fondo {_f(d['diametro_fondo'])} · exterior "
                 f"{_f(d['diametro_exterior_min'])}–{_f(d['diametro_exterior_max'])} mm")
        if v.get("cadena") in en.CADENAS:
            p, _d1, b1 = en.CADENAS[v["cadena"]]
            texto += f" · ancho de diente ISO {_f(en.ancho_diente_cadena(b1, p))} mm"
        return texto
    if tipo == "cremallera":
        return f"Paso {_f(3.141592653589793 * m['modulo'])} mm · largo {_f(3.141592653589793 * m['modulo'] * m['dientes'])} mm"
    g = en.medidas_engranaje(m["modulo"], m["dientes"], m["angulo_presion"], m["helice"], m["desplazamiento"],
                             m["holgura"], m["juego"])
    texto = (f"Ø primitivo {_f(g['diametro_primitivo'])} · exterior {_f(g['diametro_exterior'])} · fondo "
             f"{_f(g['diametro_fondo'])} mm")
    so = en.socavado(m["dientes"], m["angulo_presion"], m["desplazamiento"], m["helice"])
    if so["socavado"]:
        texto += f" · socavado (z mín {so['dientes_minimos']})"
    if v.get("par"):
        d = en.datos_par(m["modulo"], m["dientes"], m["dientes2"], m["angulo_presion"], m["desplazamiento"],
                         m["desplazamiento2"], m["helice"], m["holgura"])
        texto += (f"\nDistancia entre centros {_f(d['distancia_centros'])} mm · relación 1:{_f(d['relacion'])} · "
                  f"recubrimiento {d['recubrimiento']:.2f}")
    return texto


class Engranaje(Comando):
    CLAVE, TITULO, ICONO = "engranaje", "Engranaje", "engranaje_3d"
    AYUDA = ("Engranaje de evolvente recto o helicoidal (o un par que engrana, con su unión y vínculo de "
             "movimiento), cremallera o rueda de cadena ISO 606, sobre un plano y un punto.")
    CLASE_OP = OpEngranaje

    def __init__(self):
        self._ultima, self._ensamblar = None, False

    def campos(self, ctx):
        campos = [
            Opciones("tipo", "Tipo", TIPOS),
            Seleccion("plano", "Plano", {"plano", "cara_plana"}, minimo=0, ayuda="Sin selección: el plano XY."),
            Seleccion("centro", "Centro", {"punto", "vertice"}, minimo=0, ayuda="Sin selección: el origen del plano."),
            Opciones("cadena", "Cadena (ISO 606)", _CADENAS, "08B", visible_si=_es("rueda_cadena")),
            Expresion("paso", "Paso de la cadena", "12.7 mm", visible_si=_cadena_propia),
            Expresion("rodillo", "Diámetro del rodillo", "8.51 mm", visible_si=_cadena_propia),
            Expresion("modulo", "Módulo", "2 mm", visible_si=_es("engranaje", "cremallera")),
            Expresion("dientes", "Dientes", "20", ESCALAR),
            Expresion("angulo_presion", "Ángulo de presión", "20 deg", ANGULO, visible_si=_es("engranaje", "cremallera")),
            Expresion("ancho", "Ancho", "10 mm"),
            Expresion("helice", "Ángulo de hélice", "0 deg", ANGULO, visible_si=_es("engranaje"),
                      ayuda="0 = recto; positivo = hélice a derechas (en el par, el segundo va al revés)."),
            Expresion("desplazamiento", "Desplazamiento de perfil (x)", "0", ESCALAR, visible_si=_es("engranaje")),
            Expresion("holgura", "Holgura de fondo (× módulo)", "0.25", ESCALAR,
                      visible_si=_es("engranaje", "cremallera")),
            Expresion("juego", "Juego", "0 mm", visible_si=_es("engranaje", "cremallera"),
                      ayuda="Juego entre dientes del par en el primitivo: cada diente adelgaza la mitad."),
            Expresion("alto", "Alto hasta la línea primitiva", "10 mm", visible_si=_es("cremallera")),
            Expresion("agujero", "Agujero central (Ø; 0 = sin)", "0 mm", visible_si=_es("engranaje", "rueda_cadena")),
            Expresion("giro", "Giro", "0 deg", ANGULO),
            Casilla("par", "Par de engranajes", visible_si=_es("engranaje"),
                    ayuda="Crea también el segundo engranaje a la distancia entre centros, girado para que engranen."),
            Expresion("dientes2", "Dientes del segundo", "40", ESCALAR, visible_si=_par),
            Expresion("desplazamiento2", "Desplazamiento del segundo (x)", "0", ESCALAR, visible_si=_par),
            Expresion("agujero2", "Agujero del segundo (Ø)", "0 mm", visible_si=_par),
            Expresion("direccion", "Dirección del segundo", "0 deg", ANGULO, visible_si=_par),
        ]
        if ctx.op is None:              # al editar, el ensamblaje ya está (o no se quiso): no se vuelve a crear
            campos.append(Casilla("ensamblar", "Crear unión y vínculo de movimiento", True, visible_si=_par,
                                  ayuda="Un componente por engranaje, una unión de revolución en cada eje y el "
                                        "vínculo de movimiento con la relación de dientes."))
        campos.append(Info("medidas", "Medidas", _medidas))
        return campos

    def construir(self, v, ctx):
        op = self.crear_op(OpEngranaje, v, ctx, **_params(v))
        self._ultima, self._ensamblar = op, bool(v.get("ensamblar")) and _par(v)
        return op

    def desde_op(self, op, ctx):
        return dict(op.p, plano=_h1(op.p.get("plano"), ctx.estado), centro=_h1(op.p.get("centro"), ctx.estado))

    def al_cerrar(self, ctx):
        """Con «Par de engranajes» y «Crear unión y vínculo», el ensamblaje se agrega apenas la ventana agrega el
        engranaje (después de este cierre); si se canceló, el paso no está en el documento y no se hace nada."""
        op, ensamblar = self._ultima, self._ensamblar
        self._ultima, self._ensamblar = None, False
        if ctx.op is not None or op is None or not ensamblar:
            return
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self.ensamblar_si_aceptado(ctx, op))

    @staticmethod
    def ensamblar_si_aceptado(ctx, op):
        """Agrega componentes, uniones y vínculo del par `op` si quedó en el documento sin error (mismo paso de
        deshacer que el engranaje). Devuelve los pasos creados o None."""
        doc = ctx.doc
        if not any(o is op for o in doc.operaciones) or doc.resultado(op.id).estado == "error":
            return None
        try:
            pasos = agregar_ensamblaje(doc, op.id, un_paso=True)
        except ErrorOperacion as e:
            aviso = getattr(ctx.ventana, "mensaje", None)
            if aviso is not None:
                aviso(f"No se pudo ensamblar el par: {e}", 8000)
            return None
        aviso = getattr(ctx.ventana, "mensaje", None)
        if aviso is not None:
            aviso("Par de engranajes: se crearon los componentes, las uniones de revolución y el vínculo de "
                  "movimiento (ENSAMBLAR › Accionar uniones los mueve).", 8000)
        return pasos


# ---------------------------------------------------------------- eje escalonado
MAX_TRAMOS = 8
_DEFECTOS = [("20 mm", "30 mm", "chaflan", "ninguno"), ("30 mm", "20 mm", "ninguno", "ninguno"),
             ("16 mm", "25 mm", "ninguno", "chaflan")] + [("12 mm", "10 mm", "ninguno", "ninguno")] * (MAX_TRAMOS - 3)


def _hasta(i):
    return lambda v: int(v.get("n") or 0) >= i


def _con_remate(i, lado):
    return lambda v: int(v.get("n") or 0) >= i and (v.get(f"{lado}{i}") or "ninguno") != "ninguno"


class Eje(Comando):
    CLAVE, TITULO, ICONO = "eje_escalonado", "Eje", "eje_escalonado"
    AYUDA = ("Eje escalonado por tramos: diámetro, largo y chaflán o empalme en cada extremo (asistente de ejes). "
             "Sale del punto por la normal del plano.")
    CLASE_OP = OpEje

    def campos(self, ctx):
        campos = [Seleccion("plano", "Plano", {"plano", "cara_plana"}, minimo=0, ayuda="Sin selección: el plano XY."),
                  Seleccion("centro", "Comienzo", {"punto", "vertice"}, minimo=0,
                            ayuda="Sin selección: el origen del plano."),
                  Entero("n", "Cantidad de tramos", 3, 1, MAX_TRAMOS)]
        for i, (d, largo, ini, fin) in enumerate(_DEFECTOS, 1):
            campos += [
                Expresion(f"d{i}", f"Tramo {i}: diámetro", d, visible_si=_hasta(i)),
                Expresion(f"l{i}", f"Tramo {i}: largo", largo, visible_si=_hasta(i)),
                Opciones(f"ini{i}", f"Tramo {i}: remate al inicio", en.REMATES, ini, visible_si=_hasta(i)),
                Expresion(f"mi{i}", f"Tramo {i}: medida al inicio", "1 mm", visible_si=_con_remate(i, "ini")),
                Opciones(f"fin{i}", f"Tramo {i}: remate al final", en.REMATES, fin, visible_si=_hasta(i)),
                Expresion(f"mf{i}", f"Tramo {i}: medida al final", "1 mm", visible_si=_con_remate(i, "fin")),
            ]
        return campos + [campo_operacion(), campo_objetivos()]

    def construir(self, v, ctx):
        n = max(1, min(MAX_TRAMOS, int(v.get("n") or 1)))
        tramos = []
        for i in range(1, n + 1):
            tramo = {"diametro": v[f"d{i}"], "largo": v[f"l{i}"], "inicio": v.get(f"ini{i}") or "ninguno",
                     "fin": v.get(f"fin{i}") or "ninguno"}
            tramo["medida_inicio"] = v.get(f"mi{i}") or TRAMO["medida_inicio"]
            tramo["medida_fin"] = v.get(f"mf{i}") or TRAMO["medida_fin"]
            tramos.append(tramo)
        return self.crear_op(OpEje, v, ctx, plano=ref1(v, "plano"), centro=ref1(v, "centro"), x=v.get("x", "0 mm"),
                             y=v.get("y", "0 mm"), tramos=tramos, operacion=v.get("operacion") or "nuevo",
                             objetivos=objetivos(v))

    def desde_op(self, op, ctx):
        v = {"plano": _h1(op.p.get("plano"), ctx.estado), "centro": _h1(op.p.get("centro"), ctx.estado),
             "x": op.p.get("x", "0 mm"), "y": op.p.get("y", "0 mm"), "operacion": op.p.get("operacion", "nuevo"),
             "objetivos": objetivos_desde_op(op, ctx.estado)}
        tramos = [t for t in op.p.get("tramos") or [] if isinstance(t, dict)][:MAX_TRAMOS]
        v["n"] = max(1, len(tramos))
        for i, t in enumerate(tramos, 1):
            t = dict(TRAMO, **{k: x for k, x in t.items() if k in TRAMO})
            v.update({f"d{i}": t["diametro"], f"l{i}": t["largo"], f"ini{i}": t["inicio"], f"mi{i}": t["medida_inicio"],
                      f"fin{i}": t["fin"], f"mf{i}": t["medida_fin"]})
        return v


registrar(Engranaje, Eje)
