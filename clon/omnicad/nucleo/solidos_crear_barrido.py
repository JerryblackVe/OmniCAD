"""Sólidos › Crear: barrido."""
from typing import TYPE_CHECKING
import numpy as np
from . import geometria as geo
import math
from .solidos_crear_occ import _registrar_tema
from .solidos_crear_comun import (
    _alambre, _aristas_de, _cara, _es_cerrado, _explorar, _gdir, _lista, _longitud, _marcos, _perpendicular, _pnt,
    _punto_en, _recortar_alambre, _unir, _unit, _validar, _xyz,
)
from .solidos_crear_patrones import _traslacion, _trsf_de_marcos, aplicar, unir_instancias

if TYPE_CHECKING:
    from .solidos_crear_occ import (
        Array1_gp_Pnt2d, BRepAdaptor_Curve, BRepAdaptor_Surface, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeVertex,
        BRepBuilderAPI_MakeWire, BRepBuilderAPI_RightCorner, BRepClass_FaceClassifier, BRepExtrema_DistShapeShape,
        BRepFill_NoContact, BRepOffsetAPI_MakePipeShell, BRepTools, GeomAPI_Interpolate, GeomAbs_Line, HArray1_gp_Pnt,
        Law_Interpol, Law_Linear, TopAbs_EDGE, TopAbs_FACE, TopAbs_IN, TopAbs_REVERSED, TopAbs_WIRE, TopoDS, gp_Ax2,
        gp_Pnt, gp_Pnt2d, gp_Vec,
    )


# ================================================================ 3. barrido
# Torsión máxima del barrido: 10 vueltas, elegida por tiempo. La guía de torsión lleva un punto cada 5°. El modo plano
# (rutas abiertas sin quiebres y mitades de rutas cerradas) es rápido: 3600° en 50 mm, 0,1 s. El curvilíneo (rutas
# abiertas lisas donde el plano falla) crece con los grados y tiene su propio tope (TORSION_MAXIMA_CURVILINEA). Medido
# en curvilíneo, rectángulo 4×2: 3600° tarda 27 s en una ruta de 100 mm con empalme de R ≤ 4; 5400° en esa ruta, 57 s;
# 36.000° en 50 mm, más de 100 s.
# Cambios de compatibilidad, a propósito: una receta vieja con más de 3600°, con más de 1800° donde va el curvilíneo, o
# con torsión en una ruta con esquinas ahora falla con un mensaje que dice el tope. Antes tardaban de 15 s a minutos, y
# las de esquinas daban un sólido inválido o tiraban abajo el proceso.
TORSION_MAXIMA = 3600.0
# En el modo curvilíneo (rutas abiertas lisas donde el plano falla) el tope es más bajo: recta de 20 mm + arco
# tangente de R2 (el perfil se autointerseca), 1800° anda en 5,8 s y 3600° tira abajo el proceso (0xC0000005, violación
# de acceso, a los 18 s). Se conserva también como tope de seguridad de las rutas cerradas, ahora partidas en dos.
TORSION_MAXIMA_CURVILINEA = 1800.0
# Quiebre (ángulo entre las tangentes de dos aristas seguidas) desde el que la torsión no se calcula. Medido, rectángulo
# 4 × 2 con 90°, dos rectas de 50 mm: con 0,5° el modo plano anda (0,2 s con 3600°); con 1°, 2° y 10° da un sólido
# inválido; el curvilíneo con 0,5° tarda 7,9 s (360°: 78 s; 1800°: más de 200 s) y con 10° o 90° da inválido a los
# 15 a 36 s (3600°: violación de acceso).
QUIEBRE_MAXIMO_TORSION = 0.5
_QUIEBRE_LISO = 0.1          # hasta acá la ruta es lisa: si el modo plano falla se prueba el curvilíneo


