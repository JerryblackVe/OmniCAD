"""Sólidos › Crear: repujado."""
from typing import TYPE_CHECKING
import numpy as np
from . import geometria as geo
import math
from .solidos_crear_occ import _registrar_tema
from .solidos_crear_comun import (
    _aristas_de, _caras_de, _engrosar_lamina, _explorar, _lista, _normal_superficie, _trasladar, _unificar, _unir,
    _unit, _validar, _xyz,
)
from .solidos_crear_extrusion import _prisma

if TYPE_CHECKING:
    from .solidos_crear_occ import (
        BRepAdaptor_Curve, BRepAdaptor_Surface, BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse,
        BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire, BRepClass_FaceClassifier, BRepLib,
        BRepTools, Geom2dAPI_Interpolate, Geom2d_Line, Geom2d_TrimmedCurve, GeomAbs_Cylinder, GeomAbs_Line,
        Geom_CylindricalSurface, HArray1_gp_Pnt2d, ShapeFix_Face, TopAbs_FACE, TopAbs_IN, TopAbs_ON, TopAbs_REVERSED,
        TopAbs_SOLID, TopAbs_WIRE, TopoDS, gp_Dir2d, gp_Pnt, gp_Pnt2d, gp_Vec,
    )


# ================================================================ 6. repujado
def repujado(cuerpo, caras_perfil, cara_objetivo, profundidad, *, tipo="relieve", envolver=True, adaptar=True,
             cadena_tangente=False, desfase_h=0.0, desfase_v=0.0, giro=0.0, invertir=False):
    """Repujado (Emboss) de Fusion [SLD-EMBOSS] sobre un cuerpo (ver `repujado_en_cuerpos`): `cara_objetivo` es una
    cara o una LISTA de caras del cuerpo. Devuelve el cuerpo resultante."""
    return repujado_en_cuerpos([(cuerpo, cara_objetivo)], caras_perfil, profundidad, tipo=tipo, envolver=envolver,
                               adaptar=adaptar, cadena_tangente=cadena_tangente, desfase_h=desfase_h,
                               desfase_v=desfase_v, giro=giro, invertir=invertir)[0]


