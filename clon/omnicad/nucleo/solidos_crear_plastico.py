"""Sólidos › Crear: plastico."""
from typing import TYPE_CHECKING
import numpy as np
from . import geometria as geo
import math
from .solidos_crear_occ import _registrar_tema
from .solidos_crear_comun import (
    _MARGEN, _alambre, _aristas_de, _caja_proyectada, _cara, _explorar, _gdir, _longitud, _piezas_que_tocan, _pnt,
    _poligono, _proyectar_caja, _punto_en, _rayo, _trasladar, _unificar, _unir, _unit, _validar,
)
from .solidos_crear_extrusion import _herramienta_extrusion, _prisma, _recortar_hasta
from .solidos_crear_barrido import _barrido_alambre
from .solidos_crear_agujeros import herramienta_agujero

if TYPE_CHECKING:
    from .solidos_crear_occ import (
        BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepClass3d_SolidClassifier, BRepExtrema_DistShapeShape,
        BRepPrimAPI_MakeHalfSpace, ShapeAnalysis_Edge, TopAbs_FACE, TopAbs_IN, TopAbs_SOLID, TopoDS, gp_Ax2, gp_Circ,
    )


# ================================================================ 15. plástico (simplificado)
def saliente(cuerpo, punto, direccion, *, diametro_exterior, diametro_agujero, altura=None,
             profundidad_agujero=None, angulo_desmoldeo=0.0):
    """Saliente (Boss) de la pestaña Plástico [SLD-BOSS], versión simplificada: un solo lado, sin nervios ni
    sujetador. Columna de `diametro_exterior` que nace en `punto` y avanza según `direccion` hasta el cuerpo
    (o `altura`), con desmoldeo (más ancha en la base) y agujero piloto de `diametro_agujero` (profundidad =
    la de la columna si no se indica). Devuelve el cuerpo resultante."""
    d = _unit(direccion, "dirección del saliente")
    if diametro_agujero <= 0 or diametro_exterior <= diametro_agujero:
        raise geo.ErrorGeometria("⚠ El diámetro exterior no supera al agujero.")
    disco = _cara(BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(
        gp_Circ(gp_Ax2(_pnt(punto), _gdir(d)), diametro_exterior / 2)).Edge()).Wire())
    if altura is None:
        _, hi = _caja_proyectada(cuerpo, punto, d)
        if hi <= 0:
            raise geo.ErrorGeometria("⚠ El cuerpo no está del lado del saliente.")
        columna = _recortar_hasta(_prisma(disco, d, hi + _MARGEN, angulo_desmoldeo), [disco], cuerpo,
                                  "cuerpo", None, punto)
        if not geo.se_tocan(columna, cuerpo, 1e-4):
            raise geo.ErrorGeometria("El saliente no llega al cuerpo.")
        altura = _proyectar_caja(geo.caja_envolvente(columna), punto, d)[1]
    else:
        columna = _prisma(disco, d, altura, angulo_desmoldeo)
    resultado = _unificar(geo.booleano(cuerpo, columna, "unir"))
    hueco = herramienta_agujero(punto, d, diametro=diametro_agujero, profundidad=profundidad_agujero or altura,
                                punta="plana")
    return _validar(geo.booleano(resultado, hueco, "cortar"), "Saliente")


def _validar_aristas_labio(cuerpo, aristas):
    """Las aristas del labio tienen que tener largo y no ser de costura: si no, el kernel se cuelga (B-158)."""
    analizador = ShapeAnalysis_Edge()
    caras = [TopoDS.Face(c) for c in _explorar(cuerpo, TopAbs_FACE)]
    for arista in _aristas_de(aristas):
        if _longitud(arista) <= 1e-9:
            raise geo.ErrorGeometria("⚠ Arista sin largo: elegí un borde.")
        if any(analizador.IsSeam(arista, cara) for cara in caras):
            raise geo.ErrorGeometria("⚠ Arista de costura: elegí un borde.")


