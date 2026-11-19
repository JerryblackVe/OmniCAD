"""Boceto 2D: entidades."""
import math
import copy


TIPOS_RESTRICCION = {
    "coincidente": "Coincidente", "horizontal": "Horizontal", "vertical": "Vertical",
    "paralela": "Paralela", "perpendicular": "Perpendicular", "igual": "Igual",
    "tangente": "Tangente", "concentrica": "Concéntrica", "punto_medio": "Punto medio", "fijo": "Fijo",
    "colineal": "Colineal", "simetrica": "Simetría", "curvatura": "Curvatura", "poligono": "Polígono regular",
    "desfase": "Desfase", "patron": "Patrón",
}
# Restricciones que se pueden cambiar una por otra sobre las mismas entidades (paralela → perpendicular, horizontal →
# vertical…). Las demás (fijo, simetría, curvatura, polígono…) piden otras entidades o tienen datos propios.
CAMBIABLES = ("horizontal", "vertical", "coincidente", "paralela", "perpendicular", "igual", "tangente", "concentrica",
              "punto_medio", "colineal")
# Qué tipo de entidad va primero al guardar la restricción, elija el usuario en el orden que elija.
ORDEN_RESTRICCION = {"coincidente": "punto", "punto_medio": "punto", "tangente": "linea"}
TIPOS_COTA = {
    "distancia": "Distancia", "distancia_h": "Distancia horizontal", "distancia_v": "Distancia vertical",
    "radio": "Radio", "diametro": "Diámetro", "angulo": "Ángulo", "desfase": "Desfase",
}
COTAS_POSITIVAS = ("distancia", "distancia_h", "distancia_v", "radio", "diametro", "desfase")   # todas menos el ángulo
# mm (1 km): tope de una cota de largo. Más allá el núcleo ya no calcula bien (un barrido por una ruta de 1 km da el
# volumen exacto; por una de 10 km falla); nucleo/perfiles.py busca regiones cerradas en ±MEDIDA_MAXIMA
MEDIDA_MAXIMA = 1e6
MEDIDA_MINIMA = 1e-6      # mm (1 nm): por debajo el solver ya no distingue una medida de cero
# Cada copia de un patrón queda atada al original y el solver resuelve todo junto: medido, 200 círculos copiados (200
# puntos) tardan 3,6 s y 99 rectángulos (396 puntos) 7,5 s, y eso se repite en cada edición del boceto.
MAX_COPIAS_PATRON = 1000     # BOC-61: las copias no son incógnitas del solver; 1000 resuelven en ~15 ms
MAX_PUNTOS_PATRON = 10000    # copias × puntos de la selección
MAX_CARACTERES_TEXTO = 1000      # crear los perfiles de las letras cuesta ~10 ms por letra: 100.000 colgaban la ventana
ALTURA_MAXIMA_TEXTO = 10_000.0   # mm (10 m)
LARGO_EJE_VACIO = 100.0          # mm a cada lado de un eje o traza proyectados cuando no hay boceto ni modelo alrededor
MITAD_EJE_MINIMA = 10.0          # mm: un eje proyectado nunca queda más corto que ±10 mm
CIRCULARES = ("circulo", "arco")
ELIPTICAS = ("elipse", "arco_elipse")
LIBRES = ("spline", "conica")
GEOMETRICAS = ("linea",) + CIRCULARES + ELIPTICAS + LIBRES      # todo menos el texto
CON_CENTRO = CIRCULARES + ELIPTICAS
_DOS_PI = 2 * math.pi


def signos_cuadrante(cuadrante):
    """(s1, s2): signos de las direcciones de las dos líneas de una cota de ángulo según su cuadrante (BOC-25).
    Sin cuadrante (None) mide entre las dos direcciones tal como se dibujaron, como antes."""
    q = cuadrante or 0
    return (-1.0 if q in (1, 2) else 1.0), (-1.0 if q in (2, 3) else 1.0)


def _validar_cuadrante(tipo, cuadrante):
    if tipo != "angulo":
        raise ErrorBoceto("El cuadrante solo vale en una cota de ángulo.")
    if isinstance(cuadrante, bool) or cuadrante not in (0, 1, 2, 3):
        raise ErrorBoceto(f"Cuadrante inválido: {cuadrante!r} (0, 1, 2 o 3).")


