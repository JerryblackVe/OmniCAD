# -*- coding: utf-8 -*-
"""Red de seguridad F0: cobertura, dibujos compartidos y similitud del timeline."""
import importlib.util
import os
import sys
from collections import defaultdict
from pathlib import Path

import pytest

EXCEPCIONES = {}
EXCEPCIONES_COMANDOS = {}

# Distancia = diferencia media de color (RGB) a 24 px sobre blanco (scripts/hoja_iconos.py › distancia). Par más cercano
# hoy (2026-10-26): calcomania/empalme_3d 0.046, desplegar/plegar 0.053, convertir_malla/malla_teselar 0.054. Por debajo de
# 0.04 dos íconos se confunden en el timeline.
UMBRAL = 0.04


@pytest.fixture(scope="module")
def hoja_iconos():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    if sys.platform == "win32":
        os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
    from PySide6.QtWidgets import QApplication

    aplicacion = QApplication.instance() or QApplication([])
    ruta = Path(__file__).resolve().parents[2] / "scripts" / "hoja_iconos.py"
    espec = importlib.util.spec_from_file_location("hoja_iconos_script", ruta)
    modulo = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(modulo)
    yield modulo
    aplicacion.processEvents()


def test_ningun_paso_cae_al_icono_generico(hoja_iconos):
    from omnicad.ui import iconos
    from omnicad.ui.comandos import CATALOGO

    fallos = []
    for clave, nombre in hoja_iconos.pasos():
        if nombre not in iconos.DIBUJOS:
            fallos.append(f"{clave}: dibujo inexistente «{nombre}»")
        elif nombre == "caja" and not (clave in CATALOGO and CATALOGO[clave].ICONO == "caja"):
            fallos.append(f"{clave}: ícono genérico «caja»")
    assert not fallos, "Pasos sin ícono propio:\n" + "\n".join(fallos)


def test_dos_pasos_no_comparten_icono(hoja_iconos):
    grupos = defaultdict(set)
    for clave, nombre in hoja_iconos.pasos():
        grupos[nombre].add(clave)
    compartidos = {frozenset(claves): nombre for nombre, claves in grupos.items() if len(claves) > 1}
    faltantes = set(compartidos) - EXCEPCIONES.keys()
    sobrantes = EXCEPCIONES.keys() - set(compartidos)
    mensajes = [
        f"Sin excepción: {compartidos[claves]} → {', '.join(sorted(claves))}"
        for claves in sorted(faltantes, key=lambda grupo: sorted(grupo))
    ]
    mensajes.extend(
        f"Excepción sobrante (borrarla): {', '.join(sorted(claves))}"
        for claves in sorted(sobrantes, key=lambda grupo: sorted(grupo))
    )
    assert not mensajes, "Dibujos compartidos:\n" + "\n".join(mensajes)


def test_dos_comandos_no_comparten_icono():
    from omnicad.ui.comandos import CATALOGO

    grupos = defaultdict(set)
    for c in CATALOGO.values():
        if c.ICONO:
            grupos[c.ICONO].add(c.CLAVE)
    compartidos = {frozenset(claves): nombre for nombre, claves in grupos.items() if len(claves) > 1}
    faltantes = set(compartidos) - EXCEPCIONES_COMANDOS.keys()
    sobrantes = EXCEPCIONES_COMANDOS.keys() - set(compartidos)
    mensajes = [
        f"Sin excepción: {compartidos[claves]} → {', '.join(sorted(claves))}"
        for claves in sorted(faltantes, key=lambda grupo: sorted(grupo))
    ]
    mensajes.extend(
        f"Excepción sobrante (borrarla): {', '.join(sorted(claves))}"
        for claves in sorted(sobrantes, key=lambda grupo: sorted(grupo))
    )
    mensajes.extend(
        f"Excepción sin motivo: {', '.join(sorted(claves))}"
        for claves, motivo in EXCEPCIONES_COMANDOS.items() if not motivo.strip()
    )
    assert not mensajes, "Íconos de comandos compartidos:\n" + "\n".join(mensajes)


def test_ningun_par_se_confunde_a_24_px(hoja_iconos):
    nombres = {nombre for _, nombre in hoja_iconos.pasos()} - {"caja"}
    cercanos = hoja_iconos.mas_cercanos(nombres)
    fallos = [f"{a}/{b}: {distancia:.9f}" for distancia, a, b in cercanos if distancia < UMBRAL]
    assert cercanos[0][0] >= UMBRAL, f"Pares por debajo de {UMBRAL}:\n" + "\n".join(fallos)


def test_no_hay_dibujos_sin_uso(hoja_iconos):
    assert hoja_iconos.dibujos_sin_uso() == [], "Dibujos que ningún comando, paso ni código usa: conectarlos o borrarlos"
