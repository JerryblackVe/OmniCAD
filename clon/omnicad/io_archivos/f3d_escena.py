# -*- coding: utf-8 -*-
"""
Posición de los componentes de un .f3d: lee la escena de dibujo que Fusion guarda dentro del archivo
(`OGS.BlobFolder/OGS/DefaultScene/world` + `Fusion_mesh_000`) y saca de ahí los componentes con su matriz, las copias
de un mismo componente (instancias) y los cuerpos con su malla. Sin Qt.

Formato (descubierto mirando archivos reales de Fusion y el serializador `OGS::Serialization::WorldSerializer` de
`OGSGraphics.dll`; no hay documentación pública):

* `world` es una lista de registros: cada texto es un uint32 con el LARGO EN CARACTERES y los caracteres en UTF-16LE
  (`GroupNode`, `TransformAttribute`, `Face`, `Body`, `Instance`…); los nodos llevan después un id de 16 caracteres
  hexadecimales (la dirección del objeto en memoria de Fusion).
* Cada componente (ocurrencia) es un NODO que ocupa un tramo del archivo: arranca en la primera aparición del id de su
  envoltorio (`GroupNode <W>`), trae adentro su contenido (caras, cuerpos y los componentes que contiene) y cierra con su
  cola: `TransformAttribute` (+5 bytes de cabecera y 16 float32 en filas: la traslación va en la última fila, en
  CENTÍMETROS), el id `<W>` y la etiqueta `Instance`. Los tramos se anidan: un conjunto contiene a sus componentes.
* El contenido de un nodo es un grupo con id `<C>` (el segundo id, después de `SingleNodeWorld`). Si un componente tiene
  varias copias, el contenido se escribe una sola vez y las demás ocurrencias traen el MISMO `<C>` sin repetir las caras:
  son las instancias.
* Un cuerpo es una tanda de registros `Face` seguida de la etiqueta `Body`. Cada `Face` con malla lleva
  `[desplazamiento, 3·nV, 3·nV, 2·nV, nIdx]` (uint32) hacia `Fusion_mesh_000`, donde están nV vértices de 32 bytes
  (posición, normal, uv en float32) y nIdx índices uint32. Los cuerpos ocultos no traen malla.
* La malla y el B-rep del cuerpo están en las coordenadas DEL COMPONENTE; la matriz acumulada de los nodos que lo
  contienen lo lleva al diseño (comprobado: sin ella, 164 pares de piezas del extrusor de ejemplo se pisaban entre sí;
  con ella, 7).
"""
import re
import struct

import numpy as np

HEX16 = re.compile(rb"\x10\x00\x00\x00((?:[0-9A-F]\x00){16})")
# Topes contra un archivo hostil (el .f3d es de otro): lo que pasa de acá no se interpreta y los cuerpos quedan donde
# están guardados. Los archivos reales no se acercan (el extrusor de ejemplo: 35 componentes, 5 copias de la más repetida).
NODOS_MAX = 20000            # etiquetas `Instance` (componentes)
MARCOS_MAX = 5000            # copias de un mismo componente (cada conjunto anidado multiplica)
CUERPOS_COLOCADOS_MAX = 20000  # cuerpos que salen de colocar todas las copias
CARAS_MALLA_MAX = 2_000_000  # vértices de una cara
_VENTANA_COLA = 4000         # bytes entre el `TransformAttribute` y la etiqueta `Instance` (reales: ~150)
_VENTANA_CABECERA = 600      # bytes entre el id del envoltorio y `SingleNodeWorld` (reales: ~70)
_CM_A_MM = 10.0


def _texto(nombre):
    return struct.pack("<I", len(nombre)) + nombre.encode("utf-16-le")


_FACE, _BODY, _INSTANCE = _texto("Face"), _texto("Body"), _texto("Instance")
_TRANSFORM, _SNW = _texto("TransformAttribute"), _texto("SingleNodeWorld")
_RE_ETIQUETAS = re.compile(b"|".join(re.escape(t) for t in (_FACE, _BODY, _INSTANCE)), re.S)


