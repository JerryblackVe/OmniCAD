# -*- coding: utf-8 -*-
"""Comandos de INSPECCIONAR: Medir, Interferencia, Centro de masa y los análisis que quedan guardados
en el navegador (sección, cebra, mapa de entorno, desmoldeo, curvatura, peine, isocurva, accesibilidad,
radio mínimo)."""
import numpy as np

from ...nucleo import analisis as an
from ...timeline import entidades as ent
from ...timeline.ops_chapa import cuerpos_del_modelo, es_patron_plano
from ...timeline.parametros import ANGULO
from .. import analisis_vista, formato
from ..comando import Casilla, Comando, Entero, ErrorComando, Expresion, Info, Opciones, Seleccion, ref1
from . import registrar

GEOMETRIA = {"cara", "arista", "vertice", "cuerpo", "punto", "curva_boceto"}


def _entrada(hit, estado):
    """Lo que entiende analisis.medir: forma OCC o punto."""
    e = ent.resolver(hit["ref"], estado)
    if e.forma is not None:
        return e.forma
    if e.punto is not None:
        return np.asarray(e.punto, float)
    raise ErrorComando("Esa selección no se puede medir.")


def _n(x, dec=3):
    return formato.numero(float(x), miles=True) if hasattr(formato, "numero") else f"{x:.{dec}f}"


def _mm(x, potencia=1):
    """Un valor del modelo (mm, mm², mm³) con la unidad de longitud del documento: «1.575 in»."""
    return f"{_n(formato.longitud(float(x), potencia))} {formato.sufijo(potencia)}"


def _vec(v):
    return "(" + "; ".join(_n(formato.longitud(float(c))) for c in v) + ")"


def _texto_medida(info, prefijo=""):
    lineas = []
    claves = [("largo", "Longitud", 1), ("area", "Área", 2), ("perimetro", "Perímetro", 1),
              ("radio", "Radio", 1), ("diametro", "Diámetro", 1), ("volumen", "Volumen", 3)]
    for k, t, p in claves:
        if info.get(k) is not None:
            lineas.append(f"{prefijo}{t}: {_mm(info[k], p)}")
    for k, t in (("posicion", "Posición"), ("punto", "Posición"), ("centro", "Centro")):
        if info.get(k) is not None and np.ndim(info[k]) == 1:
            lineas.append(f"{prefijo}{t}: {_vec(info[k])}")
    return lineas