def validar_torsion(grados):
    """Frena una torsión no finita o de más de ±TORSION_MAXIMA grados antes de calcular nada."""
    if not math.isfinite(grados) or abs(grados) > TORSION_MAXIMA:
        raise geo.ErrorGeometria(f"⚠ Torsión: hasta ±{TORSION_MAXIMA:g}°; recibió {grados:g}°.")


def _quiebre_maximo(ruta):
    """Mayor ángulo (grados) entre la tangente final de una arista y la inicial de la siguiente (también entre la
    última y la primera si la ruta es cerrada); 0 en una ruta lisa."""
    tangentes = []
    for e in _aristas_de(ruta):
        c = BRepAdaptor_Curve(e)
        p, v0, v1 = gp_Pnt(), gp_Vec(), gp_Vec()
        c.D1(c.FirstParameter(), p, v0)
        c.D1(c.LastParameter(), p, v1)
        t0, t1 = _xyz(v0), _xyz(v1)
        tangentes.append((-t1, -t0) if e.Orientation() == TopAbs_REVERSED else (t0, t1))
    pares = list(zip(tangentes, tangentes[1:], strict=False))
    if _es_cerrado(ruta) and len(tangentes) > 1:
        pares.append((tangentes[-1], tangentes[0]))
    peor = 0.0
    for (_, fin), (inicio, _) in pares:
        n = float(np.linalg.norm(fin) * np.linalg.norm(inicio))
        coseno = float(fin @ inicio) / n if n > 1e-18 else -1.0
        peor = max(peor, math.degrees(math.acos(min(1.0, max(-1.0, coseno)))))
    return peor


def _guia_plana_posible(ruta, tolerancia=QUIEBRE_MAXIMO_TORSION):
    """¿La guía de torsión puede ir en modo plano sobre la ruta entera? Solo en rutas abiertas sin quiebres de más
    de `tolerancia` grados. El modo plano conserva la sección; el curvilíneo empareja por longitud de arco y puede
    deformarla. Una ruta cerrada necesita dos barridos abiertos en modo plano; un quiebre puede dar un sólido
    inválido o tirar abajo el kernel (codo de 90° con 3600°: violación de acceso)."""
    return not _es_cerrado(ruta) and _quiebre_maximo(ruta) <= tolerancia


def _guia_torsion(ruta, grados, radio):
    """Curva auxiliar que gira `grados` alrededor de la ruta: con MakePipeShell en modo auxiliar
    (NoContact) la normal del perfil apunta a ella, así el perfil se tuerce."""
    marcos = _marcos(ruta, max(64, int(abs(grados) / 5) + 2))
    arr = HArray1_gp_Pnt(1, len(marcos))
    for i, (p, _t, u, v) in enumerate(marcos):
        th = math.radians(grados) * i / (len(marcos) - 1)
        arr.SetValue(i + 1, _pnt(p + radio * (math.cos(th) * u + math.sin(th) * v)))
    interp = GeomAPI_Interpolate(arr, False, 1e-7)
    interp.Perform()
    if not interp.IsDone():
        raise geo.ErrorGeometria("No se pudo construir la guía de torsión.")
    return BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(interp.Curve()).Edge()).Wire()


def _radio_referencia(alambre, punto):
    """Radio con el que la inclinación de un barrido se pasa a escala: distancia del punto de la ruta al
    contorno si está adentro (exacto en círculos y polígonos regulares centrados); si no, √(A/π)."""
    cara = _cara(alambre)
    d = BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(_pnt(punto)).Vertex(), alambre).Value()
    if d > 1e-6 and _punto_en_cara(cara, punto):
        return d
    return math.sqrt(geo.area(cara) / math.pi)


