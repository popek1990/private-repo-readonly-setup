
## Proponowany skrypt `generate_readonly_key.py`

```python
#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
from pathlib import Path


BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def color(text: str, code: str) -> str:
    return f"{code}{text}{RESET}"


def print_box(title: str, lines: list[str]) -> None:
    width = max(len(title), *(len(line) for line in lines), 40) + 4

    print()
    print(color("┌" + "─" * width + "┐", BLUE))
    print(color("│", BLUE) + f" {color(title, BOLD)}".ljust(width) + color("│", BLUE))
    print(color("├" + "─" * width + "┤", BLUE))

    for line in lines:
        print(color("│", BLUE) + f" {line}".ljust(width) + color("│", BLUE))

    print(color("└" + "─" * width + "┘", BLUE))
    print()


def print_step(number: int, text: str) -> None:
    print(f"{color(str(number) + '.', GREEN)} {text}")


def require_ssh_keygen() -> None:
    if shutil.which("ssh-keygen") is None:
        print(color("Błąd: nie znaleziono programu ssh-keygen.", RED))
        print()
        print("Zainstaluj OpenSSH / Git for Windows / narzędzia SSH, a potem uruchom skrypt ponownie.")
        sys.exit(1)


def ask(prompt: str, default: str | None = None) -> str:
    if default:
        value = input(f"{prompt} [{default}]: ").strip()
        return value or default

    return input(f"{prompt}: ").strip()


def confirm(prompt: str) -> bool:
    value = input(f"{prompt} [t/N]: ").strip().lower()
    return value in {"t", "tak", "y", "yes"}


def main() -> None:
    print_box(
        "GitHub Read-Only Deploy Key Helper",
        [
            "Ten skrypt utworzy klucz SSH do dostępu read-only.",
            "Klucz prywatny zostaje tylko u Ciebie.",
            "Klucz publiczny przekażesz właścicielowi repo.",
            "Właściciel repo doda go jako Deploy Key bez write access.",
        ],
    )

    require_ssh_keygen()

    print(color("Kiedy używać tego skryptu?", BOLD))
    print("- Gdy masz dostać dostęp read-only do prywatnego repo GitHub.")
    print("- Gdy chcesz móc robić clone / fetch / pull.")
    print("- Gdy nie chcesz mieć możliwości pushowania do cudzego repo.")
    print()

    default_name = "github_readonly_deploy_key"
    key_name = ask("Podaj nazwę pliku dla klucza SSH", default_name)

    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(mode=0o700, exist_ok=True)

    private_key_path = ssh_dir / key_name
    public_key_path = ssh_dir / f"{key_name}.pub"

    if private_key_path.exists() or public_key_path.exists():
        print(color("Uwaga: taki klucz już istnieje.", YELLOW))
        print(f"Klucz prywatny: {private_key_path}")
        print(f"Klucz publiczny: {public_key_path}")
        print()

        if not confirm("Czy chcesz nadpisać istniejący klucz?"):
            print(color("Przerwano. Nie zmieniono istniejących plików.", YELLOW))
            sys.exit(0)

    comment = ask(
        "Podaj komentarz do klucza",
        "read-only-deploy-key",
    )

    print()
    print(color("Tworzę klucz SSH...", BLUE))

    command = [
        "ssh-keygen",
        "-t",
        "ed25519",
        "-C",
        comment,
        "-f",
        str(private_key_path),
        "-N",
        "",
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        print(color("Nie udało się utworzyć klucza SSH.", RED))
        sys.exit(1)

    try:
        private_key_path.chmod(0o600)
        public_key_path.chmod(0o644)
    except OSError:
        pass

    public_key = public_key_path.read_text(encoding="utf-8").strip()

    print_box(
        "Gotowe — klucz SSH został utworzony",
        [
            f"Klucz prywatny: {private_key_path}",
            f"Klucz publiczny: {public_key_path}",
            "Nie wysyłaj nikomu klucza prywatnego.",
            "Przekazujesz tylko klucz publiczny.",
        ],
    )

    print(color("PUBLIC KEY — przekaż ten tekst właścicielowi repo:", BOLD))
    print()
    print(color(public_key, GREEN))
    print()

    print_box(
        "Co ma zrobić właściciel repo na GitHubie?",
        [
            "1. Wejść w prywatne repozytorium.",
            "2. Kliknąć: Settings.",
            "3. Kliknąć: Deploy keys.",
            "4. Kliknąć: Add deploy key.",
            "5. Wkleić public key pokazany powyżej.",
            "6. NIE zaznaczać: Allow write access.",
            "7. Kliknąć: Add key.",
        ],
    )

    print(color("Po dodaniu klucza możesz sklonować repo po SSH:", BOLD))
    print()
    print("git clone git@github.com:OWNER/REPO.git")
    print()

    print(color("Dozwolone operacje:", GREEN))
    print("- git clone")
    print("- git fetch")
    print("- git pull")
    print()

    print(color("Zablokowana operacja:", RED))
    print("- git push")
    print()

    print(color("Ważne:", BOLD))
    print("Jeżeli chcecie działać w obie strony, druga osoba robi analogicznie to samo dla Twojego repo.")
    print()


if __name__ == "__main__":
    main()