def repujado_en_cuerpos(objetivos, caras_perfil, profundidad, *, tipo="relieve", envolver=True, adaptar=True,
                        cadena_tangente=False, desfase_h=0.0, desfase_v=0.0, giro=0.0, invertir=False):
    """Repujado (Emboss) de Fusion [SLD-EMBOSS]: "relieve" agrega material, "grabado" lo quita. La profundidad
    negativa SIEMPRE graba (Deboss), sin importar el «tipo» elegido (Fusion: «Negative values create a Deboss
    effect»; no se invierte dos veces). `objetivos` = [(cuerpo, cara o lista de caras)]; devuelve los cuerpos
    resultantes en el mismo orden (sin cambios el que no recibe nada).

    Caras planas: el texto se PROYECTA en su lugar sobre las caras elegidas y se REPARTE entre ellas, como en
    Fusion: cada cara recibe solo la parte que le cae encima (aunque las caras sean de cuerpos distintos o estén a
    distinta altura); lo que cae fuera de ellas se pierde y una cara tapada por otra elegida más afuera no recibe lo
    que queda debajo. Si no cae sobre ninguna, error. Perfiles NO paralelos a la cara (p. ej. un costado): con
    `adaptar` (por defecto) se giran para mirar hacia afuera, se centran en la zona y se achican hasta entrar.
    Cara cilíndrica (envolver por defecto): el boceto (en un plano paralelo al eje) se enrolla sobre el cilindro
    conservando las longitudes (arco = distancia en el boceto) y se le da espesor radial.
    Otras caras curvas (esfera, cono, forma libre): el boceto se proyecta según su normal sobre la cara, del lado
    que lo mira, y se engrosa según la normal de la cara (`_proyectar_en_cara`).
    `cadena_tangente` agrega caras conectadas tangencialmente, pero esas caras agregadas reciben solo lo que les cae
    encima (su proyección toca la caja del perfil): un cuadro en el medio de la tapa no se copia en los costados ni en
    los empalmes de al lado. La alineación gira alrededor del centro de los perfiles y después desplaza en los ejes
    locales horizontal/vertical (mm); `giro` va en grados.
    `invertir` cambia la dirección normal sin cambiar el efecto elegido (unión o corte)."""
    # Fusion (Emboss reference › Depth): profundidad negativa SIEMPRE graba, sin importar «tipo» (no se invierte dos veces).
    es_relieve = profundidad > 0 and tipo == "relieve"
    profundidad = abs(profundidad)
    geo.exigir_longitud(profundidad, "La profundidad del repujado")
    if tipo not in ("relieve", "grabado"):
        raise geo.ErrorGeometria(f"Efecto de repujado desconocido: {tipo}")
    perfiles = _caras_de(caras_perfil)
    if not perfiles:
        raise geo.ErrorGeometria("Elegí al menos un perfil para repujar.")
    if not all(math.isfinite(x) for x in (desfase_h, desfase_v, giro)):
        raise geo.ErrorGeometria("⚠ Alineación del repujado: valor inválido.")
    # La cadena agrega caras que el usuario no eligió: solo reciben lo que les cae encima, así que se descarta la
    # cara cuya caja proyectada sobre el plano del perfil no lo toca (planos perpendiculares, empalmes lejos, etc.).
    # shortcut: la caja de todos los perfiles se mide en el plano del primero (como el alineado y el envoltorio);
    # si alguna vez se mezclan perfiles de bocetos en planos distintos, proyectar cada perfil en el suyo.
    pl_perfil = geo.plano_de_cara(perfiles[0])
    caja_perfil = _caja_2d(perfiles, pl_perfil) if cadena_tangente else None
    caras = []
    for i, (cuerpo, cs) in enumerate(objetivos):
        for c in _lista(cs):
            if cadena_tangente:
                from .solidos_modificar import caras_tangentes
                cadena = caras_tangentes(cuerpo, c)
            else:
                cadena = [c]
            for k, cara in enumerate(cadena):
                if k and not _cajas_se_tocan(_caja_2d([cara], pl_perfil), caja_perfil):
                    continue
                if not any(j == i and cara.IsSame(otra) for j, otra in caras):
                    caras.append((i, TopoDS.Face(cara)))
    if not caras:
        raise geo.ErrorGeometria("Elegí la cara sobre la que va el repujado.")
    sentido = (1.0 if es_relieve else -1.0) * (-1.0 if invertir else 1.0)
    herramientas = [[] for _ in objetivos]
    grupos = []                                       # caras planas con la misma normal: una sola zona
    for k, (i, cara) in enumerate(caras, 1):
        pl = geo.plano_de_cara(cara)
        if pl is not None:
            grupo = next((g for g in grupos if float(g[0][2].normal @ pl.normal) > 1 - 1e-6), None)
            if grupo is None:
                grupos.append([(i, cara, pl)])
            else:
                grupo.append((i, cara, pl))
            continue
        donde = f" (cara {k})" if len(caras) > 1 else ""
        cilindro = BRepAdaptor_Surface(cara).GetType() == GeomAbs_Cylinder
        if cilindro and not (envolver or cadena_tangente):
            # B-848: 1 renglón en español simple (UX-9), sin hablar en código; la casilla la tilda el diálogo.
            raise geo.ErrorGeometria("Marcá «Envolver en la cara»" + donde + ".")
        pl_perfil = geo.plano_de_cara(perfiles[0])
        alineados = _alinear_repujado(perfiles, pl_perfil, desfase_h, desfase_v, giro)
        prof, efecto = -profundidad if invertir else profundidad, "relieve" if es_relieve else "grabado"
        herramientas[i].append(_envolver_en_cilindro(alineados, cara, prof, efecto, recortar=cadena_tangente)
                               if cilindro else _proyectar_en_cara(alineados, cara, pl_perfil, prof, efecto))
    for grupo in grupos:
        for i, h in _repujado_en_grupo(perfiles, grupo, sentido * profundidad, adaptar, desfase_h, desfase_v, giro):
            herramientas[i].append(h)
    herramientas = [[h for h in hs if not geo.esta_vacia(h)] for hs in herramientas]
    if not any(herramientas):
        raise geo.ErrorGeometria("Perfiles fuera de las caras: movelos encima.")
    operacion = "unir" if es_relieve else "cortar"
    return [_validar(_unificar(_aplicar_a_cuerpo(cuerpo, hs, operacion)), "Repujado") if hs else cuerpo
            for (cuerpo, _), hs in zip(objetivos, herramientas, strict=True)]


