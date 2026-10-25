"""Ayuda de OmniCAD (IA-8): buscar «¿cómo se hace…?» en la documentación LOCAL y devolver fragmentos con su fuente.

Busca en tres lugares, de más a menos seguro: las descripciones del catálogo (siempre), la guía de `api/guia/` (viaja
con la app instalada) y la documentación del repo (`docs/…`, `README.md`), solo si existe: en la app instalada no está.
Nunca en `docs/fusion_docs/` (es de Fusion y pesa 4,4 GB) ni en `docs/agentes/herramientas.md` (es el catálogo
generado: repetiría cada resultado). Puntaje por palabras, con y sin tildes; sin índices ni dependencias.
"""
import re
import unicodedata
from pathlib import Path

from .errores import error
from .registro import catalogo, herramienta

GUIA = Path(__file__).with_name("guia")
RAIZ_REPO = Path(__file__).resolve().parents[3]       # D:\PROGRAMA en el repo; en la app instalada no tiene docs/
DOCS_REPO = ("docs/guia_comandos.md", "docs/agentes/README.md", "docs/agentes/guia_diseno.md", "docs/agentes/cli.md",
             "docs/agentes/conectar.md", "docs/agentes/puente.md", "README.md")
VACIAS = {"como", "hace", "hago", "hacer", "que", "para", "con", "una", "uno", "los", "las", "del", "por", "the",
          "how", "and", "puedo", "quiero", "omnicad", "esto", "eso"}
LARGO_FRAGMENTO = 400
TOPE_CLAVES = 20          # una consulta pegada enorme no recorre la ayuda miles de veces


def _normal(texto):
    """Minúsculas y sin tildes: «Empalme», «empalmé» y «EMPALME» son la misma palabra."""
    sin = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sin if not unicodedata.combining(c))


def _palabras(texto):
    return re.findall(r"[a-z0-9]+", _normal(texto))     # create_hole → create, hole


def _secciones(ruta, fuente):
    """(fuente › título, texto) por cada sección de un .md (cortada en los títulos #, ## y ###)."""
    partes = re.split(r"(?m)^(#{1,3} .*)$", ruta.read_text(encoding="utf-8"))
    yield fuente, partes[0]
    for i in range(1, len(partes), 2):
        titulo = partes[i].lstrip("#").strip()
        yield f"{fuente} › {titulo}", partes[i] + partes[i + 1]


def _documentos():
    for h in catalogo():
        yield f"herramienta {h['nombre']}", f"{h['nombre']}: {h['descripcion']}"
    for ruta in sorted(GUIA.glob("*.md")):
        yield from _secciones(ruta, f"api/guia/{ruta.name}")
    if not (RAIZ_REPO / "clon" / "omnicad").is_dir():     # instalada: parents[3] es otra carpeta, no el repo
        return
    for relativa in DOCS_REPO:
        ruta = RAIZ_REPO / relativa
        if ruta.is_file():
            yield from _secciones(ruta, relativa)


def _fragmento(texto, claves):
    """Un trozo corto alrededor de la primera palabra buscada (sin tildes el texto mide lo mismo: las posiciones sirven)."""
    plano = _normal(texto)
    inicio = min((plano.find(c) for c in claves if c in plano), default=0)
    desde = max(0, inicio - LARGO_FRAGMENTO // 4)
    trozo = " ".join(texto[desde:desde + LARGO_FRAGMENTO].split())
    return ("…" if desde else "") + trozo + ("…" if desde + LARGO_FRAGMENTO < len(texto) else "")


def claves_de(query):
    """Palabras útiles de una consulta (sin las vacías ni las de 1-2 letras, salvo que no quede otra), con tope."""
    claves = [p for p in dict.fromkeys(_palabras(query)) if len(p) > 2 and p not in VACIAS]
    return (claves or [p for p in _palabras(query) if len(p) > 1])[:TOPE_CLAVES]


def puntaje(claves, fuente, texto):
    """Cada palabra buscada que aparece (también como prefijo: «empalm» encuentra «empalmes») suma 10, más sus
    apariciones (hasta 5); en el título o el nombre de la herramienta, 6 más (3 si es solo un prefijo)."""
    palabras = _palabras(texto)
    titulo = set(_palabras(fuente))
    total = 0
    for c in claves:
        veces = sum(1 for p in palabras if p.startswith(c))
        if veces:
            total += 10 + min(veces, 5) + (6 if c in titulo else 3 if any(t.startswith(c) for t in titulo) else 0)
    return total


@herramienta("search_help", "avanzado", "Busca en la ayuda LOCAL de OmniCAD (catálogo de herramientas, guía para "
             "agentes y documentación del repo si está) y devuelve fragmentos cortos con su fuente, para responder "
             "«¿cómo se hace…?» citando de dónde sale. Acepta palabras con o sin tildes, en español o inglés.")
def search_help(sesion, query: str, limit: int = 5):
    """
    query: qué se busca, en pocas palabras (p. ej. "empalme", "agujero roscado", "fillet").
    limit: cuántos resultados como máximo, de 1 a 20.
    """
    claves = claves_de(query)
    if not claves:
        raise error("INVALID_ARGUMENTS", "La consulta está vacía: escribí qué buscás (p. ej. «empalme»).")
    if not 1 <= limit <= 20:
        raise error("INVALID_ARGUMENTS", f"limit fuera de rango: {limit} (va de 1 a 20).")
    resultados = []
    for fuente, texto in _documentos():
        valor = puntaje(claves, fuente, texto)
        if valor:
            resultados.append({"source": fuente, "score": valor, "text": _fragmento(texto, claves)})
    resultados.sort(key=lambda r: (-r["score"], len(r["source"])))   # empate: la fuente más específica
    if not resultados:
        sesion.avisar(f"No hay nada sobre «{query}» en la ayuda local: decilo así, sin inventar.")
    return {"query": query, "results": resultados[:limit]}
