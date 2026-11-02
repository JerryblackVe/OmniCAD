# -*- coding: utf-8 -*-
"""
Cómo se calculan los análisis de INSPECCIONAR (sección, cebra, mapa de entorno, desmoldeo, curvatura, peine,
isocurvas, accesibilidad y radio mínimo), sin Qt: lo usan la vista 3D de la ventana (`ui/analisis_vista.py`) y el
render de la API (`get_viewport_image`).

Un análisis es {"tipo", "params"} (los guarda el documento, como la carpeta «Análisis» del navegador
de Fusion). Las opciones del panel de Fusion se guardan solo si se usan: un análisis viejo, sin ellas, se ve igual.
`calcular` lo convierte en lo que el visor sabe dibujar:
  - "mallas": id de cuerpo → (vértices, normales, colores) que reemplazan su sombreado;
  - "colores": función (normales, dirección de vista) → colores, para los que dependen de la cámara;
  - "capas": primitivas extra (líneas, triángulos, puntos);
  - "cortes": planos de recorte [(normal, punto)].
Los resultados se guardan en caché por forma: recalcular un mapa de colores tarda hasta medio segundo.
"""
import numpy as np

from ..nucleo import analisis as an
from ..nucleo import comparar_malla as cm
from ..nucleo import geometria as geo
from ..nucleo.render_estilos import segmentos_de_polilineas as _segmentos
from . import entidades as ent

_cache = {}


def _cuerpos(params, estado):
    ids = params.get("cuerpos") or [c for c, cu in estado.cuerpos.items() if getattr(cu, "tipo", "solido") != "malla"]
    return {c: estado.cuerpos[c].forma for c in ids if c in estado.cuerpos}


def _direccion(params, estado, defecto=(0.0, 0.0, 1.0)):
    if not params.get("direccion"):
        d = np.array(defecto, float)
        return -d if params.get("invertir") else d
    e = ent.resolver(params["direccion"], estado)
    d = ent.direccion(e)
    if e.tipo == "cara":
        d = -d                              # una cara: la extracción es hacia afuera del material que limita
    return -d if params.get("invertir") else d


def _con_cache(clave, funcion, forma):
    """Memoriza `funcion()` bajo `clave`. La clave usa `id(forma)`: la entrada guarda la forma misma para que Python
    no pueda reciclar ese id en otra forma mientras la entrada viva (si no, un cuerpo nuevo heredaba los colores
    de uno ya descartado)."""
    if clave not in _cache:
        if len(_cache) > 200:
            _cache.clear()
        _cache[clave] = (forma, funcion())
    return _cache[clave][1]


COLOR_SECCION = (0.85, 0.30, 0.25)     # la tapa del corte hasta ahora: el color por defecto de «Personalizado»
LINEAS_RAYADO = 40                      # rayas a lo largo del corte; el paso se adapta a su tamaño


def rayado_diagonal(tris, plano):
    """Rayado a 45° de las caras del corte (Mostrar rayado de Fusion): segmentos 3D (2N x 3) de las rayas paralelas
    recortadas contra los triángulos `tris` (Tx3x3, sobre `plano`)."""
    tris = np.asarray(tris, float).reshape(-1, 3, 3)
    uv = np.stack([(tris - plano.origen) @ plano.u, (tris - plano.origen) @ plano.v], axis=-1)
    s = (uv[..., 0] + uv[..., 1]) / np.sqrt(2)          # a lo largo de la diagonal (las rayas son s = constante)
    t = (uv[..., 1] - uv[..., 0]) / np.sqrt(2)
    paso = max(float(s.max() - s.min()), float(t.max() - t.min()), 1e-6) / LINEAS_RAYADO
    niveles = np.arange(np.ceil(s.min() / paso), np.floor(s.max() / paso) + 1) * paso
    if not len(niveles):
        return np.zeros((0, 3))
    pts, hay = [], []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        sa, sb = s[:, a, None], s[:, b, None]
        cruza = (sa <= niveles) != (sb <= niveles)               # medio abierto: 0 o 2 cruces por triángulo y raya
        with np.errstate(divide="ignore", invalid="ignore"):
            f = (niveles - sa) / (sb - sa)
        pts.append(t[:, a, None] + f * (t[:, b, None] - t[:, a, None]))
        hay.append(cruza)
    pts, hay = np.stack(pts, 1), np.stack(hay, 1)                  # (N, 3 aristas, K)
    n, k = np.nonzero(hay.sum(1) == 2)
    primeras = np.argsort(~hay[n, :, k], axis=1, kind="stable")[:, :2]
    tt = pts[n[:, None], primeras, k[:, None]]
    ss = niveles[k][:, None] * np.ones((1, 2))
    u, v = (ss - tt) / np.sqrt(2), (ss + tt) / np.sqrt(2)
    seg = plano.origen + u[..., None] * plano.u + v[..., None] * plano.v           # (rayas, 2 puntos, 3)
    return seg[np.linalg.norm(seg[:, 1] - seg[:, 0], axis=1) > 1e-9].reshape(-1, 3)   # sin las que apenas tocan un vértice


