"""B-332: avisos, «calculando…» e instrucciones van al registro de uso como `aviso`, no como `error`."""
from types import SimpleNamespace

from omnicad import registro_uso as ru
from omnicad.registro_uso import ganchos
from omnicad.ui import comando as mod_comando


class _Falso:
    def __init__(self):
        self.eventos = []

    def emitir(self, tipo, datos=None, **_):
        self.eventos.append((tipo, datos))


def _mostrar(monkeypatch, texto, tipo):
    falso = _Falso()
    monkeypatch.setattr(ru, "activo", falso)
    monkeypatch.setattr(mod_comando, "poner_mensaje", lambda *a: None)
    panel = SimpleNamespace(comando=SimpleNamespace(CLAVE="extruir"), _uso_error=None, icono_mensaje=None,
                            mensaje=None, _reubicar=lambda: None)
    mod_comando.PanelComando._mostrar(panel, texto, tipo=tipo)
    return falso.eventos


def test_aviso_calculando_e_instruccion_no_son_error(monkeypatch):
    for tipo in ("aviso", "calculando", "instruccion"):
        assert [e[0] for e in _mostrar(monkeypatch, "Calculando vista previa…", tipo)] == ["aviso"]


def test_error_e_invalido_siguen_siendo_error_y_resultado_fallido(monkeypatch):
    for tipo in ("error", "invalido"):
        ev = _mostrar(monkeypatch, "Falta un perfil.", tipo)
        assert [e[0] for e in ev] == ["error", "comando_resultado"]
        assert ev[0][1]["excepcion"] == "ErrorComando"


def test_gancho_aviso_emite_evento_propio(monkeypatch):
    falso = _Falso()
    monkeypatch.setattr(ru, "activo", falso)
    ganchos.aviso(origen="comando", comando="extruir", mensaje="hola")
    assert falso.eventos == [("aviso", {"origen": "comando", "comando": "extruir", "mensaje": "hola"})]