class ErrorBoceto(ValueError):
    pass


def validar_valor_cota(tipo, valor):
    """Como Fusion, una cota de largo, radio o diámetro tiene que ser mayor que cero (el solver toma el valor absoluto
    del radio: −5 quedaba guardado y dibujaba 5) y de hasta MEDIDA_MAXIMA (1 km; frena valores absurdos como un radio
    de 1e9 o infinito). La de desfase admite negativo: la copia pasa al otro lado. Una cota de ángulo debe estar
    estrictamente entre 0 y 180 grados (entre rectas no paralelas, como Sketch Dimension de Fusion)."""
    if tipo == "angulo" and not 0 < valor < 180:          # también NaN e infinito
        raise ErrorBoceto(f"Cota de ángulo: entre 0 y 180 (vale {valor:g}).")
    if tipo not in COTAS_POSITIVAS:
        return
    nombre = TIPOS_COTA[tipo].lower()
    if tipo == "desfase":
        valor = abs(valor)
    if not valor > 0:                                   # también NaN
        raise ErrorBoceto(f"Cota de {nombre}: mayor que 0 (vale {valor:g}).")
    if not valor <= MEDIDA_MAXIMA:                      # también infinito
        miles = f"{MEDIDA_MAXIMA:,.0f}".replace(",", ".")
        raise ErrorBoceto(f"Cota de {nombre}: máximo {miles} mm.")


def _exigir_radio_positivo(radio, achica, que):
    """Desfase hacia adentro: `achica` mm sobre `que` (de `radio` mm); si deja el radio en cero o negativo, dice cuál."""
    if achica < radio - MEDIDA_MINIMA:
        return
    if achica <= radio + MEDIDA_MINIMA:
        raise ErrorBoceto(f"Desfase {achica:g} mm: el radio queda en cero.")
    raise ErrorBoceto(f"Desfase {achica:g} mm: el radio queda negativo.")


def expresion_sin_signo(expresion, valor, evaluar):
    """Texto de una distancia con signo sin el signo, para la cota: «-4 mm» → «4 mm» si lo que sigue vale lo mismo
    en positivo; si no (p. ej. «-a+b»), «-(…)». `evaluar` pasa un texto a número."""
    if valor >= 0:
        return expresion
    resto = expresion.lstrip()[1:].strip() if expresion.lstrip().startswith("-") else None
    try:
        simple = resto is not None and abs(evaluar(resto) - abs(valor)) < 1e-9
    except (ValueError, ZeroDivisionError):     # lo que sigue al «-» no se evalúa solo: se deja entre paréntesis
        simple = False
    return resto if simple else f"-({expresion})"


def validar_texto_boceto(texto=None, altura=None):
    """Tope del largo y de la altura de un texto de boceto (los que se pasan; None = no se mira)."""
    if texto is not None:
        if not str(texto).strip():
            raise ErrorBoceto("El texto está vacío.")
        if len(str(texto)) > MAX_CARACTERES_TEXTO:
            raise ErrorBoceto(f"El texto tiene {len(str(texto)):,} caracteres y el máximo es {MAX_CARACTERES_TEXTO:,}: "
                              "cada letra se vuelve un perfil y más de eso congela la ventana.".replace(",", "."))
    if altura is not None:
        if not 0 < altura < math.inf:                   # también NaN
            raise ErrorBoceto("La altura del texto debe ser positiva.")
        if altura > ALTURA_MAXIMA_TEXTO:
            raise ErrorBoceto(f"La altura del texto no puede pasar de {ALTURA_MAXIMA_TEXTO:,.0f} mm (vale "
                              f"{altura:g}).".replace(",", "."))


# ---------------------------------------------------------------- entidades
class Punto:
    tipo = "punto"

    def __init__(self, id, x, y, proyectado=False):
        self.id, self.x, self.y, self.proyectado = id, float(x), float(y), bool(proyectado)

    def a_dict(self):
        d = {"id": self.id, "x": self.x, "y": self.y}
        if self.proyectado:
            d["proyectado"] = True
        return d


