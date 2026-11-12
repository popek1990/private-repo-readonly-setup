# Private Repo Read-Only Setup

**Clone a private GitHub repository without granting push access.**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

A small Python helper that generates an SSH deploy key and walks you through
setting up read-only access to one GitHub repository. Useful for code review,
pulling code onto a server, or sharing a private project with another developer.

- Generates an Ed25519 key pair locally using OpenSSH.
- Prints the public key, instructions for the repository owner, and clone commands.
- Saves the key choice in the clone so later fetches and pulls use it too.
- Uses only the Python standard library. No packages or GitHub API token needed.

> GitHub enforces read-only access when the owner adds the public key as a deploy
> key with **Allow write access unchecked**. Running this helper alone does not
> grant access or change repository permissions.

## Quick start

Run this on the computer or server that needs access. You need **Python 3.10+**,
**Git**, and **OpenSSH** (`ssh-keygen` and `ssh` available in your terminal).

Linux, macOS, or Git Bash:

```bash
git clone https://github.com/popek1990/private-repo-readonly-setup.git
cd private-repo-readonly-setup
python3 generate_readonly_key.py
```

Windows PowerShell:

```powershell
git clone https://github.com/popek1990/private-repo-readonly-setup.git
cd private-repo-readonly-setup
py generate_readonly_key.py
```

On Windows, PowerShell needs OpenSSH on `PATH`. Git Bash from Git for Windows is
another option; use whichever Python launcher is installed (`python3`, `python`,
or `py`).

The helper asks for a key filename, a repository, and a comment. Press Enter to
accept a default. The repository is optional; when provided, it can be
`OWNER/REPO`, an HTTPS URL, or an SSH URL from GitHub.

Example session, with the output shortened and the public key omitted:

```text
SSH key filename [github_readonly_deploy_key]: review_laptop
GitHub repository (OWNER/REPO or URL; optional) []: octocat/private-project
SSH key comment [read-only-deploy-key:octocat/private-project]:

Generating SSH key pair...
...
Private key: /home/alex/.ssh/review_laptop
Public key:  /home/alex/.ssh/review_laptop.pub
...
```

Keys are saved under `~/.ssh`. The helper refuses to overwrite an existing file;
choose a different filename if you already have a key with that name.

## Give the public key to the repository owner

Share the single `ssh-ed25519 ...` line printed by the helper, or the contents of
the `.pub` file. **Keep the file without `.pub` on your own machine.**

An administrator of the target repository then:

1. Opens the repository on GitHub.
2. Goes to **Settings > Deploy keys > Add deploy key**.
3. Enters a descriptive title, such as `Review laptop (read-only)`.
4. Pastes the public key into the **Key** field.
5. Leaves **Allow write access unchecked** and clicks **Add key**.

See GitHub's [deploy key documentation](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys)
for details.

## Clone once, then fetch and pull

After the owner adds the key, copy the `git clone --config ...` command printed
for your shell. If you left the repository blank, replace `OWNER/REPO` first.

The command stores `core.sshCommand` in the new clone's local Git configuration.
That keeps the key selection available for later commands. Inside the clone, run:

```bash
git fetch
git pull --ff-only
```

You can check read access with `git ls-remote origin`. GitHub rejects pushes
authenticated with the read-only deploy key. You can still edit files and commit
locally.

The generated SSH command ignores SSH configuration files (`-F none`) to avoid
offering other configured identities. If you use a custom SSH proxy, adapt the
command to your setup. An existing `GIT_SSH_COMMAND` environment variable takes
precedence over the saved setting; unset it before using these commands.

The helper prints instructions. It does not connect to GitHub, register a deploy
key, clone the target repository, or edit your global Git or SSH configuration.

## Security and scope

- Read-only access applies to this deploy key. Other SSH keys, tokens, or account
  permissions may still allow writes. This tool is not a sandbox for a user or
  process that already has other credentials.
- Keys are generated **without a passphrase**. Anyone who obtains the private
  file can use it. To add a passphrase, run `ssh-keygen -p -f PATH_TO_PRIVATE_KEY`
  with your actual key path, quoted if it contains spaces. OpenSSH prompts for
  the passphrase; you can use `ssh-agent` to avoid entering it on every pull.
- Use a different key pair for each repository. GitHub deploy keys are scoped
  to a single repository and cannot be reused across repositories.
- Deploy keys do not expire automatically. Remove the key in the repository's
  **Settings > Deploy keys** when access is no longer needed or the private key
  is exposed. Removing a person's repository membership does not revoke a deploy key.
- Keep private keys out of Git, issue reports, chat messages, and screenshots.
  On Linux and macOS, the helper sets the new private key's permissions to `600`.
  On Windows, access is governed by filesystem permissions; this helper does not
  manage Windows ACLs.

## Troubleshooting

**`ssh-keygen was not found`**

Install OpenSSH and open a new terminal. On Windows, you can also use Git Bash
from Git for Windows. The helper checks for `ssh-keygen` before creating files.

**`Permission denied (publickey)` or `Repository not found`**

Check the repository name, ask the owner to confirm that they added this public
key to that repository, and use the clone command printed by the helper.
If you exported `GIT_SSH_COMMAND` earlier, remove it with `unset GIT_SSH_COMMAND`
in Bash or `Remove-Item Env:GIT_SSH_COMMAND -ErrorAction SilentlyContinue` in
PowerShell before retrying.

**`Key is already in use` on GitHub**

Generate a new pair with a different filename for this repository. Do not reuse
an account key or a deploy key already assigned elsewhere.

**The key filename already exists**

Run the helper again with a new filename. Keep the old key until you know which
repositories or services still use it.

**SSH asks whether to trust GitHub's host key**

Compare the fingerprint with
[GitHub's published SSH fingerprints](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints)
before accepting it.

## Contributing

Bug reports and small, focused improvements are welcome. See
[CONTRIBUTING.md](CONTRIBUTING.md) for reporting and testing instructions.

Run the tests without installing any Python packages:

```bash
python3 -m unittest discover -s tests -v
```

Tests generate disposable keys in temporary directories and use local Git
repositories. They do not need a GitHub account or access to a private repository.
The GitHub Actions workflow is configured for Linux, macOS, and Windows.

If this helper saved you time, consider giving the repository a star.

## License

[MIT](LICENSE).

<!-- Documentation reviewed: 2026-11-12. -->
