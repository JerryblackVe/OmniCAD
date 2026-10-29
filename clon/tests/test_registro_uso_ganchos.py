"""Integración con timeline, archivos y medición A/B del recálculo real."""
import json
import time

import pytest

from omnicad import api, registro_uso as ru


@pytest.fixture(autouse=True)
def aislado(tmp_path, monkeypatch):
    ru.configurar(False)
    monkeypatch.setenv("OMNICAD_REGISTRO_DIR", str(tmp_path / "registro"))
    yield
    ru.configurar(False)
    ru.ultimo = None


def leer():
    ru.activo.cola.join()
    return [json.loads(l) for p in sorted(ru.carpeta().glob("sesion_*.jsonl")) for l in p.read_text(encoding="utf-8").splitlines()]


def test_timeline_archivos_errores_y_privacidad(tmp_path):
    s = api.Sesion()
    ru.configurar(True)
    assert api.llamar(s, "create_box", {"length": 10, "width": 20, "height": 30})["ok"]
    ruta = tmp_path / "SECRETO.omnicad"
    assert api.llamar(s, "save_document", {"path": str(ruta)})["ok"]
    s.doc.deshacer()
    s.doc.rehacer()
    assert api.llamar(s, "open_document", {"path": str(ruta), "discard": True})["ok"]
    assert api.llamar(s, "export", {"path": str(tmp_path / "SECRETO.stl")})["ok"]
    assert not api.llamar(s, "create_box", {"length": "SECRETO"})["ok"]
    es = leer()
    tipos = {e["tipo"] for e in es}
    assert {"op_ejecutada", "recalculo", "deshacer", "rehacer", "archivo_guardar", "archivo_abrir", "exportar", "error"} <= tipos
    op = next(e["datos"] for e in es if e["tipo"] == "op_ejecutada")
    assert op["antes"]["volumen"] == 0
    assert op["despues"]["volumen"] == pytest.approx(6000)
    assert "SECRETO" not in json.dumps(es)


def test_sobrecarga_recalculo_menor_dos_por_ciento():
    from omnicad.ui.bench import documento_grande
    tiempos = {False: [], True: []}
    # Medir el productor, no restar dos kernels ruidosos. La coordinación completa del
    # recálculo se suma como cota conservadora de las listas/dicts del registro en línea.
    for vuelta in range(4):
        for encendido in ((False, True) if vuelta % 2 == 0 else (True, False)):
            ru.configurar(encendido)
            doc = documento_grande(4)
            kernel = [0.0]
            if encendido:
                for op in doc.operaciones:
                    def medir(estado, ctx, calcular=op.calcular, acumulado=kernel):
                        inicio = time.perf_counter()
                        try:
                            return calcular(estado, ctx)
                        finally:
                            acumulado[0] += time.perf_counter() - inicio
                    op.calcular = medir
            inicio = time.perf_counter()
            doc.recalcular()
            t = time.perf_counter() - inicio - kernel[0]
            if vuelta:
                tiempos[encendido].append(t)
            assert all(r.estado in ("ok", "aviso") for r in doc.resultados)
            if ru.activo:
                ru.activo.cola.join()
                assert ru.activo.fallo is None
    apagado, encendido = (min(tiempos[k]) for k in (False, True))
    print(f"recálculo apagado={apagado:.6f}s productor+coordinación={encendido:.6f}s sobrecarga={encendido/apagado*100:.2f}%")
    assert encendido <= apagado * 0.02
