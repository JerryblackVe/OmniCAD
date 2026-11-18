"""Sólidos › Crear: patrones."""
from typing import TYPE_CHECKING
import numpy as np
from . import geometria as geo
import math
from .solidos_crear_occ import _registrar_tema
from .solidos_crear_comun import (
    _alambre, _es_cerrado, _gdir, _gvec, _longitud, _marcos, _pnt, _punto_en, _tipado, _unit,
)

if TYPE_CHECKING:
    from .solidos_crear_occ import (
        BRepAdaptor_Surface, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse, BRepBuilderAPI_Transform, BRepClass_FaceClassifier,
        BRepLib, BRep_Builder, BRep_Tool, GeomAbs_Plane, List_TopoDS_Shape, TopAbs_EDGE, TopAbs_FORWARD, TopAbs_IN,
        TopAbs_SHELL, TopAbs_VERTEX, TopAbs_WIRE, TopLoc_Location, TopoDS, TopoDS_Face, TopoDS_Iterator, TopoDS_Shell,
        TopoDS_Solid, gp_Ax1, gp_Ax2, gp_Pnt, gp_Trsf, gp_Vec,
    )


# ================================================================ 11. patrones y simetría
# Instancias máximas de un patrón (el original cuenta): igual al máximo de cada campo de cantidad de la interfaz.
# Se valida antes de armar nada: una cantidad enorme se comía la memoria (MemoryError sin mensaje).
INSTANCIAS_MAXIMAS = 10_000


def _miles(n):
    return f"{n:,}".replace(",", ".")


def _cantidad(n, simetrico, total=False):
    """Instancias de una dirección del patrón, original incluido: n, o 2n − 1 si es simétrico y n cuenta un solo lado
    (receta vieja; `total`: n ya es el total, como en Fusion)."""
    if int(n) < 1:
        raise geo.ErrorGeometria("La cantidad del patrón debe ser al menos 1.")
    return 2 * int(n) - 1 if simetrico and not total else int(n)


def _exigir_instancias(total):
    if total > INSTANCIAS_MAXIMAS:
        raise geo.ErrorGeometria(f"⚠ Máximo {_miles(INSTANCIAS_MAXIMAS)} instancias: pediste {_miles(total)}.")


def unir_instancias(formas):
    """Une el original y las copias de un patrón («Combinar» de Fusion) en UNA booleana con varios argumentos.
    Unirlas de a una (geo.unir_todos) crece con el cuadrado de la cantidad: cubos de 10 mm separados 20, 10 × 10 en
    3,1 s, 20 × 20 en 51 s, 32 × 32 y 100 × 100 más de 200 s; así 0,1 s, 0,3 s, 0,7 s y 8,3 s (20 × 20 solapados
    cada 5 mm: 5,6 s). Mismo resultado."""
    formas = [f for f in formas if f is not None]
    if not formas:
        raise geo.ErrorGeometria("No hay geometría para unir.")
    if len(formas) == 1:
        return formas[0]
    argumentos, herramientas = List_TopoDS_Shape(), List_TopoDS_Shape()
    argumentos.Append(formas[0])
    for f in formas[1:]:
        herramientas.Append(f)
    op = BRepAlgoAPI_Fuse()
    op.SetArguments(argumentos)
    op.SetTools(herramientas)
    op.SetRunParallel(geo.PARALELO)      # RS-X4: 1600 cubos 0,62 → 0,53 s
    op.SetNonDestructive(True)   # B-48: no escribir en las entradas
    try:
        op.Build()
        hecho = op.IsDone()
    except Exception:  # noqa: BLE001 — OCC lanza excepciones sin texto en los casos que no resuelve
        hecho = False
    if not hecho:
        raise geo.ErrorGeometria("⚠ El kernel no unió las copias del patrón.")
    return geo.unificar_caras(op.Shape())


def _mapa(formas):
    mapa = geo.IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher()
    for f in formas:
        mapa.Add(f)
    return mapa


def _cajas(formas):
    """Cajas holgadas de `formas`, una fila [x0, y0, z0, x1, y1, z1] por forma (las que tienen geometría)."""
    cajas = [c for c in (geo._caja_occ(f, 1e-6, True) for f in formas) if c is not None]
    esquinas = [(c.CornerMin(), c.CornerMax()) for c in cajas]
    return np.array([(p.X(), p.Y(), p.Z(), q.X(), q.Y(), q.Z()) for p, q in esquinas]).reshape(-1, 6)


