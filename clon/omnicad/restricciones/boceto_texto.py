"""Boceto 2D: texto."""
import math
import copy
import re

from .boceto_entidades import ErrorBoceto, Linea, Spline, Texto
from .boceto_primitivas import _medidas_marco, primitivas_entidad


_FX = re.compile(r"\{([^{}]*)\}")


def _partes_fx(contenido):
    corte = contenido.rfind(":")
    if corte < max(contenido.rfind("'"), contenido.rfind('"')):     # el «:» va entre comillas: no es formato
        corte = -1
    if corte < 0:
        return contenido.strip(), ""
    return contenido[:corte].strip(), contenido[corte + 1:].strip()


def _sumandos(expresion):
    """Partes de «'abc' + expr + ...» (como los parámetros de texto de Fusion): [(literal?, texto)], cortando en los
    «+» que no están entre comillas ni paréntesis. Sin comillas, None (es una expresión numérica común)."""
    if "'" not in expresion and '"' not in expresion:
        return None
    partes, actual, comilla, nivel = [], "", None, 0
    for ch in expresion + "+":
        if comilla:
            actual += ch
            comilla = None if ch == comilla else comilla
        elif ch in "'\"":
            actual, comilla = actual + ch, ch
        elif ch == "+" and nivel == 0:
            s = actual.strip()
            literal = len(s) >= 2 and s[0] == s[-1] and s[0] in "'\""
            partes.append((literal, s[1:-1] if literal else s))
            actual = ""
        else:
            nivel += (ch == "(") - (ch == ")")
            actual += ch
    return partes


def expresiones_de_texto(texto):
    """Expresiones que lleva un texto entre llaves: «Ancho {ancho}» → ['ancho']; «{largo / 2:.1f}» → ['largo / 2'];
    «{'R-' + rev}» → ['rev']."""
    salida = []
    for e, _f in (_partes_fx(m.group(1)) for m in _FX.finditer(str(texto))):
        partes = _sumandos(e)
        salida += [e] if partes is None else [s for literal, s in partes if not literal]
    return [e for e in salida if e]


def sustituir_expresiones(texto, valor):
    """Reemplaza cada {expresión} (o {expresión:formato}) por el valor que devuelve `valor(expresión)`.
    Las cadenas son literales. Números: hasta 4 decimales sin ceros de más, o el formato indicado (`.1f`…).
    Lo que `valor` no pueda calcular lo deja `valor` (lanza); el que llama decide qué hacer con el error."""
    def numero(expresion, formato):
        v = valor(expresion)
        if isinstance(v, str):
            return v
        unidad = None
        if isinstance(v, tuple):        # (número, unidad): el texto muestra «150 mm» (CF-12)
            v, unidad = v
        v = float(v)
        if formato:
            return format(v, formato)
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        s = "0" if s in ("", "-0") else s
        return f"{s} {unidad}" if unidad else s

    def reemplazo(m):
        expresion, formato = _partes_fx(m.group(1))
        if not expresion:
            return m.group(0)
        partes = _sumandos(expresion)
        if partes is None:
            return numero(expresion, formato)
        return "".join(s if literal else numero(s, formato) for literal, s in partes)
    return _FX.sub(reemplazo, str(texto))


