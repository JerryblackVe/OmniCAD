# -*- coding: utf-8 -*-
"""Comandos de SÓLIDO › CREAR con diálogo al estilo Fusion (Extruir y Revolución están en solido.py)."""
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QSizePolicy, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout,
                               QWidget)

from ...timeline.ops_solido import (OpAgujero, OpBarrido, OpBobina, OpLabio, OpNervio, OpPatron, OpRed,
                                    OpRellenoContorno, OpRepujado, OpRosca, OpSaliente, OpSimetria, OpSolevacion,
                                    OpSolidoEnvolvente, OpTuberia, OpVolumenFluido)
from ...timeline import entidades as ent
from ...timeline.ops_solido import TIPOS_REPETIBLES
from ...timeline.parametros import ANGULO, ESCALAR
from ..comando import (Alternar, Botones, Casilla, Comando, Entero, ErrorComando, Expresion, Info, ListaSeleccion, Opciones, OpcionesVivas, Personalizado,
                       Seleccion, Texto, exigir, hit_desde_ref, hits, hits_cuerpos as _hits_cuerpos, ref1, refs)
from . import registrar
from .comunes import campo_objetivos, campo_operacion, con_analisis, objetivos, simetria_total

PERFIL = {"perfil", "cara_plana"}
CURVA = {"curva_boceto", "arista"}
SECCIONES_BOBINA = {"circular": ("Circular", "sec_circular"), "cuadrada": ("Cuadrado", "sec_cuadrada"),
                    "triangular_externa": ("Triangular (externo)", "sec_tri_externa"),
                    "triangular_interna": ("Triangular (interno)", "sec_tri_interna")}


def _h1(ref, estado):
    return [hit_desde_ref(ref, estado)] if ref else []


def _cuerpos(lista):
    return [h["ref"]["cuerpo"] for h in lista or [] if h["ref"].get("tipo") == "cuerpo"]


def _con_objetivos(op, ctx, v):
    v["objetivos"] = _hits_cuerpos(op.p.get("objetivos") or [], ctx.estado)
    return v


def _en(grupo, *campos):
    """Pone el subtítulo `grupo` a campos ya armados (p. ej. los de `comunes`) y los devuelve."""
    for c in campos:
        c.grupo = grupo
    return campos


@con_analisis
class Barrido(Comando):
    CLAVE, TITULO, ICONO = "barrido", "Barrido", "barrido"
    AYUDA = "Lleva un perfil a lo largo de una ruta (y opcionalmente un rail guía)."
    CLASE_OP = OpBarrido

    def campos(self, ctx):
        carril = lambda v: v.get("tipo") == "ruta_carril"  # noqa: E731
        superficie = lambda v: v.get("tipo") == "ruta_superficie"  # noqa: E731
        cuerpo = lambda v: v.get("tipo") == "cuerpo"  # noqa: E731
        return [Opciones("tipo", "Tipo", {"ruta": ("Ruta individual", "bar_ruta"), "ruta_carril": ("Ruta + Rail guía", "bar_carril"),
                                          "ruta_superficie": ("Trayectoria + Superficie guía", "bar_superficie"),
                                          "cuerpo": ("Barrido sólido", "bar_solido")}),
                Seleccion("perfiles", "Perfil", PERFIL, maximo=None, visible_si=lambda v: not cuerpo(v)),
                Seleccion("cuerpos", "Cuerpo", {"cuerpo"}, maximo=None, visible_si=cuerpo,
                          ayuda="El volumen que recorre el cuerpo a lo largo de la ruta (aproximado con copias)."),
                Seleccion("ruta", "Ruta", CURVA, maximo=None),
                Casilla("cadena", "Selección de cadena", True, ayuda="Suma a cada arista de un cuerpo las que le siguen tangentes (las curvas de boceto se usan tal cual)."),
                Seleccion("carril", "Rail guía", CURVA, maximo=None, visible_si=carril),
                Seleccion("superficie_guia", "Superficie guía", {"cara"}, maximo=None, visible_si=superficie),
                Expresion("distancia", "Distancia", "1", ESCALAR,
                          ayuda="Parte de la ruta que recorre el barrido: de 0 a 1."),
                Opciones("orientacion", "Orientación", {"perpendicular": ("Perpendicular", "ori_perpendicular"),
                                                        "paralela": ("Paralelo", "ori_paralela"),
                                                        "alineada": ("Alineada", "ori_alineada")},
                         visible_si=lambda v: not carril(v) and not superficie(v)),
                Seleccion("eje_alineado", "Eje de alineación", {"eje", "arista_lineal", "plano", "cara_plana"},
                          visible_si=lambda v: v.get("orientacion") == "alineada" and not carril(v) and not superficie(v)),
                Opciones("escala_carril", "Escala del perfil", {"escalar": "Escalar", "ninguna": "Ninguna"},
                         visible_si=carril),
                Expresion("conicidad", "Ángulo de conicidad", "0 deg", ANGULO, visible_si=lambda v: not cuerpo(v),
                          avanzado=True),
                Expresion("torsion", "Ángulo de torsión", "0 deg", ANGULO, visible_si=lambda v: not cuerpo(v),
                          avanzado=True),
                campo_operacion(), campo_objetivos()]

    def construir(self, v, ctx):
        tipo = v.get("tipo")
        if tipo == "cuerpo":
            exigir(v, "cuerpos", "Seleccioná el cuerpo a barrer.")
        else:
            exigir(v, "perfiles", "Seleccioná el perfil.")
        exigir(v, "ruta", "Seleccioná la ruta.")
        if tipo == "ruta_superficie":
            exigir(v, "superficie_guia", "Seleccioná la superficie guía.")
        alineada = tipo in ("ruta", "cuerpo") and v.get("orientacion") == "alineada"
        if alineada:
            exigir(v, "eje_alineado", "Seleccioná el eje de la orientación alineada.")
        return self.crear_op(OpBarrido, v, ctx, perfiles=[] if tipo == "cuerpo" else refs(v, "perfiles"),
                             ruta=refs(v, "ruta"), cuerpos=_cuerpos(v["cuerpos"]) if tipo == "cuerpo" else [],
                             cadena=bool(v.get("cadena")),
                             carril=refs(v, "carril") if tipo == "ruta_carril" else [],
                             superficie_guia=refs(v, "superficie_guia") if tipo == "ruta_superficie" else [],
                             eje_alineado=ref1(v, "eje_alineado") if alineada else None,
                             orientacion=v["orientacion"] if tipo in ("ruta", "cuerpo") else "perpendicular",
                             **{k: v[k] for k in ("distancia", "escala_carril", "operacion")},
                             **{k: "0 deg" if tipo == "cuerpo" else v[k] for k in ("torsion", "conicidad")},
                             objetivos=objetivos(v))

    def desde_op(self, op, ctx):
        v = dict(op.p, tipo="cuerpo" if op.p.get("cuerpos") else "ruta_carril" if op.p.get("carril")
                 else "ruta_superficie" if op.p.get("superficie_guia") else "ruta",
                 cuerpos=_hits_cuerpos(op.p.get("cuerpos") or [], ctx.estado))
        for k in ("perfiles", "ruta", "carril", "superficie_guia"):
            v[k] = hits(op.p.get(k) or [], ctx.estado)
        v["eje_alineado"] = _h1(op.p.get("eje_alineado"), ctx.estado)
        return _con_objetivos(op, ctx, v)


COND_BORDE = {"libre": "Libre", "direccion": "Dirección", "tangente": "Tangente", "suave": "Suave (G2)"}


def _en_fila(lado):
    """¿Es la fila del perfil de ese extremo? Sin fila elegida se ven los dos."""
    def es(v):
        fila, n = v.get("fila_secciones"), len(v.get("secciones") or [])
        return fila is None or fila < 0 or fila == (0 if lado == "inicio" else n - 1)
    return es


def _con_direccion(lado):
    return lambda v: _en_fila(lado)(v) and v.get(f"condicion_{lado}") == "direccion"


def _con_tangente(lado):
    return lambda v: _en_fila(lado)(v) and v.get(f"condicion_{lado}") in ("tangente", "suave")


def _peso(lado):
    return lambda v: "Peso de despegue" if v.get(f"condicion_{lado}") == "direccion" else "Peso de tangencia"


def _fila_media(v):
    fila, n = v.get("fila_secciones"), len(v.get("secciones") or [])
    return fila is not None and 0 < fila < n - 1


def _condiciones_de(hit, extremo):
    """Condiciones de una fila de perfiles según lo elegido (Loft reference): boceto → Libre o Dirección; arista o cara →
    Libre, Tangente o Suave; punto → Aguda. Entre el primero y el último, Libre o Dirección."""
    tipo = hit["ref"]["tipo"]
    if tipo in ("vertice", "punto"):
        return {"libre": "Aguda"}
    if not extremo or tipo not in ("arista", "cara"):
        return {"libre": "Libre", "direccion": "Dirección"}
    return {"libre": "Libre", "tangente": "Tangente", "suave": "Suave (G2)"}