def _color_seccion(params, cuerpo, propiedades):
    if params.get("color_modo") == "componente":
        from ..nucleo.render_cpu import color_y_acabado
        from .operaciones import propiedades_cuerpo
        return tuple(color_y_acabado(cuerpo, propiedades_cuerpo(propiedades or {}, cuerpo))[0])
    return tuple(params.get("color") or COLOR_SECCION)


def centro_de_masa(params, estado, propiedades=None):
    """(punto, masa en g) de los cuerpos de `params` («cuerpos» y «componentes»; sin ninguno, todos los sólidos), con la
    densidad de su Material físico o, sin él, la del cuerpo o la del acero. (None, 0.0) si no queda ningún sólido."""
    from .ops_chapa import es_patron_plano
    from .ops_ensamblar import familia
    from .operaciones import propiedades_cuerpo
    ids = list(params.get("cuerpos") or [])
    for comp in params.get("componentes") or []:
        if comp in estado.componentes:
            grupo = familia(estado, comp)
            ids += [c for c, cu in estado.cuerpos.items() if cu.componente in grupo]
    if not params.get("cuerpos") and not params.get("componentes"):
        ids = [c for c, cu in estado.cuerpos.items() if not es_patron_plano(cu)]
    ids = [c for c in dict.fromkeys(ids) if c in estado.cuerpos and getattr(estado.cuerpos[c], "tipo", "solido") == "solido"]
    if not ids:
        return None, 0.0

    def densidad(c):
        material = propiedades_cuerpo(propiedades or {}, estado.cuerpos[c]).get("material")
        material = material or getattr(estado.cuerpos[c], "material", None) or "Acero"
        return an.TABLA_MATERIALES.get(material, {"densidad": 7.85})["densidad"]
    dens = [densidad(c) for c in ids]
    formas = [estado.cuerpos[c].forma for c in ids]
    masa = sum(an.propiedades_fisicas(f, d)["masa"] for f, d in zip(formas, dens, strict=True))
    return np.asarray(an.centro_de_masa(formas, dens), float), masa


def glifo_centro(punto):
    """El punto del centro de masa, negro con centro amarillo."""
    p = np.asarray([punto], float)
    return [("puntos", p, (0.1, 0.1, 0.1), 12), ("puntos", p, (1.0, 0.85, 0.1), 8)]


def _desviacion(params, cuerpos, estado, salida):
    """Mapa de desviación (F10): los valores quedan en `salida["valores"]` para mostrar mínimo, máximo y cursor."""
    referencia = estado.cuerpos.get(params.get("referencia"))
    tol = float(params.get("tolerancia", 0.1))
    salida["valores"] = {}
    for cid, forma in cuerpos.items():
        if referencia is None or referencia.forma is forma:
            continue
        v, n, valores = _con_cache(("desviacion", id(forma), id(referencia.forma), tol),
                                   lambda f=forma, r=referencia.forma: cm.mapa(f, r, tolerancia=tol), (forma, referencia.forma))
        salida["mallas"][cid] = (np.asarray(v, np.float32), np.asarray(n, np.float32),
                                 np.asarray(cm.colores(valores, tol), np.float32))
        salida["valores"][cid] = (v, valores)
        vacio = np.zeros((0, 3), np.float32)
        salida["mallas"][params["referencia"]] = (vacio, vacio, vacio)   # coincide con el cuerpo y taparía los colores
    return salida


