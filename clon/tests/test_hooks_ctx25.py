"""Hooks de .claude/hooks: aviso de contexto por crecimiento y recordatorio de git commit."""
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


def test_aviso_al_30_y_dice_ambos_topes(tmp_path):
    m = _cargar()
    ruta = _transcript(tmp_path, [100_000, 310_000])
    assert m.uso_actual(str(ruta)) == 310_000
    assert m.aviso(290_000, 1_000_000) == ""
    msg = m.aviso(310_000, 1_000_000)
    assert "31 %" in msg and "40 %" in msg and "35 %" in msg


def _correr(script, entrada):
    r = subprocess.run([sys.executable, str(HOOKS / script)], input=json.dumps(entrada), capture_output=True, text=True, timeout=30)
    assert r.returncode == 0
    return r.stdout


def test_aviso_commit_solo_si_es_git_commit():
    assert "ponytail-review" in _correr("aviso_commit.py", {"tool_input": {"command": "git commit -m x"}})
    assert "ponytail-review" in _correr("aviso_commit.py", {"tool_input": {"command": "git add a && git commit -m x"}})
    assert _correr("aviso_commit.py", {"tool_input": {"command": "for i in 1 2; do echo git commit; done"}}) == ""


def test_ctx25_sin_transcript_no_falla():
    assert _correr("ctx25.py", {}) == ""