class Medir(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "medir", "Medir", "medir", "I"
    AYUDA = "Mide distancias, ángulos, longitudes, áreas y volúmenes de lo que elijas."
    SIN_OP, TEXTO_ACEPTAR = True, "Cerrar"

    def campos(self, ctx):
        return [Seleccion("a", "Selección 1", GEOMETRIA), Seleccion("b", "Selección 2", GEOMETRIA, minimo=0),
                Casilla("centro", "Centro a centro"), Info("resultado", "Resultados", self._resultado)]

    def _datos(self, v, ctx):
        if not v.get("a"):
            return None
        a = _entrada(v["a"][0], ctx.estado)
        b = _entrada(v["b"][0], ctx.estado) if v.get("b") else None
        return an.medir(a, b, centro_a_centro=bool(v.get("centro")))

    def _resultado(self, v, ctx):
        r = self._datos(v, ctx)
        if r is None:
            return "Elegí una o dos entidades."
        lineas = []
        if "distancia" in r:
            lineas.append(f"Distancia: {_mm(r['distancia'])}")
            if r.get("delta") is not None:
                dx, dy, dz = r["delta"]
                lineas.append(f"ΔX {_n(formato.longitud(dx))} · ΔY {_n(formato.longitud(dy))} · ΔZ {_n(formato.longitud(dz))} "
                              f"{formato.sufijo()}")
        if r.get("angulo") is not None:
            lineas.append(f"Ángulo: {_n(r['angulo'])}°")
        for clave, prefijo in (("a", "1 › "), ("b", "2 › ")):
            if isinstance(r.get(clave), dict):
                lineas += _texto_medida(r[clave], prefijo if "b" in r else "")
        return "\n".join(lineas)

    def construir(self, v, ctx):
        return None

    # ------------------------------------------------------------ cota guía en la vista (como Fusion)
    @staticmethod
    def _tam_flecha(visor, punto):
        """Largo de las flechas en mm para que se vean de ~12 px en pantalla."""
        from ..manipuladores import mm_por_px
        try:
            return float(mm_por_px(visor, punto)) * 12.0
        except Exception:  # noqa: BLE001 — sin cámara (pruebas), un tamaño fijo
            return 2.0

    def cota(self, r, v, ctx, visor=None, color=analisis_vista.COLOR_COTA):
        """Cota guía de un resultado de `an.medir`: {"capas", "etiquetas"} (ver `analisis_vista.cota_guia`).
        Dos selecciones: la distancia mínima entre los puntos más cercanos (y el ángulo, si lo hay). Una sola:
        largo de una arista recta, Ø de lo circular, área de una cara, posición de un punto o volumen."""
        vacio = {"capas": [], "etiquetas": []}
        if not r:
            return vacio
        vista = np.asarray(visor.R[2], float) if visor is not None and hasattr(visor, "R") else None

        def tam(p):
            return self._tam_flecha(visor, p) if visor is not None else 2.0
        if r.get("punto_a") is not None and r.get("punto_b") is not None:
            pa, pb = np.asarray(r["punto_a"], float), np.asarray(r["punto_b"], float)
            texto = _mm(r["distancia"])
            if r.get("angulo") is not None and r["angulo"] > 1e-6:
                texto += f" · {_n(r['angulo'])}°"
            return analisis_vista.cota_guia(pa, pb, texto, tam((pa + pb) / 2), vista, color)
        info = r.get("a") or {}
        hit = (v.get("a") or [None])[0]
        if info.get("centro") is not None and info.get("radio"):
            centro = np.asarray(info["centro"], float)
            return analisis_vista.cota_diametro(centro, info["radio"], info.get("eje") or info.get("normal"),
                                                f"Ø {_mm(info['diametro'])}", tam(centro), vista, color)
        if info.get("tipo") == "arista":
            from ...nucleo import geometria as geo
            poli = np.asarray(geo.polilinea_arista(_entrada(hit, ctx.estado)), float)
            if info.get("direccion") is not None:          # recta: cota de punta a punta
                return analisis_vista.cota_guia(poli[0], poli[-1], _mm(info["largo"]), tam(poli[0]),
                                                vista, color)
            from ..visor3d import _segmentos
            return {"capas": [("lineas", _segmentos([poli]), color, 2.5)],
                    "etiquetas": [(poli[len(poli) // 2], _mm(info["largo"]))]}
        if info.get("posicion") is not None:
            p = np.asarray(info["posicion"], float)
            return {"capas": [("puntos", np.array([p]), color, 9)], "etiquetas": [(p, _vec(p))]}
        if info.get("tipo") == "cara":
            if hit and hit.get("punto") is not None:
                p = np.asarray(hit["punto"], float)        # donde se hizo clic sobre la cara
            else:
                from ..manipuladores import centroide
                p = centroide(_entrada(hit, ctx.estado))
            return {"capas": [], "etiquetas": [(p, _mm(info["area"], 2))]}
        if info.get("volumen") is not None and info.get("centro_masa") is not None:
            p = np.asarray(info["centro_masa"], float)
            return {"capas": [("puntos", np.array([p]), color, 8)], "etiquetas": [(p, _mm(info["volumen"], 3))]}
        return vacio

    def mostrar(self, v, ctx):
        self._v, self._ctx = v, ctx
        visor = ctx.ventana.visor if ctx.ventana else None
        if visor is None:
            return
        if not getattr(self, "_escuchando", False):        # valor en vivo de lo que está bajo el cursor
            visor.entidad_sobre.connect(self._sobre)
            self._escuchando = True
        self._limpiar(visor, "medida_previa")
        self._limpiar(visor, "medida")
        c = self.cota(self._datos(v, ctx), v, ctx, visor)
        visor.set_capa("medida", c["capas"])
        visor.set_etiquetas("medida", c["etiquetas"])

    def _sobre(self, hit):
        """Con la primera selección hecha, lo que está bajo el cursor se mide en vivo (cota celeste con «≈»),
        antes de hacer el segundo clic."""
        ctx, v = getattr(self, "_ctx", None), getattr(self, "_v", None)
        visor = ctx.ventana.visor if ctx is not None and ctx.ventana else None
        if visor is None:
            return
        self._limpiar(visor, "medida_previa")
        if hit is None or not v or not v.get("a") or v.get("b") or hit.get("ref") == v["a"][0].get("ref"):
            return
        try:
            r = an.medir(_entrada(v["a"][0], ctx.estado), _entrada(hit, ctx.estado),
                         centro_a_centro=bool(v.get("centro")))
            c = self.cota(r, {"a": v["a"], "b": [hit]}, ctx, visor, analisis_vista.COLOR_COTA_PREVIA)
        except Exception:  # noqa: BLE001 — lo que no se puede medir simplemente no muestra la cota previa
            return
        visor.set_capa("medida_previa", c["capas"])
        visor.set_etiquetas("medida_previa", [(p, f"≈ {t}") for p, t in c["etiquetas"]])

    @staticmethod
    def _limpiar(visor, capa):
        visor.set_capa(capa, None)
        visor.set_etiquetas(capa, None)

    def aplicar(self, v, ctx):
        pass

    def al_cerrar(self, ctx):
        if ctx.ventana:
            visor = ctx.ventana.visor
            if getattr(self, "_escuchando", False):
                try:
                    visor.entidad_sobre.disconnect(self._sobre)
                except (RuntimeError, TypeError):
                    pass
                self._escuchando = False
            for capa in ("medida", "medida_previa"):
                self._limpiar(visor, capa)


class Interferencia(Comando):
    CLAVE, TITULO, ICONO = "interferencia", "Interferencia", "interferencia"
    AYUDA = "Busca volúmenes donde los cuerpos se superponen."
    SIN_OP, TEXTO_ACEPTAR = True, "Cerrar"

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Cuerpos", {"cuerpo"}, minimo=0, maximo=None,
                          ayuda="Sin selección: todos los cuerpos."),
                Casilla("coincidentes", "Incluir caras coincidentes"),
                Info("resultado", "Resultados", self._resultado)]

    def _calcular(self, v, ctx):
        ids = [h["ref"]["cuerpo"] for h in v.get("cuerpos") or []] or [c.id for c in cuerpos_del_modelo(ctx.estado)]
        cuerpos = {c: ctx.estado.cuerpos[c].forma for c in ids if c in ctx.estado.cuerpos
                   and getattr(ctx.estado.cuerpos[c], "tipo", "solido") == "solido"}
        clave = (tuple(sorted((c, id(f)) for c, f in cuerpos.items())), bool(v.get("coincidentes")))
        if getattr(self, "_clave", None) != clave:
            self._clave, self._res = clave, an.interferencias(cuerpos, caras_coincidentes=bool(v.get("coincidentes")))
        return self._res

    def _resultado(self, v, ctx):
        res = self._calcular(v, ctx)
        if not res:
            return "No hay interferencias."
        nombre = lambda c: ctx.estado.cuerpos[c].nombre  # noqa: E731
        return "\n".join(f"{nombre(r['a'])} ↔ {nombre(r['b'])}: " +
                         (_mm(r["volumen"], 3) if not r.get("coincidente") else "caras coincidentes")
                         for r in res)

    def construir(self, v, ctx):
        return None

    def mostrar(self, v, ctx):
        from ...nucleo import geometria as geo
        prims = []
        for r in self._calcular(v, ctx):
            if r.get("forma") is not None and not geo.esta_vacia(r["forma"]):
                prims.append(("tris", geo.teselar(r["forma"])[0], (0.95, 0.15, 0.15), 0.7))
        if ctx.ventana:
            ctx.ventana.visor.set_capa("medida", prims)

    def al_cerrar(self, ctx):
        if ctx.ventana:
            ctx.ventana.visor.set_capa("medida", None)


class BuscarSimilares(Comando):
    CLAVE, TITULO, ICONO = "buscar_similares", "Buscar componentes similares", "buscar_similares"
    AYUDA = "Lista los componentes del diseño con la misma geometría o muy parecida a la del cuerpo elegido."
    SIN_OP, TEXTO_ACEPTAR = True, "Cerrar"
    _ESTADOS = {"duplicate": "duplicado", "highly_similar": "muy similar", "similar": "similar"}

    def campos(self, ctx):
        return [Seleccion("cuerpo", "Componente (un cuerpo suyo)", {"cuerpo"}),
                Info("resultado", "Componentes similares", self._resultado)]

    def _resultado(self, v, ctx):
        from ...api.errores import ErrorAPI
        from ...api.herramientas_similares import buscar_similares
        if not v.get("cuerpo"):
            return "Elegí un cuerpo del componente."
        componente = ctx.estado.cuerpo(v["cuerpo"][0]["ref"]["cuerpo"]).componente
        if not componente:
            return "Ese cuerpo no está en un componente: ENSAMBLAR › Nuevo componente lo crea."
        try:
            encontrados, comparados = buscar_similares(ctx.estado, componente)
        except ErrorAPI as e:
            return e.mensaje
        coincidencias = encontrados[0]["matches"] if encontrados else []
        if not coincidencias:
            return f"Ningún otro componente se parece (se compararon {comparados})."
        return "\n".join(f"{c['name']}: {self._ESTADOS[c['status']]}" for c in coincidencias)

    def construir(self, v, ctx):
        return None


class ReconocerFunciones(Comando):
    CLAVE, TITULO, ICONO = "reconocer_funciones", "Reconocer funciones", "reconocer_funciones"
    AYUDA = ("Encuentra los agujeros, empalmes, chaflanes, extrusiones, revoluciones, simetrías y patrones de un cuerpo "
             "sin historial (por ejemplo, importado) y los lista. Con «Rehacer en el timeline», Aceptar vuelve los "
             "agujeros, empalmes y chaflanes pasos paramétricos (el cuerpo queda igual).")
    SIN_OP, TEXTO_ACEPTAR = True, "Aceptar"
    _TEXTO = {"hole": "Agujeros", "fillet": "Empalmes", "chamfer": "Chaflanes", "extrude": "Extrusión",
              "revolve": "Revolución", "mirror": "Simetrías", "circular_pattern": "Patrones circulares",
              "rectangular_pattern": "Patrones rectangulares"}
    _CASILLAS = (("hole", "agujeros", "Agujeros"), ("fillet", "empalmes", "Empalmes"),
                 ("chamfer", "chaflanes", "Chaflanes"), ("extrude", "extrusion", "Extrusión"),
                 ("revolve", "revolucion", "Revolución"), ("mirror", "simetria", "Simetría"),
                 ("circular_pattern", "patron_circular", "Patrón circular"),
                 ("rectangular_pattern", "patron_rectangular", "Patrón rectangular"))

    def campos(self, ctx):
        return [Seleccion("cuerpo", "Cuerpo sólido", {"cuerpo"}),
                *(Casilla(c, texto, True) for _t, c, texto in self._CASILLAS),
                Casilla("rehacer", "Rehacer en el timeline", False,
                        ayuda="Aceptar crea los pasos Agujero, Empalme y Chaflán que rehacen lo encontrado."),
                Casilla("rehacer_extrusion", "Rehacer la extrusión (reemplaza el cuerpo)", False,
                        visible_si=lambda v: bool(v.get("rehacer")),
                        ayuda="Si el cuerpo es un prisma, lo vuelve boceto + extrusión (los agujeros pasantes quedan en el boceto)."),
                Info("resultado", "Funciones encontradas", self._resultado)]

    def _tipos(self, v):
        return [t for t, c, _texto in self._CASILLAS if v.get(c)]

    def _resultado(self, v, ctx):
        from ...api import llamar
        from ...api.sesion import Sesion
        if not v.get("cuerpo"):
            return "Elegí un cuerpo sólido."
        tipos = self._tipos(v)
        if not tipos:
            return "Marcá qué reconocer."
        r = llamar(Sesion(ctx.doc), "find_features", {"body": v["cuerpo"][0]["ref"]["cuerpo"], "types": tipos})
        if not r["ok"]:
            return r["mensaje"]
        r = r["result"]
        lineas = []
        for tipo, texto in self._TEXTO.items():
            hallados = [f for f in r["features"] if f["type"] == tipo]
            if not hallados:
                continue
            if tipo == "hole":
                detalle = ", ".join(f"Ø{f['diameter']:g}" + (" pasante" if f["through"] else f" prof. {f['depth']:g}")
                                    for f in hallados)
            elif tipo == "fillet":
                detalle = ", ".join(sorted({f"R{f['radius']:g}" for f in hallados}))
            elif tipo == "chamfer":
                detalle = ", ".join(sorted({f"{f['width']:g} mm a {f['angle']:g}°" for f in hallados}))
            elif tipo == "extrude":
                detalle = ", ".join(f"{f['distance']:g} mm" for f in hallados)
            elif tipo == "revolve":
                detalle = ", ".join(f"{f['angle']:g}°" for f in hallados)
            else:
                detalle = ", ".join(f"{f['count']} × {self._TEXTO[f['feature']].lower()}" for f in hallados)
            lineas.append(f"{texto}: {len(hallados)} ({detalle})")
        return "\n".join(lineas) or "No se encontró ninguna función."

    def construir(self, v, ctx):
        return None

    def aplicar(self, v, ctx):
        from ...api import llamar
        from ...api.sesion import Sesion
        if not v.get("rehacer"):
            return
        if not v.get("cuerpo"):
            raise ErrorComando("Elegí un cuerpo sólido.")
        tipos = [t for t in self._tipos(v) if t in ("hole", "fillet", "chamfer")]
        if v.get("rehacer_extrusion"):
            tipos = ["extrude", *tipos]
        if not tipos:
            raise ErrorComando("Marcá agujeros, empalmes o chaflanes para rehacer.")
        r = llamar(Sesion(ctx.doc), "rebuild_features", {"body": v["cuerpo"][0]["ref"]["cuerpo"], "types": tipos})
        if not r["ok"]:
            raise ErrorComando(r["mensaje"])
        if hasattr(ctx.ventana, "statusBar") and r["result"]["not_rebuilt"]:
            ctx.ventana.statusBar().showMessage(
                f"No se rehicieron {len(r['result']['not_rebuilt'])} funciones: "
                + "; ".join(f["reason"] for f in r["result"]["not_rebuilt"][:3]), 8000)


class CentroMasa(Comando):
    CLAVE, TITULO, ICONO = "centro_masa", "Centro de masa", "centro_masa"
    AYUDA = "Muestra el centro de masa de los cuerpos (con su material físico)."
    SIN_OP, TEXTO_ACEPTAR = True, "Cerrar"

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Cuerpos", {"cuerpo"}, minimo=0, maximo=None,
                          ayuda="Sin selección: todos los cuerpos."),
                Info("resultado", "Centro de masa", self._resultado)]

    def _calcular(self, v, ctx):
        ids = [h["ref"]["cuerpo"] for h in v.get("cuerpos") or []] or [
            c for c, cu in ctx.estado.cuerpos.items() if getattr(cu, "tipo", "solido") == "solido"
            and not es_patron_plano(cu)]
        if not ids:
            return None, 0.0
        def material(c):   # el Material físico asignado, si no el del cuerpo (fijación, regla de chapa), si no acero
            return ctx.doc.propiedad(c, "material") or getattr(ctx.estado.cuerpos[c], "material", None) or "Acero"
        dens = [an.TABLA_MATERIALES.get(material(c), {"densidad": 7.85})["densidad"] for c in ids]
        formas = [ctx.estado.cuerpos[c].forma for c in ids]
        masa = sum(an.propiedades_fisicas(f, d)["masa"] for f, d in zip(formas, dens, strict=True))
        return np.asarray(an.centro_de_masa(formas, dens), float), masa

    def _resultado(self, v, ctx):
        c, masa = self._calcular(v, ctx)
        return "No hay cuerpos sólidos." if c is None else f"{_vec(c)} {formato.sufijo()}\nMasa total: {_n(formato.masa(masa))} {formato.unidad_masa()}"

    def construir(self, v, ctx):
        return None

    def mostrar(self, v, ctx):
        c, _ = self._calcular(v, ctx)
        if ctx.ventana:
            ctx.ventana.visor.set_capa("medida", [("puntos", np.array([c]), (0.1, 0.1, 0.1), 12),
                                                  ("puntos", np.array([c]), (1.0, 0.85, 0.1), 8)] if c is not None
                                       else None)

    def al_cerrar(self, ctx):
        if ctx.ventana:
            ctx.ventana.visor.set_capa("medida", None)


# ---------------------------------------------------------------- análisis guardados en el navegador
class _Analisis(Comando):
    TIPO_ANALISIS = ""
    SIN_OP = True

    def construir(self, v, ctx):
        return None

    def params(self, v, ctx):
        return {"cuerpos": [h["ref"]["cuerpo"] for h in v.get("cuerpos") or []]}

    def mostrar(self, v, ctx):
        if ctx.ventana is None:
            return
        datos = analisis_vista.calcular(self.TIPO_ANALISIS, self.params(v, ctx), ctx.estado)
        analisis_vista.aplicar(ctx.ventana.visor, datos)

    def aplicar(self, v, ctx):
        ctx.doc.agregar_analisis(self.TIPO_ANALISIS, self.params(v, ctx))

    def al_cerrar(self, ctx):
        if ctx.ventana is not None:
            ctx.ventana.aplicar_analisis()


def _cuerpos_campo():
    return Seleccion("cuerpos", "Cuerpos", {"cuerpo"}, minimo=0, maximo=None, ayuda="Sin selección: todos.")


class Seccion(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "seccion", "Análisis de sección", "seccion", "seccion"
    AYUDA = "Corta la vista del modelo con un plano para ver su interior (no cambia el modelo)."

    def campos(self, ctx):
        return [Seleccion("plano", "Caras/plano", {"cara_plana", "plano"}), Expresion("desfase", "Distancia", "0 mm"),
                Expresion("angulo", "Ángulo", "0 deg", ANGULO), Casilla("invertir", "Invertir"), _cuerpos_campo()]

    def params(self, v, ctx):
        if not v.get("plano"):
            raise ErrorComando("Seleccioná el plano de corte.")
        return {"plano": ref1(v, "plano"), "desfase_mm": ctx.evaluar(v["desfase"]),
                "angulo": ctx.evaluar(v["angulo"], ANGULO), "invertir": bool(v["invertir"]),
                "cuerpos": [h["ref"]["cuerpo"] for h in v.get("cuerpos") or []]}

    def mostrar(self, v, ctx):
        if v.get("plano"):
            super().mostrar(v, ctx)


class Cebra(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "cebra", "Análisis cebra", "cebra", "cebra"
    AYUDA = "Franjas reflejadas para ver la continuidad entre caras (sigue a la cámara)."

    def campos(self, ctx):
        return [Opciones("orientacion", "Dirección de las franjas", {"horizontal": "Horizontal", "vertical": "Vertical"}),
                Entero("frecuencia", "Cantidad de franjas", 8, 2, 40)]

    def params(self, v, ctx):
        return {"orientacion": v["orientacion"], "frecuencia": int(v["frecuencia"])}


class MapaEntorno(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "mapa_entorno", "Análisis de mapas de entorno", "mapa_entorno", "mapa_entorno"
    AYUDA = "Refleja un entorno sobre las caras para evaluar su suavidad."

    def campos(self, ctx):
        return []

    def params(self, v, ctx):
        return {}


class AnguloDesmoldeo(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "angulo_desmoldeo", "Análisis de ángulo de desmoldeo", "angulo_desmoldeo", \
        "desmoldeo"
    AYUDA = "Colorea las caras según su ángulo respecto de la dirección de extracción."

    def campos(self, ctx):
        return [_cuerpos_campo(), Seleccion("direccion", "Dirección", {"cara_plana", "plano", "eje", "arista_lineal"},
                                            minimo=0, ayuda="Sin selección: eje Z."),
                Casilla("invertir", "Invertir dirección"),
                Expresion("angulo_min", "Ángulo mínimo", "0 deg", ANGULO),
                Expresion("angulo_max", "Ángulo máximo", "3 deg", ANGULO)]

    def params(self, v, ctx):
        return {"cuerpos": [h["ref"]["cuerpo"] for h in v.get("cuerpos") or []], "direccion": ref1(v, "direccion"),
                "invertir": bool(v["invertir"]), "angulo_min": ctx.evaluar(v["angulo_min"], ANGULO),
                "angulo_max": ctx.evaluar(v["angulo_max"], ANGULO)}


class MapaCurvatura(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "mapa_curvatura", "Análisis del mapa de curvatura", "mapa_curvatura", \
        "curvatura"
    AYUDA = "Colorea las caras según su curvatura (gaussiana, media, máxima o mínima)."

    def campos(self, ctx):
        return [_cuerpos_campo(), Opciones("tipo_curvatura", "Tipo de visualización",
                                           {"gaussiana": "Gaussiana", "media": "Media", "maxima": "Máxima",
                                            "minima": "Mínima"})]

    def params(self, v, ctx):
        return {"cuerpos": [h["ref"]["cuerpo"] for h in v.get("cuerpos") or []], "tipo_curvatura": v["tipo_curvatura"]}


class PeineCurvatura(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "curvatura_peine", "Análisis de curvatura en peine", "curvatura_peine", "peine"
    AYUDA = "Muestra un peine sobre las aristas: púas más largas = más curvatura."

    def campos(self, ctx):
        return [Seleccion("aristas", "Aristas", {"arista", "curva_boceto"}, maximo=None),
                Entero("densidad", "Densidad", 30, 2, 100), Expresion("escala", "Escala", "1", "escalar")]

    def params(self, v, ctx):
        if not v.get("aristas"):
            raise ErrorComando("Seleccioná aristas o curvas.")
        return {"aristas": [h["ref"] for h in v["aristas"]], "densidad": int(v["densidad"]),
                "escala": ctx.evaluar(v["escala"], "escalar")}

    def mostrar(self, v, ctx):
        if v.get("aristas"):
            super().mostrar(v, ctx)


class Isocurva(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "isocurva", "Análisis de la isocurva", "isocurva", "isocurva"
    AYUDA = "Dibuja las curvas U y V de las caras para ver su calidad."

    def campos(self, ctx):
        return [_cuerpos_campo(), Entero("densidad", "Densidad", 10, 2, 50)]

    def params(self, v, ctx):
        return {"cuerpos": [h["ref"]["cuerpo"] for h in v.get("cuerpos") or []], "densidad": int(v["densidad"])}


class Accesibilidad(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "accesibilidad", "Análisis de accesibilidad", "accesibilidad", \
        "accesibilidad"
    AYUDA = "Verde: se alcanza desde la dirección elegida; rojo: queda tapado."

    def campos(self, ctx):
        return [_cuerpos_campo(), Seleccion("direccion", "Dirección", {"cara_plana", "plano", "eje", "arista_lineal"},
                                            minimo=0, ayuda="Sin selección: desde arriba (Z)."),
                Casilla("invertir", "Invertir dirección")]

    def params(self, v, ctx):
        return {"cuerpos": [h["ref"]["cuerpo"] for h in v.get("cuerpos") or []], "direccion": ref1(v, "direccion"),
                "invertir": bool(v["invertir"])}


class RadioMinimo(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "radio_minimo", "Análisis de radio mínimo", "radio_minimo", "radio_minimo"
    AYUDA = "Marca en rojo las zonas donde no entra una herramienta del radio indicado."

    def campos(self, ctx):
        return [_cuerpos_campo(), Expresion("radio", "Radio de la herramienta", "3 mm")]

    def params(self, v, ctx):
        return {"cuerpos": [h["ref"]["cuerpo"] for h in v.get("cuerpos") or []], "radio": ctx.evaluar(v["radio"])}


registrar(ReconocerFunciones, BuscarSimilares, Medir, Interferencia, Seccion, Cebra, MapaEntorno, AnguloDesmoldeo, MapaCurvatura, PeineCurvatura, Isocurva,
          Accesibilidad, RadioMinimo, CentroMasa)
