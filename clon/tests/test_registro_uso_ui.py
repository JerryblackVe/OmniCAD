"""Vigilante, privacidad de Qt y encendido/apagado reversible en una ventana real."""
import json
import sys
import time

from PySide6.QtCore import QSettings, qWarning
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import registro_uso as ru
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def test_vigilante_muestras_y_ganchos_reversibles(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("OMNICAD_REGISTRO_DIR", str(tmp_path / "registro"))
    anterior = sys.excepthook
    vistos = []
    monkeypatch.setattr(sys, "excepthook", lambda *args: vistos.append(args))
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat)))
    v.show()
    c = v.registro_uso
    try:
        assert not c.reloj.isActive() and ru.activo is None
        v.prefs["general/registro_uso"] = True
        v.aplicar_preferencias()
        assert c.indicador.isVisible() and c.reloj.isActive()
        time.sleep(0.35)
        QTest.qWait(80)
        qWarning("SECRETO QT C:/datos/privado")
        e = ValueError("SECRETO SLOT")
        sys.excepthook(type(e), e, None)
        c._muestra -= 40                                     # la cadencia de fábrica es 30 s, no 5
        v.visor._cuadros_uso.extend([10, 20, 100])
        c._latido()
        ru.activo.cola.join()
        es = [json.loads(l) for p in ru.carpeta().glob("sesion_*.jsonl") for l in p.read_text(encoding="utf-8").splitlines()]
        assert {"bloqueo_ui", "error", "memoria", "visor_cuadros"} <= {e["tipo"] for e in es}
        volcado = json.dumps(es, ensure_ascii=False)
        assert "SECRETO QT" not in volcado and "privado" not in volcado    # lo que dice Qt: solo su longitud
        assert "SECRETO SLOT" in volcado                       # el texto de una excepción de la app sí se guarda
        assert len(vistos) == 1
        v.prefs["general/registro_uso"] = False
        v.aplicar_preferencias()
        assert not c.reloj.isActive() and not c.indicador.isVisible() and ru.activo is None
        assert sys.excepthook != c._excepcion
        assert v.visor._cuadros_uso is None
        app.processEvents()
    finally:
        c.configurar(False)
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        sys.excepthook = anterior
        ru.ultimo = None


def test_b330_extrusion_con_aviso_abre_para_editar_y_no_cuenta_como_falla(tmp_path, monkeypatch):
    """Un paso con aviso se edita como cualquier otro: el panel abre con el aviso a la vista, Aceptar aplica
    y el registro de uso no anota el aviso como una falla del comando (B-330)."""
    from omnicad.nucleo import geometria as geo
    from omnicad.restricciones import Boceto
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpBoceto, OpExtrusion
    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos.solido import Extruir

    QApplication.instance() or QApplication([])
    monkeypatch.setenv("OMNICAD_REGISTRO_DIR", str(tmp_path / "registro"))
    doc = Documento()
    b = Boceto()
    b.agregar_rectangulo((0, 0), (20, 10))
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", boceto=b))
    perfil = OpExtrusion.referencia_perfil(doc.estado_final.bocetos["op1"].perfiles[0])
    cmd, ctx = Extruir(), ContextoComando(doc)
    valores = {c.clave: c.defecto for c in cmd.campos(ctx)}
    valores.update(perfiles=[hit_desde_ref({"tipo": "perfil", "boceto": "op1", **perfil}, doc.estado_final)],
                   distancia="5 mm")
    doc.agregar(cmd.construir(valores, ctx))
    aviso = "El perfil se re-vinculó con firma parcial (prueba B-330)."
    original = Documento.previsualizar
    monkeypatch.setattr(Documento, "previsualizar", lambda self, *a, **k: (original(self, *a, **k)[0], [aviso]))
    v = VentanaPrincipal(doc, prefs=Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat)))
    v.show()
    try:
        v.prefs["general/registro_uso"] = True
        v.aplicar_preferencias()
        ext = doc.operaciones[-1]
        v.editar_operacion(ext.id)
        QTest.qWait(200)
        panel = v.panel
        assert panel is not None and panel.isVisible() and panel.mensaje.text() == aviso
        panel.aceptar()
        QTest.qWait(200)
        assert v.panel is None
        assert [round(geo.volumen(c.forma)) for c in doc.estado_final.cuerpos.values()] == [1000]
        ru.activo.cola.join()
        es = [json.loads(l) for p in ru.carpeta().glob("sesion_*.jsonl") for l in p.read_text(encoding="utf-8").splitlines()]
        resultados = [e["datos"]["exito"] for e in es if e["tipo"] == "comando_resultado"]
        assert resultados == [True]
        assert not [e for e in es if e["tipo"] == "error" and e["datos"].get("origen") == "comando"]
        assert aviso in [e["datos"]["mensaje"] for e in es if e["tipo"] == "aviso"]   # B-332: va a su propio evento
    finally:
        v.registro_uso.configurar(False)
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        ru.ultimo = None