def _curvaturas(alambre, muestras=80):
    """[(fracción 0..1 del largo, curvatura 1/mm)] dentro de cada arista del alambre: las esquinas entre aristas no
    cuentan (el barrido las resuelve con la transición en ángulo)."""
    from OCP.BRepLProp import BRepLProp_CLProps
    aristas = _aristas_de(alambre)
    largos = [_longitud(a) for a in aristas]
    total = sum(largos) or 1.0
    salida, hecho = [], 0.0
    for arista, largo in zip(aristas, largos, strict=True):
        c = BRepAdaptor_Curve(arista)
        u0, u1 = c.FirstParameter(), c.LastParameter()
        n = max(4, int(muestras * largo / total) + 1)
        for k in range(n + 1):
            props = BRepLProp_CLProps(c, u0 + (u1 - u0) * k / n, 2, 1e-7)
            avance = k / n if arista.Orientation() != TopAbs_REVERSED else 1 - k / n
            salida.append(((hecho + largo * avance) / total, props.Curvature() if props.IsTangentDefined() else 0.0))
        hecho += largo
    return salida


def _exigir_conicidad_en_curvas(perfil, ruta, p0, conicidad, escala):
    """B-372: con inclinación hacia afuera el perfil crece a lo largo de la ruta; si en una curva su borde pasa el radio
    de curvatura, el barrido se pliega sobre sí mismo y arma una forma gigante. Fusion lo rechaza: acá también, con el
    máximo que admite la ruta. `escala`: la del perfil al final de la ruta (la ley es lineal)."""
    puntos = []
    for arista in _aristas_de(perfil):
        c = BRepAdaptor_Curve(arista)
        for u in np.linspace(c.FirstParameter(), c.LastParameter(), 24):
            puntos.append(_xyz(c.Value(float(u))))
    # shortcut: el radio mayor del perfil en cualquier dirección, no solo hacia el centro de la curva: un perfil alargado
    # de costado puede rechazarse de más; medir sobre la normal de la ruta si aparece ese caso
    rmax = max(float(np.linalg.norm(q - p0)) for q in puntos)
    peor, tope = None, math.inf
    for f, k in _curvaturas(ruta):
        if k < 1e-9:
            continue
        r = rmax * (1 + f * (escala - 1))
        if f > 1e-9:       # la mayor escala que entra ahí, pasada a ángulo (la escala crece con la tangente)
            tope = min(tope, (1 / (k * rmax) - 1) / f)
        if r * k >= 1 and (peor is None or r * k > peor[0]):
            peor = (r * k, r, 1 / k, f)
    if peor is None:
        return
    _, r, radio, f = peor
    maximo = math.degrees(math.atan(max(tope, 0.0) * math.tan(math.radians(conicidad)) / (escala - 1)))
    raise geo.ErrorGeometria(
        f"Inclinación máx. {maximo:.1f}° en esta ruta.")


def _punto_en_cara(cara, punto):
    """¿El punto (sobre el plano de la cara plana) cae dentro de la cara?"""
    sup = BRepAdaptor_Surface(cara)
    pln = sup.Plane()
    d = _xyz(pln.Location())
    xd, yd = pln.XAxis().Direction(), pln.YAxis().Direction()
    rel = np.asarray(punto, float) - d
    uv = gp_Pnt2d(float(rel @ _xyz(xd)), float(rel @ _xyz(yd)))
    return BRepClass_FaceClassifier(cara, uv, 1e-7).State() == TopAbs_IN


def _ley_escala_carril(ruta, carril, n=33):
    """Ley de escala = distancia(ruta, carril) / distancia inicial, emparejando por fracción de longitud."""
    d0 = None
    puntos = Array1_gp_Pnt2d(1, n)
    for i in range(n):
        f = i / (n - 1)
        d = float(np.linalg.norm(_punto_en(carril, f)[0] - _punto_en(ruta, f)[0]))
        if d0 is None:
            if d < 1e-6:
                raise geo.ErrorGeometria("⚠ El carril no puede empezar sobre la ruta.")
            d0 = d
        puntos.SetValue(i + 1, gp_Pnt2d(f, d / d0))
    ley = Law_Interpol()
    ley.Set(puntos, False)
    return ley


