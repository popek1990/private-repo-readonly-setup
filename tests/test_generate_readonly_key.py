from __future__ import annotations

import contextlib
import io
import os
import shlex
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import generate_readonly_key as helper


class RepositoryInputTests(unittest.TestCase):
    def test_supported_github_urls(self):
        for value in (
            " owner/my-repo ",
            "https://github.com/owner/my-repo",
            "https://github.com/owner/my-repo.git/",
            "git@github.com:owner/my-repo.git",
            "ssh://git@github.com/owner/my-repo.git",
        ):
            with self.subTest(value=value):
                self.assertEqual(helper.normalize_repo(value), "owner/my-repo")

    def test_empty_repository_is_optional(self):
        self.assertEqual(helper.normalize_repo("  "), "")

    def test_invalid_repository_is_rejected(self):
        for value in (
            "owner",
            "owner/repo/extra",
            "https://example.com/owner/repo",
            "owner/repo;echo unsafe",
            "owner/$(whoami)",
            "owner/..",
            "owner/repo?tab=readme",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                helper.normalize_repo(value)


class KeyFileTests(unittest.TestCase):
    def test_existing_private_or_public_file_is_preserved(self):
        for suffix in ("", ".pub"):
            with (
                self.subTest(suffix=suffix),
                tempfile.TemporaryDirectory() as directory,
            ):
                private_key = Path(directory) / "deploy_key"
                existing = Path(f"{private_key}{suffix}")
                existing.write_text("existing file", encoding="utf-8")
                with patch.object(helper.subprocess, "run") as run:
                    with self.assertRaises(FileExistsError):
                        helper.generate_key(private_key, "test")
                    run.assert_not_called()
                self.assertEqual(existing.read_text(encoding="utf-8"), "existing file")

    @unittest.skipIf(os.name == "nt", "Symlink creation may require Windows privileges")
    def test_dangling_symlink_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            private_key = Path(directory) / "deploy_key"
            private_key.symlink_to(Path(directory) / "missing")
            with self.assertRaises(FileExistsError):
                helper.generate_key(private_key, "test")
            self.assertTrue(private_key.is_symlink())


class MainTests(unittest.TestCase):
    def run_helper(self, home, answers):
        output = io.StringIO()
        with (
            patch.object(helper.Path, "home", return_value=home),
            patch("builtins.input", side_effect=answers),
            patch.object(helper.shutil, "which", return_value="ssh-keygen"),
            contextlib.redirect_stdout(output),
        ):
            status = helper.main()
        return status, output.getvalue()

    def test_invalid_key_names_do_not_create_files(self):
        for value in (
            ".",
            "..",
            "../key",
            "my key",
            "key.pub",
            "config",
            "known_hosts",
        ):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                status, output = self.run_helper(home, [value, "owner/repo", "test"])
                self.assertEqual(status, 1)
                self.assertEqual(list(home.iterdir()), [])
                self.assertIn("key", output.lower())

    def test_existing_key_is_not_overwritten_even_if_user_answers_yes(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            ssh_directory = home / ".ssh"
            ssh_directory.mkdir()
            key = ssh_directory / "deploy_key"
            key.write_text("existing file", encoding="utf-8")
            with patch.object(helper, "generate_key", wraps=helper.generate_key):
                status, output = self.run_helper(
                    home, ["deploy_key", "owner/repo", "test", "yes"]
                )
            self.assertEqual(status, 1)
            self.assertEqual(key.read_text(encoding="utf-8"), "existing file")
            self.assertIn("different", output)

    def test_invalid_repository_does_not_create_files(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            status, output = self.run_helper(
                home, ["deploy_key", "owner/repo;echo unsafe", "test"]
            )
            self.assertEqual(status, 1)
            self.assertEqual(list(home.iterdir()), [])
            self.assertIn("OWNER/REPO", output)

    def test_missing_ssh_keygen_has_actionable_error(self):
        output = io.StringIO()
        with (
            patch.object(helper.shutil, "which", return_value=None),
            contextlib.redirect_stdout(output),
        ):
            status = helper.main()
        self.assertEqual(status, 1)
        self.assertIn("OpenSSH", output.getvalue())

    def test_generation_failure_does_not_report_success(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                helper,
                "generate_key",
                side_effect=subprocess.CalledProcessError(1, "ssh-keygen"),
            ):
                status, output = self.run_helper(
                    Path(directory), ["deploy_key", "", "test"]
                )
            self.assertEqual(status, 1)
            self.assertNotIn("Key pair created", output)

    def test_filesystem_failure_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                helper.Path, "mkdir", side_effect=PermissionError("Access denied")
            ):
                status, output = self.run_helper(
                    Path(directory), ["deploy_key", "", "test"]
                )
            self.assertEqual(status, 1)
            self.assertIn("Access denied", output)

    @unittest.skipIf(os.name == "nt", "POSIX file permissions only")
    def test_private_key_permission_failure_does_not_report_success(self):
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(helper, "generate_key"),
                patch.object(
                    helper.Path, "chmod", side_effect=PermissionError("Access denied")
                ),
            ):
                status, output = self.run_helper(
                    Path(directory), ["deploy_key", "", "test"]
                )
            self.assertEqual(status, 1)
            self.assertIn("Access denied", output)
            self.assertNotIn("Key pair created", output)

    def test_interrupted_input_exits_without_traceback(self):
        for exception in (EOFError, KeyboardInterrupt):
            with (
                self.subTest(exception=exception),
                tempfile.TemporaryDirectory() as directory,
            ):
                status, output = self.run_helper(Path(directory), exception())
                self.assertEqual(status, 130)
                self.assertIn("Cancelled", output)

    @unittest.skipUnless(shutil.which("ssh-keygen"), "OpenSSH is required")
    def test_real_key_generation_prints_only_public_key(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            status, output = self.run_helper(
                home, ["deploy_key", "owner/repo", "test-key"]
            )
            self.assertEqual(status, 0)
            private_key = home / ".ssh" / "deploy_key"
            public_key = (
                private_key.with_suffix(".pub").read_text(encoding="utf-8").strip()
            )
            self.assertTrue(public_key.startswith("ssh-ed25519 "))
            self.assertIn(public_key, output)
            self.assertNotIn("PRIVATE KEY-----", output)
            self.assertNotIn("\033[", output)
            derived = subprocess.run(
                ["ssh-keygen", "-y", "-f", str(private_key)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.split()
            self.assertEqual(derived[:2], public_key.split()[:2])
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(private_key.stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE(private_key.parent.stat().st_mode), 0o700)


class CloneCommandTests(unittest.TestCase):
    def commands(self, key):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            helper.print_clone_instructions(key, "owner/repo")
        return [
            line
            for line in helper.strip_ansi(output.getvalue()).splitlines()
            if line.startswith("git clone ")
        ]

    def test_posix_command_preserves_key_path_and_stores_config(self):
        key = Path("/tmp/Ada's projects/$example;file/.ssh/deploy_key")
        commands = self.commands(key)
        self.assertEqual(len(commands), 2)
        arguments = shlex.split(commands[0])
        self.assertEqual(arguments[:3], ["git", "clone", "--config"])
        config = arguments[3]
        self.assertTrue(config.startswith("core.sshCommand="))
        ssh_arguments = shlex.split(config.split("=", 1)[1])
        self.assertEqual(ssh_arguments[ssh_arguments.index("-i") + 1], key.as_posix())
        self.assertIn("IdentitiesOnly=yes", ssh_arguments)
        self.assertEqual(ssh_arguments[ssh_arguments.index("-F") + 1], "none")
        self.assertEqual(arguments[-1], "git@github.com:owner/repo.git")

    @unittest.skipUnless(
        shutil.which("ssh") and shutil.which("ssh-keygen") and os.name != "nt",
        "POSIX OpenSSH is required",
    )
    def test_ssh_command_selects_only_the_generated_key(self):
        with tempfile.TemporaryDirectory() as directory:
            key = Path(directory) / "Ada's projects" / "$example;file" / "deploy_key"
            key.parent.mkdir(parents=True)
            helper.generate_key(key, "test")
            config = shlex.split(self.commands(key)[0])[3].split("=", 1)[1]
            # -G prints configuration without opening a connection.
            result = subprocess.run(
                ["sh", "-c", config + " -G git@github.com"],
                check=True,
                capture_output=True,
                text=True,
            )
            identities = [
                line.removeprefix("identityfile ")
                for line in result.stdout.splitlines()
                if line.startswith("identityfile ")
            ]
            self.assertEqual(identities, [key.as_posix()])
            self.assertIn("identitiesonly yes", result.stdout)

    @unittest.skipUnless(
        shutil.which("git") and os.name != "nt", "POSIX Git is required"
    )
    def test_printed_posix_command_saves_identity_for_future_fetches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root / "remote" / "repo.git"
            remote.parent.mkdir()
            subprocess.run(
                ["git", "init", "--bare", str(remote)], check=True, capture_output=True
            )
            key = root / "Ada's projects" / "$example;file" / ".ssh" / "deploy_key"
            command = self.commands(key)[0].replace(
                "git@github.com:owner/repo.git", shlex.quote(str(remote))
            )
            subprocess.run(
                ["sh", "-c", command], cwd=root, check=True, capture_output=True
            )
            config = subprocess.run(
                [
                    "git",
                    "-C",
                    str(root / "repo"),
                    "config",
                    "--local",
                    "--get",
                    "core.sshCommand",
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            arguments = shlex.split(config)
            self.assertEqual(arguments[arguments.index("-i") + 1], key.as_posix())

    @unittest.skipUnless(
        shutil.which("pwsh") or shutil.which("powershell"), "PowerShell is required"
    )
    def test_printed_powershell_command_saves_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root / "remote" / "repo.git"
            remote.parent.mkdir()
            subprocess.run(
                ["git", "init", "--bare", str(remote)], check=True, capture_output=True
            )
            key = root / "Ada's projects" / ".ssh" / "deploy_key"
            command = self.commands(key)[1].replace(
                "git@github.com:owner/repo.git", remote.as_uri()
            )
            powershell = shutil.which("pwsh") or shutil.which("powershell")
            subprocess.run(
                [powershell, "-NoProfile", "-NonInteractive", "-Command", command],
                cwd=root,
                check=True,
                capture_output=True,
            )
            config = subprocess.run(
                [
                    "git",
                    "-C",
                    str(root / "repo"),
                    "config",
                    "--local",
                    "--get",
                    "core.sshCommand",
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            arguments = shlex.split(config)
            self.assertEqual(arguments[arguments.index("-i") + 1], key.as_posix())


if __name__ == "__main__":
    unittest.main()
