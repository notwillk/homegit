#!/usr/bin/env python

"""Utility to interact with bare git repos in the home directory."""

__version__ = "0.1.4"

from contextlib import contextmanager
import sys
import os
import subprocess
import shutil
from collections import namedtuple
from enum import Enum

HOME = os.environ.get('HOME')
VERBOSE = os.environ.get('VERBOSE') == "true"
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
    """The repo directory exists"""


class MissingRepoDir(Exception):
    """The repo directory does not exist"""


class CloneFailure(Exception):
    """The repo failed to clone"""


class InitFailure(Exception):
    """The repo failed to initialize"""


class SettingShowUntrackedFilesFailure(Exception):
    """Failed to set status.showUntrackedFiles"""


def run(*args, **kwargs):
    """Wrapper for subprocess.run that adds verbose logging"""
    if VERBOSE:
        naively_escaped_command_args = [arg if " " not in arg else f"\"{arg}\"" for arg in args[0]]
        command = " ".join(naively_escaped_command_args)
        print(f"Running: {command}")
    kwargs.setdefault('check', True)
    return subprocess.run(*args, **kwargs)


def is_within_home_dir():
    """Utility to determine if the CWD is within the HOME directory"""
    home = os.path.abspath(HOME)
    return os.path.commonprefix([os.getcwd(), home]) == home


def get_remote_origin_url():
    """Utility to get the remote origin URL"""
    command = [
        GIT_EXECUTABLE,
        f"--git-dir={BARE_REPO_DIR}",
        f"--work-tree={HOME}",
        "config",
        "--get",
        "remote.origin.url"
    ]
    completed_process = run(command, capture_output=True, check=False)
    return completed_process.stdout if completed_process.returncode == 0 else None


def bare_repo_dir_exists():
    """Utility to get determine if the repo directory exists"""
    return os.path.isdir(BARE_REPO_DIR)


@contextmanager
def friendly_error_messages():
    """Print human readable messages for known exceptions"""
    try:
        yield
    except CloneFailure:
        sys.exit(f"Error cloning repo ({HOMEGIT_REPO})")
    except ExistingRepoDir:
        sys.exit(f"Existing repo: {HOMEGIT_REPO} ({BARE_REPO_DIR})")
    except FileNotFoundError:
        sys.exit(
            f"Error executing git: No such file or directory: {GIT_EXECUTABLE}")
    except InitFailure:
        sys.exit(f"Error initializing repo ({HOMEGIT_REPO})")
    except SettingShowUntrackedFilesFailure:
        sys.exit(f"Error setting status.showUntrackedFiles for {HOMEGIT_REPO}")


def checkout_repo() -> bool:
    """Action to checkout the repo"""
    command = [
        GIT_EXECUTABLE,
        f"--git-dir={BARE_REPO_DIR}",
        f"--work-tree={HOME}",
        "checkout"
    ]
    completed_process = run(command, stderr=sys.stderr, check=False)
    return completed_process.returncode == 0


def clone_repo(git_repo_url):
    """Action to clone the repo"""
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

    try:
        completed_process = run(command, stderr=sys.stderr)
    except subprocess.CalledProcessError as exception:
        raise CloneFailure from exception

    if completed_process.returncode != 0:
        raise CloneFailure


def init_repo():
    """Action to initialize the repo"""
    if bare_repo_dir_exists():
        raise ExistingRepoDir

    command = [GIT_EXECUTABLE, 'init', '--bare', BARE_REPO_DIR]
    try:
        completed_process = run(command, cwd=HOMEGIT_DIR, stderr=sys.stderr)
    except subprocess.CalledProcessError as exception:
        raise InitFailure from exception

    if completed_process.returncode != 0:
        raise InitFailure


def do_not_show_untracked_files():
    """Action to set the showUntrackedFiles value to 'no'"""
    command = [
        GIT_EXECUTABLE,
        f"--git-dir={BARE_REPO_DIR}",
        f"--work-tree={HOME}",
        "config",
        "--local",
        "status.showUntrackedFiles",
        "no"
    ]
    try:
        completed_process = run(command, cwd=HOMEGIT_DIR, stderr=sys.stderr)
    except subprocess.CalledProcessError as exception:
        raise SettingShowUntrackedFilesFailure from exception

    if completed_process.returncode != 0:
        raise SettingShowUntrackedFilesFailure


def run_version():
    """Command to get the latest versions"""
    print(f"homegit version {__version__}")
    command = [GIT_EXECUTABLE, '--version']
    run(command, stderr=sys.stderr, stdout=sys.stdout, check=False)


def run_help():
    """Command to display the help command"""
    print("Usage:")
    print("homegit init")
    print("homegit untrack")
    print("homegit clone <repository_url>")
    print("homegit [standard git commands and arguments...]")


def run_init():
    """Command to initialize the repo"""
    with friendly_error_messages():
        init_repo()
        do_not_show_untracked_files()
        print(f"Initialized {HOMEGIT_REPO} repo")


def run_clone():
    """Command to clone the repo"""
    _exec, _cmd, git_repo_url = sys.argv

    with friendly_error_messages():
        clone_repo(git_repo_url)
        do_not_show_untracked_files()
        if not checkout_repo():
            print(f"Warning: could not checkout latest changes ({HOMEGIT_REPO})")
        print(f"Cloned {HOMEGIT_REPO} repo")


def run_untrack():
    """Command to untrack the repo"""
    shutil.rmtree(BARE_REPO_DIR)
    print(f"Stopped tracking homegit repo at {BARE_REPO_DIR}")


def run_git():
    """Command to run underlying git command"""
    if not bare_repo_dir_exists():
        sys.exit(f"Unknown repo: {HOMEGIT_REPO} ({BARE_REPO_DIR})")
    if not is_within_home_dir():
        cwd = os.getcwd()
        sys.exit(f"The current working directory must be run within the {HOME} directory ({cwd})")

    command = [
        GIT_EXECUTABLE,
        f"--git-dir={BARE_REPO_DIR}",
        f"--work-tree={HOME}"
    ] + sys.argv[1:]

    with friendly_error_messages():
        try:
            completed_process = run(command, stderr=sys.stderr, stdin=sys.stdin, stdout=sys.stdout)
        except subprocess.CalledProcessError as exception:
            raise SettingShowUntrackedFilesFailure from exception

    sys.exit(completed_process.returncode)


def parse_command():
    """Utility to parse the CLI arguments"""
    return ParsedCommand(
        command=command_dict.get(sys.argv[1], Command.GIT) if len(
            sys.argv) > 1 else None,
        ignored_args=set([arg for arg in sys.argv if arg in IGNORED_ARGS])
    )


def main():
    """Entrypoint for the script"""
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