class _Curva:
    """Base de las curvas: estilo (normal / construcción / eje) y si viene de una proyección."""
    tipo = ""
    PUNTOS = ()          # atributos que son ids de puntos del boceto
    DATOS = ()           # otros atributos que se guardan

    def _estilo(self, construccion, eje, proyectada):
        self.construccion, self.eje, self.proyectada = bool(construccion), bool(eje), bool(proyectada)

    def puntos(self):
        return [getattr(self, a) for a in self.PUNTOS]

    def extremos(self):
        """(inicio, fin) de las curvas abiertas; None en las cerradas."""
        return None

    def a_dict(self):
        d = {"tipo": self.tipo, "id": self.id}
        for a in self.PUNTOS + self.DATOS:
            v = getattr(self, a)
            d[a] = list(v) if isinstance(v, (list, tuple)) else v
        d["construccion"] = self.construccion
        if self.eje:
            d["eje"] = True
        if self.proyectada:
            d["proyectada"] = True
        return d

    def remapear(self, mapa, nuevo_id=None):
        """Copia con los ids de puntos cambiados según `mapa` (para copiar, simetría y patrones)."""
        c = copy.deepcopy(self)
        c.id = self.id if nuevo_id is None else nuevo_id
        for a in self.PUNTOS:
            setattr(c, a, mapa.get(getattr(self, a), getattr(self, a)))
        return c


class Linea(_Curva):
    tipo, PUNTOS = "linea", ("p1", "p2")

    def __init__(self, id, p1, p2, construccion=False, eje=False, proyectada=False):
        self.id, self.p1, self.p2 = id, p1, p2
        self._estilo(construccion, eje, proyectada)

    def extremos(self):
        return self.p1, self.p2


class Circulo(_Curva):
    tipo, PUNTOS, DATOS = "circulo", ("centro",), ("radio",)

    def __init__(self, id, centro, radio, construccion=False, eje=False, proyectada=False):
        self.id, self.centro, self.radio = id, centro, float(radio)
        self._estilo(construccion, eje, proyectada)


class Arco(_Curva):
    """Arco antihorario de `inicio` a `fin` alrededor de `centro` (radio = |inicio - centro|)."""
    tipo, PUNTOS = "arco", ("centro", "inicio", "fin")

    def __init__(self, id, centro, inicio, fin, construccion=False, eje=False, proyectada=False):
        self.id, self.centro, self.inicio, self.fin = id, centro, inicio, fin
        self._estilo(construccion, eje, proyectada)

    def extremos(self):
        return self.inicio, self.fin


class Elipse(_Curva):
    """Elipse de Fusion: centro, extremo del eje mayor (`mayor`, define a y el giro) y radio menor b."""
    tipo, PUNTOS, DATOS = "elipse", ("centro", "mayor"), ("radio_menor",)

    def __init__(self, id, centro, mayor, radio_menor, construccion=False, eje=False, proyectada=False):
        self.id, self.centro, self.mayor, self.radio_menor = id, centro, mayor, float(radio_menor)
        self._estilo(construccion, eje, proyectada)


class ArcoElipse(_Curva):
    """Arco de elipse antihorario de `inicio` a `fin` (sale de recortar o partir una elipse)."""
    tipo, PUNTOS, DATOS = "arco_elipse", ("centro", "mayor", "inicio", "fin"), ("radio_menor",)

    def __init__(self, id, centro, mayor, radio_menor, inicio, fin, construccion=False, eje=False,
                 proyectada=False):
        self.id, self.centro, self.mayor, self.radio_menor = id, centro, mayor, float(radio_menor)
        self.inicio, self.fin = inicio, fin
        self._estilo(construccion, eje, proyectada)

    def extremos(self):
        return self.inicio, self.fin


