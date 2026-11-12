"""`scripts/probar_todo.py`: orden de los pasos, un fallo no corta el resto, `seguir` e informe."""
import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "probar_todo.py"
ESPEC = importlib.util.spec_from_file_location("probar_todo", SCRIPT)
probar_todo = importlib.util.module_from_spec(ESPEC)
ESPEC.loader.exec_module(probar_todo)


def _falso(codigo=0, texto="salio ok"):
    """Comando falso: imprime un texto y termina con el código dado."""
    return [sys.executable, "-c", f"print({texto!r}); raise SystemExit({codigo})"]


def _marca(ruta):
    """Comando falso que deja un archivo: sirve para ver si el paso se repite."""
    return [sys.executable, "-c", f"open({str(ruta)!r}, 'w').write('x')"]


def test_el_modo_rapido_pone_caza_rapida_y_tests_afectados_en_ese_orden():
    nombres = [nombre for nombre, _ in probar_todo.pasos("rapido", 6)]
    assert nombres == ["caza_rapida", "tests_afectados"]


def test_el_modo_noche_pone_registro_caza_y_cierre_en_ese_orden():
    nombres = [nombre for nombre, _ in probar_todo.pasos("noche", 3)]
    assert nombres == ["registro_bugs", "caza_noche", "cierre_completo"]   # el cierre ya corre todo.py: la ventana no va dos veces


def test_la_caza_de_noche_recibe_las_horas_pedidas():
    comandos = dict(probar_todo.pasos("noche", 3))
    comando = comandos["caza_noche"]
    assert "--horas" in comando
    assert comando[comando.index("--horas") + 1] == "3"


def test_un_paso_que_falla_no_corta_el_resto_y_el_codigo_de_salida_refleja_el_fallo(tmp_path):
    pasos = [("roto", _falso(3, "primer paso")), ("sigue", _falso(0, "segundo paso"))]
    codigo = probar_todo.ejecutar(pasos, tmp_path, False)
    assert codigo == 1
    estado = json.loads((tmp_path / "estado.json").read_text(encoding="utf-8"))
    assert estado["pasos"]["roto"]["resultado"] == "fallo"
    assert estado["pasos"]["sigue"]["resultado"] == "ok"
    assert "segundo paso" in (tmp_path / "sigue.log").read_text(encoding="utf-8")


def test_seguir_no_repite_el_paso_terminado_y_retoma_desde_el_que_falta(tmp_path):
    marca_primero = tmp_path / "primero.marca"
    marca_segundo = tmp_path / "segundo.marca"
    (tmp_path / "estado.json").write_text(
        json.dumps(
            {
                "pasos": {
                    "primero": {
                        "resultado": "ok",
                        "duracion": 0.0,
                        "detalle": "código 0",
                        "log": str(tmp_path / "primero.log"),
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    codigo = probar_todo.ejecutar(
        [("primero", _marca(marca_primero)), ("segundo", _marca(marca_segundo))], tmp_path, True
    )
    assert codigo == 0
    assert not marca_primero.exists()
    assert marca_segundo.exists()


def test_el_informe_tiene_la_tabla_los_nombres_de_los_pasos_y_los_fallos(tmp_path):
    pasos = [("bueno", _falso(0, "salio bien")), ("malo", _falso(2, "salio mal"))]
    assert probar_todo.ejecutar(pasos, tmp_path, False) == 1
    informe = (tmp_path / "informe.md").read_text(encoding="utf-8")
    assert "| paso | resultado | duración | detalle |" in informe
    assert "| bueno | ok |" in informe
    assert "| malo | fallo |" in informe
    assert "## Fallos" in informe
    assert "**malo**" in informe


def test_la_carpeta_del_informe_toma_la_variable_de_entorno(tmp_path, monkeypatch):
    monkeypatch.setenv("OMNICAD_PROBAR_TODO_DIR", str(tmp_path))
    assert probar_todo._carpeta_informe() == tmp_path