def _validar_opciones_texto(op):
    """Opciones del Texto: claves conocidas, números finitos y valores de lista válidos."""
    desconocidas = set(op) - set(Texto._PREDETERMINADOS)
    if desconocidas:
        raise ErrorBoceto(f"Opciones de texto desconocidas: {', '.join(sorted(desconocidas))}.")
    for k in ("espaciado", "interlineado", "ancho_caja"):
        if k in op and not math.isfinite(float(op[k])):
            raise ErrorBoceto(f"«{k}» tiene que ser un número finito.")
    if "interlineado" in op and float(op["interlineado"]) <= 0:
        raise ErrorBoceto("El interlineado tiene que ser mayor que cero.")
    if "ancho_caja" in op and float(op["ancho_caja"]) < 0:
        raise ErrorBoceto("El ancho de la caja no puede ser negativo.")
    if op.get("alineacion", "izq") not in ("izq", "centro", "der"):
        raise ErrorBoceto("La alineación es izq, centro o der.")
    if op.get("ancla_v", "base") not in ("base", "arriba", "medio", "abajo"):
        raise ErrorBoceto("Anclaje vertical: base, arriba, medio, abajo.")
    if op.get("camino_lado", "izq") not in ("izq", "der"):
        raise ErrorBoceto("El lado del texto en curva es izq o der.")
    if op.get("camino_colocacion", "arriba") not in ("arriba", "abajo"):
        raise ErrorBoceto("Texto en curva: arriba o abajo.")
    for k in ("camino_pos", "camino_desfase", "desfase_base", "inclinacion", "escala_h", "escala_v",
              "grosor_decoracion"):
        if k in op and not math.isfinite(float(op[k])):
            raise ErrorBoceto(f"«{k}» tiene que ser un número finito.")
    for k in ("escala_h", "escala_v"):
        if k in op and not 1.0 <= float(op[k]) <= 1000.0:
            raise ErrorBoceto(f"La escala {'horizontal' if k == 'escala_h' else 'vertical'} va de 1 a 1000 %.")
    if "inclinacion" in op and abs(float(op["inclinacion"])) > 80.0:
        raise ErrorBoceto("La inclinación va de -80 a 80 grados.")
    if "grosor_decoracion" in op and float(op["grosor_decoracion"]) < 0:
        raise ErrorBoceto("Grosor de subrayado y tachado: no negativo.")
    if op.get("capitalizacion", "ninguno") not in ("ninguno", "mayusculas", "minusculas", "titulo", "versalitas"):
        raise ErrorBoceto("Capitalización: opción no válida.")
    for k in ("subrayado", "tachado"):
        if op.get(k, "ninguno") not in ("ninguno", "simple", "doble"):
            raise ErrorBoceto(f"El {k} es ninguno, simple o doble.")
    for par in op.get("ajustes_kerning") or []:
        try:
            i, x = par
            valido = int(i) >= 0 and math.isfinite(float(x))
        except (TypeError, ValueError):
            valido = False
        if not valido:
            raise ErrorBoceto("Kerning: cada par [posición, mm].")