def _solapa(caja, cajas):
    return bool(np.any(np.all(caja[:3] <= cajas[:, 3:], axis=1) & np.all(cajas[:, :3] <= caja[3:], axis=1)))


def _huecos_de(cara, imagen, aristas_nuevas):
    """Contornos que la booleana le agregó a `cara` (su `imagen`), o None si le cambió otra cosa que agregar huecos."""
    contornos = list(geo._explorar(imagen.Oriented(TopAbs_FORWARD), TopAbs_WIRE))
    huecos = [w for w in contornos if all(aristas_nuevas.Contains(a) for a in geo._explorar(w, TopAbs_EDGE))]
    return huecos if huecos and len(contornos) - len(huecos) == sum(1 for _ in geo._explorar(cara, TopAbs_WIRE)) else None


def _copias_intercambiables(cara, relativas):
    """¿Cada movimiento de `relativas` deja el plano de `cara` en su lugar, sin darlo vuelta?"""
    sup = BRepAdaptor_Surface(cara)
    if sup.GetType() != GeomAbs_Plane:
        return False
    plano = sup.Plane()
    o, n = plano.Location(), plano.Axis().Direction()
    return all(n.Transformed(t).Angle(n) < 1e-9 and abs(gp_Vec(o, o.Transformed(t)).Dot(gp_Vec(n))) < 1e-7 for t in relativas)


def _cara_con_huecos(cara, contornos):
    """`cara` con `contornos` agregados como huecos, en la orientación de `cara`."""
    b, nueva, ubicacion = BRep_Builder(), TopoDS_Face(), TopLoc_Location()
    b.MakeFace(nueva, BRep_Tool.Surface_s(cara, ubicacion), ubicacion, BRep_Tool.Tolerance_s(cara))
    for w in geo._explorar(cara.Oriented(TopAbs_FORWARD), TopAbs_WIRE):
        b.Add(nueva, w)
    for w in contornos:
        b.Add(nueva, w)
        for a in geo._explorar(w, TopAbs_EDGE):
            BRepLib.BuildPCurveForEdgeOnPlane_s(TopoDS.Edge(a), nueva)
    return nueva.Oriented(cara.Orientation())


