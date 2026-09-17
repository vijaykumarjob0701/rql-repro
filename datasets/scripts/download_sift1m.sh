#!/usr/bin/env bash
# Download SIFT1M: prefer Hugging Face HTTPS, then IRISA FTP.
# Date: 2026-09-17 Europe/Dublin. Does not commit binaries.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${SIFT1M_DIR:-$ROOT/datasets/cache/sift1m}"
mkdir -p "$OUT"
cd "$OUT"

HF_BASE="https://huggingface.co/datasets/qbo-odp/sift1m/resolve/main"
FTP_TGZ="ftp://ftp.irisa.fr/local/texmex/corpus/sift.tar.gz"

need_files=(sift_base.fvecs sift_query.fvecs sift_groundtruth.ivecs)
optional_files=(sift_learn.fvecs)

have_required() {
  local f
  for f in "${need_files[@]}"; do
    [[ -s "$f" ]] || return 1
  done
  return 0
}

download_hf() {
  echo "[sift1m] Trying Hugging Face mirror: $HF_BASE"
  local f
  for f in "${need_files[@]}" "${optional_files[@]}"; do
    if [[ -s "$f" ]]; then
      echo "[sift1m] skip existing $f"
      continue
    fi
    echo "[sift1m] curl -L $f"
    curl -L --fail --retry 3 --retry-delay 2 -o "$f" "$HF_BASE/$f"
  done
}

download_ftp() {
  echo "[sift1m] Trying IRISA FTP tarball: $FTP_TGZ"
  curl -L --fail --retry 3 --retry-delay 2 -o sift.tar.gz "$FTP_TGZ"
  tar xf sift.tar.gz
  # Normalize layout: archive may unpack into sift/ or .
  if [[ -d sift ]]; then
    mv -n sift/sift_*.fvecs sift/sift_*.ivecs . 2>/dev/null || true
  fi
  # Some tarballs use bare names without sift_ prefix
  for pair in "base.fvecs:sift_base.fvecs" "query.fvecs:sift_query.fvecs" \
              "groundtruth.ivecs:sift_groundtruth.ivecs" "learn.fvecs:sift_learn.fvecs"; do
    src="${pair%%:*}"
    dst="${pair##*:}"
    if [[ -f "$src" && ! -f "$dst" ]]; then
      mv "$src" "$dst"
    fi
  done
}

if have_required; then
  echo "[sift1m] Required files already present under $OUT"
else
  if ! download_hf; then
    echo "[sift1m] HF download failed; falling back to FTP" >&2
    download_ftp
  fi
  if ! have_required; then
    echo "[sift1m] ERROR: missing required files after HF+FTP attempts" >&2
    ls -la "$OUT" >&2 || true
    echo "[sift1m] NOTE: TexMex HTTPS (corpus-texmex.irisa.fr) is dead (SSL/404) as of 2026-09-17." >&2
    exit 1
  fi
fi

echo "[sift1m] Writing SHA256SUMS"
sha256sum sift_*.fvecs sift_*.ivecs 2>/dev/null | tee SHA256SUMS
echo "[sift1m] Done. Compare digests to datasets/REGISTRY.md"
echo "[sift1m] Path: $OUT"
