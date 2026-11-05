"""Escritura, privacidad, límites y costo del productor del registro local."""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from omnicad import registro_uso as ru


def eventos(carpeta):
    return [json.loads(l) for p in sorted(carpeta.glob("sesion_*.jsonl")) for l in p.read_text(encoding="utf-8").splitlines()]


@pytest.fixture(autouse=True)
def aislado(tmp_path, monkeypatch):
    ru.configurar(False)
    monkeypatch.setenv("OMNICAD_REGISTRO_DIR", str(tmp_path / "registro"))
    yield
    ru.configurar(False)
    ru.ultimo = None


def test_apagado_no_crea_archivos(tmp_path):
    assert not ru.configurar(False)["enabled"]
    assert not (tmp_path / "registro").exists()


def test_lineas_privadas_ordenadas_y_visibles_en_vivo(tmp_path):
    r = ru.Registro({"proyecto": "C:/privado/pieza.omnicad"}, destino=tmp_path)
    with ThreadPoolExecutor(4) as hilos:
        list(hilos.map(lambda n: r.emitir("comando_aceptado", {"comando": "extruir", "valores": {
            "alto": n, "texto": "SECRETO", "comando": "SECRETO", "categoria": "SECRETO",
            "ruta": "C:/privado/oculto", "chat": "CHAT_SECRETO"}}), range(100)))
    r.cola.join()
    assert len(eventos(tmp_path)) == 101  # flush sin cerrar
    r.cerrar()
    es = eventos(tmp_path)
    assert [e["seq"] for e in es] == list(range(1, 102))
    assert es[0]["tipo"] == "sesion_inicio"
    assert es[0]["datos"]["proyecto"] == "pieza.omnicad"
    texto = "".join(p.read_text(encoding="utf-8") for p in r.archivos)
    assert "CHAT_SECRETO" not in texto and "privado" not in texto   # texto libre y rutas: longitudes
    assert "SECRETO" not in texto                                   # no es una opción de lista fija
    assert es[1]["datos"]["valores"]["texto"] == {"longitud": 7}      # texto libre: solo su largo


def test_rotacion_tope_y_retencion(tmp_path):
    viejo = tmp_path / "sesion_vieja.jsonl"
    viejo.write_bytes(b"{}\n")
    os.utime(viejo, (0, 0))
    r = ru.Registro(destino=tmp_path, tope_total=3000, tope_archivo=800)
    for i in range(50):
        r.emitir("marca", {"valor": i})
    r.cerrar()
    assert not viejo.exists()
    archivos = list(tmp_path.glob("*.jsonl"))
    assert 1 < len(archivos) < 50
    assert sum(p.stat().st_size for p in archivos) <= 3000
    assert all(p.stat().st_size <= 800 for p in archivos)
    assert eventos(tmp_path)[-1]["datos"]["valor"] == 49


def test_api_activacion(tmp_path):
    from omnicad import api
    s = api.Sesion()
    assert api.llamar(s, "set_usage_logging", {"enabled": True})["result"]["enabled"]
    assert ru.activo is not None
    assert not api.llamar(s, "set_usage_logging", {"enabled": False})["result"]["enabled"]
    assert len(eventos(tmp_path / "registro")) == 2


def test_costo_por_evento(tmp_path):
    r = ru.Registro(destino=tmp_path)
    inicio = time.perf_counter()
    for i in range(3000):
        r.emitir("op_ejecutada", {"paso": "op1", "duracion_ms": i, "exito": True})
    ms = (time.perf_counter() - inicio) * 1000 / 3000
    r.cerrar()
    print(f"productor: {ms:.4f} ms/evento")
    assert ms < 0.2
    assert not r.fallo and not r.descartados


def test_entorno_sin_qt():
    import subprocess
    import sys
    codigo = "import sys; from omnicad.registro_uso.sistema import ram_total; assert ram_total() > 0; assert not any(k.startswith('PySide') for k in sys.modules)"
    subprocess.run([sys.executable, "-c", codigo], check=True)