def _barrido_alambre(perfil, ruta, carril, orientacion, torsion, conicidad, escala_carril, solido, radio_guia,
                     guia_plana=False):
    cerrada_con_torsion = carril is None and abs(torsion) > 1e-9 and _es_cerrado(ruta)
    rutas = [_recortar_alambre(ruta, 0.5), _recortar_alambre(ruta, 1.0, 0.5)] if cerrada_con_torsion else [ruta]
    torsion /= len(rutas)
    if carril is not None:
        if abs(torsion) > 1e-9 or abs(conicidad) > 1e-9:
            raise geo.ErrorGeometria("⚠ Torsión e inclinación no van con carril.")
        if escala_carril not in ("escalar", "estirar", "ninguna"):
            raise geo.ErrorGeometria(f"Escala de carril desconocida: {escala_carril}")
        if escala_carril == "estirar":
            from . import superficies as sfc        # Estirar: lo resuelven las secciones deformadas del gemelo
    partes = []
    for tramo in rutas:
        if carril is not None and escala_carril == "estirar":
            # El perfil crece solo hacia el carril y conserva la altura; la ley de escala de MakePipeShell es uniforme.
            partes.append(sfc._barrido_estirado([perfil], tramo, carril, solido=solido))
            continue
        ps = BRepOffsetAPI_MakePipeShell(tramo)
        ley = None
        if carril is not None:
            # El carril orienta el perfil (normal hacia el carril) y, salvo "ninguna", lo escala con la distancia
            # ruta→carril (ley propia: el modo ContactOnBorder de OCC solo funciona con perfiles suaves).
            ps.SetMode(carril, True, BRepFill_NoContact)
            aristas_ruta = list(_explorar(tramo, TopAbs_EDGE))
            aristas_carril = list(_explorar(carril, TopAbs_EDGE))
            if len(aristas_ruta) == len(aristas_carril) == 1 and all(
                    BRepAdaptor_Curve(TopoDS.Edge(a)).GetType() == GeomAbs_Line
                    for a in (aristas_ruta[0], aristas_carril[0])):
                p0, t0 = _punto_en(tramo, 0.0)
                p1, _ = _punto_en(tramo, 1.0)
                v0 = _punto_en(carril, 0.0)[0] - p0
                v1 = _punto_en(carril, 1.0)[0] - p1
                v0, v1 = v0 - t0 * float(v0 @ t0), v1 - t0 * float(v1 @ t0)
                if np.linalg.norm(v0) > 1e-6 and np.linalg.norm(v1) > 1e-6 and float(
                        _unit(v0) @ _unit(v1)) > 1 - 1e-12:
                    # Marco constante exacto: el auxiliar de OCC deforma hasta un prisma recto.
                    ps.SetMode(gp_Ax2(_pnt(p0), _gdir(t0), _gdir(v0)))
            if escala_carril != "ninguna":
                ley = _ley_escala_carril(tramo, carril)
        elif abs(torsion) > 1e-9:       # True = curvilíneo, False = plano (ver _guia_plana_posible)
            ps.SetMode(_guia_torsion(tramo, torsion, radio_guia),
                       not (guia_plana or cerrada_con_torsion), BRepFill_NoContact)
        elif isinstance(orientacion, tuple) and orientacion[0] == "alineada":
            ps.SetMode(_gdir(orientacion[1]))      # binormal fija: el perfil conserva su ángulo con el eje
        elif isinstance(orientacion, tuple) and orientacion[0] == "superficie":
            if not ps.SetMode(orientacion[1]):
                raise geo.ErrorGeometria("⚠ La ruta no está sobre la superficie guía.")
        elif orientacion == "paralela":
            p0, t0 = _punto_en(tramo, 0.0)
            ps.SetMode(gp_Ax2(_pnt(p0), _gdir(t0), _gdir(_perpendicular(t0))))
        elif orientacion == "perpendicular":
            ps.SetMode(False)           # triedro de Frenet corregido
        else:
            raise geo.ErrorGeometria(f"Orientación de barrido desconocida: {orientacion}")
        ps.SetTransitionMode(BRepBuilderAPI_RightCorner)
        if abs(conicidad) > 1e-9:
            p0, _ = _punto_en(tramo, 0.0)
            escala = 1.0 + _longitud(tramo) * math.tan(math.radians(conicidad)) / _radio_referencia(perfil, p0)
            if escala <= 0.01:
                raise geo.ErrorGeometria("⚠ La inclinación achica el perfil a cero.")
            if conicidad > 0:
                _exigir_conicidad_en_curvas(perfil, tramo, p0, conicidad, escala)
            ley = Law_Linear()
            ley.Set(0.0, 1.0, 1.0, escala)
        if ley is not None:
            ps.SetLaw(perfil, ley, False, False)
        else:
            ps.Add(perfil, False, False)
        try:
            ps.Build()
            hecho = ps.IsDone()
        except Exception:  # noqa: BLE001 — OCC lanza Standard_ConstructionError en los casos que no resuelve
            hecho = False
        if not hecho:
            raise geo.ErrorGeometria("⚠ El kernel no pudo barrer el perfil.")
        if cerrada_con_torsion:
            # OCC toma el perfil inicial como referencia del triedro de cada tramo: LastShape conserva el giro
            # acumulado aunque _marcos elija otro u,v inicial para la segunda mitad.
            perfil = TopoDS.Wire(ps.LastShape())
        if solido and not ps.MakeSolid():
            raise geo.ErrorGeometria("⚠ El barrido no cierra un sólido.")
        partes.append(ps.Shape())
    if len(partes) == 1:
        return partes[0]
    return _unir(partes) if solido else geo.compuesto(partes)


