"""B-629: al consumir el trazo de un texto, el desfase debe explicar qué desaparece."""
import json
import subprocess
import sys
from pathlib import Path


def test_desfase_informa_que_el_trazo_desaparece():
    # Como en B-517, aislar OpenCascade para que un cierre del proceso falle solo este test.
    codigo = '''
import json
from omnicad import api

s = api.Sesion()
for nombre, args in [("create_box", dict(length=100, width=100, height=3)),
                     ("create_sketch", dict(plane=">Z", name="texto")),
                     ("add_text", dict(text="@tienda", x=-30, y=-42, height=8, sketch="texto"))]:
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
r = api.llamar(s, "offset_profiles", dict(sketch="texto", profiles="all", distance=-0.5, keep_original=False))
assert not r["ok"] and r["error_kind"] == "OPERATION_FAILED", r
print(json.dumps(r["mensaje"]))
'''
    salida = subprocess.check_output([sys.executable, "-c", codigo], cwd=Path(__file__).resolve().parents[1],
                                     text=True, timeout=300)
    assert "desaparece" in json.loads(salida)
