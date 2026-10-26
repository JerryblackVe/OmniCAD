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
            "alto": n, "texto": "SECRETO", "ruta": "C:/privado/oculto", "chat": "CHAT_SECRETO"}}), range(100)))
    r.cola.join()
    assert len(eventos(tmp_path)) == 101  # flush sin cerrar
    r.cerrar()
    es = eventos(tmp_path)
    assert [e["seq"] for e in es] == list(range(1, 102))
    assert es[0]["tipo"] == "sesion_inicio"
    assert es[0]["datos"]["proyecto"] == "pieza.omnicad"
    texto = "".join(p.read_text(encoding="utf-8") for p in r.archivos)
    assert "SECRETO" not in texto and "privado" not in texto and "CHAT_" not in texto
    assert es[1]["datos"]["valores"]["texto"] == {"longitud": 7}


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
