#!/usr/bin/env python3
"""Stage the compiled module, dependency notices, and Wasmer package."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
SPEC = json.loads((ROOT / 'wasix/build.json').read_text())
def output(*args):
    return subprocess.check_output(args, text=True).strip()

target = Path(os.environ.get('CARGO_TARGET_DIR', 'target'))
wasm = ROOT / '.wasix/dist' / (SPEC['binary'] + '.wasm')
wasm.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(target / 'wasm32-wasmer-wasi/release' / wasm.name, wasm)
licenses = ROOT / '.wasix/licenses'
shutil.rmtree(licenses, ignore_errors=True)
licenses.mkdir()
metadata = json.loads(output('cargo', '+wasix', 'metadata', '--locked', '--format-version=1',
                             '--filter-platform', 'wasm32-wasmer-wasi'))
notices = []
for package in sorted(metadata['packages'], key=lambda p: (p['name'], p['version'])):
    notices.append({key: package[key] for key in ('name', 'version', 'license')})
    for path in Path(package['manifest_path']).parent.iterdir():
        if path.is_file() and path.name.upper().startswith(('LICENSE', 'LICENCE', 'COPYING', 'UNLICENSE', 'NOTICE')):
            dest = licenses / (package['name'] + '-' + package['version']) / path.name
            dest.parent.mkdir(exist_ok=True)
            shutil.copyfile(path, dest)
(licenses / 'DEPENDENCIES.json').write_text(json.dumps(notices, indent=2) + '\n')
# WebC stores filesystem timestamps; normalize them for reproducible packages.
for path in [licenses, *licenses.rglob('*')]:
    os.utime(path, (0, 0))
webc = ROOT / '.wasix' / f"{SPEC['package']}-{SPEC['version']}.webc"
webc.unlink(missing_ok=True)
subprocess.run(['wasmer', 'package', 'build', '.', '--out', str(webc)], check=True)
provenance = {'commit': output('git', 'rev-parse', 'HEAD'),
              'dirty': bool(output('git', 'status', '--porcelain')),
              'cargo_wasix': output('cargo', 'wasix', '--version'),
              'rustc': output('rustc', '+wasix', '-vV'),
              'cargo': output('cargo', '+wasix', '--version'),
              'wasmer': output('wasmer', '--version'),
              'lock_sha256': hashlib.sha256(Path('Cargo.lock').read_bytes()).hexdigest()}
(ROOT / '.wasix/provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
for path in (wasm, webc):
    print(hashlib.sha256(path.read_bytes()).hexdigest(), path.relative_to(ROOT), path.stat().st_size, 'bytes')
