"""Agrupado con cuatro eventos, dos sesiones y una sesión partida; sin dependencias de OmniCAD."""

from datetime import datetime, timezone
import json
from pathlib import Path
import runpy


registro = runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts/registro_bugs.py"))


def test_agrupado(tmp_path):
    eventos = [
        {"ts": "2026-11-11T09:00:00-03:00", "seq": 1, "tipo": "error", "datos": {
            "comando": "extruir", "mensaje": 'Fallo 12 en "C:\\Mis piezas\\uno.step"',
            "traza": [{"archivo": "omnicad/nucleo/geometria.py", "linea": 20, "funcion": "extruir"}]}},
        {"ts": "2026-11-11T11:00:00+00:00", "seq": 1, "tipo": "error", "datos": {
            "comando": "extruir", "mensaje": 'Fallo 99 en "/tmp/dos.step"'}},
        {"ts": "2026-11-11T12:01:00+00:00", "seq": 2, "tipo": "bloqueo_ui", "datos": {
            "comando": "", "accion": "Preferencias", "duracion_ms": 3001}},
        {"ts": "2026-11-11T12:02:00+00:00", "seq": 3, "tipo": "bloqueo_ui", "datos": {
            "comando": "extruir", "accion": "Preferencias", "duracion_ms": 3000}},
    ]
    for nombre, indices in (("sesion_una_0001.jsonl", [0, 2]),
                            ("sesion_otra_0001.jsonl", [1]), ("sesion_una_0002.jsonl", [3])):
        (tmp_path / nombre).write_text("".join(json.dumps(eventos[i]) + "\n" for i in indices), encoding="utf-8")
    datos = registro["agrupar"](tmp_path)
    assert (datos["archivos"], datos["sesiones"], datos["lineas"]) == (3, 2, 4)
    assert datos["duplicados"] == datos["ocultos"] == 0 and datos["avisos"] == []
    assert len(datos["errores"]) == len(datos["bloqueos"]) == 1
    grupo = datos["errores"][0]
    assert grupo["cantidad"] == 2 and grupo["sesiones"] == {"una", "otra"}
    assert grupo["mensaje"] == "Fallo <n> en <ruta>"
    assert grupo["primera"] == datetime(2026, 11, 11, 11, tzinfo=timezone.utc)
    assert grupo["ultima"] == datetime(2026, 11, 11, 12, tzinfo=timezone.utc)
    assert grupo["ejemplo"]["datos"]["traza"][0]["funcion"] == "extruir"
    bloqueo = datos["bloqueos"][0]
    assert bloqueo["comando"] == "Preferencias" and bloqueo["cantidad"] == 1
    assert bloqueo["maximo_ms"] == 3001
    informe = registro["generar_informe"](datos)
    assert "E01" in informe and "L01" in informe and "geometria.py" in informe
    assert "Fallo &lt;n&gt; en &lt;ruta&gt;" in informe
    assert registro["normalizar_mensaje"]("Indicá mid_x/mid_y") == "Indicá mid_x/mid_y"
    assert registro["normalizar_mensaje"]({"longitud": 22}) == "[mensaje oculto o ausente]"
