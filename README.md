# GitHub Read-Only Deploy Key Helper

Prosty helper do nadawania dostępu **read-only** do prywatnego repozytorium GitHub przez SSH Deploy Key.

## Problem

Pracujemy nad prywatnymi repozytoriami, które często się zmieniają. Chcemy móc podglądać i pobierać kod z repo drugiej osoby, ale bez ryzyka, że ktoś przypadkowo zrobi `push`, `merge` albo zmieni cudze repo.

Zwykłe zaproszenie jako collaborator w prywatnym repo osobistym GitHub może dawać zbyt szerokie uprawnienia. Dlatego używamy mechanizmu **Deploy Key** ustawionego jako **read-only**.

## Rozwiązanie

Osoba, która ma otrzymać dostęp do repo, generuje u siebie klucz SSH.

- klucz prywatny zostaje tylko u tej osoby,
- klucz publiczny przekazuje właścicielowi repo,
- właściciel repo dodaje public key w GitHub:
  `Settings → Deploy keys → Add deploy key`,
- właściciel repo **nie zaznacza** opcji `Allow write access`.

Efekt:

- repo zostaje prywatne,
- druga osoba może robić `git clone`, `git fetch`, `git pull`,
- druga osoba nie może robić `git push`.

## Jak użyć

Wymagania:

- Python 3
- zainstalowany `ssh-keygen`

Uruchom:

```bash
python3 generate_readonly_key.py
