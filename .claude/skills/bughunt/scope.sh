#!/usr/bin/env bash
# bughunt scope: list the analyzable source files of a project with line counts, as JSON on stdout.
# Read-only. Usage: bash scope.sh [target_dir]
# Respects .gitignore in git repos; skips dependencies, build output, lockfiles, minified files,
# binaries, docs and Power Apps editor-state files. Env: BUGHUNT_MAX_BYTES (default 512000),
# BUGHUNT_LARGE_IMAGE_BYTES (default 204800; larger images are listed for the performance report).
# Each file entry is [path, lines] or [path, lines, "tags"], where tags are "ui" (screen code) and/or "data"
# (database or schema files).
set -eu

TARGET="${1:-.}"
MAX_BYTES="${BUGHUNT_MAX_BYTES:-512000}"
cd "$TARGET"
ROOT="$(pwd -P)"

TMP="$(mktemp -d 2>/dev/null || mktemp -d -t bughunt)"
trap 'rm -rf "$TMP"' EXIT
FILES="$TMP/files"; SKIPS="$TMP/skips"; LARGE="$TMP/large"; MSAPP="$TMP/msapp"; BIGIMG="$TMP/bigimg"
: > "$FILES"; : > "$SKIPS"; : > "$LARGE"; : > "$MSAPP"; : > "$BIGIMG"

IS_GIT=false
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then IS_GIT=true; fi

list_files() {
  if [ "$IS_GIT" = true ]; then
    git -c core.quotePath=false ls-files --cached --others --exclude-standard -- . | sort -u
  else
    find . -type f | sed 's|^\./||' | sort
  fi
}