def _alinear_repujado(perfiles, plano, desfase_h, desfase_v, giro):
    if not (desfase_h or desfase_v or giro):
        return perfiles
    areas = [geo.area(f) for f in perfiles]
    centro = sum(a * np.array(geo.centro_masa(f, superficie=True))
                 for a, f in zip(areas, perfiles, strict=True)) / sum(areas)
    desplazamiento = plano.u * desfase_h + plano.v * desfase_v
    return [TopoDS.Face(geo.trasladar(geo.rotar(f, centro, plano.normal, giro), desplazamiento)) for f in perfiles]


def _repujado_en_grupo(perfiles, grupo, prof, adaptar, desfase_h, desfase_v, giro):
    """[(índice del cuerpo, herramienta)] para un grupo de caras planas paralelas [(índice, cara, plano)]: el texto
    se ubica una vez para todo el grupo y cada cara recibe lo que le cae encima. Se recorre de la cara más de
    afuera a la más de adentro: lo que queda debajo de una cara elegida más afuera no se repuja."""
    pl0 = grupo[0][2]
    n = np.asarray(pl0.normal, float)
    sobre = _perfiles_en_zona(perfiles, [c for _, c, _ in grupo], pl0, adaptar)
    sobre = _alinear_repujado(sobre, pl0, desfase_h, desfase_v, giro)
    cajas_piezas = [_caja_2d([f], pl0) for f in sobre]

    def altura(pl):
        return float(np.asarray(pl.origen, float) @ n)
    orden = sorted(grupo, key=lambda x: -altura(x[2]))
    cajas = [_caja_2d([c], pl0) for _, c, _ in orden]
    salida = []
    for k, (i, cara, pl) in enumerate(orden):
        dz = altura(pl) - altura(pl0)
        piezas = [f for f, cj in zip(sobre, cajas_piezas, strict=True) if _cajas_se_tocan(cj, cajas[k])]
        if not piezas:
            continue
        if abs(dz) > 1e-9:
            piezas = [_trasladar(f, n * dz) for f in piezas]
        tapan = [j for j in range(k) if altura(orden[j][2]) > altura(pl) + 1e-6 and _cajas_se_tocan(cajas[j], cajas[k])]
        # lo que cae sobre la cara se recorta en 2D (cara contra cara: ~75 veces más rápido que con sólidos) y
        # recién después se le da espesor; si una cara de más afuera la tapa, se le resta su sombra
        limite = cara
        if tapan:
            limite = _booleana_caras([cara], [_trasladar(orden[j][1], n * (altura(pl) - altura(orden[j][2])))
                                              for j in tapan], BRepAlgoAPI_Cut)
        partes = _booleana_caras(piezas, [limite], BRepAlgoAPI_Common) if limite is not None else None
        if partes is not None:
            caras_h = [TopoDS.Face(f) for f in _explorar(partes, TopAbs_FACE)]
            if caras_h:
                salida.append((i, geo.compuesto([_prisma(f, n, prof) for f in caras_h])))
            continue
        # el kernel no pudo en 2D: el recorte con sólidos (más lento)
        prismas = [_prisma(f, n, prof) for f in piezas]
        limite = _prisma(cara, n, prof)
        if tapan:
            alto = 2 * abs(prof)
            sombra = _unir([_prisma(_trasladar(orden[j][1], n * (altura(pl) - altura(orden[j][2]) - alto)), n,
                                    2 * alto) for j in tapan])
            limite = geo.booleano(limite, sombra, "cortar")
        salida.append((i, _comun_rapido(prismas, limite)))
    return salida