def patronear_caras(cuerpo, copias, trsfs, operacion):
    """«Optimizado» del patrón de operaciones (Compute Type › Optimized, «patterning feature faces»): el kernel corta o
    une solo la primera copia y sus caras se repiten en las demás, sin booleana por copia ni una contra todas. Una
    booleana con n herramientas crece más rápido que n (aristas nuevas sobre una misma cara): 100 prismas de 64 lados,
    19,5 s con la herramienta unida y 5 s así; 100 agujeros, 0,124 s y 0,064 s.
    `copias`: la herramienta ya movida con cada gp_Trsf de `trsfs`. Devuelve el cuerpo nuevo o None si las copias no son
    intercambiables (lo que en Fusion da error con «operaciones divididas»; ahí la herramienta da el mismo resultado):
    un movimiento con simetría o escala, un cuerpo de varios sólidos, una copia que hace más que abrir huecos en caras
    planas o que no cae entera adentro de esas caras, sin que su caja toque otra cara, una arista u otra copia.
    shortcut: solo caras planas, un agujero radial en un tubo va por la herramienta; sumar cilindros si un patrón lo pide."""
    solidos = geo.solidos(cuerpo)
    if (len(solidos) != 1 or len(geo.caras(solidos[0])) != len(geo.caras(cuerpo))
            or any(t.IsNegative() or abs(t.ScaleFactor() - 1) > 1e-12 for t in trsfs)):
        return None
    args, herramientas = List_TopoDS_Shape(), List_TopoDS_Shape()
    args.Append(cuerpo)
    herramientas.Append(copias[0])
    op = {"cortar": BRepAlgoAPI_Cut, "unir": BRepAlgoAPI_Fuse}[operacion]()
    op.SetArguments(args)
    op.SetTools(herramientas)
    try:
        op.Build()
        primera = op.Shape() if op.IsDone() else None
    except Exception:  # noqa: BLE001 — OCC lanza excepciones sin texto en los casos que no resuelve
        primera = None
    cascaras = list(geo._explorar(cuerpo, TopAbs_SHELL))
    if primera is None or len(geo.solidos(primera)) != 1 or len(list(geo._explorar(primera, TopAbs_SHELL))) != len(cascaras):
        return None

    tocadas, imagenes = [], []
    for cara in geo.caras(cuerpo):
        imagen = geo.lista_occ(op.Modified(cara))
        if op.IsDeleted(cara) or len(imagen) > 1:
            return None
        if imagen:
            tocadas.append(TopoDS.Face(cara))
            imagenes.append(TopoDS.Face(imagen[0]))
    conocidas = _mapa(geo.caras(cuerpo) + imagenes)
    nuevas = [c for c in geo.caras(primera) if not conocidas.Contains(c)]
    aristas_nuevas = _mapa(a for c in nuevas for a in geo._explorar(c, TopAbs_EDGE))
    huecos = [_huecos_de(c, i, aristas_nuevas) for c, i in zip(tocadas, imagenes, strict=True)]
    inversa = trsfs[0].Inverted()
    relativas = [t.Multiplied(inversa) for t in trsfs]
    if not tocadas or None in huecos or not all(_copias_intercambiables(c, relativas) for c in tocadas):
        return None

    indice = _mapa(tocadas)
    fijas = _cajas([c for c in geo.caras(cuerpo) if not indice.Contains(c)]
                   + [a for c in tocadas for a in geo._explorar(c, TopAbs_EDGE)])
    cajas = _cajas(copias)
    if any(_solapa(c, fijas) or _solapa(c, cajas[i + 1:]) for i, c in enumerate(cajas)):
        return None
    for cara, lista in zip(tocadas, huecos, strict=True):
        p = BRep_Tool.Pnt_s(TopoDS.Vertex(next(iter(geo._explorar(lista[0], TopAbs_VERTEX)))))
        if any(BRepClass_FaceClassifier(cara, p.Transformed(t), 1e-6).State() != TopAbs_IN for t in relativas):
            return None

    contornos = [w for lista in huecos for w in lista]
    paquete = geo.compuesto(contornos + nuevas)      # juntos: cada contorno sigue compartiendo aristas con sus caras
    por_copia = []
    for t in relativas:
        movido = BRepBuilderAPI_Transform(paquete, t, True).Shape()
        it, hijos = TopoDS_Iterator(movido, True, True), []
        while it.More():
            hijos.append(it.Value())
            it.Next()
        por_copia.append(hijos)
    reemplazo, desde = {}, 0
    for i, (cara, lista) in enumerate(zip(tocadas, huecos, strict=True), 1):
        reemplazo[i] = _cara_con_huecos(cara, [w for hijos in por_copia for w in hijos[desde:desde + len(lista)]])
        desde += len(lista)
    b, resultado = BRep_Builder(), TopoDS_Solid()
    b.MakeSolid(resultado)
    for cascara in cascaras:
        nueva, cambio = TopoDS_Shell(), False
        b.MakeShell(nueva)
        for cara in geo.caras(cascara):
            i = indice.FindIndex(cara)
            b.Add(nueva, reemplazo.get(i, cara))
            cambio = cambio or i > 0
        if cambio:
            for hijos in por_copia:
                for cara in hijos[len(contornos):]:
                    b.Add(nueva, cara)
        nueva.Closed(True)
        b.Add(resultado, nueva)

    v0 = geo.volumen_exacto(cuerpo)
    esperado = v0 + len(trsfs) * (geo.volumen_exacto(primera) - v0)
    herramienta = geo.compuesto(copias)
    if (abs(geo.volumen_exacto(resultado) - esperado) > 1e-6 * max(1.0, v0)
            or geo._problema_booleana(cuerpo, herramienta, operacion, resultado,
                                      geo._volumenes_entrada(cuerpo, herramienta)) is not None):
        return None
    return resultado