class Spline(_Curva):
    """Spline de Fusion. modo "ajuste": la curva PASA por sus puntos (Fit Point Spline); modo
    "control": los puntos son los polos (Control Point Spline, grado 3 o 5; con `pesos` y `nudos`
    explícitos cuando sale de recortar, proyectar o desglosar texto).

    `manijas` (solo la de ajuste abierta): [[punto de ajuste, punta, curvatura o None]]. La manija de tangente de
    Fusion es una línea de construcción del punto de ajuste a la `punta`: su dirección es la tangente de la curva
    ahí y su largo, la fuerza (largo = |C'| / tramos deja la tangente natural). `curvatura` (1/mm, con
    signo: + gira a la izquierda) es la manija de curvatura. La punta es un punto del boceto: se acota y la mueve
    el solver."""
    tipo, DATOS = "spline", ("modo", "grado", "cerrada", "pesos", "nudos", "manijas")

    def __init__(self, id, puntos, modo="ajuste", grado=3, cerrada=False, pesos=None, nudos=None,
                 construccion=False, eje=False, proyectada=False, manijas=None):
        self.id, self.pts, self.modo, self.grado = id, list(puntos), modo, int(grado)
        self.cerrada = bool(cerrada)
        self.pesos = None if pesos is None else [float(w) for w in pesos]
        self.nudos = None if nudos is None else [float(k) for k in nudos]
        self.manijas = [[int(a), int(b), None if k is None else float(k)] for a, b, k in (manijas or [])]
        self._estilo(construccion, eje, proyectada)

    def puntos(self):
        return list(self.pts) + [m[1] for m in self.manijas]

    def extremos(self):
        return None if self.cerrada else (self.pts[0], self.pts[-1])

    def a_dict(self):
        d = super().a_dict()
        d["puntos"] = list(self.pts)
        if not self.manijas:
            del d["manijas"]
        return d

    def remapear(self, mapa, nuevo_id=None):
        c = super().remapear(mapa, nuevo_id)
        c.pts = [mapa.get(p, p) for p in self.pts]
        c.manijas = [[mapa.get(a, a), mapa.get(b, b), k] for a, b, k in self.manijas]
        return c


class Conica(_Curva):
    """Curva cónica de Fusion: extremos, vértice (cruce de las tangentes) y Rho (0 < rho < 1;
    0.5 = parábola, menor = elipse, mayor = hipérbola)."""
    tipo, PUNTOS, DATOS = "conica", ("inicio", "vertice", "fin"), ("rho",)

    def __init__(self, id, inicio, vertice, fin, rho=0.5, construccion=False, eje=False, proyectada=False):
        self.id, self.inicio, self.vertice, self.fin, self.rho = id, inicio, vertice, fin, float(rho)
        self._estilo(construccion, eje, proyectada)

    def extremos(self):
        return self.inicio, self.fin


