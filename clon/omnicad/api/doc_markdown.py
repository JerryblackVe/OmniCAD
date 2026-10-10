# -*- coding: utf-8 -*-
"""
Documentación de las herramientas en Markdown, generada desde el catálogo (`api.catalogo()`).

Es la fuente de `docs/agentes/herramientas.md`: ese archivo no se edita a mano. Para regenerarlo:

    omnicad tools --markdown --output docs/agentes/herramientas.md

Un test (`tests/test_doc_agentes.py`) compara el archivo con lo que genera esta función: si cambia el catálogo
(una herramienta nueva, una descripción, un parámetro) el test falla hasta que se regenera.

Este módulo NO se llama `herramientas_*` a propósito: esos módulos se cargan solos y registran herramientas.
Es una función pura (catálogo → texto): no importa Qt ni el paquete `mcp`.
"""
import json
import re

COMANDO_REGENERAR = "omnicad tools --markdown --output docs/agentes/herramientas.md"

# Orden y descripción corta de cada grupo. Un grupo que no figure acá se documenta igual, al final y sin
# descripción; el test de sincronía exige que todos figuren, así que un grupo nuevo obliga a sumarlo.
GRUPOS = {
    "documento": "Archivo, escena, timeline y deshacer.",
    "parametros": "Medidas con nombre que gobiernan el modelo.",
    "boceto": "Bocetos 2D: geometría, restricciones y cotas.",
    "vectores": "Texto y vectores: fuentes, texto de boceto, SVG, DXF e imágenes vectorizadas.",
    "solido": "Sólidos: extruir, revolucionar, primitivas, empalmes, agujeros y patrones.",
    "chapa": "Chapa metálica: reglas, pestañas, dobladillo, plegar, desplegar, desgarro, patrón plano y DXF.",
    "ensamble": "Ensamble: componentes, uniones, accionar, límites, grupos rígidos, vínculos y estudio de movimiento.",
    "material": "Materiales físicos (densidad para la masa), materiales propios y aspecto de los cuerpos.",
    "inspeccion": "Ver y medir el resultado.",
    "avanzado": "Cualquier operación, receta, código y guía.",
    "grafo": "Programación visual sin ventana (tipo Grasshopper): correr grafos de nodos y hornearlos en el timeline.",
    "dev": "Desarrollo del programa (en el MCP, solo con --dev; en la CLI, `omnicad dev`).",
}

_TIPOS = {"string": "texto", "integer": "entero", "number": "número", "boolean": "true/false",
          "array": "lista", "object": "objeto", "null": "null"}


def _tipo_json(prop):
    """Tipo legible de una propiedad del esquema, sin el `null` (eso se dice en «opcional»)."""
    if "enum" in prop:
        return " | ".join(json.dumps(v, ensure_ascii=False) for v in prop["enum"])
    if "anyOf" in prop:
        partes = [_tipo_json(p) for p in prop["anyOf"]]
        return " o ".join(p for p in partes if p) or "cualquiera"
    tipo = prop.get("type")
    if tipo is None:
        return "cualquiera"
    tipos = [t for t in (tipo if isinstance(tipo, list) else [tipo]) if t != "null"] or ["null"]
    textos = []
    for t in tipos:
        if t == "array" and isinstance(prop.get("items"), dict) and prop["items"]:
            textos.append(f"lista de {_tipo_json(prop['items'])}")
        elif t == "object" and isinstance(prop.get("additionalProperties"), dict) and prop["additionalProperties"]:
            textos.append(f"objeto de {_tipo_json(prop['additionalProperties'])}")
        else:
            textos.append(_TIPOS.get(t, t))
    if set(tipos) == {"number", "string"}:
        return "número o expresión"
    return " o ".join(textos)


def _condicion(nombre, prop, requeridos):
    if nombre in requeridos:
        return "obligatorio"
    return f"opcional, por defecto `{json.dumps(prop.get('default'), ensure_ascii=False)}`"


