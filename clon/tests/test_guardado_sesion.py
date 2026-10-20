# -*- coding: utf-8 -*-
"""Guardado, recuperación y alerta de cambios sin guardar (revisión del 2026-10-17): un test por falla hallada.

La referencia es Fusion 360: «¿Guardar los cambios?» con Guardar / No guardar / Cancelar, y «Documentos recuperados»
con Abrir / Suprimir / Cerrar. Nada de lo que se descarta se descarta por accidente (Esc, cerrar la ventana)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api
from omnicad.api import protocolo_puente as proto
from omnicad.io_archivos import proyecto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva

from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox



def _autoguardar(v):
    """El autoguardado escribe en un hilo y avisa por una señal: se espera a los dos."""
    v.autoguardar()
    proyecto.esperar_autoguardado()
    QApplication.processEvents()

@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def ventana(app_qt, tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    carpeta = tmp_path_factory.mktemp("guardado")
    anterior = os.environ.get(proto.VARIABLE_CARPETA)
    os.environ[proto.VARIABLE_CARPETA] = str(carpeta)          # nunca el puente.json real del usuario
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(carpeta / "preferencias.ini"), QSettings.IniFormat)))
    v.resize(1280, 800)
    v.show()
    QTest.qWait(1)
    yield v
    v._puente_sesion = False
    v._aplicar_puente()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)
    if anterior is None:
        os.environ.pop(proto.VARIABLE_CARPETA, None)
    else:
        os.environ[proto.VARIABLE_CARPETA] = anterior


@pytest.fixture
def v(ventana):
    ventana.prefs.q.setValue("recientes", [])               # lo que abrió o guardó un test anterior no cuenta
    ventana.set_documento(Documento())
    yield ventana


@pytest.fixture()
def carpeta_auto(tmp_path, monkeypatch):
    """Las copias de «Sin título» van a una carpeta de prueba; los proyectos, a `tmp_path/proy`."""
    auto = tmp_path / "auto"
    auto.mkdir()
    (tmp_path / "proy").mkdir()
    monkeypatch.setattr(proyecto, "carpeta_autoguardado", lambda: auto)
    return auto


def _doc_con_caja():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho=30, largo=20, alto=10))
    return doc


def _guardar_con_hora(doc, ruta, hace_minutos=0):
    proyecto.guardar(doc, ruta)
    mtime = ruta.stat().st_mtime - hace_minutos * 60
    os.utime(ruta, (mtime, mtime))
    return ruta


def _responder(monkeypatch, v, *respuestas):
    """`v._preguntar` contesta lo dado, en orden (una pregunta de más es un error del test). Devuelve lo preguntado."""
    pendientes, preguntas = list(respuestas), []

    def falsa(texto, botones, detalle="", titulo=""):
        preguntas.append((texto, botones))
        return pendientes.pop(0)

    monkeypatch.setattr(v, "_preguntar", falsa)
    return preguntas


def _dialogo_que_elige(monkeypatch, fila):
    """«Documentos recuperados» falso: «Abrir» sobre `fila` (el diálogo real tiene su propio test)."""
    from omnicad.ui import ventana as modulo_ventana

    class _Caja:
        resultado = fila

        def __init__(self, filas, parent=None):
            pass

        def exec(self):
            return 0

    monkeypatch.setattr(modulo_ventana, "DialogoRecuperados", _Caja)


# ---------------------------------------------------------------- núcleo
def test_suprimir_copia_rechaza_un_proyecto_guardado(carpeta_auto, tmp_path):
    """Suprimir borra SOLO copias de autoguardado: un proyecto o cualquier archivo que llegue por error no se toca."""
    guardado = _guardar_con_hora(Documento(), tmp_path / "proy" / "valioso.omnicad")
    with pytest.raises(proyecto.ErrorProyecto):
        proyecto.suprimir_copia(guardado)
    assert guardado.exists()
    copia = _guardar_con_hora(Documento(), carpeta_auto / "sin_titulo_1.autoguardado.omnicad")
    proyecto.suprimir_copia(copia)
    assert not copia.exists()
    proyecto.suprimir_copia(copia)                              # ya no está: no falla


def test_borrar_autoguardado_no_falla_si_el_archivo_esta_bloqueado(carpeta_auto, monkeypatch):
    """Un guardado que salió bien no puede terminar en error porque el antivirus tiene tomada la copia vieja."""
    from pathlib import Path
    doc = Documento()
    proyecto.autoguardar(doc)

    def bloqueado(self, missing_ok=False):
        raise PermissionError("en uso")

    monkeypatch.setattr(Path, "unlink", bloqueado)
    proyecto.borrar_autoguardado(doc)                           # no lanza


def test_abrir_recuperado_huerfano_hereda_el_token_de_la_copia(carpeta_auto):
    copia = _guardar_con_hora(_doc_con_caja(), carpeta_auto / "sin_titulo_ab12cd34.autoguardado.omnicad")
    doc = proyecto.abrir_recuperado(copia)
    assert doc.token == "ab12cd34" and doc.ruta is None and doc.nombre == "Recuperado" and doc.modificado
    assert proyecto.ruta_autoguardado(doc) == copia
    assert len(doc.operaciones) == 1


# ---------------------------------------------------------------- «¿Guardar los cambios?»
def test_preguntar_con_esc_elige_cancelar(v, monkeypatch):
    """Esc o la X de la ventana no pueden elegir «No guardar»: el último botón (Cancelar) es la salida."""
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)    # sin botón apretado: como cerrar la ventana
    assert v._preguntar("¿Guardar?", ("Guardar", "No guardar", "Cancelar")) == 2


def test_confirmar_descartar_guardar_no_guardar_y_cancelar(v, carpeta_auto, monkeypatch):
    sin_cambios = _responder(monkeypatch, v)
    assert v._confirmar_descartar() is True and not sin_cambios          # nada que preguntar
    v.doc.agregar(OpPrimitiva(v.doc.nuevo_id(), forma="caja", ancho=10, largo=10, alto=10))
    _autoguardar(v)
    copia = proyecto.ruta_autoguardado(v.doc)
    assert copia.exists()

    preguntas = _responder(monkeypatch, v, 2)                            # Cancelar: sigue todo como estaba
    assert v._confirmar_descartar() is False
    assert v.doc.modificado and copia.exists()
    assert "Sin título" in preguntas[0][0] and preguntas[0][1] == ("Guardar", "No guardar", "Cancelar")

    _responder(monkeypatch, v, 1)                                        # No guardar: se pierde y se borra la copia
    assert v._confirmar_descartar() is True
    assert not copia.exists()

    monkeypatch.setattr(v, "guardar", lambda: True)
    _responder(monkeypatch, v, 0)                                        # Guardar: sigue lo que diga guardar()
    assert v._confirmar_descartar() is True


# ---------------------------------------------------------------- abrir un proyecto con autoguardado más nuevo
def test_abrir_proyecto_con_autoguardado_cancelar_y_las_dos_opciones(v, carpeta_auto, tmp_path, monkeypatch):
    proy = _guardar_con_hora(Documento(), tmp_path / "proy" / "p.omnicad", hace_minutos=30)
    copia = proy.with_name("p.autoguardado.omnicad")

    def poner_copia():
        _guardar_con_hora(_doc_con_caja(), copia)

    poner_copia()
    antes = v.doc
    _responder(monkeypatch, v, 2)                                        # Cancelar (o Esc): no abre ni borra nada
    v.abrir_ruta(str(proy))
    assert v.doc is antes and copia.exists()

    _responder(monkeypatch, v, 0)                                        # abrir el autoguardado: con sus cambios
    v.abrir_ruta(str(proy))
    assert v.doc.modificado and len(v.doc.operaciones) == 1 and v.doc.ruta == str(proy)
    assert copia.exists()                                                # sigue hasta que se guarda

    v.set_documento(Documento())
    preguntas = _responder(monkeypatch, v, 1)                            # abrir el guardado y descartar la copia
    v.abrir_ruta(str(proy))
    assert not v.doc.modificado and not v.doc.operaciones and not copia.exists()
    assert "descartar" in preguntas[0][1][1]                             # el botón dice lo que hace


def test_abrir_con_el_puente_no_abre_ningun_dialogo_modal(v, carpeta_auto, tmp_path, monkeypatch):
    """`OmniCAD.py proyecto.omnicad --puente`: preguntar dejaría al puente respondiendo APP_BUSY hasta un clic."""
    proy = _guardar_con_hora(Documento(), tmp_path / "proy" / "w.omnicad", hace_minutos=30)
    copia = _guardar_con_hora(_doc_con_caja(), proy.with_name("w.autoguardado.omnicad"))
    preguntas = _responder(monkeypatch, v)                               # cualquier pregunta sería un error
    v.abrir_ruta(str(proy), preguntar=False)
    assert not preguntas and v.doc.ruta == str(proy) and not v.doc.modificado and copia.exists()
    assert "autoguardado más nuevo" in v.timeline.estado.toolTip()


# ---------------------------------------------------------------- Documentos recuperados
def test_recuperar_un_huerfano_y_guardarlo_borra_la_copia_vieja(v, carpeta_auto, tmp_path, monkeypatch):
    """Antes de la corrección el recuperado tenía un token nuevo: al guardar se borraba SU autoguardado y la
    copia original quedaba, y «Documentos recuperados» volvía a ofrecerla en cada arranque."""
    copia = _guardar_con_hora(_doc_con_caja(), carpeta_auto / "sin_titulo_ab12cd34.autoguardado.omnicad")
    _dialogo_que_elige(monkeypatch, proyecto.pendientes_de_recuperacion()[0])
    v.verificar_autoguardado_huerfano()
    assert v.doc.nombre == "Recuperado" and v.doc.modificado and v.doc.token == "ab12cd34"
    assert v._guardar_en(str(tmp_path / "proy" / "recuperado.omnicad"))
    assert not copia.exists()
    assert proyecto.pendientes_de_recuperacion() == []
    assert not v.doc.modificado and "*" not in v.windowTitle()


def test_recuperar_pregunta_antes_de_pisar_un_documento_con_cambios(v, carpeta_auto, monkeypatch):
    """Archivo › Recuperar documentos reemplazaba el documento abierto sin preguntar: se perdía el trabajo."""
    copia = _guardar_con_hora(_doc_con_caja(), carpeta_auto / "sin_titulo_77.autoguardado.omnicad")
    _dialogo_que_elige(monkeypatch, proyecto.pendientes_de_recuperacion()[0])
    v.doc.agregar(OpPrimitiva(v.doc.nuevo_id(), forma="cilindro", radio=5, alto=20))
    abierto = v.doc

    _responder(monkeypatch, v, 2)                                        # Cancelar: queda lo que había
    v.verificar_autoguardado_huerfano()
    assert v.doc is abierto and copia.exists()

    preguntas = _responder(monkeypatch, v, 1)                            # No guardar: ahora sí entra el recuperado
    v.verificar_autoguardado_huerfano()
    assert v.doc is not abierto and v.doc.nombre == "Recuperado" and len(preguntas) == 1


def test_la_copia_del_documento_abierto_no_se_ofrece_como_recuperable(v, carpeta_auto, monkeypatch):
    from omnicad.ui import ventana as modulo_ventana

    class _Guardia:
        def __init__(self, *a, **k):
            raise AssertionError("la copia del documento que está abierto no es «recuperable»")

    monkeypatch.setattr(modulo_ventana, "DialogoRecuperados", _Guardia)
    v.doc.agregar(OpPrimitiva(v.doc.nuevo_id(), forma="caja", ancho=10, largo=10, alto=10))
    _autoguardar(v)
    assert proyecto.ruta_autoguardado(v.doc).exists()
    v.verificar_autoguardado_huerfano()                                  # solo está la suya: no abre el diálogo


def test_el_dialogo_suprime_solo_copias(app_qt, carpeta_auto, tmp_path, monkeypatch):
    from omnicad.ui.dialogos import DialogoRecuperados
    errores = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *a: errores.append(a[2]))      # modal: se anota, no se abre
    guardado = _guardar_con_hora(Documento(), tmp_path / "proy" / "intocable.omnicad")
    caja = DialogoRecuperados([{"backup": str(guardado), "name": "x", "date": "2026-10-17 10:00",
                                "folder": str(guardado.parent), "project": None}])
    caja.tabla.selectRow(0)
    caja._suprimir()
    assert guardado.exists() and "no es una copia de autoguardado" in errores[0]   # un proyecto no se borra


# ---------------------------------------------------------------- autoguardado
def test_un_autoguardado_que_falla_avisa_una_sola_vez(v, monkeypatch):
    avisos = []
    monkeypatch.setattr(v, "mensaje", lambda texto, ms=0: avisos.append(texto))

    def sin_espacio(*_a, **_k):
        raise OSError("disco lleno")

    monkeypatch.setattr(proyecto, "_escribir", sin_espacio)
    v.doc.modificado = True
    _autoguardar(v)
    _autoguardar(v)
    assert len([a for a in avisos if "No se pudo autoguardar" in a]) == 1 and "disco lleno" in avisos[0]


def test_no_autoguarda_mientras_corre_codigo_de_un_agente(v, carpeta_auto):
    """B-16: el latido de execute_code procesa eventos de Qt; el temporizador no guarda un estado a medio aplicar."""
    assert v.encender_puente()
    v.doc.agregar(OpPrimitiva(v.doc.nuevo_id(), forma="caja", ancho=10, largo=10, alto=10))
    v.puente.sesion.latido = lambda: False
    try:
        v.autoguardar()
        proyecto.esperar_autoguardado()
        assert not proyecto.ruta_autoguardado(v.doc).exists()
    finally:
        v.puente.sesion.latido = None
    v.autoguardar()
    proyecto.esperar_autoguardado()     # el ZIP se escribe en un hilo
    assert proyecto.ruta_autoguardado(v.doc).exists()


# ---------------------------------------------------------------- puente (agentes)
def test_guardar_por_el_puente_deja_el_titulo_la_copia_y_los_recientes_al_dia(v, carpeta_auto, tmp_path):
    """save_document por el puente dejaba el «*» en el título, el autoguardado en disco y los recientes sin la ruta."""
    assert v.encender_puente()
    v.doc.agregar(OpPrimitiva(v.doc.nuevo_id(), forma="caja", ancho=10, largo=10, alto=10))
    _autoguardar(v)
    copia = proyecto.ruta_autoguardado(v.doc)
    assert copia.exists() and "*" in v.windowTitle()
    destino = tmp_path / "proy" / "agente.omnicad"
    r = v.puente.ejecutar("save_document", {"path": str(destino)})
    assert r["ok"], r
    assert not copia.exists() and "*" not in v.windowTitle() and not v.doc.modificado
    assert any(str(destino.resolve()) == str(x) for x in v.prefs.recientes())


def test_descartar_por_el_puente_borra_la_copia_del_documento_descartado(v, carpeta_auto):
    assert v.encender_puente()
    v.doc.agregar(OpPrimitiva(v.doc.nuevo_id(), forma="caja", ancho=10, largo=10, alto=10))
    _autoguardar(v)
    copia = proyecto.ruta_autoguardado(v.doc)
    assert copia.exists()
    r = v.puente.ejecutar("new_document", {"discard": True})
    assert r["ok"], r
    assert not copia.exists() and proyecto.pendientes_de_recuperacion() == []


# ---------------------------------------------------------------- herramientas MCP / CLI
def test_discard_recoverable_document_borra_solo_la_copia(carpeta_auto, tmp_path):
    guardado = _guardar_con_hora(Documento(), tmp_path / "proy" / "intocable.omnicad")
    copia = _guardar_con_hora(Documento(), carpeta_auto / "sin_titulo_5.autoguardado.omnicad")
    sesion = api.Sesion()
    r = api.llamar(sesion, "discard_recoverable_document", {"path": str(guardado)})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS" and guardado.exists()
    r = api.llamar(sesion, "discard_recoverable_document", {"path": str(carpeta_auto / "sin_titulo_9.autoguardado.omnicad")})
    assert not r["ok"] and r["error_kind"] == "FILE_NOT_FOUND"
    r = api.llamar(sesion, "discard_recoverable_document", {"path": str(copia)})
    assert r["ok"] and r["result"]["discarded"] == str(copia) and not copia.exists()
    assert api.llamar(sesion, "list_recoverable_documents", {})["result"]["pending"] == []


def test_recover_document_huerfano_guarda_y_la_copia_desaparece(carpeta_auto, tmp_path):
    copia = _guardar_con_hora(_doc_con_caja(), carpeta_auto / "sin_titulo_abc123.autoguardado.omnicad")
    sesion = api.Sesion()
    assert api.llamar(sesion, "recover_document", {"path": str(copia)})["ok"]
    assert sesion.doc.token == "abc123" and sesion.doc.modificado
    assert proyecto.ruta_autoguardado(sesion.doc) == copia


def test_open_document_avisa_si_el_proyecto_tiene_un_autoguardado_mas_nuevo(carpeta_auto, tmp_path):
    proy = _guardar_con_hora(Documento(), tmp_path / "proy" / "q.omnicad", hace_minutos=30)
    _guardar_con_hora(_doc_con_caja(), proy.with_name("q.autoguardado.omnicad"))
    r = api.llamar(api.Sesion(), "open_document", {"path": str(proy), "summary": True})
    assert r["ok"] and any("autoguardado" in a for a in r["avisos"])


# ---------------------------------------------------------------- revisión ponytail (2026-10-17)
def test_abrir_el_guardado_no_borra_la_copia_si_el_guardado_no_abre(v, carpeta_auto, tmp_path, monkeypatch):
    """La copia era lo único sano: se descarta recién cuando el guardado abrió bien."""
    proy = tmp_path / "proy" / "roto.omnicad"
    proy.write_bytes(b"esto no es un zip")
    os.utime(proy, (proy.stat().st_mtime - 3600, proy.stat().st_mtime - 3600))
    copia = _guardar_con_hora(_doc_con_caja(), proy.with_name("roto.autoguardado.omnicad"))
    errores = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *a: errores.append(a[2]))
    _responder(monkeypatch, v, 1)                                        # «Abrir el guardado y descartar la copia»
    v.abrir_ruta(str(proy))
    assert errores and copia.exists()


def test_recuperar_por_el_puente_la_copia_del_documento_abierto_no_la_borra(v, carpeta_auto):
    """El documento abierto y el recuperado comparten la copia: descartar el viejo no puede borrar la del nuevo."""
    assert v.encender_puente()
    v.doc.agregar(OpPrimitiva(v.doc.nuevo_id(), forma="caja", ancho=10, largo=10, alto=10))
    _autoguardar(v)
    copia = proyecto.ruta_autoguardado(v.doc)
    r = v.puente.ejecutar("recover_document", {"path": str(copia), "discard": True})
    assert r["ok"], r
    assert copia.exists() and proyecto.ruta_autoguardado(v.doc) == copia
