#!/usr/bin/env python3
"""Exercise the real packaged command against a temporary mounted workspace."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / 'wasix/build.json').read_text())

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('package', nargs='?', type=Path,
                    default=ROOT / '.wasix' / f"{SPEC['package']}-{SPEC['version']}.webc")
args = parser.parse_args()

with tempfile.TemporaryDirectory(prefix='wasix-search-test-') as directory:
    root = Path(directory)
    (root / 'src').mkdir()
    (root / '.gitignore').write_text('ignored.txt\n')
    (root / 'src/hello world.txt').write_text('first\nneedle π\nlast\n', encoding='utf8')
    (root / 'src/π.txt').write_text('unicode filename\n', encoding='utf8')
    (root / 'ignored.txt').write_text('needle hidden\n')
    (root / 'src/alias.txt').symlink_to('hello world.txt')

    def run(*arguments, status=0):
        result = subprocess.run(['wasmer', 'run', str(args.package.resolve()),
                                 '--volume', f'{root}:/workspace', '--', *arguments],
                                text=True, capture_output=True, timeout=30)
        assert result.returncode == status, (arguments, result)
        return result.stdout

    if SPEC['binary'] == 'fd':
        assert f"fd {SPEC['version']}" in run('--version')
        common = ['--color=never', '--no-require-git']
        found = run(*common, '--glob', '--hidden', '*.txt', '/workspace')
        assert 'hello world.txt' in found and 'π.txt' in found and 'ignored.txt' not in found, found
        links = run(*common, '--type', 'l', '.', '/workspace')
        assert 'alias.txt' in links and 'hello world.txt' not in links, links
        followed = run(*common, '--follow', '--type', 'f', 'alias', '/workspace')
        assert 'alias.txt' in followed, followed
        assert 'hello world.txt' in run(*common, '--one-file-system', 'hello', '/workspace')
        assert run(*common, '--glob', 'missing.*', '/workspace') == ''
    else:
        assert f"ripgrep {SPEC['version']}" in run('--version')
        output = run('--json', '--no-require-git', 'needle', '/workspace')
        matches = [x['data'] for x in map(json.loads, output.splitlines()) if x['type'] == 'match']
        assert len(matches) == 1 and matches[0]['line_number'] == 2, matches
        assert matches[0]['lines']['text'] == 'needle π\n', matches
        listed = run('--files', '--no-require-git', '/workspace')
        assert 'hello world.txt' in listed and 'π.txt' in listed and 'ignored.txt' not in listed, listed
        assert 'needle π' in run('--follow', 'needle', '/workspace/src/alias.txt')
        for threads in ('1', '2'):
            assert 'hello world.txt' in run('--files', '--one-file-system',
                                             '--threads', threads, '/workspace/src')
        run('no-such-match', '/workspace', status=1)
        run('[', '/workspace', status=2)
        (root / 'src/loop').symlink_to('../src')
        # same-file must detect the loop and return an error, rather than recurse.
        run('--follow', 'needle', '/workspace/src', status=2)
    print(f"PASS {SPEC['binary']} WebC: search, ignore rules, Unicode, spaces, symlinks and exit behavior")
