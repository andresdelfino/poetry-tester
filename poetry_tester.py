#!/usr/bin/env python

import datetime
import logging
import os
import subprocess
import tempfile


COMMON_FLAGS = [
    '-vvv',
    '--no-cache',
    '--no-ansi',
]

logger = logging.getLogger(__name__)


def _get_commit_id(project_path: str) -> str:
    completed_process = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=project_path, capture_output=True, check=True)
    commit_id = completed_process.stdout.decode().rstrip()
    return commit_id


def _log_streams(project_path: str, completed_process: subprocess.CompletedProcess) -> None:
    joined_command = ' '.join(completed_process.args)

    for stream in 'stdout', 'stderr':
        stream_content = getattr(completed_process, stream)
        if stream_content:
            decoded_stream_content = stream_content.decode().rstrip()
            logger.info('%s, %s, %s:\n%s', project_path, joined_command, stream, decoded_stream_content)


def _run(project_path: str, command: list[str]) -> None:
    completed_process = subprocess.run(command, cwd=project_path, capture_output=True, check=True)
    _log_streams(project_path, completed_process)

    joined_command = ' '.join(command)

    if subprocess.run(['git', 'diff', '--quiet'], cwd=project_path).returncode != 0:
        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '--quiet', '--message', joined_command], cwd=project_path, check=True)

        commit_id = _get_commit_id(project_path)
    else:
        commit_id = 'N/A'

    logger.info('%s, %s, %s', project_path, joined_command, commit_id)


def _setup_logger(filename: str) -> None:
    logging.basicConfig(
        datefmt='%Y-%m-%d %H:%M:%S',
        filemode='w',
        filename=filename,
        format='%(name)s:%(levelname)s:%(asctime)s:%(message)s',
        level='INFO',
    )


def add_dependency(project_path: str, dependency: str, source_name: str | None = None) -> None:
    if source_name:
        source_args = ['--source', source_name]
    else:
        source_args = []

    _run(project_path, ['poetry', 'add', *COMMON_FLAGS, '--lock', *source_args, dependency])


def add_source(project_path: str, source_name: str, source_url: str) -> None:
    _run(project_path, ['poetry', 'source', 'add', *COMMON_FLAGS, source_name, source_url])


def build(project_path: str) -> None:
    _run(project_path, ['poetry', 'build', *COMMON_FLAGS, '--format', 'wheel'])


def bump_version(project_path: str, version: str = 'patch') -> None:
    _run(project_path, ['poetry', 'version', *COMMON_FLAGS, version])


def lock(project_path: str) -> None:
    _run(project_path, ['poetry', 'lock', *COMMON_FLAGS])


def new(project_path: str) -> None:
    command = ['poetry', 'new', *COMMON_FLAGS, project_path]

    completed_process = subprocess.run(command, capture_output=True, check=True)
    _log_streams(project_path, completed_process)

    joined_command = ' '.join(command)

    subprocess.run(['git', 'init', '--quiet', '--initial-branch', 'main'], cwd=project_path, check=True)
    subprocess.run(['git', 'config', 'user.email', 'you@example.com'], cwd=project_path, check=True)
    subprocess.run(['git', 'config', 'user.name', 'Your Name'], cwd=project_path, check=True)

    with open(f'{project_path}/.gitignore', 'w') as f:
        f.write('dist')

    subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
    subprocess.run(['git', 'commit', '--quiet', '--message', joined_command], cwd=project_path, check=True)

    commit_id = _get_commit_id(project_path)
    logger.info('%s, %s, %s', project_path, joined_command, commit_id)


def publish(project_path: str, repository_name: str) -> None:
    _run(project_path, ['poetry', 'publish', *COMMON_FLAGS, '--repository', repository_name])


def remove_environment(project_path: str) -> None:
    _run(project_path, ['poetry', 'env', 'remove', *COMMON_FLAGS, '--all'])


def remove_lock(project_path: str) -> None:
    logger.info('%s, removing poetry.lock', project_path)
    os.remove(f'{project_path}/poetry.lock')


def update_all_dependencies(project_path: str) -> None:
    _run(project_path, ['poetry', 'update', *COMMON_FLAGS, '--lock'])


def update_dependency(project_path: str, dependency: str) -> None:
    _run(project_path, ['poetry', 'update', *COMMON_FLAGS, '--lock', dependency])


def main() -> None:
    now = datetime.datetime.now()
    log_filename = f'{now:%Y%m%d%H%M%S}.log'

    _setup_logger(log_filename)
    print(log_filename)

    temp_root = tempfile.mkdtemp()
    print(temp_root)

    # lorito is a direct dependency of gatito
    # gatito is a direct dependency of perrito

    LORITO_PATH = f'{temp_root}/lorito'
    GATITO_PATH = f'{temp_root}/gatito'
    PERRITO_PATH = f'{temp_root}/perrito'

    LOCAL_SOURCE_NAME = 'local'
    LOCAL_SOURCE_URL = 'http://localhost/'

    # ------------------------------------------------------------------

    for project_path in LORITO_PATH, GATITO_PATH, PERRITO_PATH:
        new(project_path)
        add_source(project_path, LOCAL_SOURCE_NAME, LOCAL_SOURCE_URL)

    add_dependency(LORITO_PATH, 'requests')
    build(LORITO_PATH)
    publish(LORITO_PATH, LOCAL_SOURCE_NAME)

    add_dependency(GATITO_PATH, 'lorito', LOCAL_SOURCE_NAME)
    build(GATITO_PATH)
    publish(GATITO_PATH, LOCAL_SOURCE_NAME)

    add_dependency(PERRITO_PATH, 'gatito', LOCAL_SOURCE_NAME)

    # ------------------------------------------------------------------

    bump_version(LORITO_PATH)
    build(LORITO_PATH)
    publish(LORITO_PATH, LOCAL_SOURCE_NAME)

    bump_version(GATITO_PATH)
    update_dependency(GATITO_PATH, 'lorito')
    build(GATITO_PATH)
    publish(GATITO_PATH, LOCAL_SOURCE_NAME)

    update_dependency(PERRITO_PATH, 'gatito')
    # update_all_dependencies(PERRITO_PATH)


if __name__ == '__main__':
    main()
