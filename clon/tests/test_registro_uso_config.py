"""Preferencias › Registro de uso: campo rojo con rango, sin guardar inválidos, rigen al aceptar sin reiniciar."""
import json
import os
import time

import pytest

from omnicad import registro_uso as ru


@pytest.fixture(autouse=True)
def aislado(tmp_path, monkeypatch):
    ru.configurar(False)
    ru.aplicar(ru.FABRICA)
    monkeypatch.setenv("OMNICAD_REGISTRO_DIR", str(tmp_path / "registro"))
    monkeypatch.setenv("OMNICAD_AJUSTES_INI", str(tmp_path / "prefs.ini"))
    yield
    ru.configurar(False)
    ru.ultimo = None
    ru.aplicar(ru.FABRICA)


@pytest.fixture
def ventana(tmp_path):
    from PySide6.QtCore import QSettings
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    app = QApplication.instance() or QApplication([])
    prefs = Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat))
    v = VentanaPrincipal(prefs=prefs)
    v.resize(800, 520)
    v.show()
    QTest.qWait(1)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def _dialogo(ventana):
    """El diálogo como lo abre la ventana: Aplicar/Aceptar avisan a aplicar_preferencias."""
    from omnicad.ui.preferencias import DialogoPreferencias
    dlg = DialogoPreferencias(ventana.prefs, ventana, "registro")
    dlg.aplicado.connect(ventana.aplicar_preferencias)
    return dlg


def test_la_pagina_registro_existe_con_sus_campos(ventana):
    dlg = _dialogo(ventana)
    try:
        for clave in ("general/registro_uso", "registro/detallado", "registro/captura_error",
                      "registro/retencion_dias", "registro/tope_total_mb", "registro/tope_capturas_mb",
                      "registro/disco_libre_min_gb", "registro/memoria_cada_s"):
            assert clave in dlg.controles, clave
        for clave in ("registro/retencion_dias", "registro/tope_total_mb", "registro/tope_capturas_mb",
                      "registro/disco_libre_min_gb", "registro/memoria_cada_s"):
            c = dlg.controles[clave]
            assert c.toolTip() and c.whatsThis(), clave           # tooltip y ayuda de una línea
        assert dlg.b_abrir_carpeta_registro.text() == "Abrir carpeta"
        assert dlg.b_podar_registro.text() == "Borrar registros viejos ahora"
        assert dlg.b_fabrica_registro.text() == "Volver a valores de fábrica"
        assert "Ocupa" in dlg.estado_registro.text()
    finally:
        dlg.deleteLater()


def test_rojo_por_rango_y_no_se_guarda_lo_invalido(ventana):
    from PySide6.QtTest import QTest
    dlg = _dialogo(ventana)
    try:
        campo = dlg.controles["registro/retencion_dias"]
        QTest.keyClicks(campo, "200")
        assert not dlg.b_aplicar.isEnabled()                      # nunca se guarda un valor inválido
        assert "1 a 90" in campo.styleSheet() + campo.toolTip() + campo.whatsThis()
        campo.clear()
        QTest.keyClicks(campo, "15")
        assert dlg.b_aplicar.isEnabled()
        dlg.b_aplicar.click()
        assert ventana.prefs["registro/retencion_dias"] == 15
        assert ru.VALORES["retencion_dias"] == 15
        tot, cap = dlg.controles["registro/tope_total_mb"], dlg.controles["registro/tope_capturas_mb"]
        tot.clear()
        QTest.keyClicks(tot, "20")                                # el total baja por debajo de las capturas
        assert not cap.valido() and not dlg.b_aplicar.isEnabled()  # las capturas nunca pasan del total
        assert "tope total" in cap.toolTip()
        tot.clear()
        QTest.keyClicks(tot, "150")
        assert cap.valido()
        dec = dlg.controles["registro/disco_libre_min_gb"]
        dec.clear()
        QTest.keyClicks(dec, "0,2")
        assert not dlg.b_aplicar.isEnabled()
        dec.clear()
        QTest.keyClicks(dec, "2,5")
        dlg.b_aceptar.click()
        assert ventana.prefs["registro/disco_libre_min_gb"] == pytest.approx(2.5)
    finally:
        dlg.deleteLater()


def test_los_valores_nuevos_rigen_sin_reiniciar_y_podan(ventana):
    from PySide6.QtTest import QTest
    ventana.prefs["general/registro_uso"] = True
    ventana.aplicar_preferencias()
    assert ru.activo is not None
    viejo = ru.carpeta() / "sesion_vieja_vieja_0001.jsonl"
    viejo.write_bytes(b"{}\n")
    t = time.time() - 20 * 86400
    os.utime(viejo, (t, t))
    dlg = _dialogo(ventana)
    try:
        campo = dlg.controles["registro/retencion_dias"]
        campo.clear()
        QTest.keyClicks(campo, "3")
        assert dlg.b_aplicar.isEnabled()
        dlg.b_aceptar.click()
    finally:
        dlg.deleteLater()
    assert ru.VALORES["retencion_dias"] == 3
    assert not viejo.exists()                                     # se podó en ese momento
    assert ru.activo.retencion == 3 * 86400                       # la sesión en curso ya lo usa
    ventana.prefs["general/registro_uso"] = False
    ventana.aplicar_preferencias()


