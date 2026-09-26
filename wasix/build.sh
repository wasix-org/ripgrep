#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Install the pinned toolchain once as documented in WASIX.md.
[[ "$(cargo wasix --version)" == "cargo-wasix 0.1.33"* ]]
python3 wasix/prepare.py
export RUSTFLAGS="-C target-feature=+atomics,+bulk-memory,+mutable-globals,-wide-arithmetic --remap-path-prefix=$HOME=/home/build --remap-path-prefix=$PWD=/src"
export CARGO_PROFILE_RELEASE_DEBUG=0
cargo wasix build --release --locked --bin rg
wasm-tools validate --features=-wide-arithmetic,-legacy-exceptions,-function-references,-gc \
  "${CARGO_TARGET_DIR:-target}/wasm32-wasmer-wasi/release/rg.wasm"
python3 wasix/package.py
