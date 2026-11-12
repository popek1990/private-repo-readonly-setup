#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import wrap


BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def color(text: str, code: str) -> str:
    if not sys.stdout.isatty() or "NO_COLOR" in os.environ:
        return text
    return f"{code}{text}{RESET}"


def strip_ansi(text: str) -> str:
    for code in (BLUE, GREEN, YELLOW, RED, BOLD, DIM, RESET):
        text = text.replace(code, "")
    return text


def print_line(char: str = "─", width: int = 78, code: str = BLUE) -> None:
    print(color(char * width, code))


def print_header(title: str, subtitle: str | None = None) -> None:
    print()
    print_line("═", 78, BLUE)
    print(color(title, BOLD + BLUE))
    if subtitle:
        print(subtitle)
    print_line("═", 78, BLUE)
    print()


def print_section(title: str) -> None:
    print()
    print(color(f"## {title}", BOLD + BLUE))
    print_line("─", 78, BLUE)


def print_success(text: str) -> None:
    print(color(f"✓ {text}", GREEN))


def print_warning(text: str) -> None:
    print(color(f"! {text}", YELLOW))


def print_error(text: str) -> None:
    print(color(f"✗ {text}", RED))


def print_box(title: str, body: str, code: str = BLUE) -> None:
    width = 78
    print()
    print(color("┌" + "─" * (width - 2) + "┐", code))
    title_line = f" {title} "
    print(
        color("│", code) + color(title_line.ljust(width - 2), BOLD) + color("│", code)
    )
    print(color("├" + "─" * (width - 2) + "┤", code))

    for paragraph in body.splitlines():
        if not paragraph.strip():
            print(color("│", code) + " " * (width - 2) + color("│", code))
            continue

        for line in wrap(paragraph, width=width - 4):
            print(color("│", code) + f" {line}".ljust(width - 2) + color("│", code))

    print(color("└" + "─" * (width - 2) + "┘", code))
    print()


def ask(prompt: str, default: str | None = None) -> str:
    if default is not None:
        value = input(f"{prompt} [{default}]: ").strip()
        return value or default
    return input(f"{prompt}: ").strip()


def require_ssh_keygen() -> None:
    if shutil.which("ssh-keygen") is None:
        raise FileNotFoundError(
            "ssh-keygen was not found. Install OpenSSH or use Git Bash from "
            "Git for Windows, then run this script again."
        )


def validate_key_name(value: str) -> str:
    value = value.strip()
    reserved = {
        "config",
        "known_hosts",
        "known_hosts2",
        "authorized_keys",
        "authorized_keys2",
        "environment",
        "rc",
    }
    if (
        not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value)
        or value.lower() in reserved
        or value.lower().endswith(".pub")
        or value.endswith(".")
    ):
        raise ValueError(
            "Choose a key filename starting with a letter or number, using only "
            "letters, numbers, dots, underscores and hyphens. Do not use an SSH "
            "configuration filename, a trailing dot, or the .pub extension."
        )
    return value


def normalize_repo(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    for prefix in ("https://github.com/", "git@github.com:", "ssh://git@github.com/"):
        if value.startswith(prefix):
            value = value.removeprefix(prefix)
            break
    value = value.rstrip("/").removesuffix(".git")
    if not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+", value
    ) or value.split("/")[-1] in {".", ".."}:
        raise ValueError(
            "Enter OWNER/REPO or a GitHub HTTPS/SSH repository URL, or leave it blank."
        )
    return value


def generate_key(private_key_path: Path, comment: str) -> None:
    public_key_path = Path(f"{private_key_path}.pub")
    for path in (private_key_path, public_key_path):
        if path.exists() or path.is_symlink():
            raise FileExistsError(
                f"A file already exists at {path}. Run again with a different key filename."
            )

    command = [
        "ssh-keygen",
        "-q",
        "-t",
        "ed25519",
        "-C",
        comment,
        "-f",
        str(private_key_path),
        "-N",
        "",
    ]

    # No passphrase prompt is expected. EOF also prevents accepting an overwrite
    # if another process creates the private key after the checks above.
    subprocess.run(command, check=True, stdin=subprocess.DEVNULL)


def print_owner_instructions() -> None:
    print_section("For the repository owner")
    print("An administrator of the target GitHub repository must:")
    print()
    print("1. Open the target repository on GitHub.")
    print("2. Open Settings > Deploy keys > Add deploy key.")
    print("3. Give the key a descriptive title, such as Review laptop (read-only).")
    print("4. Paste the public key printed above into the Key field.")
    print(color("5. Leave Allow write access UNCHECKED.", BOLD + RED))
    print("6. Click Add key.")


