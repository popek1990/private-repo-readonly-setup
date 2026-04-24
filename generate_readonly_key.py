#!/usr/bin/env python3
from __future__ import annotations

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
    print(color("│", code) + color(title_line.ljust(width - 2), BOLD) + color("│", code))
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


def confirm(prompt: str, default_yes: bool = False) -> bool:
    suffix = "[T/n]" if default_yes else "[t/N]"
    value = input(f"{prompt} {suffix}: ").strip().lower()

    if not value:
        return default_yes

    return value in {"t", "tak", "y", "yes"}


def require_ssh_keygen() -> None:
    if shutil.which("ssh-keygen") is None:
        print_error("Nie znaleziono programu ssh-keygen.")
        print()
        print("Zainstaluj OpenSSH albo Git for Windows, a potem uruchom skrypt ponownie.")
        sys.exit(1)


def sanitize_key_name(value: str) -> str:
    value = value.strip()
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    cleaned = "".join(ch for ch in value if ch in allowed)

    if not cleaned:
        cleaned = "github_readonly_deploy_key"

    return cleaned


def normalize_repo(value: str) -> str:
    value = value.strip()
    value = value.removeprefix("https://github.com/")
    value = value.removesuffix(".git")
    value = value.strip("/")
    return value


def remove_existing_key_pair(private_key_path: Path, public_key_path: Path) -> None:
    for path in (private_key_path, public_key_path):
        if path.exists():
            path.unlink()


def generate_key(private_key_path: Path, comment: str) -> None:
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

    subprocess.run(command, check=True)


def print_owner_instructions() -> None:
    print_section("Instrukcja dla właściciela repo na GitHubie")
    print("Właściciel prywatnego repo powinien zrobić dokładnie to:")
    print()
    print("1. Wejść w swoje prywatne repozytorium na GitHubie.")
    print("2. Otworzyć: Settings → Deploy keys.")
    print("3. Kliknąć: Add deploy key.")
    print("4. W polu Title wpisać np. Kolega - read-only.")
    print("5. W pole Key wkleić public key pokazany przez ten skrypt.")
    print(color("6. NIE zaznaczać: Allow write access.", BOLD + RED))
    print("7. Kliknąć: Add key.")


def print_clone_instructions(private_key_path: Path, repo: str) -> None:
    print_section("Jak później pobierać repo")

    repo = normalize_repo(repo)
    repo_url = f"git@github.com:{repo}.git" if repo else "git@github.com:OWNER/REPO.git"

    print("Po dodaniu public key jako Deploy Key możesz klonować repo po SSH.")
    print()
    print(color("Linux / macOS / Git Bash:", BOLD))
    print(
        f'GIT_SSH_COMMAND="ssh -i {private_key_path} -o IdentitiesOnly=yes" '
        f"git clone {repo_url}"
    )
    print()
    print(color("Windows PowerShell:", BOLD))
    windows_path = str(private_key_path).replace("\\", "\\\\")
    print(f'$env:GIT_SSH_COMMAND="ssh -i {windows_path} -o IdentitiesOnly=yes"')
    print(f"git clone {repo_url}")
    print()

    print_box(
        "Dlaczego podajemy GIT_SSH_COMMAND?",
        "Dzięki temu Git używa dokładnie tego klucza SSH, który wygenerował skrypt. "
        "To jest przydatne, jeśli masz kilka różnych kluczy SSH na komputerze.",
        YELLOW,
    )


def print_security_summary(private_key_path: Path, public_key_path: Path) -> None:
    print_section("Najważniejsze zasady bezpieczeństwa")
    print_success(f"Klucz prywatny zostaje tylko u Ciebie: {private_key_path}")
    print_success(f"Przekazujesz tylko klucz publiczny: {public_key_path}")
    print_warning("Nigdy nie wysyłaj pliku bez końcówki .pub.")
    print_warning("Jeśli klucz prywatny wycieknie, właściciel repo powinien usunąć Deploy Key z GitHuba.")
    print_warning("Deploy Key działa dla konkretnego repozytorium. Dla kolejnego repo najlepiej wygenerować osobny klucz.")


def main() -> None:
    print_header(
        "Private Repo Read-Only Setup",
        "Generator klucza SSH do bezpiecznego dostępu read-only do prywatnego repo GitHub.",
    )

    print_box(
        "Co robi ten skrypt?",
        "Tworzy parę kluczy SSH. Klucz prywatny zostaje na komputerze osoby, która ma mieć dostęp. "
        "Klucz publiczny trzeba przekazać właścicielowi repo. Właściciel dodaje go w GitHub jako Deploy Key "
        "i nie zaznacza opcji Allow write access.",
    )

    print_success("Dozwolone po konfiguracji: git clone, git fetch, git pull.")
    print_error("Zablokowane: git push do repo właściciela.")
    print()

    require_ssh_keygen()

    default_name = "github_readonly_deploy_key"
    key_name = sanitize_key_name(ask("Nazwa pliku klucza SSH", default_name))

    repo = ask(
        "Repo, do którego ma być dostęp read-only, np. popek1990/moje-repo. Możesz zostawić puste",
        "",
    )
    repo = normalize_repo(repo)

    default_comment = f"read-only-deploy-key:{repo}" if repo else "read-only-deploy-key"
    comment = ask("Komentarz do klucza SSH", default_comment)

    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(mode=0o700, exist_ok=True)

    private_key_path = ssh_dir / key_name
    public_key_path = ssh_dir / f"{key_name}.pub"

    if private_key_path.exists() or public_key_path.exists():
        print_warning("Taki klucz już istnieje.")
        print(f"Klucz prywatny: {private_key_path}")
        print(f"Klucz publiczny: {public_key_path}")
        print()

        if not confirm("Czy chcesz nadpisać istniejący klucz?"):
            print_warning("Przerwano. Nie zmieniono istniejących plików.")
            sys.exit(0)

        remove_existing_key_pair(private_key_path, public_key_path)

    print()
    print(color("Generuję klucz SSH...", BLUE))

    try:
        generate_key(private_key_path, comment)
    except subprocess.CalledProcessError:
        print_error("Nie udało się utworzyć klucza SSH.")
        sys.exit(1)

    try:
        private_key_path.chmod(0o600)
        public_key_path.chmod(0o644)
    except OSError:
        # Na Windowsie chmod może zachowywać się inaczej. To nie blokuje działania helpera.
        pass

    public_key = public_key_path.read_text(encoding="utf-8").strip()

    print_section("Gotowe")
    print_success("Klucz SSH został utworzony.")
    print(f"Klucz prywatny: {color(str(private_key_path), BOLD)}")
    print(f"Klucz publiczny: {color(str(public_key_path), BOLD)}")

    print_security_summary(private_key_path, public_key_path)

    print_section("PUBLIC KEY — przekaż ten tekst właścicielowi repo")
    print(color("Skopiuj i wyślij tylko poniższą jedną linię:", BOLD))
    print()
    print_line("─", 78, GREEN)
    print(color(public_key, GREEN))
    print_line("─", 78, GREEN)

    print_owner_instructions()
    print_clone_instructions(private_key_path, repo)

    print_section("Podsumowanie")
    print("Jeśli chcecie działać w obie strony, druga osoba uruchamia ten sam skrypt u siebie,")
    print("a Ty dodajesz jej public key jako Deploy Key w swoim repo.")
    print()
    print_success("Gotowe. Private repo zostaje prywatne, a dostęp jest tylko do odczytu.")
    print()


if __name__ == "__main__":
    main()
