# -*- coding: utf-8 -*-
"""INSPECCIONAR › Buscar componentes similares [SLD-FIND-SIMILAR-COMPONENTS], sin Qt: compara la geometría de los
componentes del diseño (sólidos que no se mueven con la posición) y los clasifica en duplicado, muy similar o similar."""
from ..nucleo import analisis as an
from .errores import error
from .registro import herramienta

_ORDEN = {"duplicate": 0, "highly_similar": 1, "similar": 2}


def _firmas(estado):
    """{id de componente: firma} de los componentes con cuerpos sólidos (las mallas y superficies no se comparan)."""
    firmas = {}
    for k in estado.componentes:
        formas = [c.forma for c in estado.cuerpos.values()
                  if (c.componente or "") == k and getattr(c, "tipo", "solido") == "solido"]
        if formas:
            firmas[k] = an.firma_geometrica(formas)
    return firmas


def buscar_similares(estado, componente=None):
    """([{id, name, matches: [{id, name, status}]}], cantidad comparada) para el estado dado. `componente` (id o
    nombre) limita a ese; vacío = todos los que tengan coincidencias. Lanza ErrorAPI si no existe o no tiene sólidos."""
    firmas = _firmas(estado)
    nombre = lambda k: estado.componentes[k].get("nombre") or k  # noqa: E731
    if componente is not None:
        elegido = next((k for k in estado.componentes if componente.casefold() in (k.casefold(), nombre(k).casefold())), None)
        if elegido is None:
            raise error("ENTITY_NOT_FOUND", f"No hay un componente «{componente}».", "get_assembly lista los componentes.")
        if elegido not in firmas:
            raise error("INVALID_ARGUMENTS", f"«{nombre(elegido)}» no tiene cuerpos sólidos: solo se comparan sólidos.")
        pedidos = [elegido]
    else:
        pedidos = list(firmas)
    resultado = []
    for k in pedidos:
        coincidencias = []
        for otro, firma in firmas.items():
            estado_sim = an.similitud(firmas[k], firma) if otro != k else None
            if estado_sim:
                coincidencias.append({"id": otro, "name": nombre(otro), "status": estado_sim})
        coincidencias.sort(key=lambda c: _ORDEN[c["status"]])
        if coincidencias or componente is not None:
            resultado.append({"id": k, "name": nombre(k), "matches": coincidencias})
    return resultado, len(firmas)


@herramienta("find_similar_components", "inspeccion", "Busca componentes con geometría parecida (INSPECCIONAR › Buscar "
             "componentes similares). Compara volumen, área y momentos de inercia, que no cambian al mover o girar la "
             "pieza. Cada coincidencia trae status: duplicate (la misma geometría), highly_similar (hasta 5 % de "
             "diferencia) o similar (hasta 20 %). Sin component devuelve cada componente que tiene coincidencias; "
             "con component, solo las de ese. No cambia el documento.")
def find_similar_components(sesion, component: str | None = None):
    """
    component: id o nombre del componente a comparar; vacío = todos los que tengan coincidencias.
    """
    componentes, comparados = buscar_similares(sesion.doc.estado_final, component)
    return {"components": componentes, "compared": comparados}