@con_analisis
class Solevacion(Comando):
    CLAVE, TITULO, ICONO = "solevacion", "Solevación", "solevacion"
    AYUDA = "Crea un sólido que pasa por varios perfiles en orden (opcional: carril o línea central)."
    CLASE_OP = OpSolevacion

    def campos(self, ctx):
        return [ListaSeleccion("secciones", "Perfiles", PERFIL | CURVA | {"vertice", "punto"}, celda=self._celda),
                Opciones("condicion_inicio", "Condición inicial", COND_BORDE, visible_si=lambda v: False),
                Expresion("peso_inicio", "Peso de despegue", "1", ESCALAR, etiqueta_si=_peso("inicio"),
                          visible_si=lambda v: _con_direccion("inicio")(v) or _con_tangente("inicio")(v)),
                Expresion("angulo_inicio", "Ángulo de despegue", "90 deg", ANGULO, visible_si=_con_direccion("inicio")),
                Seleccion("cara_inicio", "Cara tangente inicial", {"cara"}, minimo=0, visible_si=_con_tangente("inicio"),
                          ayuda="La cara cuyo borde es el perfil: la superficie sale tangente a ella."),
                Expresion("peso_medio", "Peso de despegue", "1", ESCALAR, visible_si=lambda v: _fila_media(v) and self._de_fila(v)),
                Expresion("angulo_medio", "Ángulo de despegue", "90 deg", ANGULO, visible_si=lambda v: _fila_media(v) and self._de_fila(v)),
                Opciones("condicion_fin", "Condición final", COND_BORDE, visible_si=lambda v: False),
                Expresion("peso_fin", "Peso de despegue", "1", ESCALAR, etiqueta_si=_peso("fin"),
                          visible_si=lambda v: _con_direccion("fin")(v) or _con_tangente("fin")(v)),
                Expresion("angulo_fin", "Ángulo de despegue", "90 deg", ANGULO, visible_si=_con_direccion("fin")),
                Seleccion("cara_fin", "Cara tangente final", {"cara"}, minimo=0, visible_si=_con_tangente("fin"),
                          ayuda="La cara cuyo borde es el perfil: la superficie sale tangente a ella."),
                Botones("guia", "Tipo de guía", {"carriles": ("Raíles", "guia_carriles"), "linea_central": ("Línea central", "guia_central")}),
                ListaSeleccion("carriles", "Raíles", CURVA, minimo=0, visible_si=lambda v: v.get("guia") == "carriles"),
                ListaSeleccion("linea_central", "Línea central", CURVA, minimo=0, visible_si=lambda v: v.get("guia") == "linea_central"),
                Casilla("cadena", "Selección de cadena", True, ayuda="Suma a cada arista de un cuerpo las que le siguen tangentes."),
                Casilla("cerrada", "Cerrado"),
                Botones("aristas_tangentes", "Aristas tangentes", {"fusionar": ("Fusionar", "tan_fusionar"), "mantener": ("Mantener", "tan_mantener")}),
                Casilla("reglada", "Tramos rectos", avanzado=True),
                Texto("medias", "Perfiles intermedios", "", visible_si=lambda v: False,
                      ayuda="Dirección en los perfiles de en medio. Por ejemplo «2:60:1; 3:90:1.5»: el n.º cuenta desde 1 (el primer perfil) y solo vale entre el 2.º y el penúltimo."),
                campo_operacion(), campo_objetivos()]

    def _de_fila(self, v):
        return str(v["fila_secciones"]) in self._filas_medias(v)

    @staticmethod
    def _filas_medias(v):
        """{fila desde 0, en texto: [ángulo, peso]} del valor «n.º:ángulo:peso; …» (n.º desde 1)."""
        salida = {}
        for trozo in (t.strip() for t in str(v.get("medias") or "").split(";") if t.strip()):
            partes = [x.strip() for x in trozo.split(":")]
            if partes[0].isdigit():
                salida[str(int(partes[0]) - 1)] = [*partes[1:], "1"][:2]
        return salida

    @staticmethod
    def _poner_medias(panel, filas):
        panel.set_valor("medias", "; ".join(f"{int(k) + 1}:{a}:{p}" for k, (a, p) in sorted(filas.items(), key=lambda kv: int(kv[0]))))

    def _celda(self, panel, i, n):
        """Condición del perfil de la fila i: la del primero y el último son `condicion_*`; las del medio van en `medias`."""
        extremo = "inicio" if i == 0 else "fin" if i == n - 1 else None
        opciones = _condiciones_de(panel.valores["secciones"][i], extremo is not None)
        actual = panel.valores.get(f"condicion_{extremo}") if extremo else ("direccion" if str(i) in self._filas_medias(panel.valores) else "libre")
        w = QComboBox()
        for k, texto in (opciones | ({actual: COND_BORDE[actual]} if actual not in opciones else {})).items():
            w.addItem(texto, k)
        w.setCurrentIndex(max(w.findData(actual), 0))

        def cambio(_=0):
            if extremo:
                panel.set_valor(f"condicion_{extremo}", w.currentData())
                return
            filas = self._filas_medias(panel.valores)
            filas.pop(str(i), None)
            if w.currentData() == "direccion":
                filas[str(i)] = ["90 deg", "1"]
            self._poner_medias(panel, filas)
        w.currentIndexChanged.connect(cambio)
        return w

    def al_cambiar(self, panel, clave):
        fila = panel.valores.get("fila_secciones")
        if clave == "secciones":             # una fila menos: la condición de un perfil que ya no es del medio no queda oculta
            n, filas = len(panel.valores.get("secciones") or []), self._filas_medias(panel.valores)
            if any(not 0 < int(k) < n - 1 for k in filas):
                self._poner_medias(panel, {k: x for k, x in filas.items() if 0 < int(k) < n - 1})
        elif clave == "fila_secciones" and _fila_media(panel.valores) and str(fila) in self._filas_medias(panel.valores):
            angulo, peso = self._filas_medias(panel.valores)[str(fila)]
            panel.set_valores({"angulo_medio": angulo, "peso_medio": peso})
        elif clave in ("angulo_medio", "peso_medio") and _fila_media(panel.valores):
            filas = self._filas_medias(panel.valores)
            if str(fila) in filas:
                filas[str(fila)] = [panel.valores["angulo_medio"], panel.valores["peso_medio"]]
                self._poner_medias(panel, filas)

    @staticmethod
    def _condicion(v, lado):
        tipo = v.get(f"condicion_{lado}")
        if tipo == "direccion":
            return {"tipo": "direccion", "angulo": v[f"angulo_{lado}"], "peso": v[f"peso_{lado}"]}
        if tipo in ("tangente", "suave"):
            if not v.get(f"cara_{lado}"):
                raise ErrorComando(f"Seleccioná la cara a la que es tangente el {'primer' if lado == 'inicio' else 'último'} perfil.")
            return {"tipo": tipo, "angulo": "90 deg", "peso": v[f"peso_{lado}"], "cara": ref1(v, f"cara_{lado}")}
        return None

    @staticmethod
    def _medias(v, n):
        """{posición (desde 0): condición «Dirección»} del campo de texto «n.º:ángulo:peso; …» (n.º desde 1)."""
        salida = {}
        for trozo in (t.strip() for t in str(v.get("medias") or "").split(";") if t.strip()):
            partes = [x.strip() for x in trozo.split(":")]
            if len(partes) not in (2, 3) or not partes[0].isdigit() or not 1 < int(partes[0]) < n:
                raise ErrorComando(f"«{trozo}»: escribí n.º:ángulo:peso, con el n.º entre 2 y {n - 1} (hay {n} perfiles).")
            salida[str(int(partes[0]) - 1)] = {"tipo": "direccion", "angulo": partes[1],
                                              "peso": partes[2] if len(partes) == 3 else "1"}
        return salida

    def construir(self, v, ctx):
        if len(v.get("secciones") or []) < 2:
            raise ErrorComando("Seleccioná al menos dos perfiles, en orden.")
        medias = self._medias(v, len(v["secciones"]))
        for c in (self._condicion(v, "inicio"), self._condicion(v, "fin"), *medias.values()):
            if c:
                ctx.evaluar(c["angulo"], ANGULO)
                ctx.evaluar(c["peso"], ESCALAR)
        guia = v.get("guia")
        return self.crear_op(OpSolevacion, v, ctx, secciones=refs(v, "secciones"),
                             carriles=refs(v, "carriles") if guia == "carriles" else [],
                             linea_central=refs(v, "linea_central") if guia == "linea_central" else [],
                             cerrada=v["cerrada"], reglada=v["reglada"], operacion=v["operacion"],
                             condicion_inicio=self._condicion(v, "inicio"), condicion_fin=self._condicion(v, "fin"),
                             condiciones_medias=medias, fusionar_tangentes=v.get("aristas_tangentes") == "fusionar",
                             cadena=bool(v.get("cadena")), objetivos=objetivos(v))

    def desde_op(self, op, ctx):
        v = dict(op.p, guia="linea_central" if op.p.get("linea_central") else "carriles",
                 aristas_tangentes="fusionar" if op.p.get("fusionar_tangentes") else "mantener")
        for lado in ("inicio", "fin"):
            c = op.p.get(f"condicion_{lado}") or {}
            v[f"condicion_{lado}"] = c["tipo"] if c.get("tipo") in ("direccion", "tangente", "suave") else "libre"
            v[f"angulo_{lado}"], v[f"peso_{lado}"] = c.get("angulo", "90 deg"), c.get("peso", "1")
            v[f"cara_{lado}"] = _h1(c.get("cara"), ctx.estado)
        v["medias"] = "; ".join(f"{int(k) + 1}:{c.get('angulo', '90 deg')}:{c.get('peso', '1')}"
                                for k, c in sorted((op.p.get("condiciones_medias") or {}).items(), key=lambda kv: int(kv[0])))
        for k in ("secciones", "carriles", "linea_central"):
            v[k] = hits(op.p[k], ctx.estado)
        return _con_objetivos(op, ctx, v)


class _NervioRed(Comando):
    CLASE_OP = OpNervio
    ES_RED = False

    def campos(self, ctx):
        red, nervio = self.ES_RED, not self.ES_RED
        return [Seleccion("curvas", "Perfil", {"curva_boceto"}, maximo=None),
                Botones("direccion", "Dirección del espesor", {"simetrica": ("Simétrico", "esp_simetrico"),
                                                               "lado1": ("Un lado, desde abajo", "esp_lado1"),
                                                               "lado2": ("Un lado, desde arriba", "esp_lado2")}),
                Expresion("espesor", "Grosor", "2 mm"),
                Opciones("extension", "Tipo de extensión", {"hasta_siguiente": ("Al siguiente", "ext_siguiente"),
                                                            "profundidad": ("Distancia", "ext_distancia")}),
                Expresion("profundidad", "Distancia", "10 mm",
                          visible_si=lambda v: v.get("extension") == "profundidad"),
                Alternar("invertir", "Cambiar dirección", "cambiar_direccion"),
                Expresion("angulo_desmoldeo", "Ángulo de desmoldeo", "0 deg", ANGULO, avanzado=True),
                Seleccion("direccion_desmoldeo", "Dirección de extracción", {"plano", "cara_plana", "eje", "arista_lineal"},
                          minimo=0, visible_si=lambda v: nervio),
                Expresion("radio_empalme", "Radio del empalme", "0 mm", visible_si=lambda v: red, avanzado=True),
                Casilla("extender", "Alargar curvas", True, visible_si=lambda v: red),
                Seleccion("objetivo", "Cuerpo", {"cuerpo"}, minimo=0, ayuda="Sin selección: el más cercano.")]

    def construir(self, v, ctx):
        exigir(v, "curvas", "Seleccioná las curvas del boceto.")
        ctx.evaluar(v["espesor"])
        obj = _cuerpos(v.get("objetivo"))
        return self.crear_op(self.CLASE_OP, v, ctx, curvas=refs(v, "curvas"), objetivo=obj[0] if obj else "",
                             direccion_desmoldeo=None if self.ES_RED else ref1(v, "direccion_desmoldeo"),
                             radio_empalme=v["radio_empalme"] if self.ES_RED else "0 mm",
                             extender=bool(v["extender"]) if self.ES_RED else True,
                             **{k: v[k] for k in ("espesor", "extension", "profundidad", "direccion", "invertir",
                                                  "angulo_desmoldeo")})

    def desde_op(self, op, ctx):
        return dict(op.p, curvas=hits(op.p["curvas"], ctx.estado), objetivo=_hits_cuerpos(op.p.get("objetivo"),
                                                                                         ctx.estado),
                    direccion_desmoldeo=_h1(op.p.get("direccion_desmoldeo"), ctx.estado))


class Nervio(_NervioRed):
    CLAVE, TITULO, ICONO = "nervio", "Nervio", "nervio"
    AYUDA = "Pared de refuerzo desde una o varias curvas abiertas del boceto hasta el cuerpo."
    CLASE_OP = OpNervio


class Red(_NervioRed):
    ES_RED = True
    CLAVE, TITULO, ICONO = "red", "Red", "red"
    AYUDA = "Red de nervios desde varias curvas abiertas, perpendicular al boceto."
    CLASE_OP = OpRed


