# -*- coding: utf-8 -*-
"""
Pieza de calibración de holguras para impresión 3D, en una función pura (sin Qt ni timeline).

No existe en Fusion 360: es la «tira de tolerancias» que traen Cura y Printables. Sirve para saber qué holgura
radial hay que pedirle a TU impresora y TU material: se imprime, se prueba cuál agujero encaja bien en los pernos y
ese valor es el `print_clearance` de create_hole y create_thread. Para holgura según norma (H7/g6) está
`tolerancias.ajuste` (ISO 286), que no depende de la impresora.

Unidades: mm. Errores: `geo.ErrorGeometria` con el motivo en español.
"""
import math

from . import geometria as geo

CANTIDAD_MAXIMA = 20          # agujeros por pieza: con más, la tira no entra en ninguna cama
PROFUNDIDAD_ETIQUETA = 0.4    # mm de grabado (dos capas de 0,2): la etiqueta se lee sin debilitar la placa


def holguras(holgura_inicial, paso, cantidad):
    """Las holguras radiales (mm) de la tira: holgura_inicial, + paso, + 2·paso… (`cantidad` valores)."""
    return [round(holgura_inicial + i * paso, 6) for i in range(cantidad)]


def _etiquetas(textos, centros_x, y_base, z, alto, altura_texto):
    """Sólido-herramienta con todos los textos (fuente Arial, solo las letras: sin el hueco de la «0»), cada uno
    centrado en su x con la base de las letras en y_base, de `alto` mm hacia +Z desde `z`."""
    from . import perfiles as pf
    letras = []
    for texto, cx in zip(textos, centros_x, strict=True):
        prims = pf.contornos_texto(texto, "Arial", altura_texto)
        geometria = [(p[0], k) + tuple(p[2:]) for k, p in enumerate(prims)]
        caras = pf.letras_de_texto(pf.detectar(geometria, geo.Plano("XY")), {p[1] for p in geometria})
        if not caras:
            raise geo.ErrorGeometria(f"No se pudo dibujar la etiqueta «{texto}».")
        (x0, _, _), (x1, _, _) = geo.caja_envolvente(geo.compuesto([c.cara for c in caras]))
        for c in caras:
            letras.append(geo.trasladar(c.cara, (cx - (x0 + x1) / 2, y_base, z)))
    return geo.extruir(letras, (0, 0, 1), alto)


def pieza_calibracion_holguras(diametro, holgura_inicial=0.1, paso=0.1, cantidad=5, espesor=3.0, etiquetas=True):
    """Pieza de calibración de holguras: una PLACA con `cantidad` agujeros pasantes de Ø diametro + 2·holgura (la
    holgura crece de `holgura_inicial` en `paso`) y un PEINE con los pernos de Ø `diametro` a la misma distancia,
    para probar todos los agujeros de una vez. Con `etiquetas`, cada agujero lleva grabada su holgura radial (la
    misma que se le da a `print_clearance`). Placa y peine quedan lado a lado con la esquina mínima en el origen,
    apoyados en Z = 0, listos para imprimir.

    Equivale a la «tira de tolerancias» de Cura/Printables (Fusion 360 no tiene un comando así).
    Devuelve {"placa", "peine", "holguras", "diametros_agujero", "largo", "ancho_placa", "ancho_peine"}."""
    for valor, que in ((diametro, "El diámetro del perno"), (paso, "El paso de la holgura"), (espesor, "El espesor")):
        if not math.isfinite(valor) or valor < geo.LONGITUD_MINIMA:
            raise geo.ErrorGeometria(f"{que} tiene que ser positivo; recibió {valor:g} mm.")
    if not math.isfinite(holgura_inicial) or holgura_inicial < 0:
        raise geo.ErrorGeometria("La holgura inicial no puede ser negativa.")
    if cantidad != int(cantidad) or not 1 <= cantidad <= CANTIDAD_MAXIMA:
        raise geo.ErrorGeometria(f"La cantidad de agujeros va de 1 a {CANTIDAD_MAXIMA} (llegó {cantidad:g}).")
    cantidad = int(cantidad)
    hs = holguras(holgura_inicial, paso, cantidad)
    d_max = diametro + 2 * hs[-1]
    pared = max(2.0, diametro / 2)                 # material entre agujeros y hasta el borde
    distancia = d_max + pared
    largo = cantidad * distancia + pared
    xs = [pared + d_max / 2 + i * distancia for i in range(cantidad)]
    textos = [f"{h:.4f}".rstrip("0").rstrip(".") or "0" for h in hs]
    alto_texto = min(4.0, 0.9 * (distancia - 0.5) / (0.6 * max(map(len, textos)))) if etiquetas else 0.0
    ancho_placa = 2 * pared + d_max + (pared + alto_texto if etiquetas else 0)
    y_agujero = pared + d_max / 2

    placa = geo.caja(largo, ancho_placa, espesor)
    cortes = [geo.cilindro(diametro / 2 + h, espesor + 2, (x, y_agujero, -1)) for x, h in zip(xs, hs, strict=True)]
    placa = geo.booleano(placa, geo.unir_todos(cortes), "cortar")
    if etiquetas:
        profundidad = min(PROFUNDIDAD_ETIQUETA, espesor / 3)
        tinta = _etiquetas(textos, xs, y_agujero + d_max / 2 + pared, espesor - profundidad, profundidad + 1,
                          alto_texto)
        placa = geo.booleano(placa, tinta, "cortar")

    base = min(espesor, 2.0)                       # el peine es una tira con un perno por agujero
    ancho_peine = diametro + 2 * pared
    pernos = [geo.cilindro(diametro / 2, base + espesor + 1, (x, ancho_peine / 2, 0)) for x in xs]
    peine = geo.unir_todos([geo.caja(largo, ancho_peine, base)] + pernos)
    peine = geo.trasladar(peine, (0, ancho_placa + 5.0, 0))

    for nombre, forma in (("la placa", placa), ("el peine", peine)):
        if not geo.es_valida(forma):
            raise geo.ErrorGeometria(f"El kernel no pudo armar {nombre} con esas medidas.")
    return {"placa": placa, "peine": peine, "holguras": hs, "diametros_agujero": [round(diametro + 2 * h, 6) for h in hs],
            "largo": largo, "ancho_placa": ancho_placa, "ancho_peine": ancho_peine}