def barrer(perfiles, ruta, *, carril=None, orientacion="perpendicular", distancia=1.0, torsion=0.0,
           conicidad=0.0, escala_carril="escalar", solido=True, eje_alineado=None, superficie_guia=None,
           extension="completa", distancia_carril=1.0):
    """Barrido de Fusion [SLD-SWEEP-SOLID, SLD-REF-SWEEP] con BRepOffsetAPI_MakePipeShell.

    perfiles: caras planas (con agujeros) o alambres; ruta: aristas encadenadas o alambre. `distancia` =
    fracción 0..1 de la ruta. `torsion` y `conicidad` en grados (conicidad positiva = la región se ensancha;
    se aplica como escala lineal de cada lazo: los agujeros se achican). `carril` = Path + Guide Rail:
    `escala_carril` "escalar" (el perfil se agranda con la distancia ruta→carril), "ninguna" (el carril solo
    orienta) y "estirar" (crece solo hacia el carril y conserva la altura; lo resuelven las secciones deformadas
    del barrido de superficie). `extension` (Extent, con carril): "perpendicular" (Perpendicular To Path: termina en el
    plano perpendicular a la ruta en su final) o "completa" (Full Extents: la ruta hasta `distancia` y el carril hasta
    `distancia_carril`, cada uno en su fracción 0..1).
    `orientacion` "perpendicular" | "paralela" | "alineada" (Aligned: `eje_alineado` = dirección que el perfil mantiene
    como binormal, para el barrido de un cuerpo que no debe girar sobre su eje). `superficie_guia` (Path + Guide
    Surface): una cara o compuesto sobre el que va la ruta; el perfil sigue la normal de la superficie.
    `solido=False` devuelve la superficie. La torsión admite como máximo ±TORSION_MAXIMA grados y una ruta
    sin quiebres (QUIEBRE_MAXIMO_TORSION). Las rutas cerradas se barren por mitades abiertas en modo plano,
    continuando desde el perfil final anterior y uniendo los resultados. Si el plano falla en una ruta abierta
    lisa, se prueba el curvilíneo. Se conserva el tope ±TORSION_MAXIMA_CURVILINEA en rutas cerradas y en ese respaldo.
    """
    validar_torsion(torsion)
    if orientacion == "alineada":
        if eje_alineado is None or np.linalg.norm(eje_alineado) < 1e-12:
            raise geo.ErrorGeometria("⚠ La orientación alineada necesita el eje.")
        orientacion = ("alineada", tuple(float(x) for x in eje_alineado))
    if superficie_guia is not None:
        if carril is not None or abs(torsion) > 1e-9:
            raise geo.ErrorGeometria("⚠ Superficie guía sin carril ni torsión.")
        orientacion = ("superficie", superficie_guia)
    ruta = _recortar_alambre(_alambre(ruta), float(distancia))
    carril = _alambre(carril) if carril is not None else None
    if carril is not None:
        if extension == "perpendicular":
            from .superficies import _recortar_perpendicular
            ruta, carril = _recortar_perpendicular(ruta, carril)
        elif extension != "completa":
            raise geo.ErrorGeometria(f"Extensión del barrido desconocida: {extension}")
        elif not 0 < float(distancia_carril) <= 1:
            raise geo.ErrorGeometria(f"⚠ Fracción del carril fuera de 0 a 1: {distancia_carril:g}.")
        elif distancia_carril < 1:
            carril = _recortar_alambre(carril, float(distancia_carril))
    datos =(_lista(perfiles), ruta, carril, orientacion, torsion, conicidad, escala_carril, solido)
    if abs(torsion) > 1e-9 and carril is None:
        _exigir_ruta_para_torsion(ruta, torsion)
        if _guia_plana_posible(ruta):
            try:
                return _barrer(*datos, guia_plana=True)
            except geo.ErrorGeometria:
                if _quiebre_maximo(ruta) > _QUIEBRE_LISO:
                    raise           # con un quiebre el curvilíneo tarda minutos y tampoco lo resuelve
            if abs(torsion) > TORSION_MAXIMA_CURVILINEA:    # el curvilíneo de siempre, si la torsión le cabe
                raise geo.ErrorGeometria(f"Torsión máx. ±{TORSION_MAXIMA_CURVILINEA:g}° en esta ruta.")
    return _barrer(*datos, guia_plana=False)


