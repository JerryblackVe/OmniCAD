# -*- coding: utf-8 -*-
"""Texto de medidas de lo elegido para la barra de abajo a la derecha, como Fusion:
"1 Cara | Área: 3892.358 mm^2", "1 Arista | Longitud: 100.000 mm", "1 Perfil | Área: 1341.141 mm^2"."""
from ..nucleo import geometria as geo

NOMBRES = {"cara": ("Cara", "Caras"), "arista": ("Arista", "Aristas"), "vertice": ("Vértice", "Vértices"),
           "cuerpo": ("Cuerpo", "Cuerpos"), "perfil": ("Perfil", "Perfiles"),
           "curva_boceto": ("Curva de boceto", "Curvas de boceto"), "punto_boceto": ("Punto de boceto", "Puntos de boceto"),
           "plano": ("Plano", "Planos"), "eje": ("Eje", "Ejes"), "punto": ("Punto", "Puntos"),
           "boceto": ("Boceto", "Bocetos")}


def _forma(hit, estado):
    if hit.get("forma") is not None:
        return hit["forma"]
    if hit["tipo"] == "cuerpo" and estado is not None:
        cuerpo = estado.cuerpos.get(hit["ref"].get("cuerpo"))
        return cuerpo.forma if cuerpo is not None else None
    return None


def texto_medidas(hits, estado=None):
    """Resumen de la selección; "" si no hay nada elegido."""
    if not hits:
        return ""
    tipos = {h["tipo"] for h in hits}
    n = len(hits)
    if len(tipos) > 1:
        return f"{n} objetos"
    tipo = tipos.pop()
    singular, plural = NOMBRES.get(tipo, (tipo, tipo))
    cabecera = f"{n} {singular if n == 1 else plural}"
    formas = [_forma(h, estado) for h in hits]
    if any(f is None for f in formas):
        return cabecera
    try:
        if tipo in ("cara", "perfil"):
            return f"{cabecera} | Área: {sum(geo.area(f) for f in formas):.3f} mm^2"
        if tipo in ("arista", "curva_boceto"):
            return f"{cabecera} | Longitud: {sum(geo.longitud(f) for f in formas):.3f} mm"
        if tipo == "cuerpo":
            return f"{cabecera} | Volumen: {sum(geo.volumen(f) for f in formas):.3f} mm^3"
    except Exception:  # noqa: BLE001 — una medida que no se puede calcular no debe romper la selección
        return cabecera
    if tipo in ("vertice", "punto") and n == 1 and hits[0].get("punto") is not None:
        x, y, z = (float(c) for c in hits[0]["punto"])
        return f"{cabecera} | Posición: {x:.3f}, {y:.3f}, {z:.3f} mm"
    return cabecera