def calcular(tipo, params, estado, propiedades=None):
    """`propiedades`: `Documento.propiedades`, para el color por componente de la sección y la densidad del centro de masa."""
    salida = {"mallas": {}, "colores": None, "capas": [], "cortes": [], "solo": None}
    if tipo == "centro_masa":
        punto, _masa = centro_de_masa(params, estado, propiedades)
        salida["capas"] = glifo_centro(punto) if punto is not None else []
        return salida
    if tipo == "mapa_entorno":
        entorno, rotacion, reflejo = params.get("entorno"), float(params.get("rotacion", 0.0)), params.get("reflejo", True)
        salida["colores"] = lambda n, d: an.colores_mapa_entorno(n, d, entorno=entorno, rotacion=rotacion, reflejo=reflejo)
        if params.get("cuerpos"):
            salida["solo"] = [c for c in params["cuerpos"] if c in estado.cuerpos]
        return salida
    cuerpos = _cuerpos(params, estado)
    if tipo == "desviacion":
        return _desviacion(params, cuerpos, estado, salida)
    if tipo == "isocurva" and params.get("caras"):       # Cuerpos/Caras: las caras elegidas se suman a los cuerpos elegidos
        cuerpos = {c: f for c, f in cuerpos.items() if c in (params.get("cuerpos") or [])}
        cuerpos.update({i: ent.resolver(r, estado).forma for i, r in enumerate(params["caras"])})
    if tipo == "cebra":
        frecuencia, vertical = int(params.get("frecuencia", 8)), params.get("orientacion") == "vertical"
        opacidad, fija = int(params.get("opacidad", 100)), params.get("vista_fija")      # «Bloquear rayas»: no sigue a la cámara
        salida["colores"] = lambda n, d: an.colores_cebra(n, d if fija is None else fija, frecuencia=frecuencia,
                                                          vertical=vertical, opacidad=opacidad)
        if params.get("cuerpos"):
            salida["solo"] = list(cuerpos)
        if params.get("alta_calidad"):
            for cid, forma in cuerpos.items():
                v, n = _con_cache(("malla_fina", id(forma)), lambda f=forma: an.malla_fina(f), forma)
                salida["mallas"][cid] = (np.asarray(v, np.float32).reshape(-1, 3), np.asarray(n, np.float32).reshape(-1, 3), None)
        return salida
    if tipo == "seccion":
        e = ent.resolver(params["plano"], estado)
        plano = ent.como_plano(e)
        d = float(params.get("desfase_mm", 0.0))
        plano = plano.desplazado(d).girado(float(params.get("angulo", 0.0)))
        if params.get("invertir"):
            plano = geo.Plano.desde_marco(plano.origen, -plano.normal, plano.u)
        salida["cortes"].append((plano.normal, plano.origen))
        for cid, forma in cuerpos.items():
            datos = _con_cache(("seccion", id(forma), tuple(plano.origen), tuple(plano.normal)),
                               lambda f=forma: an.seccion(f, plano), forma)
            tris = np.asarray(datos["triangulos"], np.float32).reshape(-1, 3)
            if len(tris):
                salida["capas"].append(("tris", tris, _color_seccion(params, estado.cuerpos[cid], propiedades), 0.85))
                if params.get("rayado"):
                    salida["capas"].append(("lineas", rayado_diagonal(tris, plano), (0.15, 0.15, 0.15), 1.0))
            salida["capas"].append(("lineas", _segmentos(datos["polilineas"]), (0.15, 0.15, 0.15), 2.0))
        return salida
    for cid, forma in cuerpos.items():
        if tipo == "desmoldeo":
            d = _direccion(params, estado)
            a0, a1 = float(params.get("angulo_min", 0.0)), float(params.get("angulo_max", 3.0))
            op = {k: (tuple(params[k]) if k == "tolerancia" else params[k])
                  for k in ("degradado", "tolerancia", "opacidad", "alta_calidad") if k in params}
            v, n, c = _con_cache(("desmoldeo", id(forma), tuple(d), a0, a1, tuple(sorted(op.items()))),
                                 lambda f=forma, d=d, a0=a0, a1=a1, op=op: an.colores_desmoldeo(f, d, a0, a1, **op), forma)
        elif tipo == "curvatura":
            t = params.get("tipo_curvatura", "gaussiana")
            op = {k: params[k] for k in ("bandas", "alta_calidad", "escala", "opacidad") if k in params}
            limite = params.get("limite") or None
            v, n, c = _con_cache(("curvatura", id(forma), t, tuple(sorted(op.items())), limite),
                                 lambda f=forma, t=t, op=op, r=limite: an.colores_curvatura(f, tipo=t, rango=r, **op), forma)
        elif tipo == "accesibilidad":
            d = _direccion(params, estado)
            sentido, op = params.get("sentido", "dir1"), {k: params[k] for k in ("opacidad",) if k in params}
            d = -d if sentido == "dir2" else d
            v, n, c = _con_cache(("accesibilidad", id(forma), tuple(d), sentido, tuple(op.items())),
                                 lambda f=forma, d=d, a=sentido == "ambas", op=op: an.colores_accesibilidad(f, d, ambos_sentidos=a, **op),
                                 forma)
        elif tipo == "radio_minimo":
            r = float(params.get("radio", 3.0))
            op = {k: params[k] for k in ("radio_minimo", "aristas_vivas", "opacidad") if k in params}
            v, n, c = _con_cache(("radio_minimo", id(forma), r, tuple(sorted(op.items()))),
                                 lambda f=forma, r=r, op=op: an.colores_radio_minimo(f, r, **op), forma)
        elif tipo == "isocurva":
            cuantas, sentidos = int(params.get("densidad", 10)), params.get("tipo_iso", "uv")
            n_u, n_v = cuantas if "u" in sentidos else 0, cuantas if "v" in sentidos else 0
            datos = _con_cache(("isocurva", id(forma), n_u, n_v), lambda f=forma, a=n_u, b=n_v: an.isocurvas(f, n_u=a, n_v=b), forma)
            salida["capas"].append(("lineas", _segmentos(datos["u"]), (0.85, 0.25, 0.25), 1.2))
            salida["capas"].append(("lineas", _segmentos(datos["v"]), (0.25, 0.45, 0.90), 1.2))
            if params.get("peines"):
                puas = an.peines_isocurva(datos["u"] + datos["v"], densidad=int(params.get("densidad_peine", 50)),
                                          escala=float(params.get("escala_peine", 10.0)))["puas"]
                salida["capas"].append(("lineas", np.asarray(puas, np.float32).reshape(-1, 3), (0.55, 0.30, 0.85), 1.0))
            continue
        elif tipo == "peine":
            continue
        else:
            raise ValueError(f"Análisis desconocido: {tipo}")
        salida["mallas"][cid] = (np.asarray(v, np.float32).reshape(-1, 3), np.asarray(n, np.float32).reshape(-1, 3),
                                 np.asarray(c, np.float32).reshape(-1, 3))
    if tipo == "peine":
        aristas = [ent.resolver(r, estado).forma for r in params.get("aristas") or []]
        if aristas:
            datos = an.peine_curvatura(aristas, densidad=int(params.get("densidad", 30)),
                                       escala=float(params.get("escala", 1.0)))
            puas = np.asarray(datos["puas"], np.float32).reshape(-1, 3)
            salida["capas"].append(("lineas", puas, (0.55, 0.30, 0.85), 1.0))
            salida["capas"].append(("lineas", _segmentos(datos["envolventes"]), (0.85, 0.30, 0.65), 1.5))
    return salida


def combinar(resultados):
    """Junta varios análisis visibles en una sola descripción para el visor."""
    total = {"mallas": {}, "colores": None, "capas": [], "cortes": [], "solo": None}
    for r in resultados:
        total["mallas"].update(r["mallas"])
        total["capas"].extend(r["capas"])
        total["cortes"].extend(r["cortes"])
        total["colores"] = r["colores"] or total["colores"]
        total["solo"] = r["solo"] or total["solo"]
    return total
