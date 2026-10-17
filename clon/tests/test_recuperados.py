# -*- coding: utf-8 -*-
"""«Documentos recuperados» (pendiente 21): lista de autoguardados pendientes, diálogo con Abrir /
Suprimir / Cerrar como el de Fusion, y las herramientas de API para listar y recuperar."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api
from omnicad.io_archivos import proyecto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva

from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def ventana(app_qt, tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    ruta = tmp_path_factory.mktemp("prefs") / "preferencias.ini"
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    v.resize(1280, 800)
    v.show()
    QTest.qWait(1)
    yield v
    v.doc.modificado = False                  # si no, al cerrar pregunta si se descartan los cambios (modal)
    v.close()
    v.deleteLater()
    QTest.qWait(1)


@pytest.fixture
def v(ventana):
    ventana.set_documento(Documento())
    yield ventana


@pytest.fixture()
def carpeta_auto(tmp_path, monkeypatch):
    monkeypatch.setattr(proyecto, "carpeta_autoguardado", lambda: tmp_path)
    return tmp_path


def _crear_autoguardado(doc, ruta, hace_minutos=0):
    proyecto.guardar(doc, ruta)
    mtime = ruta.stat().st_mtime - hace_minutos * 60
    os.utime(ruta, (mtime, mtime))


# ---------------------------------------------------------------- núcleo (sin Qt)
def test_lista_huerfanos_y_recientes_del_mas_nuevo_al_mas_viejo(carpeta_auto):
    _crear_autoguardado(Documento(), carpeta_auto / "sin_titulo_1.autoguardado.omnicad", hace_minutos=30)
    _crear_autoguardado(Documento(), carpeta_auto / "sin_titulo_2.autoguardado.omnicad", hace_minutos=5)
    con_cambios = carpeta_auto / "proyecto.omnicad"
    _crear_autoguardado(Documento(), con_cambios, hace_minutos=30)       # el proyecto guardado hace 30 min
    _crear_autoguardado(Documento(), con_cambios.with_name("proyecto.autoguardado.omnicad"))  # copia nueva
    al_dia = carpeta_auto / "aldia.omnicad"
    _crear_autoguardado(Documento(), al_dia)

    filas = proyecto.pendientes_de_recuperacion([str(con_cambios), str(al_dia),
                                                str(carpeta_auto / "borrado.omnicad")])
    assert [f["name"] for f in filas] == ["proyecto", "Sin título", "Sin título"]
    assert filas[0]["project"] == str(con_cambios)
    assert filas[0]["backup"].endswith("proyecto.autoguardado.omnicad")
    assert filas[1]["backup"].endswith("sin_titulo_2.autoguardado.omnicad")   # del más nuevo al más viejo
    assert filas[2]["backup"].endswith("sin_titulo_1.autoguardado.omnicad")
    assert all(f["date"] and f["folder"] for f in filas)


def test_sin_pendientes_la_lista_es_vacia(carpeta_auto):
    assert proyecto.pendientes_de_recuperacion() == []


# ---------------------------------------------------------------- diálogo
def test_dialogo_tabla_suprimir_y_abrir(app_qt, carpeta_auto):
    from omnicad.ui.dialogos import DialogoRecuperados
    copia1 = carpeta_auto / "sin_titulo_1.autoguardado.omnicad"
    copia2 = carpeta_auto / "sin_titulo_2.autoguardado.omnicad"
    _crear_autoguardado(Documento(), copia1, hace_minutos=30)   # la vieja
    _crear_autoguardado(Documento(), copia2)                   # la nueva (queda primera en la tabla)
    filas = proyecto.pendientes_de_recuperacion()
    assert [f["backup"] for f in filas] == [str(copia2), str(copia1)]
    caja = DialogoRecuperados(filas)
    assert caja.tabla.rowCount() == 2
    assert caja.tabla.item(0, 1).text() == filas[0]["date"]          # fecha de recuperación a la vista
    assert caja.resultado is None
    # Suprimir la primera (la MÁS NUEVA): borra SOLO esa copia y queda la otra en la tabla
    caja.tabla.selectRow(0)
    caja._suprimir()
    assert copia1.exists() and not copia2.exists()
    assert caja.tabla.rowCount() == 1 and caja.b_abrir.isEnabled()
    # Abrir la que queda: el resultado es su fila
    caja.tabla.selectRow(0)
    caja._abrir()
    assert caja.resultado is not None and caja.resultado["backup"] == str(copia1)
    assert copia1.exists()                                          # abrir NO borra la copia


# ---------------------------------------------------------------- ventana
def test_la_ventana_recupera_un_autoguardado_desde_el_dialogo(v, carpeta_auto, monkeypatch):
    copia = carpeta_auto / "sin_titulo_7.autoguardado.omnicad"
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho=30, largo=20, alto=10))
    _crear_autoguardado(doc, copia)
    filas = proyecto.pendientes_de_recuperacion()

    from omnicad.ui import ventana as modulo_ventana

    class _CajaFalsa:
        def __init__(self, filas_recibidas, parent=None):
            assert filas_recibidas[0]["backup"] == str(copia)

        def exec(self):
            return 0

    _CajaFalsa.resultado = property(lambda self: filas[0])
    monkeypatch.setattr(modulo_ventana, "DialogoRecuperados", _CajaFalsa)
    v.verificar_autoguardado_huerfano()
    assert v.doc.ruta is None and v.doc.nombre == "Recuperado" and v.doc.modificado
    assert len(v.doc.operaciones) == 1                       # el contenido de la copia, no un documento vacío
    assert v.doc.resultados[0].estado == "ok"


def test_sin_pendientes_la_ventana_no_abre_ningun_dialogo(v, carpeta_auto, monkeypatch):
    from omnicad.ui import ventana as modulo_ventana

    class _Guardia:
        def __init__(self, *a, **k):
            raise AssertionError("no debería abrirse el diálogo")

    monkeypatch.setattr(modulo_ventana, "DialogoRecuperados", _Guardia)
    v.verificar_autoguardado_huerfano()                      # sin autoguardados: no pasa nada


# ---------------------------------------------------------------- API
def test_api_lista_y_recupera(carpeta_auto):
    copia = carpeta_auto / "sin_titulo_9.autoguardado.omnicad"
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio=5, alto=20))
    _crear_autoguardado(doc, copia)
    original = carpeta_auto / "original.omnicad"
    _crear_autoguardado(Documento(), original, hace_minutos=30)
    _crear_autoguardado(Documento(), original.with_name("original.autoguardado.omnicad"))   # copia más nueva

    r = api.llamar(api.Sesion(), "list_recoverable_documents", {"recent": [str(original)]})
    assert r["ok"]
    pendientes = r["result"]["pending"]
    assert [p["name"] for p in pendientes] == ["Sin título", "original"]   # copia nueva primero

    r = api.llamar(api.Sesion(), "recover_document", {"path": str(copia)})
    assert r["ok"] and r["result"]["name"] == "Recuperado" and len(r["result"]["bodies"]) == 1

    r = api.llamar(api.Sesion(), "recover_document", {"path": str(copia), "project": str(original)})
    assert r["ok"] and r["result"]["name"] == "original"

    r = api.llamar(api.Sesion(), "recover_document", {"path": str(carpeta_auto / "no-hay.omnicad")})
    assert not r["ok"] and r["error_kind"] == "FILE_NOT_FOUND"


def test_api_recover_con_cambios_sin_guardar_pide_confirmar(carpeta_auto):
    copia = carpeta_auto / "sin_titulo_5.autoguardado.omnicad"
    _crear_autoguardado(Documento(), copia)
    sesion = api.Sesion()
    sesion.doc.modificado = True
    r = api.llamar(sesion, "recover_document", {"path": str(copia)})
    assert not r["ok"] and r["error_kind"] == "UNSAVED_CHANGES"
    r = api.llamar(sesion, "recover_document", {"path": str(copia), "discard": True})
    assert r["ok"] and sesion.doc.nombre == "Recuperado"


def test_t15_con_el_puente_la_ventana_avisa_en_vez_de_abrir_el_dialogo_modal(v, carpeta_auto, monkeypatch):
    """Un diálogo modal al arrancar dejaba al puente respondiendo APP_BUSY hasta que alguien hacía clic."""
    from omnicad.ui import ventana as modulo_ventana
    _crear_autoguardado(Documento(), carpeta_auto / "sin_titulo_9.autoguardado.omnicad")

    class _Guardia:
        def __init__(self, *a, **k):
            raise AssertionError("con el puente no se abre el diálogo modal")

    monkeypatch.setattr(modulo_ventana, "DialogoRecuperados", _Guardia)
    v.verificar_autoguardado_huerfano(solo_avisar=True)
    assert "1 documento(s) recuperable(s)" in v.timeline.estado.toolTip()