MUESTRAS_BARRIDO_CUERPO = 200       # tope de copias del barrido de un cuerpo


def barrer_cuerpo(forma, ruta, *, orientacion="paralela", distancia=1.0, eje_alineado=None, muestras=None):
    """Barrido de un cuerpo sólido (Sweep › Solid Sweep de Fusion): el volumen que recorre `forma` al moverse a lo largo
    de `ruta`. `orientacion`: "paralela" (el cuerpo solo se traslada con el punto de la ruta), "perpendicular" (acompaña
    el marco de la ruta, de rotación mínima) o "alineada" (acompaña la ruta con `eje_alineado` fijo como binormal).
    `distancia` = fracción 0..1 de la ruta.
    shortcut: el kernel no barre sólidos (MakePrism rechaza los sólidos y el de sus caras se pliega en las siluetas):
    se une una copia del cuerpo cada cuarto de su medida menor (y cada 3° de giro), así que el borde de un barrido curvo
    queda escalonado; subir `muestras` (tope MUESTRAS_BARRIDO_CUERPO) lo afina."""
    if orientacion not in ("paralela", "perpendicular", "alineada"):
        raise geo.ErrorGeometria(f"Orientación del barrido desconocida: {orientacion}")
    if orientacion == "alineada" and (eje_alineado is None or np.linalg.norm(eje_alineado) < 1e-12):
        raise geo.ErrorGeometria("⚠ La orientación alineada necesita el eje.")
    w = _recortar_alambre(_alambre(ruta), float(distancia))
    largo = _longitud(w)
    caja = geo.caja_envolvente(forma)
    if caja is None:
        raise geo.ErrorGeometria("No hay cuerpo para barrer.")
    medidas = [m for m in np.subtract(caja[1], caja[0]) if m > 1e-6]
    if muestras is None:
        n = math.ceil(largo / (min(medidas) / 4)) + 1
        if orientacion != "paralela":
            fino = _marcos(w, 129)
            giro = sum(math.degrees(math.acos(max(-1.0, min(1.0, float(a[1] @ b[1])))))
                       for a, b in zip(fino[:-1], fino[1:], strict=True))
            n = max(n, math.ceil(giro / 3.0) + 1)
    else:
        n = int(muestras)
    n = max(2, min(n, MUESTRAS_BARRIDO_CUERPO))
    if largo / (n - 1) > min(medidas):
        raise geo.ErrorGeometria(
            f"Ruta muy larga: {MUESTRAS_BARRIDO_CUERPO} copias no alcanzan.")
    marcos = _marcos(w, n)

    def base(m):
        if orientacion == "alineada":
            t = m[1]
            b = _unit(np.asarray(eje_alineado, float) - t * float(np.asarray(eje_alineado, float) @ t), "eje alineado")
            return np.column_stack([t, np.cross(b, t), b])
        return np.column_stack([m[1], m[2], m[3]])
    p0, f0 = marcos[0][0], base(marcos[0])
    copias = [forma]
    for m in marcos[1:]:
        t = _traslacion(m[0] - p0) if orientacion == "paralela" else _trsf_de_marcos(p0, f0, m[0], base(m))
        copias.append(aplicar(forma, t))
    return _validar(unir_instancias(copias), "Barrido de cuerpo")


