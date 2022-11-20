#!/usr/bin/env python

import datetime
import logging
import os
import subprocess
import sys
import tempfile
import uuid


# docker run -p 80:8080 pypiserver/pypiserver:latest run -P . -a . --hash-algo sha256


SOURCE_NAME = 'localhost'
SOURCE_URL = 'http://localhost/'

logger = logging.getLogger(__name__)


def _get_commit_id(project_path: str) -> str:
    commit_id = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=project_path, capture_output=True, check=True).stdout.decode().rstrip()
    return commit_id


def _run(project_path: str, command: list[str]) -> None:
    subprocess.run(command, cwd=project_path, check=True)

    if subprocess.run(['git', 'diff', '--quiet'], cwd=project_path).returncode != 0:
        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', ' '.join(command)], cwd=project_path, check=True)

        commit_id = _get_commit_id(project_path)
    else:
        commit_id = 'N/A'

    logger.info('%s, %s, %s', project_path, ' '.join(command), commit_id)


def _setup_logger() -> None:
    logging.basicConfig(
        datefmt='%Y-%m-%d %H:%M:%S',
        filemode='w',
        filename=f'{datetime.datetime.now():%Y%m%d%H%M%S}.log',
        format='%(name)s:%(levelname)s:%(asctime)s:%(message)s',
        level='INFO',
    )


def add_dependency(project_path: str, dependency: str, source_name: str) -> None:
    _run(project_path, ['poetry', 'add', '--lock', '--source', source_name, dependency])


def add_source(project_path: str, source_name: str, source_url: str) -> None:
    _run(project_path, ['poetry', 'source', 'add', source_name, source_url])


def build(project_path: str) -> None:
    command = ['poetry', 'build', '--format', 'wheel']

    _run(project_path, command)


def bump_version(project_path: str, version: str) -> None:
    _run(project_path, ['poetry', 'version', version])


def lock(project_path: str) -> None:
    _run(project_path, ['poetry', 'lock'])


def new(project_path: str) -> None:
    command = ['poetry', 'new', project_path]

    subprocess.run(command, check=True)

    subprocess.run(['git', 'init', '-b', 'main'], cwd=project_path, check=True)

    with open(f'{project_path}/.gitignore', 'w') as f:
        f.write('dist')

    subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
    subprocess.run(['git', 'commit', '-m', ' '.join(command)], cwd=project_path, check=True)

    commit_id = _get_commit_id(project_path)
    logger.info('%s, %s, %s', project_path, ' '.join(command), commit_id)


def publish(project_path: str, repository_name: str) -> None:
    command = ['poetry', 'publish', '--repository', repository_name]

    _run(project_path, command)


def remove_environment(project_path: str) -> None:
    command = ['poetry', 'env', 'remove', '--all']

    _run(project_path, command)


def remove_lock(project_path: str) -> None:
    logger.info('%s, removing poetry.lock', project_path)

    os.remove(f'{project_path}/poetry.lock')


def update_all_dependencies(project_path: str) -> None:
    _run(project_path, ['poetry', 'update', '--lock'])


def update_dependency(project_path: str, dependency: str) -> None:
    _run(project_path, ['poetry', 'update', '--lock', dependency])


def main() -> None:
    _setup_logger()

    temp_root = tempfile.mkdtemp()

    # lorito is a direct dependency of gatito
    # gatito is a direct dependency of perrito

    LORITO_PATH = f'{temp_root}/lorito'
    GATITO_PATH = f'{temp_root}/gatito'
    PERRITO_PATH = f'{temp_root}/perrito'

    # ------------------------------------------------------------------

    for project_path in LORITO_PATH, GATITO_PATH, PERRITO_PATH:
        new(project_path)
        add_source(project_path, SOURCE_NAME, SOURCE_URL)

    build(LORITO_PATH)
    publish(LORITO_PATH, SOURCE_NAME)

    add_dependency(GATITO_PATH, 'lorito', SOURCE_NAME)
    build(GATITO_PATH)
    publish(GATITO_PATH, SOURCE_NAME)

    add_dependency(PERRITO_PATH, 'gatito', SOURCE_NAME)

    # ------------------------------------------------------------------

    bump_version(LORITO_PATH, 'patch')
    build(LORITO_PATH)
    publish(LORITO_PATH, SOURCE_NAME)

    bump_version(GATITO_PATH, 'patch')
    update_dependency(GATITO_PATH, 'lorito')
    build(GATITO_PATH)
    publish(GATITO_PATH, SOURCE_NAME)

    update_dependency(PERRITO_PATH, 'gatito')
    #update_all_dependencies(PERRITO_PATH)

    # ------------------------------------------------------------------

    print(temp_root)


if __name__ == '__main__':
    main()