class Repujado(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "repujado", "Repujado", "repujado", "Shift+E"
    AYUDA = "Relieve o grabado de perfiles o texto sobre una cara (también envuelto en un cilindro)."
    CLASE_OP = OpRepujado

    def campos(self, ctx):
        return [Opciones("tipo", "Tipo de repujado", {"relieve": "Relieve", "grabado": "Grabado"}),
                Seleccion("perfiles", "Perfiles", PERFIL, maximo=None),
                Seleccion("caras", "Caras", {"cara"}, maximo=None,
                          ayuda="Una o varias caras: el texto se proyecta en su lugar y se reparte entre ellas "
                                "(cada una recibe solo lo que le cae encima)."),
                Expresion("profundidad", "Profundidad", "1 mm"), Casilla("envolver", "Envolver en la cara"),
                Casilla("invertir", "Invertir normal"),
                Casilla("cadena_tangente", "Cadena tangente", avanzado=True),
                Expresion("desfase_h", "Desfase horizontal", "0 mm", avanzado=True),
                Expresion("desfase_v", "Desfase vertical", "0 mm", avanzado=True),
                Expresion("giro", "Ángulo de giro", "0 deg", ANGULO, avanzado=True)]

    def construir(self, v, ctx):
        exigir(v, "perfiles", "Seleccioná los perfiles.")
        exigir(v, "caras", "Seleccioná al menos una cara.")
        return self.crear_op(OpRepujado, v, ctx, perfiles=refs(v, "perfiles"), cara=None, caras=refs(v, "caras"),
                             **{k: v[k] for k in ("profundidad", "tipo", "envolver", "cadena_tangente",
                                                   "desfase_h", "desfase_v", "giro", "invertir")})

    def desde_op(self, op, ctx):
        caras = list(op.p.get("caras") or []) + ([op.p["cara"]] if op.p.get("cara") else [])
        return dict(op.p, perfiles=hits(op.p["perfiles"], ctx.estado), caras=hits(caras, ctx.estado))


# ---------------------------------------------------------------- roscas en los diálogos (Agujero y Rosca)
# Como Fusion: Tipo (familia de normas) → Tamaño (lista según el tipo) → Designación (cuando el tamaño tiene varios
# pasos) → Clase. Un campo de tamaño por familia y uno de designación por tamaño con varios pasos, que se muestran
# según lo elegido (el panel no cambia las listas en vivo: cada lista es un campo propio).
def _sc():
    from ...nucleo import solidos_crear
    return solidos_crear


def _tol():
    from ...nucleo import tolerancias
    return tolerancias


_CLASES = {"iso_metrica": {"auto": "Automática (6H agujero / 6g eje)", "": "Sin clase (perfil básico)",
                           "6g": "6g (exterior)", "6h": "6h (exterior)", "6H": "6H (interior)", "6G": "6G (interior)"},
           "unificada": {"auto": "Automática (2B agujero / 2A eje)", "": "Sin clase (perfil básico)",
                         "2A": "2A (exterior)", "3A": "3A (exterior)", "2B": "2B (interior)", "3B": "3B (interior)"}}


_CLASES["ansi_metrica"] = _CLASES["gb_metrica"] = _CLASES["iso_metrica"]


def _clases_de_tablas():
    """El desplegable «Clase» de los tipos cuyas clases salen de las tablas de Fusion (CAP-14)."""
    from ...nucleo import tablas_rosca
    lado = {True: "interior", False: "exterior", None: "interior y exterior"}
    salida = {}
    for fam, clases in tablas_rosca.CLASES_FAMILIA.items():
        a, b = tablas_rosca.CLASE_FUSION[fam]
        auto = " / ".join(x for x in (f"{a} agujero" if a else "", f"{b} eje" if b else "") if x)
        salida[fam] = {"auto": f"Automática ({auto})", "": "Sin clase (perfil básico)",
                       **{c: f"{c} ({lado[g]})" for c, g in clases.items()}}
    return salida


_CLASES.update(_clases_de_tablas())

_TAMANO_INICIAL = {"iso_metrica": "M6", "unificada": "1/4", "trapezoidal": "Tr12", "acme": "1/2",
                   "bsp_paralela": "1/2", "bsp_conica": "1/2", "npt": "1/2"}


def _tamano_inicial(fam, tams):
    t = _TAMANO_INICIAL.get(fam)
    return t if t in tams else tams[0]


def _familias(conicas=None, interior=False):
    """Tipos de rosca del desplegable; `interior`: sin los que son solo exteriores (Fusion no los ofrece en un agujero)."""
    return {k: f["nombre"] for k, f in _sc().FAMILIAS_ROSCA.items() if (conicas is None or f["conica"] == conicas)
            and not (interior and f.get("solo_exterior"))}


def _tipos_rosca(v, ctx):
    """Tipos de Rosca: los paralelos, según la cara elegida. Un paso viejo con una cónica la conserva."""
    fams = _familias(conicas=False, interior=_interna_de(v, ctx) is True)
    actual = _sc().FAMILIAS_ROSCA.get(v.get("tipo_rosca"))
    return fams | {v["tipo_rosca"]: actual["nombre"]} if actual and actual["conica"] else fams


def _lista_designaciones(v, clave_tipo, automatico):
    """Designaciones del tamaño elegido, sin el prefijo que separa nombres iguales de dos tipos (GB M6x1 → M6x1)."""
    sc, fam = _sc(), v.get(clave_tipo)
    des = sc.designaciones_rosca(fam, v.get(f"tam_{fam}"))
    return ({"auto": "Automático"} if automatico else {}) | {
        d: d.split(" ", 1)[1] if fam in sc.tablas_rosca.FAMILIAS else d for d in des}


def _campos_rosca(clave_tipo, familias, visible, defectos, automatico=False, clases=True, grupo=None, seccion=None, tipos=None):
    """Tipo, Tamaño (uno por familia), Designación (lista viva) y Clase (si la familia tiene). `defectos`: valores
    iniciales (lo recordado); `automatico`: el tamaño puede ser «Automático» (según la cara); `tipos(v)`: lista viva de tipos."""
    sc = _sc()
    defecto = defectos.get(clave_tipo) or ("iso_metrica" if "iso_metrica" in familias else next(iter(familias)))
    campos = [OpcionesVivas(clave_tipo, "Tipo de rosca", tipos, defecto, visible_si=visible, grupo=grupo, seccion=seccion) if tipos else
              Opciones(clave_tipo, "Tipo de rosca", familias, defecto=defecto, visible_si=visible, grupo=grupo, seccion=seccion)]
    tamanos, clase_por_fam = [], []
    for fam in familias:
        tams = sc.tamanos_rosca(fam)
        de_fam = lambda v, fam=fam: visible(v) and v.get(clave_tipo) == fam  # noqa: E731
        opciones = ({"auto": "Automático (según la cara)"} if automatico else {}) | {t: t for t in tams}
        defecto = defectos.get(f"tam_{fam}") or ("auto" if automatico else _tamano_inicial(fam, tams))
        tamanos.append(Opciones(f"tam_{fam}", "Tamaño", opciones, defecto=defecto, visible_si=de_fam, grupo=grupo, seccion=seccion))
        if clases and fam in _CLASES:
            clase_por_fam.append(Opciones(f"clase_{fam}", "Clase", _CLASES[fam], defecto=defectos.get(f"clase_{fam}", "auto"),
                                          grupo=grupo, seccion=seccion, visible_si=lambda v, fam=fam, de_fam=de_fam: de_fam(v) and
                                          clases(v) if callable(clases) else de_fam(v)))
    des = OpcionesVivas(f"des_{clave_tipo}", "Designación", lambda v: _lista_designaciones(v, clave_tipo, automatico),
                        defectos.get(f"des_{clave_tipo}") or ("auto" if automatico else ""), visible_si=visible, grupo=grupo,
                        seccion=seccion)
    return [*campos, *tamanos, des, *clase_por_fam]


def _designacion(v, clave_tipo, automatico=False):
    """Designación elegida en el diálogo ("" = tamaño automático)."""
    sc = _sc()
    fam = v.get(clave_tipo)
    if fam not in sc.FAMILIAS_ROSCA:
        fam = "iso_metrica"
    tams = sc.tamanos_rosca(fam)
    tam = v.get(f"tam_{fam}")
    if automatico and tam in (None, "", "auto"):
        return ""
    if tam not in tams:
        tam = _tamano_inicial(fam, tams)
    des = sc.designaciones_rosca(fam, tam)
    elegida = v.get(f"des_{clave_tipo}")
    return elegida if elegida in des else des[0]


def _clase(v, clave_tipo):
    fam = v.get(clave_tipo)
    return (v.get(f"clase_{fam}") or "") if fam in _CLASES else ""


def _valores_rosca(designacion, clave_tipo, clase=""):
    """Valores del diálogo que muestran una designación guardada (para editar el paso)."""
    sc = _sc()
    try:
        datos = sc.datos_rosca(designacion)
    except Exception:  # noqa: BLE001 — una designación vieja que ya no se reconoce deja el diálogo por defecto
        return {}
    fam, tam = datos["familia"], datos["tamano"]
    v = {clave_tipo: fam, f"tam_{fam}": tam, f"des_{clave_tipo}": datos["designacion"]}
    if fam in _CLASES:
        v[f"clase_{fam}"] = clase or ""
    return v


class BibliotecaRoscas(QDialog):
    """Ventana de la biblioteca de roscas (el menú «más» de Thread Library): se toca una definición y Seleccionar la aplica."""

    def __init__(self, panel, familias, familia):
        super().__init__(panel, windowTitle="Biblioteca de roscas")
        self.resize(560, 420)
        self.tipo = QComboBox()
        for k, nombre in familias.items():
            self.tipo.addItem(nombre, k)
        self.tipo.setCurrentIndex(max(self.tipo.findData(familia), 0))
        self.filtro = QLineEdit(placeholderText="Filtrar por tamaño o designación")
        self.tabla = QTableWidget(0, 5, selectionBehavior=QAbstractItemView.SelectRows, selectionMode=QAbstractItemView.SingleSelection,
                                  editTriggers=QAbstractItemView.NoEditTriggers)
        self.tabla.setHorizontalHeaderLabels(("Tamaño", "Designación", "Paso", "Ø mayor", "Ø menor"))
        self.tabla.verticalHeader().hide()
        self.tabla.horizontalHeader().setStretchLastSection(True)
        botones = QDialogButtonBox()
        self.seleccionar = botones.addButton("Seleccionar", QDialogButtonBox.AcceptRole)
        botones.addButton("Cancelar", QDialogButtonBox.RejectRole)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        caja = QVBoxLayout(self)
        for w in (self.tipo, self.filtro, self.tabla, botones):
            caja.addWidget(w)
        self.tipo.currentIndexChanged.connect(self._llenar)
        self.filtro.textChanged.connect(self._llenar)
        self.tabla.itemSelectionChanged.connect(lambda: self.seleccionar.setEnabled(self.elegida() is not None))
        self.tabla.cellDoubleClicked.connect(self.accept)
        self._llenar()

    def _llenar(self):
        sc, fam = _sc(), self.tipo.currentData()
        texto = self.filtro.text().strip().casefold()
        filas = [sc.datos_rosca(d) for t in sc.tamanos_rosca(fam) for d in sc.designaciones_rosca(fam, t)
                 if texto in d.casefold() or texto in t.casefold()]
        self.tabla.setRowCount(len(filas))
        for i, d in enumerate(filas):
            for j, x in enumerate((d["tamano"], d["designacion"], f"{d['paso']:g}", f"{d['diametro']:g}", f"{d['diametro_menor']:g}")):
                self.tabla.setItem(i, j, QTableWidgetItem(x))
        self.seleccionar.setEnabled(False)

    def elegida(self):
        fila = self.tabla.selectedItems()
        return fila[1].text() if fila else None


def _texto_limites(fam, datos, clase, interna=None):
    """«6g: Ø mayor 9.732–9.968 · Ø flancos 8.862–8.994 mm (ISO 965-1)» o por qué no hay límites."""
    tol = _tol()
    if not clase:
        return "perfil básico (sin clase)"
    if clase == "auto":
        if fam not in tol.CLASE_AUTOMATICA:
            return "sin clases cargadas para este tipo: perfil básico"
        if interna is None:
            a, b = tol.CLASE_AUTOMATICA[fam]
            return "clase automática: " + ", ".join(x for x in (f"{a} en agujeros" if a else "", f"{b} en ejes" if b else "") if x)
        clase = tol.CLASE_AUTOMATICA[fam][0 if interna else 1]
        if clase is None:
            return "este tipo no tiene clase en los agujeros: perfil básico"
    try:
        lim = tol.limites_rosca(fam, datos["diametro"], datos["paso"], clase, interna)
    except Exception as e:  # noqa: BLE001 — sin datos para el tamaño: se dice por qué
        return f"{clase}: {e}"

    def rango(par):
        a, b = par
        if a is None and b is None:
            return "—"
        return f"{a:.3f}–{b:.3f}" if a is not None and b is not None else (f"≥ {a:.3f}" if a is not None else
                                                                           f"≤ {b:.3f}")
    partes = [f"Ø mayor {rango(lim['diametro_mayor'])}", f"Ø flancos {rango(lim['diametro_flancos'])}"]
    if lim["interna"]:
        partes.append(f"Ø menor {rango(lim['diametro_menor'])}")
    return f"{clase}: " + " · ".join(partes) + f" mm ({lim['norma']})"


def _texto_rosca_basica(datos):
    fam = _sc().FAMILIAS_ROSCA[datos["familia"]]
    texto = (f"{datos['designacion']} ({fam['norma']}, {fam['angulo']:g}°): Ø {datos['diametro']:.3f}, paso "
             f"{datos['paso']:.4g}, Ø menor {datos['diametro_menor']:.3f} mm")
    if datos["conica"]:
        texto += " en el plano de calibre, conicidad 1:16"
    return texto


def _interna_de(v, ctx):
    """¿La primera cara elegida es un agujero? None si no se puede saber."""
    try:
        h = (v.get("caras") or [])[0]
        e = _ent_resuelta(h, ctx)
        return _sc().analizar_rosca(ctx.estado.cuerpo(e.cuerpo).forma, e.forma)["interna"]
    except Exception:  # noqa: BLE001
        return None


def _ent_resuelta(hit, ctx):
    from ...timeline import entidades as ent
    return ent.resolver(hit["ref"], ctx.estado)


class Agujero(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "agujero", "Agujero", "agujero", "H"
    AYUDA = ("Agujeros simples, escariados o avellanados; pasantes, ciegos o hasta una cara; lisos, con espacio libre "
             "(ISO 273), roscados (con tipo, tamaño, designación y clase) o con rosca cónica de tubería.")
    CLASE_OP = OpAgujero
    ANCHO_PANEL = "normal"

    def campos(self, ctx):
        sc = _sc()
        t = lambda *x: (lambda v: v.get("tipo") in x)  # noqa: E731
        r = lambda *x: (lambda v: v.get("rosca") in x)  # noqa: E731
        modelada = lambda v: self._rosca_del_paso(v) == "modelada"  # noqa: E731
        pos = lambda *x: (lambda v: (v.get("posicion") or "punto") in x)  # noqa: E731
        hasta = lambda v: v.get("extension") == "hasta"  # noqa: E731
        fo = "Configuración de la forma"
        return [
            Botones("posicion", "Colocación", {"punto": ("En punto (agujero individual)", "ag_punto"),
                                               "boceto": ("A partir de boceto (agujeros múltiples)", "ag_boceto"),
                                               "referencias": ("Por referencias (una cara y dos aristas)", "ag_referencias")},
                    ayuda="En punto: un clic sobre una cara plana (o un punto). A partir de boceto: un agujero en cada "
                          "punto del boceto. Por referencias: una cara y dos aristas con su distancia."),
            Seleccion("colocacion", "Puntos de cara/boceto", {"punto", "vertice", "cara_plana"}, maximo=None,
                      visible_si=pos("punto"), ayuda="Un clic sobre una cara plana (o un punto o vértice)."),
            Seleccion("puntos_boceto", "Puntos de boceto", {"punto_boceto"}, maximo=None, visible_si=pos("boceto"),
                      ayuda="Cada punto del boceto es un agujero: si el boceto cambia, los agujeros lo siguen."),
            Seleccion("ref_cara", "Cara", {"cara_plana"}, visible_si=pos("referencias")),
            Seleccion("ref_arista1", "Referencia 1", {"arista_lineal"}, visible_si=pos("referencias"),
                      ayuda="Arista recta desde la que se mide la distancia 1."),
            Expresion("ref_distancia1", "Distancia 1", "10 mm", visible_si=pos("referencias")),
            Seleccion("ref_arista2", "Referencia 2", {"arista_lineal"}, visible_si=pos("referencias"),
                      ayuda="Otra arista recta, no paralela a la primera."),
            Expresion("ref_distancia2", "Distancia 2", "10 mm", visible_si=pos("referencias")),
            Opciones("extension", "Tipo de extensión", {"distancia": ("Distancia", "ext_distancia"), "hasta": ("A", "ext_objeto"),
                                                        "todo": ("Todo", "ext_todo")}, seccion=fo),
            Expresion("profundidad", "Distancia", "10 mm", visible_si=lambda v: v.get("extension") == "distancia", seccion=fo),
            Seleccion("hasta", "A", {"cara", "plano", "cuerpo"}, visible_si=hasta, seccion=fo,
                      ayuda="Cara (si es plana, su plano extendido), plano de construcción o cuerpo donde termina."),
            Casilla("invertir", "Invertir dirección", seccion=fo),
            Botones("tipo", "Tipo de agujero", {"simple": ("Simple", "ag_simple"), "abocardado": ("Escariado", "ag_escariado"),
                                                "avellanado": ("Avellanado", "ag_avellanado")}, seccion=fo),
            Botones("rosca", "Tipo de rosca", {"simple": ("Simple", "ag_liso"), "holgura": ("Espacio libre", "ag_libre"),
                                               "cosmetica": ("Roscado", "ag_roscado"), "conico": ("Roscado cónico", "ag_conico")},
                    seccion=fo),
            Casilla("rosca_modelada", "Modelado", visible_si=r("cosmetica"), seccion=fo),
            Botones("punta", "Punto de taladro", {"plana": ("Plano", "ag_punta_plana"), "angulo": ("Ángulo", "ag_punta_angulo")},
                    defecto="angulo", seccion=fo),
            Expresion("angulo_punta", "Ángulo de la punta", "118 deg", ANGULO, visible_si=lambda v: v.get("punta") == "angulo",
                      seccion=fo),
            Expresion("diametro", "Diámetro", "6 mm", visible_si=lambda v: v.get("rosca") == "simple" or (
                v.get("rosca") == "cosmetica" and not v.get("rosca_modelada")), seccion=fo),
            Expresion("diam_abocardado", "Diámetro de escariado", "10 mm", visible_si=t("abocardado"), seccion=fo),
            Expresion("prof_abocardado", "Profundidad de escariado", "4 mm", visible_si=t("abocardado"), seccion=fo),
            Expresion("diam_avellanado", "Diámetro de avellanado", "12 mm", visible_si=t("avellanado"), seccion=fo),
            Expresion("angulo_avellanado", "Ángulo de avellanado", "90 deg", ANGULO, visible_si=t("avellanado"), seccion=fo),
            Opciones("tam_holgura", "Tamaño", {k: k for k in sc.PASO_LIBRE_ISO273}, defecto="M6", visible_si=r("holgura"),
                     seccion=fo),
            Opciones("ajuste", "Ajuste", {"fino": "Cercano (serie fina)", "normal": "Normal (serie media)",
                                          "grueso": "Holgado (serie gruesa)"}, defecto="normal", seccion=fo,
                     visible_si=r("holgura"), ayuda="Diámetro del agujero de paso según ISO 273."),
            *_campos_rosca("tipo_rosca", _familias(conicas=False, interior=True), r("cosmetica"), {}, clases=modelada, seccion=fo),
            *_campos_rosca("tipo_conica", _familias(conicas=True), r("conico"), {}, clases=False, seccion=fo),
            Info("info_rosca", "Detalle de rosca", self._info, visible_si=r("holgura", "cosmetica", "conico"), seccion=fo),
            Expresion("desfase_hasta", "Desfase del límite", "0 mm", visible_si=hasta, avanzado=True),
            Expresion("holgura_3d", "Holgura impresión 3D", "0 mm", visible_si=modelada, avanzado=True,
                      ayuda="Desfase radial extra de los flancos y del agujero, para que el tornillo entre en una "
                            "pieza impresa."),
            Opciones("mano", "Dirección de la rosca", {"derecha": "Mano derecha", "izquierda": "Mano izquierda"},
                     visible_si=modelada, avanzado=True),
            campo_objetivos(),
        ]

    @staticmethod
    def _rosca_del_paso(v):
        """El panel tiene un solo «Roscado» con la casilla Modelado; el paso distingue cosmetica y modelada."""
        rosca = v.get("rosca")
        return "modelada" if rosca == "cosmetica" and v.get("rosca_modelada") else rosca

    @classmethod
    def _rosca_elegida(cls, v):
        """(designación, clase) que guarda el paso según el tipo de rosca del diálogo."""
        rosca = cls._rosca_del_paso(v)
        if rosca == "holgura":
            return v.get("tam_holgura") or "M6", ""
        if rosca == "conico":
            return _designacion(v, "tipo_conica"), ""
        return _designacion(v, "tipo_rosca"), (_clase(v, "tipo_rosca") if rosca == "modelada" else "")

    def _info(self, v, ctx):
        sc = _sc()
        designacion, clase = self._rosca_elegida(v)
        rosca = self._rosca_del_paso(v)
        if rosca == "holgura":
            d = sc.diametro_paso_libre(designacion, v.get("ajuste") or "normal")
            return f"Agujero de paso para {designacion}: Ø {d:g} mm (ISO 273, serie {v.get('ajuste') or 'normal'})"
        datos = sc.datos_rosca(designacion)
        texto = _texto_rosca_basica(datos)
        if rosca == "modelada":
            clase_r, aviso = _tol().resolver_clase(datos["familia"], datos["diametro"], datos["paso"], clase, True)
            holgura = ctx.evaluar(v.get("holgura_3d") or "0 mm")
            texto += (f" · {_texto_limites(datos['familia'], datos, clase_r) if clase_r else (aviso or 'perfil básico')}"
                      f" · Ø taladro {sc.diametro_taladro_rosca(designacion, clase_r, holgura):.3f} mm")
        elif rosca == "cosmetica" and datos.get("broca"):
            texto += f" · broca para roscar {datos['broca']:g} mm"
        return texto

    def construir(self, v, ctx):
        posicion = v.get("posicion") or "punto"
        posiciones, puntos_cara, ref_cara, ref_aristas = [], [], None, []
        if posicion == "boceto":
            posiciones = [h["ref"] for h in exigir(v, "puntos_boceto", "Elegí los puntos del boceto (un agujero por "
                                                                       "punto).")]
        elif posicion == "referencias":
            exigir(v, "ref_cara", "Elegí la cara plana donde va el agujero.")
            exigir(v, "ref_arista1", "Elegí la primera arista de referencia.")
            exigir(v, "ref_arista2", "Elegí la segunda arista de referencia.")
            ctx.evaluar(v["ref_distancia1"])
            ctx.evaluar(v["ref_distancia2"])
            ref_cara, ref_aristas = ref1(v, "ref_cara"), [ref1(v, "ref_arista1"), ref1(v, "ref_arista2")]
        else:
            sel = exigir(v, "colocacion", "Elegí puntos de boceto o hacé clic sobre una cara plana.")
            posiciones = [h["ref"] for h in sel if h["ref"]["tipo"] != "cara"]
            puntos_cara = [{"cara": h["ref"], "punto": [float(c) for c in np.asarray(h.get("punto"), float)]}
                           for h in sel if h["ref"]["tipo"] == "cara" and h.get("punto") is not None]
        hasta = None
        if v.get("extension") == "hasta":
            hasta = ref1(v, "hasta")
            if hasta is None:
                raise ErrorComando("Elegí la cara, el plano o el cuerpo donde termina el agujero.")
        designacion, clase = self._rosca_elegida(v)
        params = {k: v[k] for k in ("tipo", "diametro", "extension", "profundidad", "punta", "angulo_punta",
                                     "diam_abocardado", "prof_abocardado", "diam_avellanado", "angulo_avellanado",
                                     "invertir", "holgura_3d", "mano", "ajuste", "desfase_hasta",
                                     "ref_distancia1", "ref_distancia2") if k in v}
        params["rosca"] = self._rosca_del_paso(v)
        return self.crear_op(OpAgujero, v, ctx, posiciones=posiciones, puntos_cara=puntos_cara, objetivos=objetivos(v),
                             designacion=designacion, clase_rosca=clase, hasta=hasta, ref_cara=ref_cara,
                             ref_aristas=ref_aristas, **params)

    def manipuladores(self, ctx, v):
        """Flecha de profundidad en el primer agujero: sale del fondo y apunta hacia el material."""
        from .. import manipuladores as mp
        posicion = v.get("posicion") or "punto"
        if not v.get({"punto": "colocacion", "boceto": "puntos_boceto", "referencias": "ref_cara"}[posicion]):
            return []
        try:
            cols = self.construir(v, ctx)._colocaciones(ctx.estado, ctx)
        except Exception:  # noqa: BLE001 — sin colocación válida no hay flecha ni asas
            return []
        asas = []
        if v.get("extension") == "distancia":
            asas.append(mp.Flecha("profundidad", cols[0][0], cols[0][1], minimo=0.0))
        if self._rosca_del_paso(v) in ("simple", "cosmetica"):
            # como Fusion: asa en el borde del agujero que se tira para agrandarlo (el valor es el diámetro)
            radial, _ = mp.perpendiculares(cols[0][1])
            asas.append(mp.AsaRadial("diametro", cols[0][0], radial, factor=0.5, minimo=0.1))
        if posicion != "punto":
            return asas
        # un aro por cada agujero puesto con un clic sobre una cara: se arrastra por la cara
        sel = v["colocacion"]
        n_fijos = sum(1 for h in sel if h["ref"]["tipo"] != "cara")
        por_cara = [i for i, h in enumerate(sel) if h["ref"]["tipo"] == "cara" and h.get("punto") is not None]
        for k, i in enumerate(por_cara):
            if n_fijos + k >= len(cols):
                break
            punto, direccion = cols[n_fijos + k]

            forma_cara = self._forma_cara(sel[i], ctx)

            def al_mover(q, i=i, forma_cara=forma_cara):
                if forma_cara is not None and not mp.punto_en_cara(forma_cara, q):
                    return {}                      # el agujero no sale de la cara
                actual = list(v["colocacion"])
                actual[i] = dict(actual[i], punto=np.asarray(q, float))
                return {"colocacion": actual}
            asas.append(mp.Posicion(f"agujero{i}", punto, direccion, al_mover,
                                    candidatos=self._enganches(sel[i], ctx)))
        return asas

    @staticmethod
    def _forma_cara(hit, ctx):
        from .. import manipuladores as mp
        e = mp.entidad(hit, ctx.estado)
        return e.forma if e is not None else None

    @staticmethod
    def _enganches(hit, ctx):
        """Puntos de enganche de la cara del hit: su centro, esquinas, puntos medios y centros de arcos."""
        from .. import manipuladores as mp
        e = mp.entidad(hit, ctx.estado)
        if e is None or e.forma is None:
            return []
        try:
            return mp.puntos_enganche_cara(e.forma)
        except Exception:  # noqa: BLE001 — sin candidatos, el agujero se mueve libre
            return []

    def ajustar_hit(self, campo, hit, ctx, visor):
        """Al hacer clic en una cara, el punto se engancha al centro de la cara (o a una esquina, un punto
        medio…) si queda a menos de ENGANCHE_PX píxeles, como Fusion."""
        from .. import manipuladores as mp
        if campo.clave != "colocacion" or hit["ref"].get("tipo") != "cara" or hit.get("punto") is None:
            return None
        cands = self._enganches(hit, ctx)
        if not cands:
            return None
        click = np.asarray(hit["punto"], float)
        s, ok = visor.puntos_pantalla(np.array([c[0] for c in cands] + [click], float))
        s, ok = np.asarray(s, float), np.asarray(ok, bool)
        if not ok[-1]:
            return None
        d = np.linalg.norm(s[:-1] - s[-1], axis=1)
        d[~ok[:-1]] = np.inf
        i = int(np.argmin(d))
        if d[i] > mp.ENGANCHE_PX:
            return None
        return dict(hit, punto=np.asarray(cands[i][0], float))

    def previa_vista(self, ctx, v, op):
        """Como Fusion, el agujero se ve en ROJO mientras el diálogo está abierto (lo que se va a quitar). La rosca
        modelada se dibuja con su agujero liso (sin el surco: es lo lento)."""
        from .. import manipuladores as mp
        return mp.herramientas_rojas(op.herramientas(ctx.estado, ctx, rapido=True))

    def desde_op(self, op, ctx):
        p = op.p
        v = dict(p)
        if p.get("ref_cara"):
            v["posicion"] = "referencias"
        elif p.get("posiciones") and not p.get("puntos_cara") and all(
                isinstance(r, dict) and r.get("tipo") == "punto_boceto" for r in p["posiciones"]):
            v["posicion"] = "boceto"
        else:
            v["posicion"] = "punto"
        sel = hits(p["posiciones"], ctx.estado)
        if v["posicion"] == "boceto":
            v["puntos_boceto"], sel = sel, []
        for d in p.get("puntos_cara") or []:
            h = hit_desde_ref(d["cara"], ctx.estado)
            h["punto"] = np.asarray(d["punto"], float)
            sel.append(h)
        v["colocacion"] = sel
        v["ref_cara"] = _h1(p.get("ref_cara"), ctx.estado)
        aristas = list(p.get("ref_aristas") or []) + [None, None]
        v["ref_arista1"], v["ref_arista2"] = _h1(aristas[0], ctx.estado), _h1(aristas[1], ctx.estado)
        v["hasta"] = _h1(p.get("hasta"), ctx.estado)
        rosca = p.get("rosca")
        if rosca == "modelada":
            v.update(rosca="cosmetica", rosca_modelada=True)
        if rosca == "holgura":
            v["tam_holgura"] = p.get("designacion")
        elif rosca == "conico":
            v.update(_valores_rosca(p.get("designacion"), "tipo_conica"))
        else:
            v.update(_valores_rosca(p.get("designacion"), "tipo_rosca", p.get("clase_rosca") or ""))
        return _con_objetivos(op, ctx, v)


class Rosca(Comando):
    CLAVE, TITULO, ICONO = "rosca", "Rosca", "rosca"
    AYUDA = ("Rosca sobre caras cilíndricas: tipo (métrica, unificada, trapezoidal, ACME, tubería), tamaño "
             "(automático o de la lista), designación, clase de tolerancia y holgura para impresión 3D; cosmética o "
             "modelada. «Recordar tamaño» vuelve a proponer el último tipo y tamaño elegidos.")
    CLASE_OP = OpRosca
    _recuerdo = {}           # «Recordar tamaño»: lo último elegido con la casilla marcada (vale en la sesión)

    def campos(self, ctx):
        modelada = lambda v: bool(v.get("modelada"))  # noqa: E731
        recuerdo = dict(Rosca._recuerdo)
        return [Seleccion("caras", "Caras", {"cara"}, maximo=None),
                Casilla("modelada", "Modelado"),
                Casilla("largo_completo", "Longitud completa", True),
                Expresion("longitud", "Longitud", "10 mm", visible_si=lambda v: not v.get("largo_completo")),
                Personalizado("biblioteca", "Biblioteca", self._fila_biblioteca),
                *_campos_rosca("tipo_rosca", _familias(), lambda v: True, recuerdo, automatico=True,
                               tipos=lambda v: _tipos_rosca(v, ctx)),
                Info("info_rosca", "Detalle de rosca", self._info),
                Opciones("mano", "Dirección", {"derecha": "Mano derecha", "izquierda": "Mano izquierda"}),
                Casilla("recordar", "Recordar tamaño", bool(recuerdo)),
                Casilla("invertir", "Invertir", avanzado=True),
                Expresion("desfase", "Desfase de inicio", "0 mm", visible_si=lambda v: not v.get("largo_completo"),
                          avanzado=True),
                Expresion("holgura_3d", "Holgura impresión 3D", "0 mm", visible_si=modelada, avanzado=True,
                          ayuda="Desfase radial extra de los flancos, para que la rosca impresa enrosque.")]

    def _fila_biblioteca(self, panel):
        w = QWidget()
        fila = QHBoxLayout(w)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.addWidget(QLabel("Pública"), 1)
        w.mas = QToolButton(objectName="opcion_cmd", text="…", toolTip="Abrir la biblioteca de roscas", accessibleName="Abrir la biblioteca de roscas")
        w.mas.clicked.connect(lambda: self._abrir_biblioteca(panel))
        fila.addWidget(w.mas)
        return w

    def _abrir_biblioteca(self, panel):
        dlg = panel.biblioteca = BibliotecaRoscas(panel, _tipos_rosca(panel.valores, panel.ctx), panel.valores.get("tipo_rosca"))

        def aplicar():
            d = _sc().datos_rosca(dlg.elegida())
            panel.set_valores({"tipo_rosca": d["familia"], f"tam_{d['familia']}": d["tamano"], "des_tipo_rosca": d["designacion"]})
        dlg.accepted.connect(aplicar)
        dlg.open()

    def _info(self, v, ctx):
        designacion = _designacion(v, "tipo_rosca", automatico=True)
        fam = v.get("tipo_rosca") or "iso_metrica"
        if not designacion:
            return "Tamaño automático: el de la lista más cercano al diámetro de la cara."
        datos = _sc().datos_rosca(designacion)
        texto = _texto_rosca_basica(datos)
        if datos["conica"]:
            return texto + " · sobre una cara cilíndrica va cosmética"
        return texto + " · " + _texto_limites(fam, datos, _clase(v, "tipo_rosca"), _interna_de(v, ctx))

    def construir(self, v, ctx):
        exigir(v, "caras", "Seleccioná las caras cilíndricas.")
        fam = v.get("tipo_rosca") or "iso_metrica"
        if v.get("recordar"):
            Rosca._recuerdo = {k: x for k, x in v.items() if k == "tipo_rosca" or k.startswith(("tam_", "des_",
                                                                                                    "clase_"))}
        return self.crear_op(OpRosca, v, ctx, caras=refs(v, "caras"), designacion=_designacion(v, "tipo_rosca", True),
                             familia=fam, clase_rosca=_clase(v, "tipo_rosca"), holgura_3d=v.get("holgura_3d") or "0 mm",
                             **{k: v[k] for k in ("largo_completo", "longitud", "desfase", "modelada", "mano",
                                                  "invertir")})

    def desde_op(self, op, ctx):
        v = dict(op.p, caras=hits(op.p["caras"], ctx.estado))
        fam = op.p.get("familia") or "iso_metrica"
        if op.p.get("designacion"):
            v.update(_valores_rosca(op.p["designacion"], "tipo_rosca", op.p.get("clase_rosca") or ""))
        else:
            v.update({"tipo_rosca": fam, f"tam_{fam}": "auto"})
            if fam in _CLASES:
                v[f"clase_{fam}"] = op.p.get("clase_rosca") or ""
        return v


class Bobina(Comando):
    CLAVE, TITULO, ICONO = "bobina", "Bobina", "bobina"
    AYUDA = "Resorte, hélice o espiral plana con sección circular, cuadrada o triangular."
    CLASE_OP = OpBobina

    def campos(self, ctx):
        t = lambda *x: (lambda v: v.get("tipo") in x)  # noqa: E731
        return [Seleccion("plano", "Plano", {"plano", "cara_plana"}, minimo=0,
                          ayuda="Clic en un plano o una cara: el centro queda donde hacés clic y mover da el diámetro. Sin selección: plano XY."),
                Seleccion("centro", "Centro", {"punto", "vertice"}, minimo=0, visible_si=lambda v: bool(v.get("centro")),
                          ayuda="Un paso viejo con su centro en un punto."),
                Opciones("tipo", "Tipo", {"rev_altura": "Revolución y altura", "rev_paso": "Revolución y paso",
                                          "altura_paso": "Altura y paso", "espiral": "Espiral"}),
                Alternar("horario", "Giro", "cambiar_direccion", ayuda="Cambia el sentido de giro: horario o antihorario."),
                Expresion("diametro", "Diámetro", "20 mm"),
                Expresion("revoluciones", "Revoluciones", "5", ESCALAR, visible_si=t("rev_altura", "rev_paso", "espiral")),
                Expresion("altura", "Altura", "30 mm", visible_si=t("rev_altura", "altura_paso")),
                Expresion("paso", "Paso", "6 mm", visible_si=t("rev_paso", "altura_paso", "espiral")),
                Expresion("angulo", "Ángulo", "0 deg", ANGULO, visible_si=lambda v: v.get("tipo") != "espiral"),
                Opciones("seccion", "Sección", SECCIONES_BOBINA),
                Opciones("posicion", "Posición de sección", {"sobre": ("En el centro", "pos_centro"),
                                                             "dentro": ("Interior", "pos_interior"),
                                                             "fuera": ("Exterior", "pos_exterior")}),
                Expresion("tamano", "Tamaño de sección", "3 mm"),
                campo_operacion(), campo_objetivos(),
                Casilla("girar", "Rotar 90° en Y local", ayuda="Rota la bobina 90° alrededor de su eje Y local.", avanzado=True)]

    @staticmethod
    def _clic(v):
        """El punto del clic sobre el plano (None sin clic)."""
        punto = (v.get("plano") or [{}])[0].get("punto")
        return None if punto is None or v.get("centro") else [float(x) for x in punto]

    def al_elegir(self, panel, clave):
        from .. import manipuladores as mp
        punto, gestor = self._clic(panel.valores), panel.manipuladores
        if clave != "plano" or punto is None or panel.ctx.op is not None or gestor is None:
            return
        o = np.array(punto)
        normal = mp.entidad(panel.valores["plano"][0], panel.ctx.estado).plano.normal
        gestor.trazo = mp.Trazo(o, normal, lambda q: {"diametro": max(2 * float(np.linalg.norm(q - o)), 0.01)})

    def manipuladores(self, ctx, v):
        from ...nucleo import geometria as geo
        from .. import manipuladores as mp
        e = mp.entidad(v["plano"][0], ctx.estado) if v.get("plano") else None
        plano = e.plano if e is not None and e.plano is not None else geo.Plano("XY")
        centro = self._clic(v) or plano.origen
        return [mp.AsaRadial("diametro", centro, plano.u, factor=0.5, minimo=0.01)]

    def construir(self, v, ctx):
        ctx.evaluar(v["diametro"])
        return self.crear_op(OpBobina, v, ctx, plano=ref1(v, "plano"), centro=ref1(v, "centro"), centro_xyz=self._clic(v), objetivos=objetivos(v),
                             **{k: v[k] for k in ("diametro", "tipo", "revoluciones", "altura", "paso", "angulo",
                                                  "seccion", "tamano", "posicion", "horario", "girar", "operacion")})

    def desde_op(self, op, ctx):
        plano = [dict(h, punto=op.p["centro_xyz"]) if op.p.get("centro_xyz") else h for h in _h1(op.p["plano"], ctx.estado)]
        return _con_objetivos(op, ctx, dict(op.p, plano=plano, centro=_h1(op.p["centro"], ctx.estado)))


class Tuberia(Comando):
    CLAVE, TITULO, ICONO = "tuberia", "Tubería", "tuberia"
    AYUDA = "Caño de sección circular, cuadrada o triangular a lo largo de una ruta."
    CLASE_OP = OpTuberia

    def campos(self, ctx):
        return [Seleccion("ruta", "Ruta", CURVA, maximo=None), Casilla("cadena", "Selección de cadena", True),
                Opciones("seccion", "Sección", {"circular": ("Circular", "sec_circular"), "cuadrada": ("Cuadrado", "sec_cuadrada"),
                                                "triangular": ("Triangular", "sec_tri_externa")}),
                Expresion("tamano", "Tamaño de la sección", "5 mm"),
                Casilla("hueca", "Hueco"),
                Expresion("espesor", "Espesor de sección", "0.5 mm", visible_si=lambda v: bool(v.get("hueca"))),
                Expresion("distancia2", "Distancia inicial", "0.00", ESCALAR, avanzado=True,
                          ayuda="Inicio de la ruta: fracción entre 0 y 1."),
                Expresion("distancia", "Distancia final", "1.00", ESCALAR, avanzado=True,
                          ayuda="Fin de la ruta: fracción entre 0 y 1."),
                campo_operacion(), campo_objetivos()]

    def construir(self, v, ctx):
        exigir(v, "ruta", "Seleccioná la ruta.")
        return self.crear_op(OpTuberia, v, ctx, ruta=refs(v, "ruta"), objetivos=objetivos(v),
                             **{k: v[k] for k in ("cadena", "distancia", "distancia2", "seccion", "tamano", "hueca",
                                                  "espesor", "operacion")})

    def desde_op(self, op, ctx):
        return _con_objetivos(op, ctx, dict(op.p, ruta=hits(op.p["ruta"], ctx.estado)))


def _de_cuerpos(v):
    return v.get("objeto", "cuerpos") == "cuerpos"


def _objeto_es(clase):
    return lambda v: v.get("objeto", "cuerpos") == clase


def campos_objeto():
    """«Tipo de objeto» de Fusion para Patrón, Multitransformación y Simetría: cuerpos y caras (se eligen en la vista),
    operaciones (pasos anteriores del timeline, por nombre o id: el agujero, la extrusión que corta…), componentes
    (por nombre o id) y geometría de construcción (planos, ejes y puntos)."""
    return [Opciones("objeto", "Tipo de objeto", {"cuerpos": "Cuerpos", "operaciones": "Operaciones", "caras": "Caras",
                                                  "componentes": "Componentes",
                                                  "construccion": "Geometría de construcción"}),
            Seleccion("cuerpos", "Objetos (cuerpos)", {"cuerpo"}, maximo=None, visible_si=_de_cuerpos),
            Texto("pasos", "Operaciones", "", visible_si=_objeto_es("operaciones"),
                  ayuda="Tocá los pasos en el timeline (o escribí sus nombres, separados por coma). Valen los que cortan, "
                        "unen o crean con una herramienta: " + ", ".join(TIPOS_REPETIBLES) + "."),
            Opciones("calculo", "Tipo de cálculo", {"identico": "Idéntico", "optimizado": "Optimizado", "ajustar": "Ajustar"},
                     visible_si=_objeto_es("operaciones"),
                     ayuda="Idéntico copia la herramienta del paso tal cual; Optimizado da lo mismo repitiendo las caras de "
                           "una copia, más rápido, si las copias no tocan nada más; Ajustar omite las copias que ya no "
                           "tocan al cuerpo."),
            Seleccion("caras", "Caras", {"cara"}, maximo=None, visible_si=_objeto_es("caras"),
                      ayuda="Cada copia queda como un cuerpo de superficie nuevo."),
            Texto("componentes", "Componentes (nombres o ids, separados por coma)", "", visible_si=_objeto_es("componentes"),
                  ayuda="Cada copia es un componente nuevo con copias de los cuerpos."),
            Seleccion("construccion", "Geometría de construcción", {"plano", "eje", "punto"}, maximo=None,
                      visible_si=_objeto_es("construccion"), ayuda="Cada copia es un plano, eje o punto nuevo.")]


def tocar_paso(panel, op_id):
    """Clic en un paso del timeline con «Tipo de objeto» Operaciones: lo suma al campo, o lo saca si ya estaba."""
    if panel.valores.get("objeto") != "operaciones" or not panel._visible(panel._por_clave["pasos"]):
        return
    op = next((o for o in panel.ctx.doc.operaciones[:panel.ctx.indice] if o.id == op_id), None)
    if op is None:
        panel._mostrar("Ese paso está después de este en el timeline.", tipo="aviso")
        return
    nombres = [x.strip() for x in str(panel.valores.get("pasos") or "").replace(";", ",").split(",") if x.strip()]
    panel.set_valor("pasos", ", ".join(x for x in nombres if x.casefold() != op.nombre.casefold())
                    if op.nombre.casefold() in [x.casefold() for x in nombres] else ", ".join([*nombres, op.nombre]))


def pasos_repetibles(texto, ctx):
    """Ids de los pasos escritos en el campo «Operaciones» (nombres o ids separados por coma): tienen que estar antes
    del paso que se crea o edita y ser de un tipo que deja su herramienta (TIPOS_REPETIBLES)."""
    anteriores = ctx.doc.operaciones[:ctx.indice]
    ids = []
    for nombre in (x.strip() for x in str(texto or "").replace(";", ",").split(",")):
        if not nombre:
            continue
        op = next((o for o in anteriores if o.id == nombre), None) or next(
            (o for o in anteriores if o.nombre.casefold() == nombre.casefold()), None)
        if op is None:
            raise ErrorComando(f"No hay un paso «{nombre}» antes de este en el timeline.")
        if op.TIPO not in TIPOS_REPETIBLES or (op.TIPO in ("patron", "multitransformar")
                                               and op.p.get("objeto") != "operaciones"):
            raise ErrorComando(f"«{op.nombre}» ({op.ETIQUETA}) no deja una herramienta para repetir. Se repiten: "
                               + ", ".join(TIPOS_REPETIBLES) + " (patrones, solo los de operaciones).")
        ids.append(op.id)
    if not ids:
        raise ErrorComando("Escribí las operaciones a repetir (nombres del timeline, separados por coma).")
    return ids


def componentes_escritos(texto, ctx):
    """Ids de los componentes escritos en el campo «Componentes» (nombres o ids separados por coma)."""
    from ...timeline.operaciones import ErrorOperacion
    from ...timeline.ops_ensamblar import componente_por_ref
    ids = []
    for nombre in (x.strip() for x in str(texto or "").replace(";", ",").split(",")):
        if not nombre:
            continue
        try:
            k = componente_por_ref(ctx.estado, nombre)
        except ErrorOperacion as e:                      # dos componentes con ese nombre: pide el id
            raise ErrorComando(str(e)) from None
        if k is None:
            raise ErrorComando(f"No hay un componente «{nombre}».")
        ids.append(k)
    if not ids:
        raise ErrorComando("Escribí los componentes a repetir (nombres o ids, separados por coma).")
    return ids


def objeto_params(v, ctx):
    """objeto y lo que repite (cuerpos, pasos, caras, componentes o construcción) según el «Tipo de objeto»."""
    objeto = v.get("objeto", "cuerpos")
    if objeto == "operaciones":
        return {"objeto": "operaciones", "cuerpos": [], "pasos": pasos_repetibles(v.get("pasos"), ctx),
                "calculo": v.get("calculo", "identico")}
    if objeto == "caras":
        exigir(v, "caras", "Seleccioná las caras.")
        return {"objeto": "caras", "cuerpos": [], "pasos": [], "caras": refs(v, "caras")}
    if objeto == "componentes":
        return {"objeto": "componentes", "cuerpos": [], "pasos": [],
                "componentes": componentes_escritos(v.get("componentes"), ctx)}
    if objeto == "construccion":
        exigir(v, "construccion", "Seleccioná los planos, ejes o puntos de construcción.")
        return {"objeto": "construccion", "cuerpos": [], "pasos": [], "construccion": refs(v, "construccion")}
    exigir(v, "cuerpos", "Seleccioná los cuerpos.")
    return {"objeto": "cuerpos", "cuerpos": _cuerpos(v["cuerpos"]), "pasos": []}


def _nombre_unico_de_componente(estado, k):
    """El nombre del componente `k` si nadie más lo tiene; si no, su id (el campo se vuelve a leer por nombre)."""
    nombre = str(estado.componentes.get(k, {}).get("nombre") or "")
    repetido = sum(str(c.get("nombre") or "").casefold() == nombre.casefold() for c in estado.componentes.values()) > 1
    return k if not nombre or repetido else nombre


def objeto_valores(op, ctx):
    """Los valores de los campos de `campos_objeto` desde una operación guardada."""
    nombres = {o.id: o.nombre for o in ctx.doc.operaciones}
    return {"objeto": op.p.get("objeto", "cuerpos"), "cuerpos": _hits_cuerpos(op.p.get("cuerpos") or [], ctx.estado),
            "pasos": ", ".join(nombres.get(i, i) for i in op.p.get("pasos") or []),
            "calculo": op.p.get("calculo", "identico"), "caras": hits(op.p.get("caras") or [], ctx.estado),
            "componentes": ", ".join(_nombre_unico_de_componente(ctx.estado, k) for k in op.p.get("componentes") or []),
            "construccion": hits(op.p.get("construccion") or [], ctx.estado)}


DIRECCION = {"eje", "arista_lineal", "plano", "cara_plana"}
EJE_GIRO = {"eje", "arista_circular", "curva_boceto"}          # línea, arista recta o circular, eje, cara cilíndrica, círculo de boceto
FORMAS_PATRON = {"rectangular": "Rectangular", "circular": "Circular", "ruta": "En trayectoria", "puntos": "En puntos"}
MODOS_CIRCULAR = {"completo": "Completo (360°)", "parcial": "Parcial", "simetrico": "Simétrico",
                  "espaciado": "Ángulo entre copias"}
COLOR_DIRECCION_DERIVADA = (0.1, 0.62, 0.55)


# ---------------------------------------------------------------- copias suprimidas: texto ⇄ identificadores
def suprimir_a_texto(forma, suprimir):
    """Lo que se ve en el campo «Copias suprimidas»: pares «i:j» en el rectangular, números en el resto."""
    if forma == "rectangular":
        pares = [(int(s[0]), int(s[1])) if isinstance(s, (list, tuple)) else (int(s), 0) for s in suprimir or []]
        return ", ".join(f"{i}:{j}" for i, j in pares)
    return ", ".join(str(int(s)) for s in suprimir or [])


def texto_a_suprimir(forma, texto):
    """Identificadores de instancia del campo «Copias suprimidas»: [i, j] en el rectangular («2:1»; un «2» solo es el
    (2, 0)) y enteros en el resto. Sin repetir; el original (0) no se puede suprimir."""
    salida = []
    for tok in str(texto or "").replace(";", ",").split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            if forma == "rectangular":
                i, _, j = tok.partition(":")
                ident = [int(i), int(j or 0)]
            else:
                ident = int(tok)
        except ValueError:
            ejemplo = "«2:1» (paso i en la dirección 1 : paso j en la 2)" if forma == "rectangular" else "números enteros"
            raise ErrorComando(f"En «Copias suprimidas» van {ejemplo} separados por coma; «{tok}» no sirve.") from None
        if ident in (0, [0, 0]):
            raise ErrorComando("El original no se puede suprimir (es el cuerpo fuente).")
        if ident not in salida:
            salida.append(ident)
    return salida


def _numero_limpio(x):
    return f"{round(float(x), 10):.10f}".rstrip("0").rstrip(".") or "0"


def porcentaje_a_fraccion(texto):
    """El «Punto de inicio (%)» del diálogo → la fracción 0 a 1 que guarda la receta (una expresión se divide por 100)."""
    texto = str(texto if texto not in (None, "") else "0").strip().rstrip("% ")           # «25 %» también vale
    try:
        return _numero_limpio(float(texto.replace(",", ".")) / 100)
    except ValueError:
        return f"({texto})/100"


def fraccion_a_porcentaje(valor):
    """La fracción 0 a 1 de la receta → lo que muestra el campo en porcentaje (las recetas viejas siguen igual)."""
    texto = str(valor if valor not in (None, "") else "0").strip()
    try:
        return _numero_limpio(float(texto.replace(",", ".")) * 100)
    except ValueError:
        return f"({texto})*100"


def _cantidad(v, clave):
    try:
        return int(v.get(clave) or 1)
    except (TypeError, ValueError):
        return 1


def direccion_derivada(ctx, v, pre=""):
    """La dirección 2 derivada del rectangular (perpendicular a la 1; dentro del plano elegido si hay uno)."""
    plano = ent.como_plano(ent.resolver(v[pre + "plano_dir2"][0]["ref"], ctx.estado)) if v.get(pre + "plano_dir2") else None
    return ent.direccion_perpendicular(ent.resolver(v[pre + "dir1"][0]["ref"], ctx.estado), plano)


def _info_dir2(pre):
    def texto(v, ctx):
        if v.get(pre + "dir2"):
            return "La elegida."
        try:
            d = direccion_derivada(ctx, v, pre)
        except ent.ErrorReferencia as e:
            return str(e)
        except Exception:  # noqa: BLE001 — sin dirección 1 todavía
            return "Dirección derivada: perpendicular a la 1 (elegí la 1)."
        donde = "dentro del plano elegido" if v.get(pre + "plano_dir2") else "perpendicular a la 1"
        return f"Dirección derivada, {donde}: ({d[0]:.2f}, {d[1]:.2f}, {d[2]:.2f}) · flecha verde"
    return texto


def _info_circular(pre):
    def texto(v, ctx):
        from ...nucleo import solidos_crear as sc
        try:
            n, modo = _cantidad(v, pre + "n"), v.get(pre + "modo", "completo")
            if modo == "completo":
                total, extra = 360.0, ""
            else:
                total = ctx.evaluar(v.get(pre + ("angulo_paso" if modo == "espaciado" else "angulo")), ANGULO)
                extra = ""
            simetrico = modo == "simetrico" or (modo == "espaciado" and bool(v.get(pre + "simetrico_paso")))
            paso = sc.paso_angular(n, total, "espaciado" if modo == "espaciado" else "completa", simetrico)
            if modo == "parcial" and abs(abs(total) - 360.0) < 1e-9:
                extra = " 360° es una vuelta completa: igual que «Completo»."
            ks = sc._indices(n, simetrico, -1 if simetria_total(ctx) else 0)
            return f"Copias a {', '.join(f'{k * paso:g}°' for k in ks[:8])}{'…' if len(ks) > 8 else ''}.{extra}"
        except Exception:  # noqa: BLE001 — valores a medio escribir: lo dice la vista previa
            return ""
    return texto


def _info_puntos(v, ctx):
    ref = "el punto de referencia elegido" if v.get("referencia") else "el origen (0, 0, 0)"
    return (f"Cada copia lleva {ref} a uno de los puntos (cruz verde = referencia, cruces azules = destinos). "
            "Un boceto entero aporta solo sus puntos sueltos, no los extremos de sus curvas.")


def campos_patron(pre="", forma=None):
    """Campos de cada tipo de patrón (rectangular, circular, en trayectoria y en puntos) con las claves prefijadas con
    `pre`; `forma(v)` dice qué tipo está activo. Los usan el diálogo del Patrón y cada transformación de la
    Multitransformación (pre = «t_»)."""
    forma = forma or (lambda v: v.get("forma"))
    k = lambda c: pre + c                                                      # noqa: E731
    en = lambda *fs: (lambda v: forma(v) in fs)                                # noqa: E731
    cuando = lambda f, test: (lambda v: forma(v) == f and test(v))             # noqa: E731
    n1_mayor = lambda v: _cantidad(v, k("n1")) > 1                             # noqa: E731
    n2_mayor = lambda v: _cantidad(v, k("n2")) > 1                             # noqa: E731
    rn_mayor = lambda v: _cantidad(v, k("rn")) > 1                             # noqa: E731
    modo = lambda *ms: (lambda v: v.get(k("modo"), "completo") in ms)          # noqa: E731
    dist = lambda v: v.get(k("distribucion"), "extension")                      # noqa: E731
    total = lambda v: "Extensión total" if dist(v) == "extension" else "Separación entre instancias"   # noqa: E731
    return [
        Opciones(k("distribucion"), "Distribución", {"extension": "Extensión", "espaciado": "Espaciado"},
                 visible_si=en("rectangular", "ruta"),
                 ayuda="Extensión: la distancia es el largo total de la primera a la última copia. Espaciado: es la "
                       "separación entre copias consecutivas."),
        Seleccion(k("dir1"), "Dirección", DIRECCION, visible_si=en("rectangular"), grupo="Dirección 1"),
        Entero(k("n1"), "Cantidad", 3, 1, visible_si=en("rectangular"), grupo="Dirección 1"),
        Expresion(k("d1"), "Extensión total", "30 mm", visible_si=cuando("rectangular", n1_mayor), grupo="Dirección 1",
                  etiqueta_si=total),
        Casilla(k("simetrico"), "Simétrico", visible_si=cuando("rectangular", n1_mayor), grupo="Dirección 1",
                ayuda="La cantidad es el total con el original, repartido a los dos lados; si es par, la de más va "
                      "hacia adelante. En Extensión, la medida es por lado."),
        Seleccion(k("dir2"), "Dirección (opcional)", DIRECCION, minimo=0, visible_si=en("rectangular"), grupo="Dirección 2",
                  ayuda="Vacía = la perpendicular a la dirección 1 (derivada). Elegí un eje o una arista para cambiarla."),
        Entero(k("n2"), "Cantidad", 1, 1, visible_si=en("rectangular"), grupo="Dirección 2",
               ayuda="1 = solo la dirección 1. Con más de 1 se muestra la dirección 2."),
        Seleccion(k("plano_dir2"), "Plano de referencia", {"plano", "cara_plana"}, minimo=0,
                  visible_si=lambda v: forma(v) == "rectangular" and _cantidad(v, k("n2")) > 1 and not v.get(k("dir2")),
                  grupo="Dirección 2",
                  ayuda="Vacío = la dirección 2 derivada sale del boceto, la cara o el eje de la dirección 1. Con un plano o "
                        "una cara plana, la dirección 2 es la perpendicular a la 1 dentro de ese plano."),
        Info(k("info_dir2"), "", _info_dir2(pre), visible_si=cuando("rectangular", n2_mayor), grupo="Dirección 2"),
        Expresion(k("d2"), "Extensión total", "30 mm", visible_si=cuando("rectangular", n2_mayor), grupo="Dirección 2",
                  etiqueta_si=total),
        Casilla(k("simetrico2"), "Simétrico", visible_si=cuando("rectangular", n2_mayor), grupo="Dirección 2"),
        Seleccion(k("eje"), "Eje", EJE_GIRO, visible_si=en("circular"),
                  ayuda="Una línea, una arista recta o circular, un eje de construcción, una cara cilíndrica o un "
                        "círculo de boceto: gira alrededor de su eje."),
        Opciones(k("modo"), "Distribución", MODOS_CIRCULAR, "completo", visible_si=en("circular"),
                 ayuda="Completo: 360° sin repetir el cierre. Parcial: hasta el ángulo total, a un lado. Simétrico: la "
                       "cantidad y el ángulo son el total, repartido a los dos lados del original. Espaciado: se da el "
                       "ángulo entre copias, no el total."),
        Entero(k("n"), "Cantidad", 6, 1, visible_si=en("circular")),
        Expresion(k("angulo"), "Ángulo total", "180 deg", ANGULO, visible_si=cuando("circular", modo("parcial", "simetrico"))),
        Expresion(k("angulo_paso"), "Ángulo entre instancias", "30 deg", ANGULO,
                  visible_si=cuando("circular", modo("espaciado"))),
        Casilla(k("simetrico_paso"), "A los dos lados del original", visible_si=cuando("circular", modo("espaciado"))),
        Info(k("info_circular"), "", _info_circular(pre), visible_si=en("circular")),
        Seleccion(k("ruta"), "Ruta", CURVA, maximo=None, visible_si=en("ruta"),
                  ayuda="Una o varias aristas o curvas de boceto seguidas: el patrón recorre toda la cadena."),
        Entero(k("rn"), "Cantidad", 3, 1, visible_si=en("ruta")),
        Expresion(k("rd"), "Extensión total", "30 mm", visible_si=cuando("ruta", rn_mayor), etiqueta_si=total),
        Casilla(k("r_simetrico"), "Simétrico", visible_si=cuando("ruta", rn_mayor)),
        Opciones(k("orientacion"), "Orientación", {"identica": "Idéntica", "direccion_ruta": "Dirección de ruta"},
                 visible_si=en("ruta")),
        Expresion(k("inicio"), "Punto de inicio (%)", "0", ESCALAR, visible_si=en("ruta"), avanzado=True,
                  ayuda="Dónde está el original sobre la ruta, en porcentaje de su largo: 0 es su principio y 100 su "
                        "final. Se ve como el disco que se desliza por la ruta."),
        Expresion(k("giro"), "Giro total alrededor de la ruta", "0 deg", ANGULO, visible_si=en("ruta"), avanzado=True,
                  ayuda="Cada copia gira alrededor de la ruta, de a poco, hasta este ángulo en la última."),
        Seleccion(k("puntos"), "Puntos", {"punto_boceto", "vertice", "punto", "boceto"}, maximo=None,
                  visible_si=en("puntos"),
                  ayuda="Destinos: puntos de boceto, vértices, puntos de construcción o un boceto entero (sus puntos "
                        "sueltos)."),
        Seleccion(k("referencia"), "Punto de referencia", {"punto_boceto", "vertice", "punto"}, minimo=0,
                  visible_si=en("puntos"),
                  ayuda="El punto que se lleva a cada destino (vacío = el origen). Para repetir un agujero, el punto "
                        "donde está el agujero."),
        Info(k("info_puntos"), "", _info_puntos, visible_si=en("puntos")),
        Texto(k("suprimir"), "Copias suprimidas", "", visible_si=lambda v: forma(v) in FORMAS_PATRON, avanzado=True,
              ayuda="Rectangular: «i:j» (pasos desde el original en cada dirección; 2 solo = 2:0). Circular y en "
                    "trayectoria: el paso (negativo = el otro lado). En puntos: el n.º del punto (1 = el primero). "
                    "Cada número sigue a SU copia aunque cambies las cantidades."),
    ]


def params_patron(v, forma, pre="", estricto=True):
    """Parámetros de OpPatron (sin el objeto) desde los valores de `campos_patron`. Con `estricto` falla si falta lo
    imprescindible (la dirección, el eje, la ruta); sin él deja esos campos vacíos."""
    k = lambda c: pre + c                                                      # noqa: E731
    exigir_ = exigir if estricto else (lambda *_a: None)
    if forma == "rectangular":
        exigir_(v, k("dir1"), "Seleccioná la dirección 1.")
        p = dict(dir1=ref1(v, k("dir1")), dir2=ref1(v, k("dir2")), n1=_cantidad(v, k("n1")), d1=v.get(k("d1")),
                 n2=_cantidad(v, k("n2")), d2=v.get(k("d2")), distribucion=v.get(k("distribucion"), "extension"),
                 simetrico=bool(v.get(k("simetrico"))), simetrico2=bool(v.get(k("simetrico2"))), dir2_derivada=True,
                 plano_dir2=ref1(v, k("plano_dir2")))
    elif forma == "circular":
        exigir_(v, k("eje"), "Seleccioná el eje.")
        modo = v.get(k("modo"), "completo")
        p = dict(eje=ref1(v, k("eje")), n=_cantidad(v, k("n")), distribucion=modo,
                 angulo="360 deg" if modo == "completo" else v.get(k("angulo_paso" if modo == "espaciado" else "angulo")),
                 simetrico=modo == "espaciado" and bool(v.get(k("simetrico_paso"))))
    elif forma == "ruta":
        exigir_(v, k("ruta"), "Seleccioná la ruta.")
        p = dict(ruta=refs(v, k("ruta")), n1=_cantidad(v, k("rn")), d1=v.get(k("rd")),
                 distribucion=v.get(k("distribucion"), "extension"), inicio=porcentaje_a_fraccion(v.get(k("inicio"))),
                 orientacion=v.get(k("orientacion"), "identica"), giro=v.get(k("giro")),
                 simetrico=bool(v.get(k("r_simetrico"))))
    else:
        p = dict(puntos=refs(v, k("puntos")), referencia=ref1(v, k("referencia")))
    p.update(forma_patron=forma, suprimir=texto_a_suprimir(forma, v.get(k("suprimir"))))
    return p


def valores_patron(p, estado, pre=""):
    """Valores de los campos de `campos_patron` desde los parámetros de un OpPatron (o de una transformación). Lo que
    el diálogo no puede mostrar se conserva aparte (ver `crear_patron`)."""
    k = lambda c: pre + c                                                      # noqa: E731
    forma = p.get("forma_patron") or p.get("tipo")
    v = {k("suprimir"): suprimir_a_texto(forma, p.get("suprimir"))}
    if forma == "rectangular":
        n2_ignorada = not p.get("dir2") and not p.get("dir2_derivada", False)   # receta vieja: esa cantidad nunca se aplicó
        sim1 = bool(p.get("simetrico"))
        v.update({k("dir1"): _h1(p.get("dir1"), estado), k("dir2"): _h1(p.get("dir2"), estado),
                  k("plano_dir2"): _h1(p.get("plano_dir2"), estado), k("n1"): p.get("n1", 3), k("d1"): p.get("d1", "30 mm"), k("simetrico"): sim1,
                  k("n2"): 1 if n2_ignorada else p.get("n2", 1), k("d2"): p.get("d2", "30 mm"),
                  k("simetrico2"): sim1 if p.get("simetrico2") is None else bool(p["simetrico2"]),
                  k("distribucion"): p.get("distribucion", "extension")})
    elif forma == "circular":
        dist, sim = p.get("distribucion", "extension"), bool(p.get("simetrico"))
        modo = {"extension": "simetrico" if sim else "parcial"}.get(dist, dist)
        v.update({k("eje"): _h1(p.get("eje"), estado), k("modo"): modo, k("n"): p.get("n", 6),
                  k("simetrico_paso"): dist == "espaciado" and sim})
        v[k("angulo_paso" if modo == "espaciado" else "angulo")] = p.get("angulo", "360 deg")
    elif forma == "ruta":
        v.update({k("ruta"): hits(p.get("ruta"), estado), k("rn"): p.get("n1", 3), k("rd"): p.get("d1", "30 mm"),
                  k("distribucion"): p.get("distribucion", "extension"), k("inicio"): fraccion_a_porcentaje(p.get("inicio", "0")),
                  k("orientacion"): p.get("orientacion", "identica"), k("giro"): p.get("giro", "0 deg"),
                  k("r_simetrico"): bool(p.get("simetrico"))})
    else:
        v.update({k("puntos"): hits(p.get("puntos"), estado), k("referencia"): _h1(p.get("referencia"), estado)})
    return v


class _Patron(Comando):
    """Diálogo único de los cuatro patrones de sólido (rectangular, circular, en trayectoria y en puntos): el «Tipo de
    patrón» se cambia al vuelo (como en Fusion) y las selecciones compatibles se conservan."""
    CLASE_OP = OpPatron
    FORMA = "rectangular"
    MODIFICADORES = {}
    ANCHO_PANEL = "normal"
    TITULOS_MODO = ("forma", {"rectangular": ("Patrón rectangular", "patron_rectangular_3d"),
                              "circular": ("Patrón circular", "patron_circular_3d"),
                              "ruta": ("Patrón en trayectoria", "patron_ruta"),
                              "puntos": ("Patrón en puntos", "patron_puntos")})

    def campos(self, ctx):
        return ([Opciones("forma", "Tipo de patrón", FORMAS_PATRON, self.FORMA)]
                + campos_objeto()
                + campos_patron("")
                + [Casilla("ver_casillas", "Elegir copias a suprimir en la vista", avanzado=True,
                           ayuda="Dibuja una casilla sobre cada copia: tocala para suprimirla o restaurarla."),
                   Casilla("combinar", "Unir al original", visible_si=_de_cuerpos),
                   Casilla("ligeras", "Copias ligeras (comparten la geometría)", avanzado=True,
                           visible_si=lambda v: _de_cuerpos(v) and not v.get("combinar"),
                           ayuda="Cada copia es la MISMA geometría con otra ubicación: pesa casi nada en memoria "
                                 "y en el visor. Para volverlas copias de verdad, destildá la casilla.")])

    def construir(self, v, ctx):
        objeto = objeto_params(v, ctx)
        forma = v.get("forma", self.FORMA)
        if forma == "puntos" and not v.get("puntos") and not (ctx.op is not None and ctx.op.p.get("coordenadas")):
            raise ErrorComando("Seleccioná los puntos.")
        params = params_patron(v, forma)
        params.update(objeto)
        params["combinar"] = bool(v.get("combinar")) and _de_cuerpos(v)
        params["ligeras"] = bool(v.get("ligeras")) and _de_cuerpos(v) and not v.get("combinar")   # la casilla oculta no cuenta
        if forma == "puntos" and ctx.op is not None:                 # lo que el diálogo no muestra (de la API)
            params.update(coordenadas=ctx.op.p.get("coordenadas") or [],
                          referencia_xyz=[] if params["referencia"] else ctx.op.p.get("referencia_xyz") or [])
        return self.crear_op(OpPatron, v, ctx, **params)

    def desde_op(self, op, ctx):
        forma = op.p.get("forma_patron", "rectangular")
        v = dict(valores_patron(op.p, ctx.estado), forma=forma, combinar=op.p.get("combinar", False),
                 ligeras=op.p.get("ligeras", False), **objeto_valores(op, ctx))
        return v

    def al_tocar_paso(self, panel, op_id):
        tocar_paso(panel, op_id)

    def al_cambiar(self, panel, clave):
        """Al pasar el tipo circular a Parcial o Simétrico con los 360° de «Completo», el ángulo se baja (360° sería lo
        mismo que Completo y el panel lo explica en vez de dejar un valor incompatible)."""
        if clave == "modo" and panel.valores.get("modo") in ("parcial", "simetrico"):
            try:
                completo = abs(abs(panel.ctx.evaluar(str(panel.valores.get("angulo")), ANGULO)) - 360.0) < 1e-9
            except Exception:  # noqa: BLE001 — una expresión a medio escribir no se toca
                return
            if completo:
                panel.set_valor("angulo", "180 deg" if panel.valores["modo"] == "parcial" else "90 deg")

    def manipuladores(self, ctx, v):
        from . import asas_patron
        return asas_patron.manipuladores(self, ctx, v)

    def previa_vista(self, ctx, v, op):
        from . import asas_patron
        return asas_patron.previa_vista(self, ctx, v, op)


class PatronRectangular(_Patron):
    CLAVE, TITULO, ICONO, FORMA = "patron_rectangular_3d", "Patrón rectangular", "patron_rectangular_3d", "rectangular"
    AYUDA = "Copias en filas y columnas."
    VARIANTE = ("forma_patron", "rectangular")


class PatronCircular(_Patron):
    CLAVE, TITULO, ICONO, FORMA = "patron_circular_3d", "Patrón circular", "patron_circular_3d", "circular"
    AYUDA = "Copias alrededor de un eje."
    VARIANTE = ("forma_patron", "circular")


class PatronRuta(_Patron):
    CLAVE, TITULO, ICONO, FORMA = "patron_ruta", "Patrón en trayectoria", "patron_ruta", "ruta"
    AYUDA = "Copias a lo largo de una curva."
    VARIANTE = ("forma_patron", "ruta")


class Simetria(Comando):
    CLAVE, TITULO, ICONO = "simetria_3d", "Simetría", "simetria_3d"
    AYUDA = "Copia reflejada de cuerpos respecto de un plano."
    CLASE_OP = OpSimetria

    def al_tocar_paso(self, panel, op_id):
        tocar_paso(panel, op_id)

    def campos(self, ctx):
        return campos_objeto() + [Seleccion("plano", "Plano de simetría", {"plano", "cara_plana"}),
                                  Casilla("combinar", "Unir al original", visible_si=_de_cuerpos)]

    def construir(self, v, ctx):
        objeto = objeto_params(v, ctx)
        exigir(v, "plano", "Seleccioná el plano de simetría.")
        return self.crear_op(OpSimetria, v, ctx, plano=ref1(v, "plano"),
                             combinar=bool(v.get("combinar")) and objeto["objeto"] == "cuerpos", **objeto)

    def desde_op(self, op, ctx):
        return dict(op.p, plano=_h1(op.p["plano"], ctx.estado), **objeto_valores(op, ctx))


class RellenoContorno(Comando):
    CLAVE, TITULO, ICONO = "relleno_contorno", "Llenado de contorno", "relleno_contorno"
    AYUDA = "Rellena con sólido el volumen encerrado por cuerpos, superficies y planos."
    CLASE_OP = OpRellenoContorno

    def campos(self, ctx):
        return [Seleccion("herramientas", "Seleccionar herramientas", {"cuerpo", "cara", "plano"}, maximo=None),
                Personalizado("celdas", "Seleccionar celdas", self._lista_celdas, "1",
                              ayuda="Marcá las celdas en la lista o tocá sus casillas en la vista."),
                campo_operacion(), campo_objetivos(), Casilla("eliminar_herramientas", "Eliminar herramientas")]

    def _celdas(self, v, ctx):
        """Las celdas de las herramientas elegidas (calcularlas es caro: se recuerdan mientras no cambien)."""
        if not v.get("herramientas"):
            return []
        clave = repr(refs(v, "herramientas"))
        if getattr(self, "_recuerdo", (None,))[0] != clave:
            from ...nucleo import solidos_crear
            op = OpRellenoContorno("tmp", herramientas=refs(v, "herramientas"))
            self._recuerdo = clave, solidos_crear.relleno_contorno_celdas(op.formas_herramienta(ctx.estado))
        return self._recuerdo[1]

    @staticmethod
    def _numeros(v):
        """Números de celda elegidos (desde 1) del valor del campo: «1, 3»."""
        try:
            return [int(x) for x in str(v.get("celdas") or "").replace(";", ",").split(",") if x.strip()]
        except ValueError as e:
            raise ErrorComando("Los números de celda van separados por coma.") from e

    def _lista_celdas(self, panel):
        lista = QListWidget(objectName="lista_celdas")
        lista.setMaximumHeight(110)
        lista.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)      # su ancho de fábrica (256 px) ensanchaba el cuerpo del panel y daba barra horizontal
        lista.itemChanged.connect(lambda _i: panel._cambiar("celdas", ", ".join(
            str(i + 1) for i in range(lista.count()) if lista.item(i).checkState() == Qt.Checked)))
        return lista

    def _refrescar_lista(self, panel):
        lista = panel.widgets["celdas"]
        lista.blockSignals(True)
        lista.clear()
        try:
            celdas, elegidas = self._celdas(panel.valores, panel.ctx), self._numeros(panel.valores)
        except Exception:  # noqa: BLE001 — herramientas que no encierran nada: el mensaje lo da la vista previa
            celdas, elegidas = [], []
        for i, c in enumerate(celdas, 1):
            item = QListWidgetItem(f"Celda {i}: {c['volumen']:.1f} mm³", lista)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if i in elegidas else Qt.Unchecked)
        lista.blockSignals(False)

    def preparar_panel(self, panel):
        self._refrescar_lista(panel)

    def al_cambiar(self, panel, clave):
        if clave == "herramientas":
            self._refrescar_lista(panel)
        elif clave == "celdas":
            lista = panel.widgets["celdas"]
            elegidas = self._numeros(panel.valores)
            lista.blockSignals(True)
            for i in range(lista.count()):
                lista.item(i).setCheckState(Qt.Checked if i + 1 in elegidas else Qt.Unchecked)
            lista.blockSignals(False)

    def manipuladores(self, ctx, v):
        """Una casilla sobre cada celda: tocarla la elige o la deja de elegir."""
        from .. import manipuladores as mp
        try:
            celdas, elegidas = self._celdas(v, ctx), self._numeros(v)
        except Exception:  # noqa: BLE001 — sin celdas no hay casillas
            return []
        if not celdas:
            return []

        def alternar(n):
            actuales = self._numeros(v)
            actuales.remove(n) if n in actuales else actuales.append(n)
            return {"celdas": ", ".join(str(x) for x in sorted(actuales))}
        casillas = mp.CasillasCopias([(i, np.asarray(c["centroide"], float), "ok" if i in elegidas else "suprimida")
                                      for i, c in enumerate(celdas, 1)], alternar)
        casillas.ayuda = "Tocá una celda para elegirla o dejarla de elegir"
        return [casillas]

    def previa_vista(self, ctx, v, op):
        """Cada celda se resalta: azul las elegidas y gris las demás."""
        from ...nucleo import geometria as geo
        elegidas = self._numeros(v)
        return [("tris", geo.teselar(c["solido"])[0], (0.2, 0.5, 0.95) if i in elegidas else (0.6, 0.6, 0.65),
                 0.35 if i in elegidas else 0.12) for i, c in enumerate(self._celdas(v, ctx), 1)]

    def construir(self, v, ctx):
        exigir(v, "herramientas", "Seleccioná las herramientas.")
        numeros = self._numeros(v)
        if not numeros:
            raise ErrorComando("Elegí al menos una celda.")
        return self.crear_op(OpRellenoContorno, v, ctx, herramientas=refs(v, "herramientas"), celdas=[n - 1 for n in numeros],
                             operacion=v["operacion"], objetivos=objetivos(v),
                             eliminar_herramientas=bool(v.get("eliminar_herramientas")))

    def desde_op(self, op, ctx):
        return _con_objetivos(op, ctx, dict(op.p, herramientas=hits(op.p["herramientas"], ctx.estado),
                                            celdas=", ".join(str(i + 1) for i in op.p["celdas"])))