def _indices(n, simetrico, de_mas=0):
    """Pasos desde el original, el original primero. Simétrico con `de_mas` (+1 o −1, PAT-1): n es el total con el
    original y la copia que sobra cuando n es par va a ese lado, como en Fusion; sin él, n a cada lado (receta vieja)."""
    if int(n) < 1:
        raise geo.ErrorGeometria("La cantidad del patrón debe ser al menos 1.")
    n = int(n)
    if simetrico and de_mas:
        menos = (n - 1) // 2
        return sorted((de_mas * k for k in range(-menos, n - menos)), key=abs)
    return [0] + [s * i for i in range(1, n) for s in (-1, 1)] if simetrico else list(range(n))


def _paso(n, distancia, distribucion, por_lado=False):
    """Avance entre instancias. `por_lado` (Fusion, simétrico): la Extensión se mide del original a la última."""
    if distribucion == "extension" and por_lado:
        return distancia / (n // 2) if n > 1 else 0.0
    if distribucion == "extension":
        return distancia / (n - 1) if n > 1 else 0.0
    if distribucion == "espaciado":
        return distancia
    raise geo.ErrorGeometria(f"Distribución desconocida: {distribucion}")


def _traslacion(v):
    t = gp_Trsf()
    t.SetTranslation(_gvec(v))
    return t


def _rotacion(punto, eje, radianes):
    t = gp_Trsf()
    t.SetRotation(gp_Ax1(_pnt(punto), _gdir(eje)), radianes)
    return t


def _identidad():
    return gp_Trsf()


def _componer(t, previa):
    """Primero `previa`, después `t`."""
    return t.Multiplied(previa)


def _id_rectangular(s):
    """Identificador (i, j) de una instancia del patrón rectangular desde lo que guarda `suprimir`: un entero i (las
    recetas viejas: la copia i de la primera fila, (i, 0)) o un par [i, j]."""
    if isinstance(s, (tuple, list)):
        if len(s) != 2 or any(isinstance(x, bool) or int(x) != x for x in s):
            raise geo.ErrorGeometria("⚠ Copia a suprimir: entero i o par [i, j].")
        return int(s[0]), int(s[1])
    if isinstance(s, bool) or int(s) != s:
        raise geo.ErrorGeometria("⚠ Copia a suprimir: entero i o par [i, j].")
    return int(s), 0


def exigir_no_paralelas(dir1, dir2):
    """Falla si las direcciones 1 y 2 de un patrón rectangular son paralelas (las copias de la segunda caerían sobre
    las de la primera)."""
    if np.linalg.norm(np.cross(_unit(dir1, "dirección 1"), _unit(dir2, "dirección 2"))) < 1e-6:
        raise geo.ErrorGeometria("Direcciones 1 y 2 paralelas: cambiá la 2.")


def instancias_rectangulares(dir1, n1, d1, dir2=None, n2=1, d2=0.0, *, distribucion="extension",
                             simetrico1=False, simetrico2=False, suprimir=(), total=False):
    """Todas las instancias del patrón rectangular [SLD-REF-PATTERN] con su identificador estable: lista de
    ((i, j), gp_Trsf, suprimida) en orden i por dir1, j por dir2; (0, 0) es el original y nunca se suprime.
    i y j son los pasos desde el original (con simetría hay negativos: i = −1 es la copia del otro lado). "extension":
    d = largo total por dirección; "espaciado": d = paso. Cada dirección es simétrica o no por su cuenta:
    simétrica da 2n − 1 instancias (la misma cantidad hacia los dos lados). `total` (PAT-1, Fusion real): la cantidad
    simétrica es el total con el original, si es par la de más va al lado +, y en «extension» d se mide por lado (3 en
    100: −100, 0, +100). Con `dir2` vacía la segunda dirección no existe (j = 0). `suprimir`: enteros i (= (i, 0),
    recetas viejas) o pares [i, j]. Como máximo INSTANCIAS_MAXIMAS."""
    _exigir_instancias(_cantidad(n1, simetrico1, total) * (_cantidad(n2, simetrico2, total) if dir2 is not None else 1))
    u1 = _unit(dir1, "dirección 1")
    u2 = _unit(dir2, "dirección 2") if dir2 is not None else np.zeros(3)
    if dir2 is not None and int(n2) > 1:
        exigir_no_paralelas(u1, u2)
    for n, d, que in ((n1, d1, "1"), (n2, d2, "2")):
        if (que == "1" or dir2 is not None) and int(n) > 1 and abs(d) < 1e-9:
            raise geo.ErrorGeometria(f"⚠ Distancia {que}: no puede ser cero.")
    s1 = _paso(int(n1), d1, distribucion, total and simetrico1)
    s2 = _paso(int(n2), d2, distribucion, total and simetrico2) if dir2 is not None else 0.0
    fuera = {_id_rectangular(s) for s in suprimir} - {(0, 0)}
    de_mas = 1 if total else 0
    js = _indices(n2, simetrico2, de_mas) if dir2 is not None else [0]
    return [((i, j), _traslacion(i * s1 * u1 + j * s2 * u2), (i, j) in fuera)
            for i in _indices(n1, simetrico1, de_mas) for j in js]


def transformaciones_rectangulares(dir1, n1, d1, dir2=None, n2=1, d2=0.0, *, distribucion="extension",
                                   simetrico1=False, simetrico2=False, suprimir=(), total=False):
    """gp_Trsf del patrón rectangular sin las instancias suprimidas (ver `instancias_rectangulares`); la primera es
    la identidad (el original)."""
    return [t for _, t, sup in instancias_rectangulares(dir1, n1, d1, dir2, n2, d2, distribucion=distribucion,
                                                        simetrico1=simetrico1, simetrico2=simetrico2,
                                                        suprimir=suprimir, total=total) if not sup]


def paso_angular(n, angulo_total, distribucion="completa", simetrico=False):
    """Grados entre instancias consecutivas del patrón circular: lo usan el cálculo, la vista previa y el manipulador
    (así las tres posiciones coinciden). "completa" (y "extension", el nombre de las recetas viejas): las instancias
    reparten `angulo_total`; con una vuelta de 360° sin simetría la última no cae sobre el original (360 / n), si no
    la última queda justo en el ángulo (total / (n − 1)); "espaciado": `angulo_total` es el paso."""
    n = int(n)
    if distribucion in ("completa", "extension"):
        if abs(abs(angulo_total) - 360.0) < 1e-9 and not simetrico:
            return angulo_total / n
        return angulo_total / (n - 1) if n > 1 else 0.0
    if distribucion == "espaciado":
        return angulo_total
    raise geo.ErrorGeometria(f"Distribución desconocida: {distribucion}")


def instancias_circulares(punto, eje, n, *, angulo_total=360.0, distribucion="completa", simetrico=False, suprimir=(),
                          total=False):
    """Todas las instancias del patrón circular [SLD-REF-PATTERN] con su identificador: lista de (k, gp_Trsf,
    suprimida); k = 0 es el original (nunca se suprime) y, con simetría, hay k negativos (el otro lado). "completa":
    las instancias reparten `angulo_total` (con 360° la última no se superpone con el original); "espaciado":
    `angulo_total` es el ángulo entre instancias. Simétrico: n hacia cada lado del original (2n − 1 en total); con
    `total` (PAT-1, Fusion real), n es el total con el original y si es par la de más va al lado − (4 en 90°: −60,
    −30, 0, +30). Como máximo INSTANCIAS_MAXIMAS."""
    n = int(n)
    _exigir_instancias(_cantidad(n, simetrico, total))
    paso = paso_angular(n, angulo_total, distribucion, simetrico)
    if n > 1 and (abs(paso) < 1e-9 or (n - 1) * abs(paso) * (2 if simetrico and not total else 1) >= 360.0 - 1e-9):
        raise geo.ErrorGeometria("Ángulo: distinto de 0 y menor que 360°.")
    u = _unit(eje, "eje del patrón")
    fuera = {int(s) for s in suprimir} - {0}
    return [(k, _rotacion(punto, u, math.radians(k * paso)), k in fuera) for k in _indices(n, simetrico, -1 if total else 0)]


def transformaciones_circulares(punto, eje, n, *, angulo_total=360.0, distribucion="completa", simetrico=False,
                                suprimir=(), total=False):
    """gp_Trsf del patrón circular sin las instancias suprimidas (ver `instancias_circulares`); la primera es la
    identidad."""
    return [t for _, t, sup in instancias_circulares(punto, eje, n, angulo_total=angulo_total, distribucion=distribucion,
                                                     simetrico=simetrico, suprimir=suprimir, total=total) if not sup]


def _trsf_de_marcos(p0, f0, p1, f1):
    """gp_Trsf que lleva el marco ortonormal f0 (columnas) ubicado en p0 al marco f1 ubicado en p1."""
    m = f1 @ f0.T
    tr = np.asarray(p1, float) - m @ np.asarray(p0, float)
    t = gp_Trsf()
    t.SetValues(*(float(c) for fila in np.hstack([m, tr[:, None]]) for c in fila))
    return t


def recorrido_ruta(ruta, n, distancia, *, inicio=0.0, distribucion="extension"):
    """(largo, cerrada, s0, paso): el largo de la cadena de aristas `ruta`, si es cerrada, la longitud de arco donde
    está el original (la fracción `inicio` de 0 a 1, limitada a ese intervalo) y el avance con signo entre instancias
    consecutivas (mm). Es el recorrido real que usan el patrón, su vista previa y el manipulador. Una vuelta completa de
    una ruta cerrada (distancia = ± el largo, en "extension") reparte el largo entre n instancias: la última no cae
    encima del original."""
    w = _alambre(ruta)
    largo = _longitud(w)
    cerrada = _es_cerrado(w)
    paso = _paso(int(n), distancia, distribucion)
    if cerrada and distribucion == "extension" and int(n) > 1 and abs(abs(distancia) - largo) < 1e-6 * largo:
        paso = math.copysign(largo / int(n), distancia)      # vuelta completa, positiva o negativa
    return largo, cerrada, min(max(float(inicio), 0.0), 1.0) * largo, paso


def perfil_ruta(ruta, muestras=161):
    """(puntos (N, 3), longitudes de arco (N,), cerrada) de la cadena de aristas `ruta`, la misma que recorre el patrón
    sobre ruta: sirve para dibujar el recorrido y ubicar los manipuladores sobre él."""
    w = _alambre(ruta)
    largo = _longitud(w)
    s = np.linspace(0.0, largo, int(muestras))
    return np.array([np.asarray(_punto_en(w, x / largo)[0], float) for x in s]), s, _es_cerrado(w)


def exigir_cantidad_patron_ruta(cantidad):
    """Exige al menos dos instancias, incluido el original, del Patrón en trayectoria de Fusion."""
    if ((not isinstance(cantidad, int) and not math.isfinite(cantidad)) or cantidad < 2 or int(cantidad) != cantidad):
        raise geo.ErrorGeometria("Cantidad: entero de 2 o más.")


def instancias_en_ruta(ruta, n, distancia, *, orientacion="identica", inicio=0.0, distribucion="extension",
                       simetrico=False, suprimir=(), giro=0.0):
    """Todas las instancias del patrón sobre ruta [SLD-REF-PATTERN] con su estado: lista de (k, gp_Trsf o None, estado).
    k = 0 es el original (en la fracción `inicio` de 0 a 1 de la ruta); con simetría hay k negativos. Estado: "ok",
    "suprimida", "fuera" (en una ruta abierta la instancia caería pasado el extremo: no se crea ni se extrapola) o
    "repetida" (en una ruta cerrada caería sobre otra instancia: no se duplica). Las instancias avanzan `distancia` mm
    (largo total o paso, según `distribucion`). "identica" solo traslada, de modo que el cuerpo conserva su posición
    respecto del punto de la ruta donde está el original; "direccion_ruta" además gira cada instancia con la ruta
    (marco de rotación mínima). Como máximo INSTANCIAS_MAXIMAS.

    `giro` (grados, como el Twisted Path Array de FreeCAD Draft): además, cada instancia gira alrededor de la
    tangente de la ruta en su lugar, en forma progresiva: la instancia k gira giro · k / (n − 1), así la última
    gira el ángulo total y el original nada (con «simétrico», las de atrás giran al revés)."""
    exigir_cantidad_patron_ruta(n)
    if orientacion not in ("identica", "direccion_ruta"):
        raise geo.ErrorGeometria(f"Orientación desconocida: {orientacion}")
    giro = float(giro)
    if not math.isfinite(giro):
        raise geo.ErrorGeometria("⚠ Giro del patrón en ruta: ángulo finito.")
    _exigir_instancias(_cantidad(n, simetrico))
    if int(n) > 1 and abs(distancia) < 1e-9:
        raise geo.ErrorGeometria("⚠ Distancia 0 en ruta: las copias se pisan.")
    w = _alambre(ruta)
    largo, cerrada, s0, paso = recorrido_ruta(ruta, n, distancia, inicio=inicio, distribucion=distribucion)
    marcos = _marcos(w, 257)

    def marco(s):
        p, t = _punto_en(w, s / largo)
        r = marcos[int(round(s / largo * (len(marcos) - 1)))][2]
        r = _unit(r - t * float(r @ t))
        return p, np.column_stack([t, r, np.cross(t, r)])

    p0, f0 = marco(s0)
    fuera = {int(s) for s in suprimir} - {0}
    salida = []
    celdas = max(int(round(largo / (1e-6 * largo))), 1)          # la ruta cerrada en celdas de 1e-6 de su largo
    celda = lambda x: int(round(x / largo * celdas)) % celdas   # noqa: E731
    ocupadas = {celda(s0)}
    for k in _indices(n, simetrico):
        s = s0 + k * paso
        if cerrada:
            s %= largo
            c = celda(s)
            if k != 0 and any((c + d) % celdas in ocupadas for d in (-1, 0, 1)):     # misma celda o vecina: es la misma
                salida.append((k, None, "repetida"))
                continue
            ocupadas.add(c)
        elif s < -1e-9 or s > largo + 1e-9:
            salida.append((k, None, "fuera"))
            continue
        p1, f1 = marco(min(max(s, 0.0), largo))
        t = _traslacion(p1 - p0) if orientacion == "identica" else _trsf_de_marcos(p0, f0, p1, f1)
        angulo = giro * k / (int(n) - 1) if int(n) > 1 else 0.0
        if abs(angulo) > 1e-12:
            r = gp_Trsf()
            r.SetRotation(gp_Ax1(_pnt(p1), _gdir(f1[:, 0])), math.radians(angulo))
            t = r.Multiplied(t)             # primero lleva la copia a su lugar y después la gira sobre la tangente
        salida.append((k, t, "suprimida" if k in fuera else "ok"))
    return salida


def transformaciones_en_ruta(ruta, n, distancia, *, orientacion="identica", inicio=0.0, distribucion="extension",
                             simetrico=False, suprimir=(), giro=0.0):
    """gp_Trsf del patrón sobre ruta sin las instancias suprimidas, fuera de una ruta abierta o repetidas (ver
    `instancias_en_ruta`); la primera es la identidad."""
    return [t for _, t, estado in instancias_en_ruta(ruta, n, distancia, orientacion=orientacion, inicio=inicio,
                                                     distribucion=distribucion, simetrico=simetrico,
                                                     suprimir=suprimir, giro=giro) if estado == "ok"]


def instancias_en_puntos(puntos, referencia=(0.0, 0.0, 0.0), *, suprimir=()):
    """Todas las instancias del patrón en puntos con su identificador: lista de (k, gp_Trsf o None, estado). k = 0 es el
    original y k = 1, 2… el primer punto, el segundo…: cada copia lleva `referencia` a su punto (la traslación es
    exactamente punto − referencia). Estado: "ok", "suprimida" o "repetida" (un punto igual a la referencia o a otro
    ya usado no repite la copia). Como máximo INSTANCIAS_MAXIMAS."""
    ref = np.asarray(referencia, float).reshape(-1)
    pts = [np.asarray(p, float).reshape(-1) for p in puntos]
    if ref.size != 3 or not np.all(np.isfinite(ref)):
        raise geo.ErrorGeometria("⚠ Referencia del patrón: 3 números finitos.")
    if any(p.size != 3 or not np.all(np.isfinite(p)) for p in pts):
        raise geo.ErrorGeometria("⚠ Cada punto del patrón: 3 números finitos.")
    if not pts:
        raise geo.ErrorGeometria("⚠ El patrón en puntos necesita un punto.")
    _exigir_instancias(len(pts) + 1)
    fuera = {int(i) for i in suprimir} - {0}
    usados = [ref]
    salida = [(0, _identidad(), "ok")]
    for k, p in enumerate(pts, start=1):
        if any(np.linalg.norm(p - q) < 1e-6 for q in usados):
            salida.append((k, None, "repetida"))
            continue
        usados.append(p)
        salida.append((k, _traslacion(p - ref), "suprimida" if k in fuera else "ok"))
    return salida


def transformaciones_en_puntos(puntos, referencia=(0.0, 0.0, 0.0), *, suprimir=()):
    """gp_Trsf del patrón en puntos sin las copias suprimidas ni repetidas (ver `instancias_en_puntos`); la primera es
    la identidad (el original)."""
    return [t for _, t, estado in instancias_en_puntos(puntos, referencia, suprimir=suprimir) if estado == "ok"]


def transformacion_simetria(plano):
    """gp_Trsf de la simetría (Mirror) respecto de un geo.Plano."""
    t = gp_Trsf()
    t.SetMirror(gp_Ax2(_pnt(plano.origen), _gdir(plano.normal)))
    return t


def transformacion_escala(factor):
    """gp_Trsf del cambio de escala uniforme (Scaled de FreeCAD) respecto del origen de coordenadas."""
    t = gp_Trsf()
    t.SetScale(gp_Pnt(0.0, 0.0, 0.0), float(factor))
    return t


def _clave_trsf(t):
    """Huella de una gp_Trsf (matriz 3×4 redondeada a 1e-6): dos instancias con la misma huella son la misma."""
    return tuple(round(t.Value(i, j), 6) + 0.0 for i in (1, 2, 3) for j in (1, 2, 3, 4))


def componer_transformaciones(listas):
    """Multitransformación (PartDesign › MultiTransform de FreeCAD): compone listas de gp_Trsf en orden; cada
    lista se aplica a TODAS las instancias que dejaron las anteriores (patrón 3 + simetría = 6 instancias). Cada
    lista empieza por la identidad (el original). Devuelve la lista compuesta, con la identidad primero y sin
    repetir instancias iguales. Como máximo INSTANCIAS_MAXIMAS (se controla antes de componer)."""
    listas = [list(lista) for lista in listas]
    if not listas:
        raise geo.ErrorGeometria("⚠ Multitransformación sin transformaciones.")
    total = 1
    for lista in listas:
        if not lista:
            raise geo.ErrorGeometria("⚠ Una transformación no dejó instancias.")
        total *= len(lista)
    _exigir_instancias(total)
    salida = [_identidad()]
    for lista in listas:
        nuevas = {}
        for t in lista:
            for previa in salida:
                c = _componer(t, previa)     # primero las transformaciones anteriores, después esta
                nuevas.setdefault(_clave_trsf(c), c)
        salida = list(nuevas.values())
    identidad = _identidad()
    return [identidad] + [t for t in salida if _clave_trsf(t) != _clave_trsf(identidad)]


def aplicar(forma, trsf):
    """Aplica una gp_Trsf (o una matriz 4x4) a una forma y devuelve la copia transformada."""
    if not isinstance(trsf, gp_Trsf):
        m = np.asarray(trsf, float)
        trsf = gp_Trsf()
        trsf.SetValues(*(float(c) for fila in m[:3, :4] for c in fila))
    return _tipado(BRepBuilderAPI_Transform(forma, trsf, True).Shape())


def instanciar(forma, trsf):
    """Copia LIGERA de una forma (instancia: PL8, F17 y RH17): la MISMA geometría con otra ubicación (`TopLoc_Location`),
    sin duplicarla. Solo para movimientos rígidos; una simetría o un cambio de escala no se pueden ubicar así y salen
    como copia de verdad (`aplicar`). Acepta una gp_Trsf o una matriz 4x4."""
    if not isinstance(trsf, gp_Trsf):
        m = np.asarray(trsf, float)
        trsf = gp_Trsf()
        trsf.SetValues(*(float(c) for fila in m[:3, :4] for c in fila))
    if trsf.IsNegative() or abs(trsf.ScaleFactor() - 1.0) > 1e-9:
        return aplicar(forma, trsf)
    return _tipado(forma.Moved(TopLoc_Location(trsf)))


def a_matriz(trsf):
    """gp_Trsf → matriz 4x4 de numpy (para guardar el patrón en el documento)."""
    m = np.eye(4)
    for i in range(3):
        for j in range(4):
            m[i, j] = trsf.Value(i + 1, j + 1)
    return m


def simetria(forma, plano):
    """Simetría (Mirror) de Fusion [SLD-REF-MIRROR-DIALOG]: copia reflejada respecto de un geo.Plano."""
    return aplicar(forma, transformacion_simetria(plano))


_registrar_tema(globals())
