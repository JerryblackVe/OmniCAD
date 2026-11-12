#!/usr/bin/env bash
# Un worktree por ítem; comparte clon/.venv con el repositorio principal.
set -euo pipefail

fallar() { echo "Error: $*" >&2; exit 1; }
uso() { echo "Uso: bash scripts/worktree_item.sh crear|borrar <ID>" >&2; exit 2; }

[[ $# == 2 ]] || uso
accion=$1
id=$2
[[ $accion == crear || $accion == borrar ]] || uso
[[ $id =~ ^[a-zA-Z0-9-]+$ ]] || fallar "ID inválido: solo letras ASCII, números y guiones."

git rev-parse --show-toplevel >/dev/null 2>&1 || fallar "No estás dentro de un repositorio Git."
# La primera entrada siempre es el principal; -z conserva espacios y caracteres de la ruta.
IFS= read -r -d '' registro < <(git worktree list --porcelain -z)
raiz=$(git -C "${registro#worktree }" rev-parse --show-toplevel)
comun=$(git -C "$raiz" rev-parse --path-format=absolute --git-common-dir)
rama="item/$id"
destino="$raiz-$id"

if [[ $accion == crear ]]; then
    ! git -C "$raiz" show-ref --verify --quiet "refs/heads/$rama" || fallar "Ya existe la rama $rama."
    [[ ! -e $destino && ! -L $destino ]] || fallar "Ya existe la carpeta $destino."
    git -C "$raiz" worktree add -b "$rama" "$destino" main >&2
    metadatos=$(git -C "$destino" rev-parse --absolute-git-dir)
    printf '%s\n' "$rama" > "$metadatos/worktree-item"
    printf '%s\n' "$destino"
    printf 'Usá el Python de %s/clon/.venv; el worktree no lleva venv propio.\n' "$raiz"
else
    [[ -d $destino && ! -L $destino ]] || fallar "No existe el worktree $destino."
    [[ $(git -C "$destino" rev-parse --show-toplevel) == "$destino" &&
       $(git -C "$destino" rev-parse --path-format=absolute --git-common-dir) == "$comun" ]] ||
        fallar "La carpeta no es un worktree de este repositorio."
    metadatos=$(git -C "$destino" rev-parse --absolute-git-dir)
    [[ -f $metadatos/worktree-item ]] || fallar "El worktree no fue creado por este script."
    IFS= read -r propietario < "$metadatos/worktree-item"
    [[ $propietario == "$rama" && $(git -C "$destino" symbolic-ref -q HEAD) == "refs/heads/$rama" ]] ||
        fallar "La rama del worktree no coincide con $rama."
    [[ -z $(git -C "$destino" status --porcelain --untracked-files=all) ]] ||
        fallar "El worktree tiene cambios sin commitear."
    git -C "$raiz" merge-base --is-ancestor "$rama" main || fallar "La rama $rama no está fusionada en main."
    # evidencias/ no va a git: sin copiarla, worktree remove borra los informes (2026-11-12 se perdió una caza)
    if [[ -d $destino/evidencias ]]; then
        mkdir -p "$raiz/evidencias" && cp -an "$destino/evidencias/." "$raiz/evidencias/" &&
            printf 'Evidencias copiadas a %s/evidencias.\n' "$raiz"
    fi
    git -C "$raiz" worktree remove "$destino"
    git -C "$raiz" branch -d "$rama"
fi