class SolidoEnvolvente(Comando):
    CLAVE, TITULO, ICONO = "cuerpo_envolvente", "Sólido delimitador", "cuerpo_envolvente"
    AYUDA = "Caja, cilindro o tubo que encierra los cuerpos elegidos."
    CLASE_OP = OpSolidoEnvolvente

    def campos(self, ctx):
        dos_ejes = lambda v: v.get("orientacion") in ("z_x", "z_y", "x_y")  # noqa: E731
        return [Seleccion("cuerpos", "Cuerpos", {"cuerpo"}, maximo=None),
                Opciones("tipo", "Forma", {"caja": "Caja", "cilindro": "Cilindro", "tubo": "Tubo", "esfera": "Esfera"}),
                Opciones("eje", "Eje del cilindro", {"z": "Z", "x": "X", "y": "Y"},
                         visible_si=lambda v: v.get("tipo") != "caja" and v.get("orientacion", "modelo") == "modelo"),
                Expresion("espesor_tubo", "Pared del tubo", "", visible_si=lambda v: v.get("tipo") == "tubo"),
                Expresion("margen", "Desfase", "0 mm"),
                Opciones("orientacion", "Orientación", {"modelo": "Del modelo", "automatica": "Automática",
                                                        "z_x": "Eje Z / eje X", "z_y": "Eje Z / eje Y",
                                                        "x_y": "Ejes X e Y", "scu": "SCU"}),
                Texto("scu", "SCU (id del paso)", "", visible_si=lambda v: v.get("orientacion") == "scu"),
                Seleccion("eje_a", "Primer eje", {"eje", "arista"}, visible_si=dos_ejes),
                Seleccion("eje_b", "Segundo eje", {"eje", "arista"}, visible_si=dos_ejes),
                Casilla("componente", "En un componente nuevo", avanzado=True),
                Casilla("grupo_rigido", "Grupo rígido", visible_si=lambda v: v.get("componente"), avanzado=True),
                Opciones("origen", "Origen del componente", {"modelo": "Del modelo", "centro": "Centro",
                                                             "esquina": "Esquina mínima"},
                         visible_si=lambda v: v.get("componente"), avanzado=True),
                campo_operacion(), campo_objetivos()]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná los cuerpos.")
        if v.get("orientacion") in ("z_x", "z_y", "x_y"):
            exigir(v, "eje_a", "Elegí el primer eje de la orientación.")
            exigir(v, "eje_b", "Elegí el segundo eje de la orientación.")
        if v.get("orientacion") == "scu" and not str(v.get("scu") or "").strip():
            raise ErrorComando("Escribí el id del paso del sistema de coordenadas de usuario.")
        return self.crear_op(OpSolidoEnvolvente, v, ctx, cuerpos=_cuerpos(v["cuerpos"]), objetivos=objetivos(v),
                             eje_a=ref1(v, "eje_a"), eje_b=ref1(v, "eje_b"), scu=str(v.get("scu") or "").strip() or None,
                             componente=bool(v.get("componente")), grupo_rigido=bool(v.get("componente") and v.get("grupo_rigido")),
                             origen=v["origen"] if v.get("componente") or v.get("grupo_rigido") else "modelo",
                             **{k: v[k] for k in ("tipo", "margen", "eje", "operacion", "orientacion", "espesor_tubo")})

    def desde_op(self, op, ctx):
        return _con_objetivos(op, ctx, dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado),
                                            eje_a=_h1(op.p.get("eje_a"), ctx.estado),
                                            eje_b=_h1(op.p.get("eje_b"), ctx.estado)))