def shell_quote(value: str) -> str:
    # Single quotes and backslash escapes also survive Windows PowerShell's
    # native argument handling when passed on to Git's POSIX shell.
    return "'" + value.replace("'", "'\\''") + "'"


def powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def print_clone_instructions(private_key_path: Path, repo: str) -> None:
    print_section("Clone and pull with this key")

    repo = normalize_repo(repo)
    repo_url = f"git@github.com:{repo}.git" if repo else "git@github.com:OWNER/REPO.git"

    ssh_command = f"ssh -F none -i {shell_quote(private_key_path.as_posix())} -o IdentitiesOnly=yes"
    config = f"core.sshCommand={ssh_command}"

    print("After the owner adds the deploy key, run the command for your shell.")
    if not repo:
        print("Replace OWNER/REPO with the target repository.")
    print()
    print(color("Linux / macOS / Git Bash:", BOLD))
    print(f"git clone --config {shlex.quote(config)} {shlex.quote(repo_url)}")
    print()
    print(color("Windows PowerShell:", BOLD))
    print(f"git clone --config {powershell_quote(config)} {powershell_quote(repo_url)}")
    print()

    print_box(
        "The key choice stays with this clone",
        "Git saves core.sshCommand inside the cloned repository. Later git fetch "
        "and git pull commands use the same key. The command ignores SSH config "
        "files so other configured identities are not offered. Custom proxy "
        "settings may need manual adjustment. An existing GIT_SSH_COMMAND "
        "environment variable overrides this setting; unset it first.",
        YELLOW,
    )


def print_security_summary(private_key_path: Path, public_key_path: Path) -> None:
    print_section("Keep the private key private")
    print_success(f"Keep on this machine: {private_key_path}")
    print_success(f"Share only the public key: {public_key_path}")
    print_warning(
        "This key has no passphrase. You can add one later with ssh-keygen -p."
    )
    print_warning("If the private key is exposed, remove its deploy key from GitHub.")
    print_warning("Use a separate key pair for each repository.")


def run_setup() -> None:
    print_header(
        "Private Repo Read-Only Setup",
        "Set up a GitHub SSH deploy key for read-only repository access.",
    )

    print_box(
        "Run this on the machine that needs access",
        "This helper creates an Ed25519 SSH key pair locally, without a passphrase. "
        "Keep the private key here and share only the public key with the repository "
        "owner. The owner adds it as a deploy key with Allow write access unchecked. "
        "The helper does not contact GitHub or grant access by itself.",
    )

    print_success("With a read-only deploy key: git clone, git fetch and git pull.")
    print_warning("GitHub rejects git push authenticated with that read-only key.")
    print()

    require_ssh_keygen()

    default_name = "github_readonly_deploy_key"
    key_name = validate_key_name(ask("SSH key filename", default_name))

    repo = ask(
        "GitHub repository (OWNER/REPO or URL; optional)",
        "",
    )
    repo = normalize_repo(repo)

    default_comment = f"read-only-deploy-key:{repo}" if repo else "read-only-deploy-key"
    comment = ask("SSH key comment", default_comment)

    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(mode=0o700, exist_ok=True)

    private_key_path = ssh_dir / key_name
    public_key_path = ssh_dir / f"{key_name}.pub"

    print()
    print(color("Generating SSH key pair...", BLUE))
    generate_key(private_key_path, comment)

    if os.name != "nt":
        private_key_path.chmod(0o600)
        public_key_path.chmod(0o644)

    public_key = public_key_path.read_text(encoding="utf-8").strip()

    print_section("Key pair created")
    print_success("Your local SSH key pair is ready.")
    print(f"Private key: {color(str(private_key_path), BOLD)}")
    print(f"Public key:  {color(str(public_key_path), BOLD)}")

    print_security_summary(private_key_path, public_key_path)

    print_section("PUBLIC KEY: share this with the repository owner")
    print(color("Copy only the single line below:", BOLD))
    print()
    print_line("─", 78, GREEN)
    print(color(public_key, GREEN))
    print_line("─", 78, GREEN)

    print_owner_instructions()
    print_clone_instructions(private_key_path, repo)

    print_section("Next step")
    print(
        "Ask the repository owner to add the public key, then use the clone command above."
    )
    print("Read-only access starts only after the owner completes the GitHub setup.")
    print()


def main() -> int:
    try:
        run_setup()
    except (KeyboardInterrupt, EOFError):
        print()
        print_warning("Cancelled.")
        return 130
    except subprocess.CalledProcessError:
        print_error(
            "ssh-keygen could not create the key pair. Check its error message above."
        )
        return 1
    except (OSError, ValueError) as error:
        print_error(str(error))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