def test_memoria_y_cuadros_solo_cada_30s_o_al_moverse_5_por_ciento(ventana, monkeypatch):
    rss = [1000.0]
    import omnicad.ui.bench as bench
    monkeypatch.setattr(bench, "memoria_mb", lambda: (rss[0], 0))
    ventana.prefs["general/registro_uso"] = True
    ventana.aplicar_preferencias()
    c = ventana.registro_uso
    try:
        c._muestra = time.perf_counter() - 40
        rss[0] = 1001.0                                            # +0,1 %: no alcanza el 5 %
        c._latido()
        c._latido()
        ru.activo.cola.join()
        tipos = [e["tipo"] for e in eventos(ru.carpeta())]
        assert tipos.count("memoria") == 1
        rss[0] = 1200.0                                            # +20 %: mide aunque no pasen los 30 s
        c._latido()
        ru.activo.cola.join()
        assert len([e for e in eventos(ru.carpeta()) if e["tipo"] == "memoria"]) == 2
    finally:
        ventana.prefs["general/registro_uso"] = False
        ventana.aplicar_preferencias()


def eventos(carpeta):
    return [json.loads(l) for p in sorted(carpeta.glob("sesion_*.jsonl")) for l in p.read_text(encoding="utf-8").splitlines()]


def test_capta_png_del_visor_en_cada_error_con_el_detalizado(ventana, monkeypatch):
    """Error de la app con el detallado prendido: mensaje completo, traza y una captura del visor."""
    import sys
    from PySide6.QtTest import QTest
    ventana.prefs["general/registro_uso"] = True
    ventana.prefs["registro/detallado"] = True
    ventana.prefs["registro/captura_error"] = True
    ventana.aplicar_preferencias()
    anterior = sys.excepthook
    try:
        monkeypatch.setattr(type(ventana.visor), "captura_png",
                            lambda self, ancho=320: b"PNGfake" + b"x" * 50, raising=False)
        try:
            raise ValueError("El resultado quedó vacío: la herramienta no se interseca con Caja")
        except ValueError as e:
            sys.excepthook(type(e), e, e.__traceback__)           # la excepción de un slot, como en la app real
        QTest.qWait(300)                                          # el latido toma la foto que el registro pidió
        ru.activo.cola.join()
        pngs = list(ru.carpeta().glob("error_*.png"))
        assert pngs and pngs[0].read_bytes().startswith(b"PNGfake")
        assert pngs[0].name.startswith(f"error_{ru.activo.id}_")     # la captura lleva el número del error
        es = [x for x in eventos(ru.carpeta()) if x["tipo"] == "error" and x["datos"].get("origen") == "qt_slot"]
        assert es and es[-1]["datos"]["mensaje"].startswith("El resultado quedó vacío")
        assert es[-1]["datos"]["traza"] and "archivo" in es[-1]["datos"]["traza"][-1]
        assert es[-1]["datos"]["traza"][-1]["archivo"].startswith("tests/")
    finally:
        sys.excepthook = anterior
        ventana.prefs["general/registro_uso"] = False
        ventana.prefs["registro/detallado"] = False
        ventana.prefs["registro/captura_error"] = False
        ventana.aplicar_preferencias()
        for p in ru.carpeta().glob("error_*.png"):
            p.unlink()


def test_sin_detalizado_no_hay_captura(ventana, monkeypatch):
    from PySide6.QtCore import qCritical
    ventana.prefs["general/registro_uso"] = True
    ventana.aplicar_preferencias()
    try:
        monkeypatch.setattr(type(ventana.visor), "captura_png", lambda self, ancho=320: b"\x89PNG", raising=False)
        qCritical("sin detallado")
        ru.activo.cola.join()
        assert not list(ru.carpeta().glob("error_*.png"))
    finally:
        ventana.prefs["general/registro_uso"] = False
        ventana.aplicar_preferencias()


def test_el_vigilante_poda_cada_hora(ventana, monkeypatch):
    """El latido llama a la poda horaria (al arrancar ya se podó en Registro.__init__)."""
    llamadas = []
    monkeypatch.setattr(ru, "toca_podar", lambda: True)
    monkeypatch.setattr(ru, "marcar_podar", lambda: None)
    monkeypatch.setattr(ru, "podar", lambda *a, **k: llamadas.append(1) or 0)
    ventana.prefs["general/registro_uso"] = True
    ventana.aplicar_preferencias()
    try:
        ventana.registro_uso._latido()
        assert llamadas                                   # el latido llama la poda horaria
    finally:
        ventana.prefs["general/registro_uso"] = False
        ventana.aplicar_preferencias()