class Texto(_Curva):
    """Texto de boceto: `punto` es la esquina inferior izquierda de la línea base; el ángulo, en grados.
    Sus contornos forman perfiles (se pueden extruir), como en Fusion.

    Además de fuente, altura, negrita y cursiva: `espaciado` (mm entre letras; la pantalla lo muestra en %, ver
    `fuentes.espaciado_cien`), `interlineado` (factor),
    `alineacion` ("izq", "centro", "der" dentro de la caja), `ancla_v` ("base", "arriba", "medio", "abajo":
    qué parte del bloque cae sobre `punto`), `ancho_caja` (mm; 0 = sin caja, >0 parte las líneas) y
    `voltear_h` / `voltear_v` (espejo dentro del bloque).

    Como el panel «Carácter» de los editores de diseño: `kerning` (False ignora los pares de la fuente),
    `inclinacion` (grados de sesgo), `escala_h` / `escala_v` (% del ancho y del alto de las letras),
    `desfase_base` (mm que sube el texto), `capitalizacion` ("ninguno", "mayusculas", "minusculas", "titulo",
    "versalitas"), `subrayado` y `tachado` ("ninguno", "simple", "doble"; barras que también forman perfiles),
    `grosor_decoracion` (mm; 0 = el de la fuente) y `sin_division` (True: `ancho_caja` no parte las líneas).

    Texto en curva (Fusion: texto en trayectoria): `camino` es el id de una curva del mismo boceto; entonces
    `punto` y `angulo` no se usan y las letras siguen la curva. `camino_lado` ("izq" / "der": de qué lado del
    sentido de la curva van las letras), `camino_pos` (fracción 0-1 del largo donde cae el ancla, según
    `alineacion`), `camino_desfase` (mm entre la curva y la línea base), `camino_ajustar` (repartir en todo el largo)
    y `camino_colocacion` ("arriba": la línea base apoya en la curva; "abajo": las letras cuelgan de ella con la misma
    lectura, la Placement de Fusion). Si la curva se borra, el texto vuelve a ser recto. En curva no se dibujan subrayado ni tachado.
    `camino_alineado`: los textos nuevos sin posición manual se alinean al inicio, centro o fin del camino; en ellos
    `camino_pos` es el desplazamiento por arrastre (0.5 = sin mover). Sin la marca, una receta anterior conserva su ancla.

    Marco (Fusion: el rectángulo del texto, que se acota y restringe): `marco` = [esquina derecha, esquina de
    arriba], ids de puntos; con `punto` (esquina de abajo a la izquierda) definen el giro, el ancho de la caja y el
    alto donde se ubica el texto según `ancla_v`. `altura_expr`: la altura como expresión con parámetros (Fusion
    crea el parámetro «Text height»); el paso del boceto la evalúa y la deja en `altura`. `parametro_texto`
    liga el contenido al parámetro automático «Text»; sin él se conserva el texto de las recetas anteriores.
    `parametro_altura`: el parámetro automático «Text height» (lo escrito en `altura_expr` pasa a él al guardar).

    `altura_a`: True si `altura` es el alto de la «A» de la fuente, como en Fusion (los textos nuevos). Sin la marca, una
    receta anterior: `altura` es el tamaño de la fuente y el texto se sigue viendo igual (B-152)."""
    tipo, PUNTOS = "texto", ("punto",)
    DATOS = ("texto", "fuente", "altura", "angulo", "negrita", "cursiva", "espaciado", "interlineado", "alineacion",
             "ancla_v", "ancho_caja", "voltear_h", "voltear_v", "camino", "camino_lado", "camino_pos",
             "camino_desfase", "camino_ajustar", "kerning", "inclinacion", "escala_h", "escala_v", "desfase_base",
             "capitalizacion", "subrayado", "tachado", "grosor_decoracion", "sin_division", "ajustes_kerning",
             "marco", "altura_expr", "parametro_texto", "camino_colocacion", "parametro_altura", "altura_a", "camino_alineado")
    _PREDETERMINADOS = {"espaciado": 0.0, "interlineado": 1.0, "alineacion": "izq", "ancla_v": "base",
                        "ancho_caja": 0.0, "voltear_h": False, "voltear_v": False, "camino": None,
                        "camino_lado": "izq", "camino_pos": 0.5, "camino_desfase": 0.0, "camino_ajustar": False,
                        "kerning": True, "inclinacion": 0.0, "escala_h": 100.0, "escala_v": 100.0,
                        "desfase_base": 0.0, "capitalizacion": "ninguno", "subrayado": "ninguno",
                        "tachado": "ninguno", "grosor_decoracion": 0.0, "sin_division": False,
                        "ajustes_kerning": [], "marco": None, "altura_expr": None, "parametro_texto": None,
                        "camino_colocacion": "arriba", "parametro_altura": None, "altura_a": False, "camino_alineado": False}
    # opciones del panel «Carácter» que se guardan tal cual (el tipo de cada una, para convertir lo que llega)
    TIPOGRAFIA = {"kerning": bool, "inclinacion": float, "escala_h": float, "escala_v": float, "desfase_base": float,
                  "capitalizacion": str, "subrayado": str, "tachado": str, "grosor_decoracion": float,
                  "sin_division": bool,
                  "ajustes_kerning": lambda v: [[int(i), float(x)] for i, x in v]}

    def __init__(self, id, punto, texto, fuente="Arial", altura=5.0, angulo=0.0, negrita=False, cursiva=False,
                 construccion=False, eje=False, proyectada=False, espaciado=0.0, interlineado=1.0,
                 alineacion="izq", ancla_v="base", ancho_caja=0.0, voltear_h=False, voltear_v=False, camino=None,
                 camino_lado="izq", camino_pos=0.5, camino_desfase=0.0, camino_ajustar=False, kerning=True,
                 inclinacion=0.0, escala_h=100.0, escala_v=100.0, desfase_base=0.0, capitalizacion="ninguno",
                 subrayado="ninguno", tachado="ninguno", grosor_decoracion=0.0, sin_division=False,
                 ajustes_kerning=None, marco=None, altura_expr=None, parametro_texto=None,
                 camino_colocacion="arriba", parametro_altura=None, altura_a=False, camino_alineado=False):
        self.id, self.punto, self.texto, self.fuente = id, punto, str(texto), str(fuente)
        self.altura, self.angulo = float(altura), float(angulo)
        self.negrita, self.cursiva = bool(negrita), bool(cursiva)
        self.espaciado, self.interlineado = float(espaciado), float(interlineado)
        self.alineacion, self.ancla_v, self.ancho_caja = str(alineacion), str(ancla_v), float(ancho_caja)
        self.voltear_h, self.voltear_v = bool(voltear_h), bool(voltear_v)
        self.camino = None if camino is None else int(camino)
        self.camino_lado, self.camino_pos = str(camino_lado), float(camino_pos)
        self.camino_desfase, self.camino_ajustar = float(camino_desfase), bool(camino_ajustar)
        self.kerning, self.inclinacion = bool(kerning), float(inclinacion)
        self.escala_h, self.escala_v, self.desfase_base = float(escala_h), float(escala_v), float(desfase_base)
        self.capitalizacion, self.subrayado, self.tachado = str(capitalizacion), str(subrayado), str(tachado)
        self.grosor_decoracion, self.sin_division = float(grosor_decoracion), bool(sin_division)
        self.ajustes_kerning = [[int(i), float(x)] for i, x in (ajustes_kerning or [])]
        self.marco = None if marco is None else [int(p) for p in marco]
        self.altura_expr = None if altura_expr is None else str(altura_expr)
        self.parametro_texto = None if parametro_texto is None else str(parametro_texto)
        self.camino_colocacion = str(camino_colocacion)
        self.parametro_altura = None if parametro_altura is None else str(parametro_altura)
        self.altura_a = bool(altura_a)
        self.camino_alineado = bool(camino_alineado)
        self._estilo(construccion, eje, proyectada)

    def puntos(self):
        return [self.punto] + (self.marco or [])

    def remapear(self, mapa, nuevo_id=None):
        c = super().remapear(mapa, nuevo_id)
        if nuevo_id is not None:                 # la copia conserva su altura, sin seguir al parámetro del original
            c.parametro_altura = c.altura_expr = None
        if self.marco:
            c.marco = [mapa.get(p, p) for p in self.marco]
        return c

    def a_dict(self):
        """Como las demás curvas, pero sin las opciones que tienen su valor por defecto (los archivos viejos
        y los nuevos sin opciones quedan iguales)."""
        d = super().a_dict()
        for k, v in self._PREDETERMINADOS.items():
            if d.get(k) == v:
                del d[k]
        return d

    def tamano_fuente(self):
        """Tamaño de fuente (mm) con el que se dibuja: ver `altura_a`."""
        if not self.altura_a:
            return self.altura
        from ..nucleo import fuentes
        return fuentes.tamano_fuente(self.fuente, self.altura, self.negrita, self.cursiva)

    def opciones_contorno(self):
        """Opciones de `fuentes.contornos_texto` en el orden en que se guardan en el caché."""
        return (self.espaciado, self.interlineado, self.alineacion, self.ancla_v, self.ancho_caja,
                self.voltear_h, self.voltear_v) + self.opciones_tipografia()

    def opciones_tipografia(self):
        """Las del panel «Carácter» (kerning, inclinación, escalas, desfase de base, capitalización, subrayado,
        tachado, grosor y sin división), en el orden de `_contornos_texto`."""
        return (self.kerning, self.inclinacion, self.escala_h, self.escala_v, self.desfase_base,
                self.capitalizacion, self.subrayado, self.tachado, self.grosor_decoracion, self.sin_division,
                tuple((i, x) for i, x in self.ajustes_kerning))