class VolumenFluido(Comando):
    CLAVE, TITULO, ICONO = "volumen_fluido", "Volumen de fluido", "volumen_fluido"
    AYUDA = ("Crea el sólido del interior o del exterior de un diseño, para análisis de flujo. Las aberturas se tapan "
             "con superficies.")
    CLASE_OP = OpVolumenFluido

    def campos(self, ctx):
        externo = lambda v: v.get("tipo") == "externo"  # noqa: E731
        return [Opciones("tipo", "Tipo de volumen", {"interno": "Interno", "externo": "Externo"}),
                Seleccion("cuerpos", "Cuerpos del diseño", {"cuerpo"}, maximo=None),
                Seleccion("tapas", "Tapas de aberturas", {"cuerpo"}, minimo=0, maximo=None,
                          ayuda="Superficies que tapan las aberturas del diseño."),
                Opciones("forma_externa", "Forma exterior", {"caja": "Caja", "cilindro": "Cilindro",
                                                              "semiesfera": "Semiesfera"}, visible_si=externo),
                Expresion("margen", "Distancia al modelo", "10 mm", visible_si=externo),
                Casilla("separar_caras", "Separar caras")]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná los cuerpos del diseño.")
        ctx.evaluar(v["margen"])
        return self.crear_op(OpVolumenFluido, v, ctx, cuerpos=_cuerpos(v["cuerpos"]), tapas=_cuerpos(v.get("tapas")),
                             **{k: v[k] for k in ("tipo", "forma_externa", "margen", "separar_caras")})

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado), tapas=_hits_cuerpos(op.p["tapas"], ctx.estado))