def _marco_labio(cuerpo, aristas, tirar, ancho, alto):
    """(alambre, punto de arranque, dirección hacia la pared) de las aristas del labio."""
    w = _alambre(aristas)
    p0, t0 = _punto_en(w, 0.0)
    m = _unit(np.cross(tirar, t0), "arista (no puede ser paralela a la dirección de tirado)")
    # De qué lado de la arista está la pared: se prueba en el medio de la primera arista (no en un vértice,
    # que suele ser una esquina sobre el borde del cuerpo), un poco hacia el lateral, hacia AMBOS lados de
    # la dirección de tirado (con uno solo el labio crecía mal en el borde superior o en el inferior: B-08).
    pm, tm = _punto_en(w, 0.5 * _longitud(_aristas_de(w)[0]) / _longitud(w))
    mm = _unit(np.cross(tirar, tm))
    eps = min(ancho, alto) * 0.25
    if all(BRepClass3d_SolidClassifier(cuerpo, _pnt(pm + mm * eps + s * eps), 1e-7).State() != TopAbs_IN
           for s in (tirar, -tirar)):
        m = -m
    return w, p0, m


def _sector_labio(p0, m, tirar, w, base, altura):
    """Sector del labio: sección rectangular `base` × `altura` (con signo: la altura negativa va al otro lado
    del tirado, como la ranura) barrida por la cadena de aristas."""
    seccion = _poligono([p0, p0 + m * base, p0 + m * base + tirar * altura, p0 + tirar * altura])
    return _barrido_alambre(seccion, w, None, "perpendicular", 0.0, 0.0, "escalar", True, 1.0)


def labio_ranura(cuerpo, aristas, direccion_tirado, *, tipo="labio", ancho, alto, holgura=0.0):
    """Labio / ranura (Lip) de la pestaña Plástico [SLD-LIP], versión simplificada: sección rectangular barrida
    por la cadena de aristas del borde de la pared. "labio": `ancho` hacia adentro de la pared desde la arista
    y `alto` hacia `direccion_tirado` (se une); "ranura": la misma sección agrandada en `holgura`, hacia
    adentro del material (se corta). Sin desmoldeo ni reglas de plástico. Devuelve el cuerpo resultante."""
    if tipo not in ("labio", "ranura"):
        raise geo.ErrorGeometria(f"Tipo desconocido: {tipo}")
    if ancho <= 0 or alto <= 0 or holgura < 0:
        raise geo.ErrorGeometria("⚠ Ancho y alto positivos, holgura 0 o más.")
    _validar_aristas_labio(cuerpo, aristas)
    tirar = _unit(direccion_tirado, "dirección de tirado")
    w, p0, m = _marco_labio(cuerpo, aristas, tirar, ancho, alto)
    base, altura = (ancho, alto) if tipo == "labio" else (ancho + holgura, -(alto + holgura))
    sector = _sector_labio(p0, m, tirar, w, base, altura)
    resultado = geo.booleano(cuerpo, sector, "unir" if tipo == "labio" else "cortar")
    return _validar(_unificar(resultado), "Labio" if tipo == "labio" else "Ranura")


def labio_y_ranura(cuerpo_labio, cuerpo_ranura, aristas, direccion_tirado, *, ancho, alto, holgura=0.0):
    """Labio y acanalado (Lip And Groove) de la pestaña Plástico [SLD-LIP]: el labio en `cuerpo_labio` y la ranura
    calculada del labio (con `holgura`) en `cuerpo_ranura`, en un paso. La ranura sale de las medidas del labio: la
    holgura agranda el ancho y el alto. Los dos cuerpos tienen que tocarse y las aristas tienen que estar alineadas
    (Fusion: «las caras normales entre sí»). Devuelve {"labio": forma, "ranura": forma}."""
    if ancho <= 0 or alto <= 0 or holgura < 0:
        raise geo.ErrorGeometria("⚠ Ancho y alto positivos, holgura 0 o más.")
    _validar_aristas_labio(cuerpo_labio, aristas)
    tirar = _unit(direccion_tirado, "dirección de tirado")
    w, p0, m = _marco_labio(cuerpo_labio, aristas, tirar, ancho, alto)
    con_labio = geo.booleano(cuerpo_labio, _sector_labio(p0, m, tirar, w, ancho, alto), "unir")
    sin_ranura = geo.booleano(cuerpo_ranura, _sector_labio(p0, m, tirar, w, ancho + holgura, alto + holgura), "cortar")
    return {"labio": _validar(_unificar(con_labio), "Labio"), "ranura": _validar(_unificar(sin_ranura), "Ranura")}



def _fuera(forma, objeto):
    """`forma` sin lo que quedó afuera del sólido o de los sólidos `objeto`."""
    afuera = geo.booleano(forma, objeto, "cortar")
    return _unir(_piezas_que_tocan(afuera, [forma], 1e-5)) if not geo.esta_vacia(afuera) else forma


