# -*- coding: utf-8 -*-
"""
Descompresor Zstandard escrito desde cero en Python, siguiendo la especificación pública RFC 8878.

Los .f3d de Fusion guardan sus partes dentro del ZIP con el método 93 (Zstandard), que el `zipfile` de Python
recién trae desde la versión 3.14. Si el intérprete ya tiene `compression.zstd` (3.14+) se usa ese, que es mucho
más rápido; si no, este decodificador puro (sin dependencias). Solo descomprime: tramas, bloques crudos, RLE y
comprimidos (literales Huffman, secuencias FSE, offsets repetidos). No soporta diccionarios (Fusion no los usa).

Sin Qt.
"""
import struct

try:                                         # Python 3.14+: el módulo de la biblioteca estándar
    from compression import zstd as _zstd_std
except ImportError:                          # pragma: no cover - depende de la versión de Python
    _zstd_std = None

MAGICO = 0xFD2FB528
METODO_ZIP_ZSTD = 93


class ErrorZstd(ValueError):
    """Los datos no son Zstandard válido (o usan algo no soportado, como un diccionario)."""


# ---------------------------------------------------------------- tablas fijas de la especificación (RFC 8878)
_LL_BASE = list(range(16)) + [16, 18, 20, 22, 24, 28, 32, 40, 48, 64, 128, 256, 512, 1024, 2048, 4096, 8192,
                              16384, 32768, 65536]