class Escena:
    """Nodos de componente y cuerpos de la escena de un .f3d.

    `nodos[i]`: dict(pos, ini, M (4×4 en filas, traslación en cm), W, C, padre, primario, es_ref).
    `cuerpos[k]`: dict(pos, nodo, caras (n), vol_mm3, lo, hi, centro (mm) — None si el cuerpo no trae malla)."""

    def __init__(self, world, malla):
        self.w, self.m = world, malla
        self.nodos, self.cuerpos = [], []
        self._leer()

    # ------------------------------------------------------------------ lectura
    def _leer(self):
        w = self.w
        caras, cuerpos, etiquetas = [], [], []
        for m in _RE_ETIQUETAS.finditer(w):
            tipo = m.group()
            if tipo == _FACE:
                caras.append(m.end())
            elif tipo == _BODY:
                cuerpos.append({"pos": m.start(), "caras_fin": caras})
                caras = []
            else:                                                       # Instance
                etiquetas.append(m.start())
                if len(etiquetas) > NODOS_MAX:
                    raise ValueError("demasiados componentes")
        nodos = []
        for pos in etiquetas:
            t = w.rfind(_TRANSFORM, max(0, pos - _VENTANA_COLA), pos)
            ini_m = t + len(_TRANSFORM) + 5
            if t < 0 or ini_m + 64 > len(w):
                continue
            h = HEX16.search(w, t, pos)
            nodos.append({"pos": pos, "W": h.group(1) if h else None, "t": t,
                          "M": np.frombuffer(w[ini_m:ini_m + 64], "<f4").reshape(4, 4).astype(float)})
        # `ini`: primera aparición del id del envoltorio (solo se buscan los ids de las colas, no todos los del archivo)
        buscados, primera = {n["W"] for n in nodos if n["W"]}, {}
        for m in HEX16.finditer(w):
            if len(primera) == len(buscados):
                break
            if m.group(1) in buscados:
                primera.setdefault(m.group(1), m.start())
        for n in nodos:
            n["ini"] = primera.get(n["W"], n["t"])
            del n["t"]
        nodos.sort(key=lambda n: n["pos"])
        for n in nodos:
            s = w.find(_SNW, n["ini"], n["ini"] + _VENTANA_CABECERA)
            h = HEX16.search(w, s, s + 220) if s >= 0 else None
            n["C"] = h.group(1) if h else None
        self.nodos, self.cuerpos = nodos, cuerpos
        self._jerarquia()
        self._vertices_libres = len(self.m) // 32 * 2                   # un archivo honesto no lee dos veces la misma zona
        for c in cuerpos:
            self._malla_del_cuerpo(c)

    def _jerarquia(self):
        """Padre de cada nodo y nodo de cada cuerpo: un recorrido por el archivo con la pila de tramos abiertos (los
        tramos se anidan o no se tocan). En la misma posición se abre, se cuenta el cuerpo y recién después se cierra."""
        nodos = self.nodos
        eventos = [(n["ini"], 0, i) for i, n in enumerate(nodos)] + [(n["pos"], 2, i) for i, n in enumerate(nodos)]
        eventos += [(c["pos"], 1, k) for k, c in enumerate(self.cuerpos)]
        eventos.sort()
        pila = []
        for _, tipo, i in eventos:
            if tipo == 0:
                nodos[i]["padre"] = pila[-1] if pila else None
                pila.append(i)
            elif tipo == 1:
                self.cuerpos[i]["nodo"] = pila[-1] if pila else None
            elif i in pila:
                pila.remove(i)
        primario = {}
        for i, n in enumerate(nodos):
            if n["C"] is not None:
                primario.setdefault(n["C"], i)
        for i, n in enumerate(nodos):
            n["primario"] = primario.get(n["C"], i)
            n["es_ref"] = n["primario"] != i

    def _malla_cara(self, fin):
        """(vértices Nx3 en cm, triángulos Mx3) de la cara cuyo nombre termina en `fin`, o None si no trae malla."""
        w, m = self.w, self.m
        for p in range(fin, min(fin + 200, len(w) - 20)):
            desp, a, a2, b, n_idx = struct.unpack_from("<5I", w, p)
            if not (a and a == a2 and a % 3 == 0 and b == a // 3 * 2 and n_idx and n_idx % 3 == 0):
                continue
            n_ver = a // 3
            if n_ver > CARAS_MALLA_MAX or desp + n_ver * 32 + n_idx * 4 > len(m):
                continue
            self._vertices_libres -= n_ver
            if self._vertices_libres < 0:                               # varias caras apuntan a la misma malla
                return None
            v = np.frombuffer(m, "<f4", count=n_ver * 8, offset=desp).reshape(n_ver, 8)[:, :3].astype(float)
            idx = np.frombuffer(m, "<u4", count=n_idx, offset=desp + n_ver * 32)
            if idx.max() >= n_ver or not np.isfinite(v).all():
                continue
            return v, idx.reshape(-1, 3)
        return None

    def _malla_del_cuerpo(self, c):
        fines = c.pop("caras_fin")
        c["caras"] = len(fines)
        c["vol_mm3"] = c["lo"] = c["hi"] = c["centro"] = None
        mallas = [self._malla_cara(f) for f in fines]
        if not mallas or any(x is None for x in mallas):               # sin malla (cuerpo oculto) o incompleta
            return
        puntos = np.vstack([v for v, _ in mallas]) * _CM_A_MM
        vol, momento = 0.0, np.zeros(3)
        for v, t in mallas:                                          # tetraedros contra el origen
            a, b, c3 = v[t[:, 0]] * _CM_A_MM, v[t[:, 1]] * _CM_A_MM, v[t[:, 2]] * _CM_A_MM
            dv = np.einsum("ij,ij->i", a, np.cross(b, c3)) / 6.0
            vol += float(dv.sum())
            momento += (dv[:, None] * (a + b + c3)).sum(axis=0) / 4.0
        c["vol_mm3"], c["lo"], c["hi"] = abs(vol), puntos.min(axis=0), puntos.max(axis=0)
        c["centro"] = momento / vol if abs(vol) > 1e-12 else None

    # ------------------------------------------------------------------ marcos
    def marcos(self):
        """{índice del nodo primario: [matrices 4×4 de columnas en mm]}: una por cada ocurrencia del contenido
        (la del primario y las de sus copias), ya con las matrices de todos los conjuntos que lo contienen."""
        nodos = self.nodos
        miembros = {}
        for i, n in enumerate(nodos):
            miembros.setdefault(n["primario"], []).append(i)
        memo, en_curso = {}, set()

        def de(p):
            if p in memo:
                return memo[p]
            if p in en_curso:                                          # un archivo hostil con un lazo
                return [np.eye(4)]
            en_curso.add(p)
            salida = []
            for i in miembros[p]:
                n = nodos[i]
                padres = [np.eye(4)] if n["padre"] is None else de(nodos[n["padre"]]["primario"])
                salida += [n["M"] @ P for P in padres]
                if len(salida) > MARCOS_MAX:
                    raise ValueError("demasiadas copias de un componente")
            en_curso.discard(p)
            memo[p] = salida
            return salida

        return {p: [_a_columnas_mm(F) for F in de(p)] for p in miembros}


def _a_columnas_mm(F):
    """Matriz de filas en cm (v·F) → matriz de columnas en mm (F·v), con la rotación ortonormalizada."""
    R = F[:3, :3]
    u, s, vt = np.linalg.svd(R)
    if np.allclose(s, 1.0, atol=1e-3):                                 # movimiento rígido: se limpia el ruido float32
        R = u @ vt
    M = np.eye(4)
    M[:3, :3] = R.T
    M[:3, 3] = F[3, :3] * _CM_A_MM
    return M


def es_identidad(M, tol=1e-6):
    return bool(np.allclose(M, np.eye(4), atol=tol))


# ---------------------------------------------------------------------- B-rep ↔ escena
TOL_CAJA_MM = 0.6            # la malla (a veces más tosca) puede quedar medio milímetro por dentro de la caja exacta
TOL_VOLUMEN = 0.03           # y su volumen difiere un par de décimas de por ciento (teselado)


def asignar(escena, solidos):
    """Ubica los cuerpos B-rep de un .f3d en el diseño. `solidos`: lista de dicts con `bloque` (de qué archivo
    BREP.*.smbh salió: un componente), `tipo`, `caras`, `lo`/`hi` (una caja en mm que puede ser holgada, barata de
    calcular) y funciones sin argumentos que se llaman solo cuando hace falta: `caja` (la caja exacta, `(lo, hi)`),
    `vol` (el volumen en mm³) y, si está, `centro` (el centro de masa en mm).

    Cada cuerpo de la escena con malla se empareja con el sólido de igual caja y volumen (una superficie: igual caja
    y cantidad de caras); entre dos iguales en caja y volumen (dos piezas espejo) gana el de centro de masa más cercano; los emparejamientos votan qué componente de la escena es cada bloque BREP, y todos los
    cuerpos del bloque (también los ocultos, que no traen malla) toman las matrices de ese componente. Un componente que
    se quedó sin bloque porque era una copia idéntica de otro (el lector descarta los cuerpos repetidos) comparte el
    bloque de su gemelo; un bloque sin malla visible se empareja por la cantidad de caras de sus cuerpos.

    Fusion guarda en el bloque de un componente también cuerpos VIEJOS de su historial (el del panel de la cartera de
    ejemplo trae 83 cuerpos y el diseño tiene 1). Si todos los cuerpos de la escena de los componentes de un bloque ya
    tienen su sólido, los demás sólidos de ese bloque no están en el diseño actual: van en `info["descartados"]`
    (comprobado abriendo los ejemplos en Fusion: ninguno de esos cuerpos existe en el diseño).

    Un cuerpo actual sin malla en la escena es un cuerpo OCULTO (Fusion no tesela lo que no se ve): si se salva por
    esa vía va en `info["ocultos"]` y entra con el ojo cerrado, como en el navegador de Fusion.

    Devuelve (matrices, info): `matrices[j]` = lista de matrices 4×4 de columnas en mm (una por copia) o None si no se
    pudo ubicar (o se descarta); `info` = contadores para informar, `descartados` y `ocultos` (índices de `solidos`)."""
    marcos = escena.marcos()
    nodos = escena.nodos
    visibles = [(i, c) for i, c in enumerate(escena.cuerpos) if c["vol_mm3"] is not None and c["nodo"] is not None]
    primario_de = {i: nodos[c["nodo"]]["primario"] for i, c in visibles}
    lo_s = np.array([s["lo"] for s in solidos], float).reshape(-1, 3)
    hi_s = np.array([s["hi"] for s in solidos], float).reshape(-1, 3)
    es_solido = np.array([s["tipo"] == "solido" for s in solidos], bool)
    candidatos = []
    for i, c in visibles:
        dentro = (c["lo"] >= lo_s - TOL_CAJA_MM).all(axis=1) & (c["hi"] <= hi_s + TOL_CAJA_MM).all(axis=1)
        for j in np.nonzero(dentro)[0]:                              # la malla cabe en la caja holgada: se mide de cerca
            if not es_solido[j] and solidos[j]["caras"] != c["caras"]:
                continue
            lo, hi = solidos[j]["caja"]()
            d_lo = float(np.abs(c["lo"] - lo).max())
            d_hi = float(np.abs(c["hi"] - hi).max())
            if d_lo > TOL_CAJA_MM or d_hi > TOL_CAJA_MM:
                continue
            if not es_solido[j]:                                    # una superficie abierta no tiene volumen
                candidatos.append((d_lo + d_hi, i, int(j)))
                continue
            vol = solidos[j]["vol"]()
            dv = abs(c["vol_mm3"] - vol) / max(vol, 1e-9)
            if dv <= TOL_VOLUMEN or abs(c["vol_mm3"] - vol) < 0.5:
                d_c = 0.0
                if c.get("centro") is not None and "centro" in solidos[j]:
                    d_c = float(np.linalg.norm(c["centro"] - np.asarray(solidos[j]["centro"]())))
                candidatos.append((dv + d_lo + d_hi + d_c, i, int(j)))
    candidatos.sort()
    cuerpo_usado, solido_usado, votos = set(), set(), {}
    for _, i, j in candidatos:
        if i in cuerpo_usado or j in solido_usado:
            continue
        cuerpo_usado.add(i)
        solido_usado.add(j)
        clave = (solidos[j]["bloque"], primario_de[i])
        votos[clave] = votos.get(clave, 0) + 1
    bloque_de, nodo_de = {}, {}                                     # bloque → [componentes]; componente → bloque
    for (bloque, primario), _n in sorted(votos.items(), key=lambda kv: -kv[1]):
        if bloque not in bloque_de and primario not in nodo_de:
            bloque_de[bloque], nodo_de[primario] = [primario], bloque
    # componentes sin bloque cuyos cuerpos visibles son idénticos a los de un bloque ya repartido (copias hechas a mano)
    cubre, visibles_de = {}, {}
    for i, p in primario_de.items():
        visibles_de.setdefault(p, set()).add(i)
    for _, i, j in candidatos:
        cubre.setdefault((primario_de[i], solidos[j]["bloque"]), set()).add(i)
    for p in sorted(visibles_de):
        if p in nodo_de:
            continue
        igual = [(len(c), b) for (q, b), c in cubre.items() if q == p and c == visibles_de[p] and b in bloque_de]
        if igual:
            b = max(igual, key=lambda x: x[0])[1]
            bloque_de[b].append(p)
            nodo_de[p] = b
    # bloques sin ningún cuerpo visible: por la cantidad de caras de sus cuerpos
    por_bloque, por_nodo = {}, {}
    for s in solidos:
        por_bloque.setdefault(s["bloque"], []).append(s["caras"])
    for c in escena.cuerpos:
        if c["nodo"] is not None:
            por_nodo.setdefault(nodos[c["nodo"]]["primario"], []).append(c["caras"])
    libres_b = [b for b in por_bloque if b not in bloque_de]
    libres_n = [p for p in por_nodo if p not in nodo_de]
    for b in libres_b:
        a = sorted(por_bloque[b])
        parecidos = [p for p in libres_n if _caras_parecidas(a, sorted(por_nodo[p]))]
        rivales = [x for x in libres_b if _caras_parecidas(a, sorted(por_bloque[x]))]
        if len(parecidos) == 1 and len(rivales) == 1:
            bloque_de[b], nodo_de[parecidos[0]] = [parecidos[0]], b
            libres_n.remove(parecidos[0])
    # cuerpos viejos del historial: en un bloque con algún sólido emparejado, cuyos componentes ya tienen todos sus
    # cuerpos con malla emparejados. Un cuerpo actual puede no traer malla (la «tela» del abanico de ejemplo): un registro
    # de la escena sin malla con la misma cantidad de caras lo salva (no todos esos registros son cuerpos: en el
    # extrusor de ejemplo casi cada cuerpo con malla trae otro sin malla, y Fusion muestra un solo cuerpo).
    con_par = {solidos[j]["bloque"] for j in solido_usado}
    cubiertos = {p for p, cs in visibles_de.items() if cs <= cuerpo_usado}
    sin_malla = {}
    for c in escena.cuerpos:
        if c["vol_mm3"] is None and c["nodo"] is not None:
            caras_p = sin_malla.setdefault(nodos[c["nodo"]]["primario"], {})
            caras_p[c["caras"]] = caras_p.get(c["caras"], 0) + 1
    # bloques de componentes que ya no existen: si TODOS los componentes de la escena con cuerpos tienen su bloque, un
    # bloque sin componente no es de ninguno (comprobado en Fusion: Sherpa, 2 bloques sin dueño que el diseño no tiene)
    huerfanos = not [p for p in por_nodo if p not in nodo_de]
    descartados = [j for j, s in enumerate(solidos) if huerfanos and s["bloque"] not in bloque_de]
    ocultos = []
    for j, s in enumerate(solidos):
        if j in descartados:
            continue
        componentes = bloque_de.get(s["bloque"], [None])
        if j in solido_usado or s["bloque"] not in con_par or not all(p in cubiertos for p in componentes):
            continue
        salva = next((p for p in componentes if sin_malla.get(p, {}).get(s["caras"], 0) > 0), None)
        if salva is None:
            descartados.append(j)
        else:
            sin_malla[salva][s["caras"]] -= 1
            ocultos.append(j)
    fuera = set(descartados)
    matrices = []
    ubicados = copias = 0
    for j, s in enumerate(solidos):
        componentes = bloque_de.get(s["bloque"])
        if componentes is None or j in fuera:
            matrices.append(None)
            continue
        propias = [M for p in componentes for M in marcos[p]]
        matrices.append(propias)
        ubicados += 1
        copias += len(propias) - 1
        if sum(len(m) for m in matrices if m) > CUERPOS_COLOCADOS_MAX:
            raise ValueError("demasiados cuerpos al colocar las copias")
    return matrices, {"bloques": len(por_bloque), "bloques_ubicados": len(bloque_de), "ubicados": ubicados,
                      "copias": copias, "componentes": len(por_nodo), "componentes_ubicados": len(nodo_de),
                      "descartados": descartados, "ocultos": ocultos}


def _caras_parecidas(a, b):
    return len(a) == len(b) and all(abs(x - y) <= max(2, 0.05 * max(x, y)) for x, y in zip(a, b, strict=True))