def apoyo(cuerpos, perfiles, *, direccion, invertir=False, desfase=0.0, grosor, lados=(), angulo_desmoldeo=0.0,
          extension="todo", caras_superiores=(), recortar=True):
    """Apoyo (Rest) de la pestaña Plástico [PLA-2]: desde perfiles cerrados de boceto da una pared de `grosor` en la
    cara del cuerpo que quedó en su lugar, sobre cada perfil. `direccion` = normal del plano del boceto; el perfil se
    desplaza `desfase` según ella (`invertir` = Flip). `lados`: distancias de cada pared al perfil, con signo
    (+n hacia el cuerpo). El apoyo atraviesa los cuerpos; lo que queda afuera se va y lo que asoma en una cara se
    recorta en ella (Trim): queda el área plana que llega a esa cara. `angulo_desmoldeo` = Draft Angle: la pared mira
    el cuerpo de `direccion` y se angosta hacia él. `extension` "todo" (All: atraviesa los cuerpos) o "objeto" (To
    Object: termina en las caras del cuerpo que se ve desde el perfil, del lado de `direccion`). `caras_superiores`
    (Top Faces de Avanzado): si se dan, el apoyo solo se crea bajo esas caras planas y termina en ellas, sin sobresalir
    del cuerpo. `recortar` (Trim de Avanzado, por defecto activado): quita el área que queda afuera del cuerpo; con
    False se deja el apoyo extendido hasta la extrusión completa. Devuelve la herramienta para unir a los cuerpos."""
    d = _unit(direccion, "dirección del apoyo")
    if grosor <= 0:
        raise geo.ErrorGeometria("El grosor del apoyo debe ser positivo.")
    if extension not in ("todo", "objeto"):
        raise geo.ErrorGeometria(f"Extensión desconocida: {extension}")
    if any(geo.plano_de_cara(cara) is None for cara in caras_superiores):
        raise geo.ErrorGeometria("⚠ Caras superiores del apoyo no son planas.")
    if not lados:
        raise geo.ErrorGeometria("⚠ El apoyo necesita la distancia de un lado.")
    if any(dist < 0 for _, dist in lados):
        raise geo.ErrorGeometria("⚠ Distancias de lado negativas en el apoyo.")
    if any(signo == -1 for signo, _ in lados) and not any(signo == 1 for signo, _ in lados):
        raise geo.ErrorGeometria("⚠ El apoyo necesita material del lado 1.")
    suma = sum(dist for _, dist in lados)
    if not abs(suma - grosor) <= 1e-6 * max(grosor, 1.0):
        raise geo.ErrorGeometria(f"⚠ Grosor del apoyo: {suma:g} mm (suma lados).")
    compuestos = cuerpos if isinstance(cuerpos, (list, tuple)) else [cuerpos]
    solidos = [c if c.ShapeType() == TopAbs_SOLID else TopoDS.Solid(c)
               for c in (list(_explorar(geo.compuesto(compuestos), TopAbs_SOLID)) if cuerpos else [])]
    if not solidos:
        raise geo.ErrorGeometria("El apoyo necesita un cuerpo.")
    cuerpos_forma = _unir(solidos)
    caras = [TopoDS.Face(f) for perfil in perfiles for f in _explorar(perfil, TopAbs_FACE)]
    if not caras:
        raise geo.ErrorGeometria("⚠ Apoyo: perfiles cerrados de boceto o caras.")
    centro = np.mean([geo.centro_masa(f, superficie=True) for f in caras], axis=0)
    inicios = [_trasladar(f, d * desfase) for f in caras] if desfase else caras
    cerca = min(solidos, key=lambda s: min(BRepExtrema_DistShapeShape(i, s).Value() for i in inicios))
    lo, hi = _caja_proyectada(cerca, centro, d)
    if not lo <= desfase <= hi:
        raise geo.ErrorGeometria("⚠ El perfil del apoyo queda fuera del cuerpo.")
    # La pared se angosta hacia la cara final (donde apoya el cuerpo): en `_prisma` la conicidad positiva ensancha
    # desde el perfil, así que se pasa cambiada de signo. `invertir` es el espejo del abanico.
    if invertir:
        angulo_desmoldeo = -angulo_desmoldeo
    angulo_desmoldeo = -angulo_desmoldeo
    rango = min(signo * dist for signo, dist in lados), max(signo * dist for signo, dist in lados)
    lo, hi = _caja_proyectada(cuerpos_forma, centro, d)
    # El abanico del grosor va del lado 1 al lado 2 con el perfil como plano neutro; para atravesar el cuerpo sigue
    # la misma pared (Todo, hasta la última cara) o se queda en él (Hasta objeto).
    abajo, arriba = min(rango[0], lo), max(rango[1], hi)
    herramienta = _herramienta_extrusion(inicios, [], d, 0.0, [(v, angulo_desmoldeo) for v in (abajo, arriba)
                                                              if abs(v) > 1e-9 or v == abajo == arriba], None)
    # Todo: atraviesa el cuerpo y el Trim lo deja en la cara extrema de cada lado (semiespacio hasta ella); con
    # Recortar desactivado se queda la extrusión completa, que sobresale del cuerpo cuando el perfil está desfazado.
    if recortar:
        herramienta = _recortar_semiespacio(herramienta, centro, d, hi)
        herramienta = _recortar_semiespacio(herramienta, centro, -d, -lo)
    if extension == "objeto":
        # Hasta objeto: la pared termina donde el cuerpo la contiene (lo que hay del cuerpo desde el perfil).
        herramienta = geo.booleano(herramienta, cuerpos_forma, "intersecar")
        if geo.esta_vacia(herramienta):
            raise geo.ErrorGeometria("El perfil queda dentro del cuerpo objetivo.")
    if caras_superiores:
        # Top Faces: cada cara elegida baja una columna vertical hasta el fondo: el apoyo solo se crea en su área
        # y termina en la cara (la tapa de la columna es la cara misma).
        columnas = [_prisma(TopoDS.Face(cara), -d, arriba - abajo + 2.0) for cara in caras_superiores]
        acotado = geo.booleano(herramienta, _unir(columnas), "intersecar")
        if geo.esta_vacia(acotado):
            raise geo.ErrorGeometria("⚠ Las caras elegidas quedan fuera del perfil.")
        herramienta = _validar(acotado, "Apoyo")
    if geo.esta_vacia(herramienta) or BRepExtrema_DistShapeShape(herramienta, cuerpos_forma).Value() > 1e-4:
        raise geo.ErrorGeometria("⚠ El apoyo no toca el cuerpo.")
    return _validar(herramienta, "Apoyo")