def _lista_de_formas(formas):
    from OCP.collections import List_TopoDS_Shape
    lista = List_TopoDS_Shape()
    for f in formas:
        lista.Append(f)
    return lista


def _booleana_caras(piezas, herramientas, clase):
    """Booleana 2D entre caras coplanares (`BRepAlgoAPI_Common` o `_Cut`), cada pieza como argumento propio (en un
    compuesto, las que se tocan salían mal). None si el kernel no la resuelve."""
    try:
        op = clase()
        op.SetArguments(_lista_de_formas(piezas))
        op.SetTools(_lista_de_formas(herramientas))
        op.SetRunParallel(geo.PARALELO)
        op.SetNonDestructive(True)   # B-48: no escribir en las entradas
        op.Build()
        if op.IsDone() and not op.Shape().IsNull():
            return op.Shape()
    except Exception:  # noqa: BLE001
        pass
    return None


def _comun_rapido(piezas, limite):
    """Parte de `piezas` (sólidos que pueden tocarse, como los perfiles de un boceto) que cae dentro de `limite`,
    en UNA operación general (cada pieza es un argumento: en un compuesto, las que se tocan salían mal) y sin
    unificar caras: es lo que más tarda con el texto. Si el kernel no la resuelve, une primero las piezas."""
    try:
        op = BRepAlgoAPI_Common()
        op.SetArguments(_lista_de_formas(piezas))
        op.SetTools(_lista_de_formas([limite]))
        op.SetRunParallel(geo.PARALELO)                       # OpenCascade reparte el trabajo en varios núcleos
        op.SetNonDestructive(True)   # B-48: no escribir en las entradas
        op.Build()
        if op.IsDone() and not op.Shape().IsNull():
            return op.Shape()
    except Exception:  # noqa: BLE001
        pass
    return geo.booleano(_unir(piezas), limite, "intersecar")


def _aplicar_a_cuerpo(cuerpo, herramientas, operacion):
    """Une o corta al cuerpo todas las herramientas (sólidos que pueden tocarse) en una sola operación general."""
    solidos = [TopoDS.Solid(x) for h in herramientas for x in _explorar(h, TopAbs_SOLID)]
    if solidos:
        try:
            op = BRepAlgoAPI_Fuse() if operacion == "unir" else BRepAlgoAPI_Cut()
            op.SetArguments(_lista_de_formas([cuerpo]))
            op.SetTools(_lista_de_formas(solidos))
            op.SetRunParallel(geo.PARALELO)
            op.SetNonDestructive(True)   # B-48: no escribir en las entradas
            op.Build()
            if op.IsDone() and not op.Shape().IsNull():
                return geo.unificar_caras(op.Shape())
        except Exception:  # noqa: BLE001
            pass
    return geo.booleano(cuerpo, _unir(herramientas), operacion)