_LL_BITS = [0] * 16 + [1, 1, 1, 1, 2, 2, 3, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
_ML_BASE = list(range(3, 35)) + [35, 37, 39, 41, 43, 47, 51, 59, 67, 83, 99, 131, 259, 515, 1027, 2051, 4099, 8195,
                                 16387, 32771, 65539]
_ML_BITS = [0] * 32 + [1, 1, 1, 1, 2, 2, 3, 3, 4, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
_LL_DEFECTO = ([4, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 2, 1, 1, 1, 1, 1]
               + [-1] * 4, 6)
_ML_DEFECTO = ([1, 4, 3, 2, 2, 2, 2, 2, 2] + [1] * 37 + [-1] * 7, 6)
_OF_DEFECTO = ([1, 1, 1, 1, 1, 1, 2, 2, 2] + [1] * 15 + [-1] * 5, 5)


def descomprimir(datos):
    """Descomprime una o varias tramas Zstandard seguidas. Devuelve bytes."""
    datos = bytes(datos)
    if _zstd_std is not None:
        try:
            return _zstd_std.decompress(datos)
        except Exception as e:  # noqa: BLE001 — el error de la biblioteca se traduce al nuestro
            raise ErrorZstd(f"Zstandard inválido: {e}") from None
    return _descomprimir_puro(datos)


def _descomprimir_puro(datos):
    salida = bytearray()
    p = 0
    while p < len(datos):
        if len(datos) - p < 4:
            raise ErrorZstd("Trama Zstandard truncada.")
        magico = struct.unpack_from("<I", datos, p)[0]
        if magico & 0xFFFFFFF0 == 0x184D2A50:            # trama salteable (metadatos): se ignora
            tam = struct.unpack_from("<I", datos, p + 4)[0]
            p += 8 + tam
            continue
        if magico != MAGICO:
            raise ErrorZstd("No es Zstandard (número mágico incorrecto).")
        p = _trama(datos, p + 4, salida)
    return bytes(salida)


def _trama(d, p, salida):
    desc = d[p]
    p += 1
    fcs_flag, un_segmento, checksum, dict_flag = desc >> 6, (desc >> 5) & 1, (desc >> 2) & 1, desc & 3
    if desc & 0x08:
        raise ErrorZstd("Trama Zstandard con bit reservado.")
    if not un_segmento:
        p += 1                                           # descriptor de ventana: no hace falta para descomprimir
    if dict_flag:
        tam_dict = (0, 1, 2, 4)[dict_flag]
        if int.from_bytes(d[p:p + tam_dict], "little"):
            raise ErrorZstd("Zstandard con diccionario: no soportado.")
        p += tam_dict
    p += (1 if un_segmento else 0, 2, 4, 8)[fcs_flag]
    inicio = len(salida)
    ctx = _Contexto()
    while True:
        if p + 3 > len(d):
            raise ErrorZstd("Bloque Zstandard truncado.")
        cab = d[p] | (d[p + 1] << 8) | (d[p + 2] << 16)
        p += 3
        ultimo, tipo, tam = cab & 1, (cab >> 1) & 3, cab >> 3
        if tipo == 0:
            salida += d[p:p + tam]
            p += tam
        elif tipo == 1:
            salida += bytes([d[p]]) * tam
            p += 1
        elif tipo == 2:
            _bloque(d, p, p + tam, salida, inicio, ctx)
            p += tam
        else:
            raise ErrorZstd("Tipo de bloque Zstandard reservado.")
        if ultimo:
            break
    if checksum:
        p += 4                                           # xxHash64 del contenido: no se verifica
    return p


class _Contexto:
    """Estado que se arrastra entre bloques de una trama: tabla Huffman, tablas FSE y offsets repetidos."""

    def __init__(self):
        self.huffman = None
        self.tablas = {"ll": None, "of": None, "ml": None}
        self.rep = [1, 4, 8]


# ---------------------------------------------------------------- lectores de bits
class _BitsAdelante:
    """Bits en orden little-endian desde el principio (descripción de tablas FSE)."""

    def __init__(self, d, p):
        self.d, self.inicio, self.bit = d, p, p * 8

    def leer(self, n):
        i = self.bit >> 3
        v = int.from_bytes(self.d[i:i + 8], "little") >> (self.bit & 7)
        self.bit += n
        return v & ((1 << n) - 1)

    def bytes_consumidos(self):
        return (self.bit + 7) // 8 - self.inicio


class _BitsAtras:
    """Flujo de bits que se lee desde el final hacia el principio (Huffman y secuencias). Pasado el principio
    devuelve ceros, como pide la especificación; `pos < 0` indica que se consumió todo."""

    def __init__(self, d, ini, fin):
        if fin <= ini or d[fin - 1] == 0:
            raise ErrorZstd("Flujo de bits Zstandard sin marca final.")
        self.d, self.ini = d, ini
        self.pos = (fin - ini) * 8 - (8 - d[fin - 1].bit_length()) - 1

    def leer(self, n):
        if n == 0:
            return 0
        self.pos -= n
        p = self.pos
        if p >= 0:
            i = self.ini + (p >> 3)
            return (int.from_bytes(self.d[i:i + 8], "little") >> (p & 7)) & ((1 << n) - 1)
        if p + n <= 0:
            return 0
        v = int.from_bytes(self.d[self.ini:self.ini + 8], "little") & ((1 << (p + n)) - 1)
        return v << (-p)

    def mirar(self, n):
        """Los próximos `n` bits sin consumirlos."""
        p = self.pos - n
        if p >= 0:
            i = self.ini + (p >> 3)
            return (int.from_bytes(self.d[i:i + 8], "little") >> (p & 7)) & ((1 << n) - 1)
        if self.pos <= 0:
            return 0
        v = int.from_bytes(self.d[self.ini:self.ini + 8], "little") & ((1 << self.pos) - 1)
        return v << (-p)


# ---------------------------------------------------------------- FSE
def _leer_distribucion(d, p, simbolo_max):
    """Descripción de una tabla FSE (conteos normalizados). Devuelve (conteos, log_precision, bytes_leídos)."""
    b = _BitsAdelante(d, p)
    log = b.leer(4) + 5
    restante = (1 << log) + 1
    umbral = 1 << log
    nbits = log + 1
    conteos = []
    while restante > 1 and len(conteos) <= simbolo_max:
        maximo = (2 * umbral - 1) - restante
        v = b.leer(nbits - 1)
        if v < maximo:
            cuenta = v
        else:
            v |= b.leer(1) << (nbits - 1)
            cuenta = v if v < umbral else v - maximo
        cuenta -= 1
        restante -= abs(cuenta)
        conteos.append(cuenta)
        if cuenta == 0:
            while True:
                rep = b.leer(2)
                conteos.extend([0] * rep)
                if rep != 3:
                    break
        while restante < umbral:
            nbits -= 1
            umbral >>= 1
    if restante != 1 or len(conteos) > simbolo_max + 1:
        raise ErrorZstd("Tabla FSE corrupta.")
    return conteos, log, b.bytes_consumidos()


def _tabla_fse(conteos, log):
    """Tabla de decodificación FSE: lista de (símbolo, nbits, base) indexada por estado."""
    tam = 1 << log
    simbolos = [0] * tam
    alto = tam - 1
    siguiente = []
    for s, c in enumerate(conteos):
        if c == -1:
            simbolos[alto] = s
            alto -= 1
            siguiente.append(1)
        else:
            siguiente.append(c)
    paso = (tam >> 1) + (tam >> 3) + 3
    pos = 0
    for s, c in enumerate(conteos):
        for _ in range(max(c, 0)):
            simbolos[pos] = s
            pos = (pos + paso) & (tam - 1)
            while pos > alto:
                pos = (pos + paso) & (tam - 1)
    if pos != 0:
        raise ErrorZstd("Tabla FSE inconsistente.")
    tabla = []
    for estado in range(tam):
        s = simbolos[estado]
        nxt = siguiente[s]
        siguiente[s] += 1
        nb = log - (nxt.bit_length() - 1)
        tabla.append((s, nb, (nxt << nb) - tam))
    return tabla, log


def _tabla_rle(simbolo):
    return [(simbolo, 0, 0)], 0


_TABLAS_DEFECTO = {"ll": _tabla_fse(*_LL_DEFECTO), "ml": _tabla_fse(*_ML_DEFECTO), "of": _tabla_fse(*_OF_DEFECTO)}


# ---------------------------------------------------------------- Huffman
def _leer_huffman(d, p):
    """Descripción del árbol Huffman de los literales. Devuelve ((tabla, max_bits), bytes_leídos)."""
    cab = d[p]
    if cab < 128:                                         # pesos comprimidos con FSE (dos estados intercalados)
        conteos, log, usados = _leer_distribucion(d, p + 1, 255)
        tabla, log = _tabla_fse(conteos, log)
        bits = _BitsAtras(d, p + 1 + usados, p + 1 + cab)
        e1, e2 = bits.leer(log), bits.leer(log)
        pesos = []
        while True:
            s, nb, base = tabla[e1]
            pesos.append(s)
            e1 = base + bits.leer(nb)
            if bits.pos < 0:
                pesos.append(tabla[e2][0])
                break
            s, nb, base = tabla[e2]
            pesos.append(s)
            e2 = base + bits.leer(nb)
            if bits.pos < 0:
                pesos.append(tabla[e1][0])
                break
            if len(pesos) > 255:
                raise ErrorZstd("Árbol Huffman corrupto.")
        usados_total = 1 + cab
    else:                                                 # pesos directos, 4 bits cada uno
        n = cab - 127
        pesos = []
        for i in range(n):
            byte = d[p + 1 + i // 2]
            pesos.append(byte >> 4 if i % 2 == 0 else byte & 15)
        usados_total = 1 + (n + 1) // 2
    total = sum(1 << (w - 1) for w in pesos if w)
    if total == 0:
        raise ErrorZstd("Árbol Huffman vacío.")
    max_bits = total.bit_length()
    resto = (1 << max_bits) - total
    if resto & (resto - 1):
        raise ErrorZstd("Árbol Huffman corrupto (el último peso no es potencia de 2).")
    pesos.append(resto.bit_length())
    tabla = [None] * (1 << max_bits)
    pos = 0
    for w in range(1, max_bits + 1):
        nb = max_bits + 1 - w
        ancho = 1 << (w - 1)
        for s, ws in enumerate(pesos):
            if ws == w:
                entrada = (s, nb)
                for k in range(pos, pos + ancho):
                    tabla[k] = entrada
                pos += ancho
    return (tabla, max_bits), usados_total


def _decodificar_huffman(d, ini, fin, n, huffman, salida):
    tabla, max_bits = huffman
    bits = _BitsAtras(d, ini, fin)
    for _ in range(n):
        s, nb = tabla[bits.mirar(max_bits)]
        bits.pos -= nb
        salida.append(s)


# ---------------------------------------------------------------- bloque comprimido
def _bloque(d, p, fin, salida, inicio_trama, ctx):
    literales, p = _literales(d, p, ctx)
    _secuencias(d, p, fin, literales, salida, inicio_trama, ctx)


def _literales(d, p, ctx):
    b0 = d[p]
    tipo, formato = b0 & 3, (b0 >> 2) & 3
    if tipo in (0, 1):                                    # crudos o RLE
        if formato in (0, 2):
            tam, p = b0 >> 3, p + 1
        elif formato == 1:
            tam, p = (b0 >> 4) | (d[p + 1] << 4), p + 2
        else:
            tam, p = (b0 >> 4) | (d[p + 1] << 4) | (d[p + 2] << 12), p + 3
        if tipo == 0:
            return d[p:p + tam], p + tam
        return bytes([d[p]]) * tam, p + 1
    if formato in (0, 1):
        h = int.from_bytes(d[p:p + 3], "little")
        regen, comp, p = (h >> 4) & 0x3FF, (h >> 14) & 0x3FF, p + 3
    elif formato == 2:
        h = int.from_bytes(d[p:p + 4], "little")
        regen, comp, p = (h >> 4) & 0x3FFF, (h >> 18) & 0x3FFF, p + 4
    else:
        h = int.from_bytes(d[p:p + 5], "little")
        regen, comp, p = (h >> 4) & 0x3FFFF, (h >> 22) & 0x3FFFF, p + 5
    fin = p + comp
    q = p
    if tipo == 2:
        ctx.huffman, usados = _leer_huffman(d, q)
        q += usados
    elif ctx.huffman is None:
        raise ErrorZstd("Literales sin árbol Huffman previo.")
    salida = bytearray()
    if formato == 0:                                      # un solo flujo
        _decodificar_huffman(d, q, fin, regen, ctx.huffman, salida)
    else:                                                 # cuatro flujos con tabla de saltos
        t1, t2, t3 = struct.unpack_from("<3H", d, q)
        q += 6
        por_flujo = (regen + 3) // 4
        limites = [q, q + t1, q + t1 + t2, q + t1 + t2 + t3, fin]
        for k in range(4):
            n = por_flujo if k < 3 else regen - 3 * por_flujo
            _decodificar_huffman(d, limites[k], limites[k + 1], n, ctx.huffman, salida)
    return bytes(salida), fin


def _secuencias(d, p, fin, literales, salida, inicio_trama, ctx):
    if p >= fin:
        salida += literales
        return
    b0 = d[p]
    if b0 == 0:
        salida += literales
        return
    if b0 < 128:
        nseq, p = b0, p + 1
    elif b0 < 255:
        nseq, p = ((b0 - 128) << 8) + d[p + 1], p + 2
    else:
        nseq, p = d[p + 1] + (d[p + 2] << 8) + 0x7F00, p + 3
    modos = d[p]
    p += 1
    for clave, desplazamiento, simbolo_max in (("ll", 6, 35), ("of", 4, 31), ("ml", 2, 52)):
        modo = (modos >> desplazamiento) & 3
        if modo == 0:
            ctx.tablas[clave] = _TABLAS_DEFECTO[clave]
        elif modo == 1:
            ctx.tablas[clave] = _tabla_rle(d[p])
            p += 1
        elif modo == 2:
            conteos, log, usados = _leer_distribucion(d, p, simbolo_max)
            ctx.tablas[clave] = _tabla_fse(conteos, log)
            p += usados
        elif ctx.tablas[clave] is None:
            raise ErrorZstd("Modo repetido sin tabla previa.")
    (tll, logll), (tof, logof), (tml, logml) = ctx.tablas["ll"], ctx.tablas["of"], ctx.tablas["ml"]
    bits = _BitsAtras(d, p, fin)
    leer = bits.leer
    ell, eof, eml = leer(logll), leer(logof), leer(logml)
    rep = ctx.rep
    lit_pos = 0
    for i in range(nseq):
        cof = tof[eof][0]
        cml = tml[eml][0]
        cll = tll[ell][0]
        valor_of = (1 << cof) + leer(cof)
        ml = _ML_BASE[cml] + leer(_ML_BITS[cml])
        ll = _LL_BASE[cll] + leer(_LL_BITS[cll])
        if valor_of > 3:
            offset = valor_of - 3
            rep = [offset, rep[0], rep[1]]
        else:
            idx = valor_of + (1 if ll == 0 else 0)
            if idx == 1:
                offset = rep[0]
            elif idx == 2:
                offset = rep[1]
                rep = [rep[1], rep[0], rep[2]]
            elif idx == 3:
                offset = rep[2]
                rep = [rep[2], rep[0], rep[1]]
            else:
                offset = rep[0] - 1
                rep = [offset, rep[0], rep[1]]
        if ll:
            salida += literales[lit_pos:lit_pos + ll]
            lit_pos += ll
        n = len(salida)
        if offset <= 0 or offset > n - inicio_trama:
            raise ErrorZstd("Offset Zstandard fuera de rango.")
        ini = n - offset
        if offset >= ml:
            salida += salida[ini:ini + ml]
        else:                                             # copia solapada: se repite el patrón
            patron = salida[ini:n]
            veces, resto = divmod(ml, offset)
            salida += patron * veces + patron[:resto]
        if i != nseq - 1:
            s, nb, base = tll[ell]
            ell = base + leer(nb)
            s, nb, base = tml[eml]
            eml = base + leer(nb)
            s, nb, base = tof[eof]
            eof = base + leer(nb)
    ctx.rep = rep
    salida += literales[lit_pos:]