def _exigir_ruta_para_torsion(ruta, torsion):
    """Antes de calcular: la torsión necesita una ruta sin quiebres (QUIEBRE_MAXIMO_TORSION) y, si es cerrada,
    conserva el tope de seguridad de ±TORSION_MAXIMA_CURVILINEA grados."""
    quiebre = _quiebre_maximo(ruta)
    if quiebre > QUIEBRE_MAXIMO_TORSION:
        grados = (f"{x:.3g}°".replace(".", ",") for x in (quiebre, QUIEBRE_MAXIMO_TORSION))
        raise geo.ErrorGeometria("⚠ Torsión: quiebre {} (máx. {}).".format(*grados))
    if _es_cerrado(ruta) and abs(torsion) > TORSION_MAXIMA_CURVILINEA:
        raise geo.ErrorGeometria(f"⚠ Ruta cerrada: torsión admite ±{TORSION_MAXIMA_CURVILINEA:g}°.")


def _barrer(perfiles, ruta, carril, orientacion, torsion, conicidad, escala_carril, solido, guia_plana):
    """Barre cada perfil (el exterior menos sus agujeros) con la guía de torsión en el modo pedido."""
    salida = []
    for perfil in perfiles:
        if perfil.ShapeType() == TopAbs_FACE:
            cara = TopoDS.Face(perfil)
            exterior = BRepTools.OuterWire_s(cara)
            interiores = [TopoDS.Wire(w) for w in _explorar(cara, TopAbs_WIRE) if not w.IsSame(exterior)]
        else:
            exterior, interiores = _alambre(perfil), []
        bb = geo.caja_envolvente(exterior)
        radio_guia = max(1.0, float(np.linalg.norm(np.subtract(bb[1], bb[0]))))
        forma = _barrido_alambre(exterior, ruta, carril, orientacion, torsion, conicidad, escala_carril, solido,
                                 radio_guia, guia_plana)
        if solido:
            for w in interiores:   # el agujero se achica cuando la región se ensancha
                hueco = _barrido_alambre(w, ruta, carril, orientacion, torsion, -conicidad, escala_carril, True,
                                         radio_guia, guia_plana)
                forma = geo.booleano(forma, hueco, "cortar")
        salida.append(forma)
    if not salida:
        raise geo.ErrorGeometria("Elegí al menos un perfil para barrer.")
    resultado = _unir(salida) if solido else geo.compuesto(salida)
    return _validar(resultado, "Barrido")


_registrar_tema(globals())
