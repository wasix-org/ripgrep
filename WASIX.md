# ripgrep for WASIX

Standalone `rg` from upstream **15.2.0** (base `e89fff89ac9af12e8d4ce9d5fd07beb408ca730f`).
No Pi code, JavaScript runtime, or Bash wrapper is included.

## Build and test

Install Rustup, Python 3.9+, `patch`, a native C compiler, **Wasmer 7.4.2**,
and **wasm-tools 1.251.0**. On macOS the C compiler comes with Xcode command
line tools. Install the pinned cargo-wasix and WASIX compiler once:

```sh
cargo install cargo-wasix --version 0.1.33 --locked
cargo wasix download-toolchain v2026-07-07.3+rust-1.96
```

On Linux, restore the executable bits missing from the pinned archive's native
linker shims (needed to compile Cargo build scripts):

```sh
chmod +x "$(rustc +wasix --print sysroot)"/lib/rustlib/*-unknown-linux-gnu/bin/gcc-ld/*
```

Then clone the fork and build:

```sh
git clone --branch codex/wasix https://github.com/wasix-org/ripgrep.git
cd ripgrep
bash wasix/build.sh
python3 wasix/test.py
```

`build.sh` runs `python3 wasix/prepare.py`, then
**`cargo wasix build --release --locked --bin rg`**. Cargo-wasix handles
the compiler, Binaryen 130 and exception conversion. The script disables wide
arithmetic for browser compatibility, removes debug metadata, validates the
result, collects license notices, and runs `wasmer package build`.

You can also run `python3 wasix/prepare.py` followed by `cargo wasix build
--release --locked` directly. Use `build.sh` for the browser-compatible release
flags and WebC packaging. Dependencies are fixed by the root `Cargo.lock` and
`.cargo/config.toml`; the tiny portability patches are applied to
checksum-verified crate archives under ignored `.wasix/deps/`.

Outputs: `.wasix/dist/rg.wasm` and `.wasix/ripgrep-15.2.0.webc`.
`.wasix/provenance.json` records the source revision, dirty state, compiler,
Cargo/cargo-wasix versions, Wasmer version, and lockfile hash. Artifact hashes
and byte sizes are printed by the build.

The [WASIX workflow](.github/workflows/wasix.yml) builds and tests on Linux,
rebuilds into a fresh Cargo target directory, compares both artifacts byte for
byte, and uploads them with SHA-256 checksums. Reproduce that check with:

```sh
cp .wasix/dist/rg.wasm .wasix/first.wasm
cp .wasix/ripgrep-15.2.0.webc .wasix/first.webc
CARGO_TARGET_DIR=.wasix/repro-target bash wasix/build.sh
cmp .wasix/first.wasm .wasix/dist/rg.wasm
cmp .wasix/first.webc .wasix/ripgrep-15.2.0.webc
```

The byte comparison uses the same checkout and host toolchain. Cross-host
compiler distributions are not assumed to produce identical output. Check out
a release tag and use its recorded versions to reproduce a published release.

## Port patches

The ripgrep source change is confined to `crates/ignore`: it enables WASI
metadata and directory traversal. The default Rust regex engine is included;
the optional PCRE2 feature is not enabled.

`ignore` supplies directory traversal and filesystem IDs; `same-file` uses
WASI device/inode metadata for identity and symlink-loop detection; `walkdir`
uses WASI filesystem IDs for its single-threaded walker. Only the necessary
WASI paths are added; Unix/Windows behavior is preserved. Versions and archive
checksums are in `wasix/dependencies.json`, patches in `wasix/patches/`.
No Wasmer, libc, or libuv changes are required.

Tests execute the actual WebC and cover searches, ignore rules, Unicode,
spaces, symlinks, filesystem limits, and exit behavior. Commands launched by
`rg --pre or decompression flags` must be supplied by the surrounding environment.

## Use as a package

```sh
wasmer run wasmer/ripgrep@15.2.0 --volume "$PWD:/workspace" -- --no-require-git "pattern" /workspace
wasmer run --registry wasmer.wtf wasmer/ripgrep@15.2.0 -- --version
```

Other Wasmer packages can reference the command without embedding its binary:

```toml
[dependencies]
"wasmer/ripgrep" = "=15.2.0"

[[command]]
name = "rg"
module = "wasmer/ripgrep:rg"
runner = "wasi"
```

## Publish

Build and test from a clean, committed checkout. Authenticate with an account
that can publish in the `wasmer` namespace, then upload the same staged package:

```sh
wasmer login --registry wasmer.io
wasmer publish . --registry wasmer.io --wait=container --non-interactive
wasmer login --registry wasmer.wtf
wasmer publish . --registry wasmer.wtf --wait=container --non-interactive
```

Packages: [wasmer.io](https://wasmer.io/wasmer/ripgrep) and
[wasmer.wtf](https://wasmer.wtf/wasmer/ripgrep). To update, change `wasmer.toml`
and `wasix/build.json` together and publish a new version. Keep license notices
in the package. CI does not publish or require registry credentials.