def _primera_oracion(texto):
    """Primera oración de la descripción (corta en «. » seguido de mayúscula: «p. ej.» no corta)."""
    texto = " ".join(texto.split())
    corte = re.search(r"(?<=[a-záéíóúñ0-9\)\]'])\.\s+(?=[A-ZÁÉÍÓÚ¿¡\"'`])", texto)
    return texto[:corte.start() + 1] if corte else texto


def _celda(texto):
    return texto.replace("|", "\\|")


def _herramienta(h):
    props, req = h["esquema"]["properties"], h["esquema"]["required"]
    lineas = [f"### `{h['nombre']}`", "", h["descripcion"].strip(), ""]
    lineas.append("- Modifica el documento: " + ("sí, es un paso de deshacer." if h["modifica"] else "no."))
    if props:
        lineas.append("- Parámetros:")
        for nombre, prop in props.items():
            texto = f"  - `{nombre}` ({_tipo_json(prop)}; {_condicion(nombre, prop, req)})"
            lineas.append(texto + (f": {prop['description']}" if prop.get("description") else ""))
    else:
        lineas.append("- Parámetros: ninguno.")
    obligatorios = " ".join(f"{n}=…" for n in req)
    lineas.append(f"- CLI: `omnicad call {h['nombre']} --doc pieza.omnicad" + (f" {obligatorios}`" if obligatorios else "`"))
    return lineas + [""]


def catalogo_a_markdown(herramientas):
    """Markdown de `herramientas` (la lista que devuelve `api.catalogo()`): un índice por grupo y una ficha por
    herramienta (descripción, si modifica, parámetros con tipo, obligatoriedad, valor por defecto y su
    descripción). Siempre termina en un salto de línea; usa solo "\\n"."""
    grupos = [g for g in GRUPOS if any(h["grupo"] == g for h in herramientas)]
    grupos += sorted({h["grupo"] for h in herramientas} - set(GRUPOS))
    lineas = [
        f"<!-- ARCHIVO GENERADO: no editar a mano. Regenerar con: {COMANDO_REGENERAR} -->",
        "",
        "# Herramientas de OmniCAD",
        "",
        f"> Archivo generado: no editar a mano. Regenerar con `{COMANDO_REGENERAR}` (desde la raíz del repo).",
        "> Sale del catálogo de `omnicad.api`, la misma fuente del servidor MCP y de la CLI. Un test avisa si queda viejo.",
        "",
        f"{len(herramientas)} herramientas en {len(grupos)} grupos. Unidades: mm y grados. Nombres, parámetros y claves "
        "del resultado en inglés; textos en español.",
        "Cada llamada devuelve `{\"ok\": true, \"result\": ..., \"avisos\": [...]}` o "
        "`{\"ok\": false, \"error_kind\": ..., \"mensaje\": ..., \"pistas\": [...]}`.",
        "",
        "El servidor MCP en modo en vivo o auto suma `get_mode`, que no está en el catálogo (ver `puente.md`).",
        "",
        "| Grupo | Herramientas | Para qué |",
        "|---|---|---|",
    ]
    for g in grupos:
        n = sum(1 for h in herramientas if h["grupo"] == g)
        lineas.append(f"| [{g}](#grupo-{g}) | {n} | {_celda(GRUPOS.get(g, ''))} |")
    lineas.append("")
    for g in grupos:
        delgrupo = [h for h in herramientas if h["grupo"] == g]
        lineas += [f"## Grupo {g}", "", GRUPOS.get(g, ""), "", "| Herramienta | Modifica | Resumen |", "|---|---|---|"]
        for h in delgrupo:
            lineas.append(f"| [`{h['nombre']}`](#{h['nombre']}) | {'sí' if h['modifica'] else 'no'} | "
                          f"{_celda(_primera_oracion(h['descripcion']))} |")
        lineas.append("")
        for h in delgrupo:
            lineas += _herramienta(h)
    return "\n".join(lineas).rstrip("\n") + "\n"