class Saliente(Comando):
    CLAVE, TITULO, ICONO = "saliente", "Saliente de fijación", "saliente"
    AYUDA = "Columna para tornillo (plástico) en puntos de boceto."
    CLASE_OP = OpSaliente

    def campos(self, ctx):
        return [Seleccion("posiciones", "Puntos", {"punto", "vertice"}, maximo=None),
                Expresion("diametro_exterior", "Diámetro exterior", "8 mm"),
                Expresion("diametro_agujero", "Diámetro del agujero", "3 mm"),
                Expresion("altura", "Altura (vacío = auto)", "", ayuda="Vacío: hasta el cuerpo."),
                Expresion("angulo_desmoldeo", "Ángulo de desmoldeo", "0 deg", ANGULO), Casilla("invertir", "Invertir")]

    def construir(self, v, ctx):
        exigir(v, "posiciones", "Seleccioná los puntos.")
        # El sentido no se elige (Fusion solo tiene «Invertir»): al editar se conserva el del paso (una receta
        # vieja sigue con "plano"); un saliente nuevo usa el automático.
        sentido = ctx.op.p.get("sentido", "plano") if ctx.op is not None else OpSaliente.PARAMS["sentido"]
        return self.crear_op(OpSaliente, v, ctx, posiciones=refs(v, "posiciones"), sentido=sentido,
                             **{k: v[k] for k in ("diametro_exterior", "diametro_agujero", "altura", "angulo_desmoldeo",
                                                  "invertir")})

    def desde_op(self, op, ctx):
        return dict(op.p, posiciones=hits(op.p["posiciones"], ctx.estado))


