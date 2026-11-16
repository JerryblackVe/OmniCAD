"""Hooks de .claude/hooks: aviso de contexto por porcentaje y recordatorio de git commit."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[2] / ".claude" / "hooks"


def _cargar():
    spec = importlib.util.spec_from_file_location("ctx25", HOOKS / "ctx25.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _transcript(tmp_path, usos):
    ruta = tmp_path / "t.jsonl"
    ruta.write_text("\n".join(json.dumps({"message": {"usage": {"input_tokens": u}}}) for u in usos), encoding="utf-8")
    return ruta


def test_aviso_1m_y_rol(monkeypatch):
    monkeypatch.delenv("OMNICAD_CTX_VENTANA", raising=False)
    m = _cargar()
    assert m.aviso(290_000, "OmniCAD · E1") == ""  # 29 % de 1M
    e = m.aviso(310_000, "OmniCAD · E1 Bocetos")
    assert "31 %" in e and "35 %" in e and "te vacía el coordinador" in e
    c = m.aviso(310_000, "Coordinador principal OmniCAD en VPS")
    assert "40 %" in c and "sin clear_session" in c
    monkeypatch.setenv("OMNICAD_CTX_VENTANA", "200000")
    assert m.aviso(70_000, "OmniCAD · E1") != ""  # 35 % de 200K


def test_leer_transcript(tmp_path):
    m = _cargar()
    ruta = tmp_path / "t.jsonl"
    filas = [{"type": "custom-title", "customTitle": "OmniCAD · E7"},
             {"message": {"model": "claude-sonnet-5-5", "usage": {"input_tokens": 10, "cache_read_input_tokens": 70_000}}}]
    ruta.write_text("\n".join(json.dumps(f) for f in filas), encoding="utf-8")
    assert m.leer(str(ruta)) == (70_010, "OmniCAD · E7")


def _correr(script, entrada):
    r = subprocess.run([sys.executable, str(HOOKS / script)], input=json.dumps(entrada), capture_output=True, text=True, timeout=30)
    assert r.returncode == 0
    return r.stdout


def test_aviso_commit_solo_si_es_git_commit():
    for c in ("git commit -m x", "git -C /p commit -m y", "git add a && git commit -m x", "git add a\ngit commit -m z", "git commit"):
        assert "ponytail-review" in _correr("aviso_commit.py", {"tool_input": {"command": c}}), c
    for c in ("echo git commit", "for i in 1 2; do echo git commit; done", "git log --oneline", "git commit-tree abc", "git commit-graph write"):
        assert _correr("aviso_commit.py", {"tool_input": {"command": c}}) == "", c


def test_ctx25_sin_transcript_no_falla():
    assert _correr("ctx25.py", {}) == ""
