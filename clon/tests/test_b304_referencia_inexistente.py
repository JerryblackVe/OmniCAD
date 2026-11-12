"""B-304: ante un id o nombre que no existe, el error nombra el argumento que lo trajo y, si hay nombres parecidos, los
sugiere. Se resuelve en `registro.llamar` (una vez), no herramienta por herramienta."""
import pytest

from omnicad import api

# (herramienta, argumentos con UNA referencia mal escrita, el argumento que la trae, parecido que se espera sugerir)
CASOS = [
    ("split_body", {"body": "Cajaa", "tool": "XY"}, "body", "Caja"),
    ("split_body", {"body": "Caja", "tool": "Planoo"}, "tool", None),
    ("extrude", {"sketch": "Basee", "distance": 5}, "sketch", "Base"),
    ("create_hole", {"diameter": 3, "depth": 4, "face": ">Z", "body": "Cajaa"}, "body", "Caja"),
    ("create_hole", {"diameter": 3, "depth": 4, "face": ">Z", "positions": ["Puntoo"], "body": "Caja"}, "positions", None),
    ("mirror", {"bodies": ["Cajaa"], "plane": "XY"}, "bodies", "Caja"),
    ("mirror", {"bodies": ["Caja"], "plane": "Planoo"}, "plane", None),
    ("fillet", {"body": "Cajaa", "edges": ">Z", "radius": 1}, "body", "Caja"),
    ("loft", {"sketches": ["Basee", "Base"]}, "sketches", "Base"),
    ("edit_feature", {"feature": "op99", "params": {}}, "feature", "op1"),
    ("suppress_feature", {"feature": "op99"}, "feature", "op1"),
    ("insert_fastener", {"positions": ["Puntoo"], "body": "Caja"}, "positions", None),
]


@pytest.fixture
def sesion():
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 20, "width": 20, "height": 10, "name": "Caja"})["ok"]
    assert api.llamar(s, "create_sketch", {"plane": "XY", "name": "Base"})["ok"]
    return s


@pytest.mark.parametrize("herramienta,args,argumento,parecido", CASOS)
def test_una_referencia_que_no_existe_nombra_el_argumento(sesion, herramienta, args, argumento, parecido):
    r = api.llamar(sesion, herramienta, args)
    assert not r["ok"], r
    assert f"«{argumento}»" in r["mensaje"], r["mensaje"]
    if parecido:
        assert any(parecido in p for p in r["pistas"]), r["pistas"]


def test_no_toca_los_errores_que_no_son_de_una_referencia(sesion):
    r = api.llamar(sesion, "extrude", {"sketch": "Base", "distance": 5})        # el boceto existe pero está vacío
    assert not r["ok"] and "argumento" not in r["mensaje"], r["mensaje"]


def test_un_valor_en_dos_argumentos_no_se_adivina(sesion):
    r = api.llamar(sesion, "split_body", {"body": "Nada", "tool": "Nada"})
    assert not r["ok"] and "(argumento" not in r["mensaje"], r["mensaje"]