class Labio(Comando):
    CLAVE, TITULO, ICONO = "labio", "Labio", "labio"
    AYUDA = "Labio, ranura o labio y acanalado a lo largo del borde de una pared (carcasas de plástico)."
    CLASE_OP = OpLabio
    TITULOS_MODO = ("tipo", {"labio": ("Labio", "labio"), "ranura": ("Ranura", "labio"),
                             "labio y acanalado": ("Labio y acanalado", "labio")})

    def campos(self, ctx):
        return [Opciones("tipo", "Tipo", {"labio": "Labio", "ranura": "Ranura",
                                          "labio y acanalado": "Labio y acanalado"}),
                Seleccion("aristas", "Aristas del borde", {"arista"}, maximo=None),
                Seleccion("cuerpo_ranura", "Cuerpo de la ranura", {"cuerpo"}, minimo=0,
                          visible_si=lambda v: v.get("tipo") == "labio y acanalado",
                          ayuda="El cuerpo que recibe la ranura del labio; tiene que tocar al del labio."),
                Expresion("ancho", "Ancho", "1 mm"), Expresion("alto", "Alto", "1.5 mm"),
                Expresion("holgura", "Holgura", "0.1 mm", visible_si=lambda v: v.get("tipo") != "labio"),
                Casilla("invertir", "Invertir"),
                Seleccion("direccion", "Dirección de tirado", {"plano", "cara_plana", "eje", "arista_lineal"}, minimo=0)]

    def construir(self, v, ctx):
        exigir(v, "aristas", "Seleccioná las aristas del borde.")
        if v["tipo"] == "labio y acanalado":
            exigir(v, "cuerpo_ranura", "Elegí el cuerpo de la ranura del labio y acanalado.")
        ranura = next((h["ref"]["cuerpo"] for h in v.get("cuerpo_ranura") or [] if h["ref"].get("tipo") == "cuerpo"), None)
        return self.crear_op(OpLabio, v, ctx, aristas=refs(v, "aristas"), direccion=ref1(v, "direccion"),
                             cuerpo_ranura={"tipo": "cuerpo", "cuerpo": ranura} if ranura else None,
                             **{k: v[k] for k in ("tipo", "ancho", "alto", "holgura", "invertir")})

    def desde_op(self, op, ctx):
        return dict(op.p, aristas=hits(op.p["aristas"], ctx.estado), direccion=_h1(op.p["direccion"], ctx.estado),
                    cuerpo_ranura=hits([op.p["cuerpo_ranura"]], ctx.estado) if op.p.get("cuerpo_ranura") else [])


registrar(Barrido, Solevacion, Nervio, Red, Repujado, Agujero, Rosca, Bobina, Tuberia, PatronRectangular, VolumenFluido,
          PatronCircular, PatronRuta, Simetria, RellenoContorno, SolidoEnvolvente, Saliente, Labio)
