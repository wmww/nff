#!/usr/bin/python3

import subprocess
import os
import sys
from typing import List

repo_dir = os.path.dirname(__file__)
gpg_home = os.path.join(repo_dir, 'gpghome')
key_dir = os.path.join(repo_dir, 'keys')

# gpg --armor --export A7D927063079E2BE3626BD59B2FD86AC890B698D > mykey.asc

def run(command: List[str]) -> str:
    return subprocess.run(command, cwd=repo_dir, capture_output=True, text=True, encoding='utf-8').stdout

def setup_git_signing(key: str) -> None:
    run(['git', 'config', 'user.signingkey', key])
    run(['git', 'config', 'commit.gpgsign', 'true'])

def install_pub_key(key: str) -> None:
    pubkey = run(['gpg', '--armor', '--export', key])
    with open(os.path.join(key_dir, key + '.asc'), 'w') as f:
        f.write(pubkey)



if __name__ == '__main__':
    try:
        assert len(sys.argv) <= 2, 'too many args, please just provide the key'
        assert len(sys.argv) == 2, (
            'please provide a key, ' +
            'see `gpg --list-secret-keys` or ' +
            '`gpg --full-generate-key` to create a new one'
        )
        key = sys.argv[1]
        setup_git_signing(key)
        install_pub_key(key)
    except AssertionError as e:
        print(str(e))
        exit(1)
