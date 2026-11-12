# Contributing

Keep this helper easy to inspect and run: one Python script, the standard
library, and the OpenSSH tools already used by Git.

## Report a problem

[Open an issue](https://github.com/popek1990/private-repo-readonly-setup/issues/new)
with your operating system, shell, Python version, what you tried, and what
happened. Include the exact error message after removing personal paths and
private repository names. Do not include private keys or tokens.

For a feature request, describe the setup you need and where the current
workflow falls short.

## Make a change

1. Fork the repository and create a branch for your change.
2. Update the README if prompts, commands, requirements, or behavior change.
3. Add a regression test for a bug that affects key files, input validation,
   or generated commands.
4. Run the tests and open a pull request explaining the problem and result.

```bash
python3 -m unittest discover -s tests -v
```

Use `py` instead of `python3` on Windows if needed. Git and `ssh-keygen` must be
on `PATH` for integration tests. The PowerShell test runs when `pwsh` or
`powershell` is available; otherwise it is skipped.

All test keys belong in temporary directories. Tests must not modify the user's
actual `~/.ssh`, call GitHub, or require real repository credentials.

The CI workflow runs the suite on Linux, macOS, and Windows with Python 3.10 and
3.14. If you have Ruff installed, also run:

```bash
ruff check generate_readonly_key.py tests
ruff format --check generate_readonly_key.py tests
```

<!-- Documentation reviewed: 2026-11-12. -->
