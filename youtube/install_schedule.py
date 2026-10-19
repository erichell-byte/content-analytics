"""Install or remove a daily macOS LaunchAgent after a successful live collection."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
from common import PRIVATE, private_dir

LABEL = 'local.content-analytics.youtube'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--remove', action='store_true')
    args = parser.parse_args()
    domain = 'gui/' + str(os.getuid())
    dest = Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist')
    if args.remove:
        subprocess.run(['launchctl', 'bootout', domain + '/' + LABEL], check=False, capture_output=True)
        dest.unlink(missing_ok=True)
        print('Daily schedule removed; private data retained.')
        return
    status = json.loads((PRIVATE / 'status.json').read_text())
    if not status.get('ok'):
        raise RuntimeError('Run a successful real collection before installing the schedule.')
    # Keep the unattended runtime outside Documents and the working checkout.
    runtime = private_dir(PRIVATE / 'runtime')
    source = Path(__file__).resolve().parent
    for name in ('common.py', 'collect.py', 'scheduled.py', 'requirements.lock.txt'):
        shutil.copyfile(source / name, runtime / name)
        (runtime / name).chmod(0o600)
    python = runtime / '.venv/bin/python'
    subprocess.run([sys.executable, '-m', 'venv', str(runtime / '.venv')], check=True)
    subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(runtime / 'requirements.lock.txt')], check=True)
    subprocess.run([str(python), '-m', 'pip', 'check'], check=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    config = {'Label': LABEL,
        'ProgramArguments': [str(python), str(runtime / 'scheduled.py')],
        'WorkingDirectory': str(runtime),
        'StartCalendarInterval': {'Hour': 10, 'Minute': 15},
        'RunAtLoad': True, 'ProcessType': 'Background', 'Umask': 0o077,
        'StandardOutPath': '/dev/null', 'StandardErrorPath': '/dev/null'}
    with dest.open('wb') as stream:
        plistlib.dump(config, stream)
    dest.chmod(0o600)
    subprocess.run(['launchctl', 'bootout', domain + '/' + LABEL], check=False, capture_output=True)
    subprocess.run(['launchctl', 'bootstrap', domain, str(dest)], check=True, capture_output=True)
    print('Daily collection installed for 10:15 in the Mac system timezone and at login.')

if __name__ == '__main__':
    main()