class _Texto:
    # ------------------------------------------------------------ texto
    def agregar_marco_texto(self, tid, ancho, alto):
        """Marco del texto (Fusion: el rectángulo de Text, que se acota): 4 líneas de construcción desde su `punto`
        (esquina de abajo a la izquierda) con el giro del texto; perpendicular y paralelas, así se puede girar.
        Devuelve los ids de las 4 líneas."""
        t = self.curvas[tid]
        if not (1e-6 < ancho < math.inf and 1e-6 < alto < math.inf):
            raise ErrorBoceto("El marco del texto pide ancho y alto > 0.")
        (ax, ay), a = self.coords(t.punto), math.radians(t.angulo)
        u, v = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
        der = self.agregar_punto(ax + ancho * u[0], ay + ancho * u[1])
        opuesta = self.agregar_punto(ax + ancho * u[0] + alto * v[0], ay + ancho * u[1] + alto * v[1])
        arriba = self.agregar_punto(ax + alto * v[0], ay + alto * v[1])
        lados = [self.agregar_linea(i, j, construccion=True)
                 for i, j in ((t.punto, der), (der, opuesta), (opuesta, arriba), (arriba, t.punto))]
        self.agregar_restriccion("perpendicular", [lados[0], lados[1]])
        self.agregar_restriccion("paralela", [lados[0], lados[2]])
        self.agregar_restriccion("paralela", [lados[1], lados[3]])
        t.marco, t.ancho_caja = [der, arriba], float(ancho)
        return lados

    def marco_texto_ajustado(self, tid, ancho=0.0, alto=0.0):
        """Marco que rodea las letras del texto (Fusion: Text › marco); `ancho`/`alto` > 0 lo fijan a mano."""
        t = self.curvas[tid]
        pts = [q for p in self.primitivas(tid) for q in ((p[2], p[3]) if p[0] == "linea" else p[2])] or [(0, 0)]
        w = max(q[0] for q in pts) - min(q[0] for q in pts)
        h = max(q[1] for q in pts) - min(q[1] for q in pts)
        ancho = ancho if ancho > 0 else t.ancho_caja or w or t.altura      # con caja de ancho, el marco la respeta
        return self.agregar_marco_texto(tid, ancho, alto if alto > 0 else h or t.altura)

    def esquina_marco(self, tid, esquina):
        """(x, y) de una esquina del marco del texto (Fusion: el punto del marco elegido como pivote del giro):
        "bl" abajo a la izquierda (el ancla), "br", "tl", "tr" o "center". El texto tiene que tener marco."""
        t = self.curvas[tid]
        if not isinstance(t, Texto) or not t.marco:
            raise ErrorBoceto("Ese texto no tiene marco: agregalo.")
        bl, br, tl = (self.coords(p) for p in (t.punto, *t.marco))
        tr = (br[0] + tl[0] - bl[0], br[1] + tl[1] - bl[1])
        puntos = {"bl": bl, "br": br, "tl": tl, "tr": tr, "center": ((bl[0] + tr[0]) / 2, (bl[1] + tr[1]) / 2)}
        if esquina not in puntos:
            raise ErrorBoceto(f"Esquina desconocida: {esquina!r}.")
        return puntos[esquina]

    def angulo_texto(self, tid):
        """Giro (grados) con que se escribe el texto: el de su marco si lo tiene, el suyo si no. 0 si sus letras
        siguen una curva (no hay una dirección única)."""
        t = self.curvas[tid]
        if t.camino in self.curvas:
            return 0.0
        return math.degrees(_medidas_marco(*map(self.coords, t.puntos()))[0]) if t.marco else t.angulo

    def girar_texto(self, tid, angulo, pivote=None):
        """Gira el texto (y su marco) hasta `angulo` grados alrededor de `pivote` (por defecto, su ancla)."""
        t = self.curvas[tid]
        actual = math.degrees(_medidas_marco(*map(self.coords, t.puntos()))[0]) if t.marco else t.angulo
        self.transformar([tid] + self._lineas_auxiliares(t), angulo=angulo - actual,
                         centro=self.coords(t.punto) if pivote is None else pivote)
        t.angulo = float(angulo)

    def desglosar_texto(self, tid):
        """Desglosar texto (SKT-EXPLODE-TEXT): curvas exactas dentro del mismo objeto lógico."""
        c = self.curvas.get(tid)
        if not isinstance(c, Texto):
            raise ErrorBoceto("Hacé clic en un texto.")
        prims = primitivas_entidad(c, self.coords, curvas=self.curvas)
        if not prims:
            raise ErrorBoceto("No se pudo generar la geometría del texto.")
        cache = {}

        def punto(q):
            clave = (round(q[0], 6), round(q[1], 6))
            if clave not in cache:
                cache[clave] = self.agregar_punto(*q)
            return cache[clave]
        objetos_antes = copy.deepcopy(self.objetos)
        self.eliminar(tid)
        ids = []
        for prim in prims:
            if prim[0] == "linea":
                ids.append(self._agregar_curva(Linea(self._nuevo_id(), punto(prim[2]), punto(prim[3]))))
            else:
                ids.append(self._agregar_curva(Spline(self._nuevo_id(), [punto(q) for q in prim[2]], "control",
                                                      prim[4], False, prim[5], prim[3])))
        if ids:
            self.agregar_restriccion("fijo", ids)
            from . import objetos
            if any(tid in o["entidades"] for o in objetos_antes.values()):
                for oid, o in objetos_antes.items():
                    o["entidades"] = [j for i in o["entidades"] for j in (ids if i == tid else [i])
                                      if j in self.curvas or j in objetos_antes]
                    if o.get("texto_automatico") == tid:
                        o.pop("texto_automatico")
                        o["clase"] = "texto"           # convertido, sigue en «Textos» del navegador
                    if o["entidades"]:
                        self.objetos[oid] = o
                objetos.invalidar(self)
            else:
                self.objetos[objetos.crear(self, ids, "Texto convertido")]["clase"] = "texto"
        return ids