class Restriccion:
    def __init__(self, id, tipo, entidades, datos=None):
        if tipo not in TIPOS_RESTRICCION:
            raise ErrorBoceto(f"Restricción desconocida: {tipo}")
        self.id, self.tipo, self.entidades, self.datos = id, tipo, list(entidades), dict(datos or {})

    def a_dict(self):
        return {"id": self.id, "tipo": self.tipo, "entidades": self.entidades, "datos": self.datos}


class Cota:
    def __init__(self, id, tipo, entidades, expresion, datos=None, nombre="", referencia=False):
        if tipo not in TIPOS_COTA:
            raise ErrorBoceto(f"Cota desconocida: {tipo}")
        self.id, self.tipo, self.entidades, self.expresion = id, tipo, list(entidades), str(expresion)
        self.datos = dict(datos or {})
        self.nombre = nombre
        self.referencia = referencia

    def a_dict(self):
        return {"id": self.id, "tipo": self.tipo, "entidades": self.entidades,
                "expresion": self.expresion, "datos": dict(self.datos),
                **({"nombre": self.nombre} if self.nombre else {}),
                **({"referencia": True} if self.referencia else {})}


_CURVAS = {k.tipo: k for k in (Linea, Circulo, Arco, Elipse, ArcoElipse, Spline, Conica, Texto)}
_CON_RADIO = (Circulo, Elipse, ArcoElipse)      # llevan un radio (o radio menor) como incógnita propia


