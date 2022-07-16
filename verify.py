#!/usr/bin/python3

import subprocess
import os
import re
import shutil
from typing import Optional, Set, List

repo_dir = os.path.dirname(__file__)
gpg_home = os.path.join(repo_dir, 'gpghome')
master_key = 'A7D927063079E2BE3626BD59B2FD86AC890B698D'

# gpg --armor --export A7D927063079E2BE3626BD59B2FD86AC890B698D > mykey.asc

def run_git(command: List[str]) -> str:
    result = subprocess.run(
        ['git'] + command,
        cwd=repo_dir,
        env={'GNUPGHOME': gpg_home},
        capture_output=True,
        encoding='utf-8',
        text=True,
    )
    assert result.returncode == 0, (
        '`git ' + ' '.join(command) + '` returned exit code ' + str(result.returncode)
    )
    return result.stdout + result.stderr

def signing_key_of(commit: str) -> str:
    '''Returns the GPG key that signed the given commit'''
    result = run_git(['verify-commit', commit])
    assert result.strip(), 'is not signed'
    match = re.search(r'using RSA key (\w+)', result)
    assert match, 'failed to read signing key'
    return match.group(1)

def owner_of(path: str) -> str:
    '''Returns directory name'''
    return path.split('/')[0]

def filename_of(path: str) -> str:
    '''Returns the file name including extension'''
    return path.rsplit('/', 1)[-1]

def basename_of(path: str) -> str:
    '''Returns file name without extension'''
    return filename_of(path).split('.')[0]

def required_key_of_line(line: str) -> str:
    parts = line.split()
    if parts[0] == 'R100' and owner_of(parts[1]) != owner_of(parts[2]):
        source, dest = parts[1], parts[2]
        assert filename_of(source) == filename_of(dest), (
            source + ' renamed while being transferred'
        )
        return owner_of(source)
    elif parts[0].startswith('R'):
        source, dest = parts[1], parts[2]
        assert owner_of(source) == owner_of(dest), (
            source + ' modified while being transferred'
        )
        assert basename_of(source) == basename_of(dest), (
            source + ' renamed, only extension can be changed'
        )
        return owner_of(parts[1])
    elif parts[0].startswith('A'):
        if owner_of(parts[1]) == 'keys':
            return basename_of(parts[1])
        else:
            assert False, 'only allowed to add to keys directory'
    else:
        assert False, 'unknown git operation ' + line

def required_key_of(commit: str) -> str:
    result = run_git(['diff', '--name-status', commit + '~1', commit])
    keys = set()
    for line in result.splitlines():
        keys.add(required_key_of_line(line))
    assert len(keys) <= 1, (
        'commit would need to be authorized by multiple keys (' +
        ', '.join(keys) + ')'
    )
    assert len(keys) == 1, 'could not determine the key that is required to sign'
    return list(keys)[0]

def verify_commit(commit: str) -> None:
    signing_key = signing_key_of(commit)
    required_key = required_key_of(commit)
    assert signing_key == required_key or signing_key == master_key, (
        'signed with invalid key ' + signing_key +
        ', needs to be signed with ' + required_key
    )

def get_all_commits() -> List[str]:
    result = run_git(['log', '--pretty=tformat:%H'])
    return result.splitlines()

def verify_all_commits() -> None:
    failed = False
    for commit in get_all_commits():
        try:
            verify_commit(commit)
            print('  ' + commit + ' is valid')
        except AssertionError as e:
            failed = True
            print('invalid commit ' + commit + ': ' + str(e))
    if failed:
        exit(1)

def wipe_gpg_home() -> None:
    if os.path.exists(gpg_home):
        shutil.rmtree(gpg_home)

def set_up_gpg() -> None:
    key_dir = os.path.join(repo_dir, 'keys')
    wipe_gpg_home()
    os.makedirs(gpg_home)
    for key in os.listdir(key_dir):
        subprocess.run(
            ['gpg', '--import', os.path.join(key_dir, key)],
            env={'GNUPGHOME': gpg_home},
            capture_output=True,
            check=True,
        )

if __name__ == '__main__':
    set_up_gpg()
    verify_all_commits()
    wipe_gpg_home()