# Prints a skip reason, or nothing if the file should be analyzed.
skip_reason() {
  case "$1" in
    .git/*|*/.git/*) echo vcs; return;;
    .bughunt/*|.claude/*) echo tooling; return;;
    node_modules/*|*/node_modules/*|bower_components/*|*/bower_components/*|jspm_packages/*|*/jspm_packages/*) echo dependency; return;;
    __pycache__/*|*/__pycache__/*|.venv/*|*/.venv/*|venv/*|*/venv/*|.tox/*|*/.tox/*) echo dependency; return;;
    *.editorstate.json|*/EditorState/*|EditorState/*) echo powerapps-editor-state; return;;
    *.msapp) echo packed-powerapp; return;;
    package-lock.json|*/package-lock.json|npm-shrinkwrap.json|*/npm-shrinkwrap.json|yarn.lock|*/yarn.lock|pnpm-lock.yaml|*/pnpm-lock.yaml|*.lock|*.lockb|packages.lock.json|*/packages.lock.json) echo lockfile; return;;
    *.min.js|*.min.mjs|*.min.css|*.map|*.bundle.js|*.chunk.js) echo minified; return;;
    *.md|*.mdx|*.txt|*.rst|*.adoc|LICENSE|*/LICENSE|LICENSE.*|*/LICENSE.*|CHANGELOG*|*/CHANGELOG*) echo docs; return;;
    *.png|*.jpg|*.jpeg|*.gif|*.webp|*.bmp|*.tif|*.tiff|*.svg|*.avif) echo image; return;;
    *.ico|*.icns|*.psd|*.ai|*.sketch|*.fig) echo asset; return;;
    *.woff|*.woff2|*.ttf|*.otf|*.eot|*.mp3|*.mp4|*.mov|*.wav|*.avi|*.webm|*.ogg|*.flac) echo asset; return;;
    *.pdf|*.zip|*.gz|*.tgz|*.bz2|*.xz|*.7z|*.rar|*.jar|*.war|*.nupkg|*.exe|*.dll|*.so|*.dylib|*.a|*.o|*.obj|*.class|*.pyc|*.wasm|*.bin|*.dat) echo binary; return;;
    *.xlsx|*.xls|*.docx|*.doc|*.pptx|*.ppt|*.db|*.sqlite|*.sqlite3|*.csv|*.tsv|*.parquet) echo data; return;;
  esac
  if [ "$IS_GIT" = false ]; then
    case "$1" in
      dist/*|*/dist/*|build/*|*/build/*|out/*|*/out/*|coverage/*|*/coverage/*|.next/*|*/.next/*|.nuxt/*|*/.nuxt/*|target/*|*/target/*|bin/*|*/bin/*|obj/*|*/obj/*) echo build-output; return;;
    esac
  fi
}

# Tags: "ui" for screen code, "data" for database or schema files. Used to route checkpoints to the right files.
file_tags() {
  t=""
  case "$1" in
    *.html|*.htm|*.jsx|*.tsx|*.vue|*.svelte|*.astro|*.css|*.scss|*.sass|*.less|*.cshtml|*.razor|*.hbs|*.ejs|*.pug|*.xaml|*.pa.yaml|*.fx.yaml) t="ui";;
    *.js|*.mjs|*.cjs|*.ts|*.mts|*.cts)
      if grep -Eqs 'document\.|window\.|addEventListener|innerHTML|createElement\(|getElementById|querySelector|React|useState|className=|<template|jQuery|\$\(|Office\.context' "$1"; then t="ui"; fi;;
  esac
  case "$1" in
    *.sql|*.prisma|*.graphql|*.gql|*.dbml|*.cds|*migrations/*|*migration/*|*/models/*|models/*|*/entities/*|*/Entities/*|*/tables/*|*/Tables/*|*schema*|*Schema*|*ustomizations.xml|*solution.yml)
      t="${t:+$t,}data";;
  esac
  printf '%s' "$t"
}

PA_SOURCE=0
TOTAL_LINES=0
TOTAL_FILES=0

while IFS= read -r f; do
  [ -n "$f" ] || continue
  [ -f "$f" ] || continue
  reason="$(skip_reason "$f")"
  if [ "$reason" = image ]; then
    ib=$(wc -c < "$f" | tr -d ' ')
    if [ "$ib" -gt "${BUGHUNT_LARGE_IMAGE_BYTES:-204800}" ]; then printf '%s\t%s\n' "$f" "$ib" >> "$BIGIMG"; fi
    reason=asset
  fi
  if [ "$reason" = packed-powerapp ]; then printf '%s\n' "$f" >> "$MSAPP"; fi
  if [ -n "$reason" ]; then printf '%s\n' "$reason" >> "$SKIPS"; continue; fi
  bytes=$(wc -c < "$f" | tr -d ' ')
  if [ "$bytes" -eq 0 ]; then echo empty >> "$SKIPS"; continue; fi
  if ! grep -Iq . "$f" 2>/dev/null; then echo binary >> "$SKIPS"; continue; fi
  if [ "$bytes" -gt "$MAX_BYTES" ]; then printf '%s\t%s\n' "$f" "$bytes" >> "$LARGE"; echo too-large >> "$SKIPS"; continue; fi
  lines=$(wc -l < "$f" | tr -d ' ')
  [ "$lines" -gt 0 ] || lines=1
  case "$f" in *.pa.yaml|*.fx.yaml|*CanvasManifest.json|*solution.yml|*Solution.xml) PA_SOURCE=$((PA_SOURCE + 1));; esac
  printf '%s\t%s\t%s\n' "$f" "$lines" "$(file_tags "$f")" >> "$FILES"
  TOTAL_LINES=$((TOTAL_LINES + lines))
  TOTAL_FILES=$((TOTAL_FILES + 1))
done <<EOF
$(list_files)
EOF

json_str() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

PA_DETECTED=false
if [ "$PA_SOURCE" -gt 0 ] || [ -s "$MSAPP" ]; then PA_DETECTED=true; fi

printf '{\n'
printf '  "root": "%s",\n' "$(json_str "$ROOT")"
printf '  "git": %s,\n' "$IS_GIT"
printf '  "total_files": %s,\n' "$TOTAL_FILES"
printf '  "total_lines": %s,\n' "$TOTAL_LINES"
printf '  "powerapps": {"detected": %s, "source_files": %s, "packed_msapp": [' "$PA_DETECTED" "$PA_SOURCE"
first=true
while IFS= read -r m; do
  [ -n "$m" ] || continue
  if [ "$first" = true ]; then first=false; else printf ', '; fi
  printf '"%s"' "$(json_str "$m")"
done < "$MSAPP"
printf ']},\n'
printf '  "skipped_counts": {'
first=true
sort "$SKIPS" | uniq -c | while read -r count reason; do
  if [ "$first" = true ]; then first=false; else printf ', '; fi
  printf '"%s": %s' "$reason" "$count"
done
printf '},\n'
printf '  "skipped_large": ['
first=true
while IFS="$(printf '\t')" read -r p b; do
  [ -n "$p" ] || continue
  if [ "$first" = true ]; then first=false; else printf ', '; fi
  printf '["%s", %s]' "$(json_str "$p")" "$b"
done < "$LARGE"
printf '],\n'
printf '  "large_images": ['
first=true
while IFS="$(printf '\t')" read -r p b; do
  [ -n "$p" ] || continue
  if [ "$first" = true ]; then first=false; else printf ', '; fi
  printf '["%s", %s]' "$(json_str "$p")" "$b"
done < "$BIGIMG"
printf '],\n'
printf '  "files": ['
first=true
while IFS="$(printf '\t')" read -r p n tg; do
  [ -n "$p" ] || continue
  if [ "$first" = true ]; then first=false; printf '\n'; else printf ',\n'; fi
  if [ -n "$tg" ]; then printf '    ["%s", %s, "%s"]' "$(json_str "$p")" "$n" "$tg"; else printf '    ["%s", %s]' "$(json_str "$p")" "$n"; fi
done < "$FILES"
printf '\n  ]\n}\n'