def _estados_en_cara(formas, cara, maximo=4000):
    """Estado (adentro, en el borde, afuera) de los vértices de la malla de `formas` (coplanares con la cara) respecto
    de la cara. Es lo que reemplaza a una booleana para saber si el texto entra: ~13 µs por punto."""
    pts = np.vstack([np.asarray(geo.teselar(f)[0], float).reshape(-1, 3) for f in formas])
    if len(pts) > maximo:
        pts = pts[::len(pts) // maximo + 1]
    return [BRepClass_FaceClassifier(cara, gp_Pnt(*map(float, p)), 1e-6).State() for p in pts]


def _dentro_de_cara(formas, cara):
    return all(e in (TopAbs_IN, TopAbs_ON) for e in _estados_en_cara(formas, cara))


def _matriz_giro(a, b, eje_alterno):
    """Rotación 4x4 que lleva el vector unitario `a` sobre `b` (`eje_alterno` si son opuestos)."""
    c = float(a @ b)
    m = np.identity(4)
    if c > 1 - 1e-9:
        return m
    if c < -1 + 1e-9:
        eje, ang = np.asarray(eje_alterno, float), math.pi
    else:
        eje, ang = np.cross(a, b), math.acos(c)
    eje = eje / np.linalg.norm(eje)
    x, y, z = eje
    k = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    m[:3, :3] = np.identity(3) + math.sin(ang) * k + (1 - math.cos(ang)) * (k @ k)
    return m


def _puntos_2d(formas, pl):
    """Vértices de la malla de `formas` en los ejes u, v del plano `pl` (coordenadas absolutas: el punto 3D de (x, y)
    es `pl.origen + x u + y v`)."""
    pts = np.vstack([np.asarray(geo.teselar(f)[0], float).reshape(-1, 3) for f in formas])
    return np.column_stack([pts @ np.asarray(pl.u, float), pts @ np.asarray(pl.v, float)])


def _caja_2d(formas, pl):
    p = _puntos_2d(formas, pl)
    return p.min(axis=0), p.max(axis=0)


def _cajas_se_tocan(a, b, tol=1e-3):         # cajas de la malla (float32): tolerancia en milésimas
    return bool(np.all(a[0] <= b[1] + tol) and np.all(b[0] <= a[1] + tol))


def _zona_convexa(caras, pl):
    """(A, b, centro) de la envolvente convexa de las caras en u, v: adentro es A x <= b (filas de A unitarias) y
    `centro` es su centro de áreas. Es la zona donde se ubica el texto que se reparte entre las caras."""
    from scipy.spatial import ConvexHull
    pts = _puntos_2d(caras, pl)
    try:
        env = ConvexHull(pts)
        a, b = env.equations[:, :2], -env.equations[:, 2]
        poli = pts[env.vertices]                      # antihorario
        x, y = poli[:, 0], poli[:, 1]
        cruz = x * np.roll(y, -1) - np.roll(x, -1) * y
        area = cruz.sum() / 2
        centro = (np.array([((x + np.roll(x, -1)) * cruz).sum(), ((y + np.roll(y, -1)) * cruz).sum()]) / (6 * area)
                  if abs(area) > 1e-12 else pts.mean(axis=0))
    except Exception:  # noqa: BLE001 — puntos alineados (cara degenerada): la caja
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        a = np.array([[1.0, 0.0], [-1.0, 0.0], [0.0, 1.0], [0.0, -1.0]])
        b = np.array([hi[0], -lo[0], hi[1], -lo[1]])
        centro = (lo + hi) / 2
    return a, b, centro


def _ubicar_en_zona(rel, a, b, preferido):
    """(escala, centro) para el texto de puntos `rel` (relativos a su punto de referencia) dentro de la zona A x <= b:
    la escala es 1 si entra y, si no, el 90 % de la máxima con la que entra (un programa lineal); el centro es el
    más cercano a `preferido` (se mueve lo menos posible, en línea recta) con un margen chico al borde si cabe."""
    from scipy.optimize import linprog, minimize
    soporte = (a @ rel.T).max(axis=1)                 # cuánto se estira el texto hacia cada lado de la zona
    libre = [(None, None), (None, None)]
    r = linprog([0, 0, -1], A_ub=np.column_stack([a, soporte]), b_ub=b, bounds=libre + [(0, None)], method="highs")
    if not r.success or r.x[2] <= 1e-9:
        return 1.0, np.asarray(preferido, float)
    s_max = float(r.x[2])
    escala = 1.0 if s_max >= 1.0 else 0.9 * s_max
    tam = float(np.ptp(b))                            # ~ tamaño de la zona
    p = np.asarray(preferido, float)
    for margen in (0.02 * tam, 0.0):
        tope = b - escala * soporte - margen          # el centro tiene que cumplir A c <= tope
        hay = linprog([0, 0], A_ub=a, b_ub=tope, bounds=libre, method="highs")
        if not hay.success:
            continue
        if np.all(a @ p <= tope + 1e-9):
            return escala, p
        res = minimize(lambda c: float(((c - p) ** 2).sum()), hay.x, jac=lambda c: 2 * (c - p), method="SLSQP",
                       constraints=[{"type": "ineq", "fun": lambda c, t=tope: t - a @ c, "jac": lambda c: -a}])
        ok = res.success and np.all(a @ res.x <= tope + 1e-6)
        return escala, (res.x if ok else hay.x)
    return escala, r.x[:2]


def _perfiles_en_zona(perfiles, caras, pl, adaptar):
    """Perfiles apoyados en el plano `pl` del grupo de caras paralelas `caras`. Paralelos al grupo: en su lugar, tal
    cual (se proyectan: cada cara recibe después lo que le cae encima, como en Fusion). No paralelos: con `adaptar`
    se giran para mirar hacia afuera, se centran en la zona (envolvente convexa de las caras) y se achican sin
    deformarse hasta entrar; sin `adaptar`, error."""
    n = np.asarray(pl.normal, float)
    origen = np.asarray(pl.origen, float)
    normales = [_normal_superficie(f) for f in perfiles]
    if all(abs(abs(float(x @ n)) - 1) < 1e-6 for x in normales):
        return [_trasladar(f, n * float((origen - np.array(geo.centro_masa(f, superficie=True))) @ n))
                for f in perfiles]
    if not adaptar:
        raise geo.ErrorGeometria("⚠ Los perfiles no son paralelos a la cara.")
    areas = [geo.area(f) for f in perfiles]           # se gira para mirar hacia afuera (se lee bien desde afuera)
    c0 = sum(x * np.array(geo.centro_masa(f, superficie=True)) for x, f in zip(areas, perfiles, strict=True)) / sum(areas)
    m = np.identity(4)
    m[:3, 3] = c0 - n * float((c0 - origen) @ n)      # el centro, bajado al plano
    traslado = np.identity(4)
    traslado[:3, 3] = -c0
    giro = _matriz_giro(normales[int(np.argmax(areas))], n, pl.v)
    sobre = [geo.transformar(f, m @ giro @ traslado) for f in perfiles]
    a, b, centro_zona = _zona_convexa(caras, pl)
    pts = _puntos_2d(sobre, pl)
    ref = (pts.min(axis=0) + pts.max(axis=0)) / 2
    escala, centro = _ubicar_en_zona(pts - ref, a, b, centro_zona)
    u, v = np.asarray(pl.u, float), np.asarray(pl.v, float)
    r3, c3 = origen + u * ref[0] + v * ref[1], origen + u * centro[0] + v * centro[1]
    una = len(caras) == 1
    for _ in range(30):                               # con una cara no convexa: achica hasta que entre de verdad
        m = np.identity(4)
        m[:3, :3] *= escala
        m[:3, 3] = c3 - escala * r3
        cand = [geo.transformar(f, m) for f in sobre]
        if not una or _dentro_de_cara(cand, caras[0]):
            return cand
        escala *= 0.9
    return cand


def _normal_orientada(cara, u, v):
    sup = BRepAdaptor_Surface(cara)
    p, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
    sup.D1(u, v, p, du, dv)
    nrm = np.cross(_xyz(du), _xyz(dv))
    if cara.Orientation() == TopAbs_REVERSED:
        nrm = -nrm
    return _xyz(p), _unit(nrm, "normal de la cara")


def _segmento2d(a, b):
    largo = a.Distance(b)
    if largo < 1e-12:
        raise geo.ErrorGeometria("El boceto tiene un segmento de largo nulo.")
    return Geom2d_TrimmedCurve(Geom2d_Line(a, gp_Dir2d(b.X() - a.X(), b.Y() - a.Y())), 0.0, largo)


def _aristas_envueltas(e, a_uv, superficie):
    """Arista del boceto llevada al cilindro: las rectas quedan exactas (hélices); las curvas se interpolan,
    partidas en 4 tramos si son cerradas (un lazo de una sola arista BSpline deja mal el engrosado)."""
    curva = BRepAdaptor_Curve(e)
    u_a, u_b = curva.FirstParameter(), curva.LastParameter()
    if e.Orientation() == TopAbs_REVERSED:
        u_a, u_b = u_b, u_a
    if curva.GetType() == GeomAbs_Line:
        tramos = [_segmento2d(a_uv(_xyz(curva.Value(u_a))), a_uv(_xyz(curva.Value(u_b))))]
    else:
        partes = 4 if curva.Value(u_a).Distance(curva.Value(u_b)) < 1e-7 else 1
        tramos = []
        for i in range(partes):
            t0 = u_a + (u_b - u_a) * i / partes
            t1 = u_a + (u_b - u_a) * (i + 1) / partes
            muestras = 16
            arr = HArray1_gp_Pnt2d(1, muestras + 1)
            for k in range(muestras + 1):
                arr.SetValue(k + 1, a_uv(_xyz(curva.Value(t0 + (t1 - t0) * k / muestras))))
            interp = Geom2dAPI_Interpolate(arr, False, 1e-9)
            interp.Perform()
            tramos.append(interp.Curve())
    aristas = []
    for c2d in tramos:
        arista = BRepBuilderAPI_MakeEdge(c2d, superficie).Edge()
        BRepLib.BuildCurves3d_s(arista, 1e-6)
        aristas.append(arista)
    return aristas


def _proyectar_en_cara(perfiles, cara, plano, profundidad, tipo):
    """Repujado sobre una cara que no es plana ni cilíndrica (esfera, cono, forma libre; H-96): el boceto se proyecta
    según su normal sobre la cara, solo del lado que mira al boceto, y lo que cae se engrosa según la normal de la cara
    (afuera el relieve, adentro el grabado)."""
    # shortcut: proyecta en vez de envolver conservando longitudes como Fusion; en piezas chicas frente a la curvatura
    # casi no cambia. Si se nota (texto largo sobre una esfera), mapear en (u, v) como `_envolver_en_cilindro`.
    n = np.asarray(plano.normal, float)
    minimo, maximo = (np.asarray(v, float) for v in geo.caja_envolvente(geo.compuesto([cara, *perfiles])))
    largo = 2 * float(np.linalg.norm(maximo - minimo)) + 1
    # del lado del boceto: hacia donde queda su plano visto desde el centro de la cara (+normal si la corta)
    lado = n if float((np.asarray(plano.origen, float) - geo.centro_masa(cara, superficie=True)) @ n) >= -1e-9 else -n
    herramientas = []
    for f in perfiles:
        partes = _booleana_caras([cara], [_prisma(_trasladar(f, -n * largo), n, 2 * largo)], BRepAlgoAPI_Common)
        if partes is None:
            raise geo.ErrorGeometria("⚠ No se pudo proyectar el boceto en la cara.")
        for parte in _caras_de(partes):
            bu0, bu1, bv0, bv1 = BRepTools.UVBounds_s(parte)
            if float(_normal_orientada(parte, (bu0 + bu1) / 2, (bv0 + bv1) / 2)[1] @ lado) > 0:
                herramientas.append(_engrosar_lamina(parte, profundidad if tipo == "relieve" else -profundidad))
    return _unir(herramientas) if herramientas else geo.compuesto([])


def _envolver_en_cilindro(perfiles, cara, profundidad, tipo, *, recortar=False):
    sup = BRepAdaptor_Surface(cara)
    cil = sup.Cylinder()
    radio = cil.Radius()
    ax3 = cil.Position()
    o, z = _xyz(ax3.Location()), _xyz(ax3.Direction())
    x, y = _xyz(ax3.XDirection()), _xyz(ax3.YDirection())
    giro = 1.0 if float(np.cross(z, x) @ y) > 0 else -1.0     # terna derecha o izquierda del cilindro
    um = (sup.FirstUParameter() + sup.LastUParameter()) / 2
    vm = (sup.FirstVParameter() + sup.LastVParameter()) / 2
    p, nrm = _normal_orientada(cara, um, vm)
    afuera = float(nrm @ (p - o - z * float((p - o) @ z))) > 0      # cilindro macizo (True) o agujero
    superficie = Geom_CylindricalSurface(ax3, radio)
    herramientas = []
    for f in perfiles:
        nf = _normal_superficie(f)
        if abs(float(nf @ z)) > 1e-6:
            raise geo.ErrorGeometria("⚠ El boceto a envolver no es paralelo al eje.")
        c = np.array(geo.centro_masa(f, superficie=True))
        er = nf if float((c - o) @ nf) >= 0 else -nf
        et = np.cross(z, er)
        # B-849: hasta una vuelta completa (2π·r) el contorno se reparte sin dar dos vueltas; más ancho no entra.
        s = np.asarray(geo.teselar(f)[0], float).reshape(-1, 3) @ et
        if float(s.max() - s.min()) > 2 * math.pi * radio + 1e-6:
            raise geo.ErrorGeometria(
                f"Más ancho que el cilindro (máx. {2 * math.pi * radio:.1f} mm).")
        # B-220: más lejos que media vuelta de cada lado, alcanzarlo daría la vuelta entera al cilindro y
        # repujaría del otro lado: queda afuera, como un perfil fuera de las caras.
        if float(s.max()) > math.pi * radio + 1e-6 or float(s.min()) < -math.pi * radio - 1e-6:
            continue
        u0 = math.atan2(float(er @ y), float(er @ x))

        def a_uv(q, et=et, u0=u0):
            rel = np.asarray(q, float) - o
            return gp_Pnt2d(u0 + giro * float(rel @ et) / radio, float(rel @ z))

        exterior = BRepTools.OuterWire_s(f)
        envueltos = []
        for w in [exterior] + [TopoDS.Wire(w) for w in _explorar(f, TopAbs_WIRE) if not w.IsSame(exterior)]:
            mk = BRepBuilderAPI_MakeWire()
            for e in _aristas_de(w):
                for arista in _aristas_envueltas(e, a_uv, superficie):
                    mk.Add(arista)
            if not mk.IsDone():
                raise geo.ErrorGeometria("⚠ No se envolvió el contorno en el cilindro.")
            envueltos.append(mk.Wire())
        mf = BRepBuilderAPI_MakeFace(superficie, envueltos[0], True)
        for w in envueltos[1:]:
            mf.Add(w)
        arreglo = ShapeFix_Face(mf.Face())
        arreglo.Perform()
        lamina = arreglo.Face()
        partes = _booleana_caras([lamina], [cara], BRepAlgoAPI_Common) if recortar else lamina
        if partes is None:
            raise geo.ErrorGeometria("⚠ No se pudo recortar el repujado en la cara.")
        for parte in _caras_de(partes):
            bu0, bu1, bv0, bv1 = BRepTools.UVBounds_s(parte)
            p_l, n_l = _normal_orientada(parte, (bu0 + bu1) / 2, (bv0 + bv1) / 2)
            normal_afuera = float(n_l @ (p_l - o - z * float((p_l - o) @ z))) > 0
            # relieve: hacia afuera del material (lejos del eje en un macizo, hacia el eje en un agujero)
            lejos_del_eje = (tipo == "relieve") == afuera
            herramientas.append(_engrosar_lamina(parte, profundidad if lejos_del_eje == normal_afuera else -profundidad))
    return _unir(herramientas) if herramientas else geo.compuesto([])


_registrar_tema(globals())
