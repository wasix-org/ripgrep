#!/usr/bin/env python3
"""Fetch checksum-pinned crates and apply the small WASIX patches."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEPS = ROOT / '.wasix/deps'
DEPS.mkdir(parents=True, exist_ok=True)
for dep in json.loads((ROOT / 'wasix/dependencies.json').read_text()):
    name = f"{dep['name']}-{dep['version']}"
    archive = DEPS / (name + '.crate')
    if not archive.exists():
        urllib.request.urlretrieve(f"https://static.crates.io/crates/{dep['name']}/{name}.crate", archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != dep['sha256']:
        raise RuntimeError('Checksum mismatch: ' + str(archive))
    directory = DEPS / name
    patch = ROOT / 'wasix/patches' / (name + '.patch')
    digest = hashlib.sha256(patch.read_bytes()).hexdigest()
    stamp = directory / '.wasix-patch'
    if stamp.exists() and stamp.read_text() == digest:
        continue
    shutil.rmtree(directory, ignore_errors=True)
    with tarfile.open(archive) as tar:
        for item in tar.getmembers():
            parts = Path(item.name).parts
            if not parts or parts[0] != name or '..' in parts or not (item.isfile() or item.isdir()):
                raise RuntimeError('Unexpected crate archive entry: ' + item.name)
        tar.extractall(DEPS)
    subprocess.run(['patch', '-p1', '--batch', '-i', str(patch)], cwd=directory, check=True)
    stamp.write_text(digest)
