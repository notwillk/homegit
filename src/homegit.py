#!/usr/bin/env python

"""Utility to interact with bare git repos in the home directory."""

__version__ = "0.1.4"

import sys
import os
import subprocess
import shutil
from collections import namedtuple
from enum import Enum

HOME = os.environ.get('HOME')
GIT_EXECUTABLE = os.getenv('GIT_EXECUTABLE') or shutil.which('git')
HOMEGIT_DIR = os.environ.get('HOMEGIT_DIR') or f"{HOME}/.homegit"
HOMEGIT_REPO = os.environ.get('HOMEGIT_REPO') or "default"
BARE_REPO_DIR = f"{HOMEGIT_DIR}/{HOMEGIT_REPO}"
IGNORED_ARGS = ["--bare", "--git-dir", "--work-tree"]

COMMANDS = ['INIT', 'CLONE', 'HELP', 'VERSION', 'UNTRACK']
Command = Enum('Command', COMMANDS + ['GIT'])
CONVENIENCE_COMMANDS = [
    ['--version', Command.VERSION],
    ['-v', Command.VERSION],
    ['--help', Command.HELP],
    ['-h', Command.HELP],
]
command_dict = dict(
    [[cmd.lower(), Command[cmd]] for cmd in COMMANDS] + CONVENIENCE_COMMANDS
)

ParsedCommand = namedtuple('ParsedCommand', ['command', 'ignored_args'])
ShellProcess = namedtuple('ShellProcess', ['stdout', 'stderr', 'returncode'])


class ExistingRepoDir(Exception):
    pass


class MissingRepoDir(Exception):
    pass


def execute_command(cmd, cwd=None):
    process = subprocess.Popen(
        " ".join(cmd) if isinstance(cmd, list) else cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    )
    out, err = process.communicate()
    return ShellProcess(stdout=out.decode('utf-8').strip(), stderr=err.decode('utf-8').strip(), returncode=process.returncode)


def is_within_home_dir():
    home = os.path.abspath(HOME)
    return os.path.commonprefix([os.getcwd(), home]) == home


def get_remote_origin_url():
    output = execute_command([
        GIT_EXECUTABLE,
        f"--git-dir={BARE_REPO_DIR}",
        f"--work-tree={HOME}",
        "config",
        "--get",
        "remote.origin.url"
    ])
    return output.stdout if output.returncode == 0 else None


def bare_repo_dir_exists():
    return os.path.isdir(BARE_REPO_DIR)


def checkout_repo():
    output = execute_command([
        GIT_EXECUTABLE,
        f"--git-dir={BARE_REPO_DIR}",
        f"--work-tree={HOME}",
        "checkout"
    ])
    if output.returncode != 0:
        print(f"Warning: could not checkout latest changes ({HOMEGIT_REPO}):")
        print(output.stderr)


def clone_repo(git_repo_url):
    dir_exists = bare_repo_dir_exists()
    existing_repo_url = get_remote_origin_url() if dir_exists else None

    if dir_exists:
        if existing_repo_url != git_repo_url:
            raise ExistingRepoDir

    if existing_repo_url == git_repo_url:
        print(f"Repo ({HOMEGIT_REPO}) is already cloned")
        sys.exit(0)

    try:
        os.mkdir(HOMEGIT_DIR)
    except FileExistsError:
        pass

    os.mkdir(BARE_REPO_DIR)

    command = [GIT_EXECUTABLE, 'clone', '--bare', git_repo_url, BARE_REPO_DIR]
    output = execute_command(command)
    if output.returncode != 0:
        print(f"Error initializing repo ({HOMEGIT_REPO}):")
        print(output.stderr)
        sys.exit(1)


def init_repo():
    if bare_repo_dir_exists():
        raise ExistingRepoDir

    command = [GIT_EXECUTABLE, 'init', '--bare', BARE_REPO_DIR]
    output = execute_command(command, cwd=HOMEGIT_DIR)
    if output.returncode != 0:
        print(f"Error initializing repo ({HOMEGIT_REPO}):")
        print(output.stderr)
        sys.exit(1)


def do_not_show_untracked_files():
    command = [
        GIT_EXECUTABLE,
        f"--git-dir={BARE_REPO_DIR}",
        f"--work-tree={HOME}",
        "config",
        "--local",
        "status.showUntrackedFiles",
        "no"
    ]
    output = execute_command(command, cwd=HOMEGIT_DIR)
    if output.returncode != 0:
        print(f"Error setting status.showUntrackedFiles for {HOMEGIT_REPO}:")
        print(output.stderr)
        sys.exit(1)


def run_version():
    git_version_output = execute_command([GIT_EXECUTABLE, '--version'])
    print(f"homegit version {__version__}")
    print(git_version_output.stdout)


def run_help():
    print("Usage:")
    print("homegit init")
    print("homegit untrack")
    print("homegit clone <repository_url>")
    print("homegit [standard git commands and arguments...]")


def run_init():
    try:
        init_repo()
        do_not_show_untracked_files()
        print(f"Initialized {HOMEGIT_REPO} repo")
    except ExistingRepoDir:
        sys.exit(f"Existing repo: {HOMEGIT_REPO} ({BARE_REPO_DIR})")


def run_clone():
    _exec, _cmd, git_repo_url = sys.argv

    try:
        clone_repo(git_repo_url)
        do_not_show_untracked_files()
        checkout_repo()
        print(f"Cloned {HOMEGIT_REPO} repo")
    except ExistingRepoDir:
        sys.exit(f"Existing repo: {HOMEGIT_REPO} ({BARE_REPO_DIR})")


def run_untrack():
    shutil.rmtree(BARE_REPO_DIR)
    print(f"Stopped tracking homegit repo at {BARE_REPO_DIR}")


def run_git():
    if not bare_repo_dir_exists():
        sys.exit(f"Unknown repo: {HOMEGIT_REPO} ({BARE_REPO_DIR})")
    if not is_within_home_dir():
        sys.exit(
            f"The current working directory must be run within the {HOME} directory ({os.getcwd()})")

    cmd = [
        GIT_EXECUTABLE,
        f"--git-dir={BARE_REPO_DIR}",
        f"--work-tree={HOME}"
    ] + sys.argv[1:]

    try:
        subprocess.run(cmd, shell=False, stderr=sys.stderr,
                       stdin=sys.stdin, stdout=sys.stdout, check=True)
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)


def parse_command():
    return ParsedCommand(
        command=command_dict.get(sys.argv[1], Command.GIT) if len(
            sys.argv) > 1 else None,
        ignored_args=set([arg for arg in sys.argv if arg in IGNORED_ARGS])
    )


def main():
    if HOME is None:
        sys.exit("You must set a value of the HOME environment vairable")

    parsed_command = parse_command()

    for ignored_arg in parsed_command.ignored_args:
        print(f"Ignoring \"{ignored_arg}\" argument")

    if parsed_command.command is None or parsed_command.command == Command.HELP:
        run_help()
    elif parsed_command.command == Command.VERSION:
        run_version()
    elif parsed_command.command == Command.INIT:
        run_init()
    elif parsed_command.command == Command.CLONE:
        run_clone()
    elif parsed_command.command == Command.UNTRACK:
        run_untrack()
    else:
        run_git()


if __name__ == "__main__":
    main()