def _recortar_semiespacio(herr, origen, d, altura):
    """`herr` sin lo que pasa de la altura `altura` según `d` (semiespacio del lado del origen)."""
    d = np.asarray(d, float)
    pl = geo.Plano.desde_marco(np.asarray(origen, float) + d * altura, d, (0.0, 0.0, 1.0) if abs(d[2]) < 0.9
                               else (1.0, 0.0, 0.0))
    semi = BRepPrimAPI_MakeHalfSpace(geo.cara_de_plano(pl, 1e3), _pnt(np.asarray(origen, float) - d * 1e-3)).Solid()
    return _validar(geo.booleano(herr, semi, "intersecar"), "Apoyo")


def _caja_local(p, a, b, n, da, db, dn):
    """Caja rectangular p + α·a + β·b + γ·n con α∈da, β∈db, γ∈dn (intervalos en mm)."""
    esq = [p + n * dn[0] + a * da[0] + b * db[0], p + n * dn[0] + a * da[1] + b * db[0],
           p + n * dn[0] + a * da[1] + b * db[1], p + n * dn[0] + a * da[0] + b * db[1]]
    return _prisma(_cara(_poligono(esq)), n, dn[1] - dn[0])


def grampa(cuerpo_gancho, cuerpo_ranura, marcos, *, tipo="paralelo", largo, ancho, espesor, alto_gancho,
           holgura=0.1, angulo=0.0, extension="siguiente", distancia=None):
    """Grampa de fijación (Snap Fit) de la pestaña Plástico [SLD-SNAP-FIT], versión simplificada: en cada marco
    (punto, normal, brazo) del boceto arma un gancho en voladizo —base, brazo de `largo` según la normal y cabeza
    de `alto_gancho`— que se une al cuerpo del gancho, y le copia al cuerpo de la ranura un hueco con `holgura`
    alrededor, así los dos cuerpos encajan sin interferencia (equivale al comando Snap Fit de Fusion).
    `tipo`: "paralelo" empuja la cabeza a lo largo del brazo, "perpendicular" a lo ancho (gancho y ranurado
    perpendiculares) y "contorno" la pone como collarín abrazando la punta (gancho y contorno). `angulo` gira el
    brazo alrededor de la normal (giro Uniforme, el mismo para todos los puntos). `extension`: "siguiente" hunde la
    base hasta la cara más cercana del cuerpo del gancho (To Next) o "distancia" hasta `distancia` (Distance).
    `cuerpo_ranura=None` deja solo el gancho. Devuelve {"gancho": forma, "ranura": forma o None}."""
    if tipo not in ("paralelo", "perpendicular", "contorno"):
        raise geo.ErrorGeometria(f"Tipo de grampa desconocido: {tipo}")
    if extension not in ("siguiente", "distancia"):
        raise geo.ErrorGeometria(f"Extensión desconocida: {extension}")
    if extension == "distancia" and distancia is None:
        raise geo.ErrorGeometria("⚠ Falta la distancia de la extensión.")
    if min(largo, ancho, espesor, alto_gancho) <= 0 or (distancia is not None and distancia < 0):
        raise geo.ErrorGeometria("Las medidas de la grampa deben ser positivas.")
    if holgura < 0:
        raise geo.ErrorGeometria("La holgura no puede ser negativa.")
    cabezas = {"paralelo": ((espesor / 2, espesor / 2 + alto_gancho), (-ancho / 2, ancho / 2),
                            (largo - alto_gancho, largo)),
               "perpendicular": ((-espesor / 2, espesor / 2), (ancho / 2, ancho / 2 + alto_gancho),
                                 (largo - alto_gancho, largo)),
               "contorno": ((-(espesor / 2 + alto_gancho), espesor / 2 + alto_gancho),
                            (-(ancho / 2 + alto_gancho), ancho / 2 + alto_gancho),
                            (largo, largo + alto_gancho))}
    partes_g, partes_r = [], []
    for punto, normal, brazo in marcos:
        p = np.asarray(punto, float)
        n = _unit(normal, "normal de la grampa")
        a = _unit(geo._rotar(np.asarray(brazo, float), n, math.radians(angulo)), "brazo de la grampa")
        b = _unit(np.cross(n, a), "lateral de la grampa")
        if extension == "distancia":
            base = float(distancia)
        else:
            golpes = [t for t in _rayo(cuerpo_gancho, p, -n) if t >= 0]
            base = golpes[0] if golpes else 0.0
        brazo_caja = _caja_local(p, a, b, n, (-espesor / 2, espesor / 2), (-ancho / 2, ancho / 2), (0, largo))
        ha, hb, hn = cabezas[tipo]
        cabeza = _caja_local(p, a, b, n, ha, hb, hn)
        partes_g += [brazo_caja, cabeza]
        if base > 1e-9:
            partes_g.append(_caja_local(p, a, b, n, (-espesor / 2, espesor / 2), (-ancho / 2, ancho / 2),
                                        (-base, 0)))
        c = holgura
        partes_r += [_caja_local(p, a, b, n, (-espesor / 2 - c, espesor / 2 + c), (-ancho / 2 - c, ancho / 2 + c),
                                 (-c, largo + c)),
                     _caja_local(p, a, b, n, (ha[0] - c, ha[1] + c), (hb[0] - c, hb[1] + c), (hn[0] - c, hn[1] + c))]
    herramienta = _validar(_unir(partes_g), "Grampa")
    if not geo.se_tocan(cuerpo_gancho, herramienta, 1e-4):
        raise geo.ErrorGeometria("El gancho debe tocar el cuerpo.")
    salida = {"gancho": _validar(_unificar(geo.booleano(cuerpo_gancho, herramienta, "unir")), "Grampa")}
    if cuerpo_ranura is not None:
        ranura = _validar(_unir(partes_r), "Grampa")
        recortado = geo.booleano(cuerpo_ranura, ranura, "cortar")
        if geo.volumen(cuerpo_ranura) - geo.volumen(recortado) <= 1e-9:
            raise geo.ErrorGeometria("⚠ El gancho no llega al cuerpo.")
        salida["ranura"] = _validar(_unificar(recortado), "Grampa")
    else:
        salida["ranura"] = None
    return salida


_registrar_tema(globals())
