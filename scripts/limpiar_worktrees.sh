#!/usr/bin/env bash
# Borra las carpetas de trabajo (worktrees) que no aportan nada: sin cambios sin guardar, sin commits fuera de main,
# sin tarea de la cola de OpenCode y sin proceso trabajando adentro. `git worktree remove` se niega si hay algo sucio.
# Crontab de la VPS, domingos 07:00 UTC (Gerardo, 2026-11-17). Registro en ~/coordinador/limpieza_worktrees.log.
cd "$HOME/OmniCAD" || exit 1; C=$HOME/coordinador/opencode_cola; L=$HOME/coordinador/limpieza_worktrees.log
usados=$(cat "$C"/*.tarea "$C"/reserva/*.tarea "$C"/hechos/*.tarea 2>/dev/null | grep -oE "^WT=.*" | cut -d= -f2 | sort -u)
en_uso=$(for p in $(pgrep -f "opencode|codebuddy|pytest|lanzador|claude"); do readlink "/proc/$p/cwd"; done 2>/dev/null | sort -u)
n=0
while read -r w b; do
  [ "$w" = "$HOME/OmniCAD" ] && continue; b=${b#refs/heads/}
  echo "$usados" | grep -qx "$w" && continue; echo "$en_uso" | grep -q "^$w" && continue
  [ -n "$(git -C "$w" status --porcelain 2>/dev/null | head -1)" ] && continue
  [ -n "$(git log "main..$b" --oneline 2>/dev/null | head -1)" ] && continue
  git worktree remove "$w" 2>/dev/null && n=$((n + 1))
done < <(git worktree list --porcelain | awk "/^worktree /{w=\$2} /^branch /{print w, \$2}")
git worktree prune
echo "$(date -u "+%F %T") borradas=$n quedan=$(git worktree list | wc -l)" >> "$L"