_ORIENTADAS = ("horizontal", "vertical")
_COTAS_ORIENTADAS = ("distancia_h", "distancia_v")


def _cambia_orientacion(angulo):
    """True si un giro de `angulo` grados deja de respetar horizontales y verticales (no es múltiplo de 180°)."""
    resto = float(angulo) % 180.0
    return min(resto, 180.0 - resto) > 1e-9


# ---------------------------------------------------------------- utilidades geométricas 2D
def _numero(v):
    return f"{v:.6f}".rstrip("0").rstrip(".")


def _es_numero(texto):
    try:
        float(texto)
        return True
    except ValueError:
        return False


def _antihorario_por(a, medio, b, centro):
    """True si el arco antihorario de a a b (alrededor de centro) pasa por `medio`."""
    a0 = math.atan2(a[1] - centro[1], a[0] - centro[0])
    am = math.atan2(medio[1] - centro[1], medio[0] - centro[0])
    a1 = math.atan2(b[1] - centro[1], b[0] - centro[0])
    return (am - a0) % _DOS_PI <= (a1 - a0) % _DOS_PI


def circunferencia_3_puntos(a, b, c):
    (ax, ay), (bx, by), (cx, cy) = a, b, c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    return ux, uy, math.hypot(ax - ux, ay - uy)


def aviso_tangencias_fuera(pares=()):
    """Texto del aviso de `tangencias_fuera_del_arco` (en 2D y en 3D). `pares`, los [[a, b]] de ids para un agente; en la
    ventana no van: la persona ve la curva, no su número."""
    if not pares:
        return "Toca fuera del arco dibujado: alargalo."        # ≤45 (regla 14); el detalle va en el «?» de Tangente
    quien = "Tangente entre " + ", ".join(f"{a} y {b}" for a, b in pares)
    return (f"{quien}: el contacto cae fuera del tramo dibujado del arco (vale para su círculo entero). "
            "Mové la línea o alargá el arco para que se toquen.")


def distancia_con_circulo(tipos, entidades, modo, P, C, R, L, anidados=None):
    """Distancia CON signo de una cota de distancia con un círculo o arco (BOC-3; la medida es su valor absoluto).
    `P(pid)`, `C(cid)` (centro), `R(cid)` y `L(lid)` (extremos) dan la geometría: la usan el boceto y el solver.
    modo "centro": hasta el centro; "tangente": hasta el borde más cercano (entre círculos, de borde a borde;
    `anidados` congela si uno está adentro del otro, None = según la geometría)."""
    if tipos[0] not in CIRCULARES:
        tipos, entidades = tipos[::-1], entidades[::-1]
    c, o = entidades
    if tipos[1] == "punto":
        d = math.dist(P(o), C(c))
        return d if modo == "centro" else d - R(c)
    if tipos[1] == "linea":
        d = distancia_punto_recta(C(c), *L(o))
        return d if modo == "centro" else abs(d) - R(c)
    d = math.dist(C(c), C(o))
    if modo == "centro":
        return d
    r1, r2 = R(c), R(o)
    if anidados is None:
        anidados = d < abs(r1 - r2)
    return abs(r1 - r2) - d if anidados else d - r1 - r2


def _invertir_curvatura(spline):
    """Al reflejar una spline de ajuste, la curvatura (con signo) de sus manijas cambia de signo."""
    spline.manijas = [[a, b, None if k is None else -k] for a, b, k in spline.manijas]


def distancia_punto_recta(p, a, b):
    """Distancia CON signo de p a la recta a→b (positiva a la izquierda)."""
    (px, py), (ax, ay), (bx, by) = p, a, b
    n = math.hypot(bx - ax, by - ay)
    if n < 1e-12:
        return math.hypot(px - ax, py - ay)
    return ((bx - ax) * (py - ay) - (by - ay) * (px - ax)) / n