@pytest.mark.parametrize("via", ["atajo", "boton", "menu"])
@pytest.mark.parametrize("origen", ["clave", "objeto"])
def test_b187_las_herramientas_del_boceto_se_registran_con_nombre(tmp_path, via, origen):
    from types import SimpleNamespace
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QAction, QMouseEvent
    from PySide6.QtWidgets import QApplication, QMenu, QToolButton
    from omnicad.ui.registro_uso import RegistroVentana
    app = QApplication.instance() or QApplication([])
    accion = QAction("Texto en ruta")
    esperado = "sk_texto"
    if origen == "clave":
        accion.setProperty("clave", esperado)
        accion.setObjectName("otra_cosa")
    elif origen == "objeto":
        accion.setObjectName(esperado)
    observador = SimpleNamespace(ventana=SimpleNamespace(visor=object()), _ultima_accion="")
    ru.configurar(True)
    menu, boton = QMenu(), QToolButton()
    try:
        if via == "atajo":
            obj, evento, tipo = accion, QEvent(QEvent.Shortcut), "atajo"
        elif via == "boton":
            boton.setDefaultAction(accion)
            obj, tipo = boton, "boton_cinta"
            evento = QMouseEvent(QEvent.MouseButtonPress, QPointF(8, 8), QPointF(8, 8),
                                  Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        else:
            menu.addAction(accion)
            menu.setActiveAction(accion)
            menu.setObjectName("menu_boceto")
            obj, evento, tipo = menu, QEvent(QEvent.MouseButtonRelease), "menu_item"
        assert RegistroVentana.eventFilter(observador, obj, evento) is False
        ru.activo.cola.join()
        datos = [e["datos"] for e in eventos(tmp_path / "registro") if e["tipo"] == tipo]
        assert datos and datos[-1]["accion"] == esperado
        assert observador._ultima_accion == esperado
    finally:
        menu.close()
        boton.close()
        app.processEvents()


def test_b187_todas_las_acciones_reales_del_boceto_tienen_su_clave(tmp_path):
    from types import SimpleNamespace
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication, QMainWindow
    from omnicad.ui.modo_boceto import ModoBoceto
    from omnicad.ui.registro_uso import RegistroVentana
    app = QApplication.instance() or QApplication([])
    ventana = QMainWindow()
    modo = ModoBoceto(ventana)
    observador = SimpleNamespace(ventana=ventana, _ultima_accion="")
    ru.configurar(True)
    try:
        for clave, accion in modo.acciones.items():
            assert accion.property("clave") == clave
            RegistroVentana.eventFilter(observador, accion, QEvent(QEvent.Shortcut))
        ru.activo.cola.join()
        assert [e["datos"]["accion"] for e in eventos(tmp_path / "registro") if e["tipo"] == "atajo"] == list(modo.acciones)
    finally:
        ventana.close()
        ventana.deleteLater()
        app.processEvents()


def test_sano_oculta_tokens_pero_no_rutas_de_codigo_y_abrevia_rutas_de_windows():
    assert ru._sano("Fallo en omnicad/ui/editor_boceto.py cuando x = 5") == "Fallo en omnicad/ui/editor_boceto.py cuando x = 5"
    assert ru._sano("Fallo en omnicad/ui/editor_3d.py con x = 5") == "Fallo en omnicad/ui/editor_3d.py con x = 5"
    assert ru._sano("clave sk-ABCdef1234567890xyz_abc fin") == "clave [token] fin"
    assert ru._sano(r"D:\Clientes\Juan\pieza.step no existe") == "~/pieza.step no existe"


def test_boton_de_la_cinta_sin_clave_ni_nombre_no_usa_su_texto():
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QApplication
    from omnicad.ui.registro_uso import _nombre_accion
    QApplication.instance() or QApplication([])
    accion = QAction("Algo que escribió la persona")
    assert _nombre_accion(accion, con_texto=False) == "" and _nombre_accion(accion) == "Algo que escribió la persona"
