# Private Repo Read-Only Setup

Prosty helper do ustawienia dostępu **read-only** do prywatnego repozytorium GitHub przez **SSH Deploy Key**.

Repo służy do sytuacji, w której dwie osoby pracują nad prywatnymi projektami i chcą móc regularnie pobierać od siebie kod, ale bez ryzyka przypadkowego `push`, `merge` albo zmian w cudzym repo.

<img width="897" height="670" alt="image" src="https://github.com/user-attachments/assets/67b13e60-8bd2-496e-82f0-de5aebb2df25" />

## Problem

Mamy prywatne repozytoria, które zmieniają się dynamicznie. Chcemy:

- móc robić `git clone`, `git fetch`, `git pull` z repo drugiej osoby,
- zachować prywatność repozytoriów,
- nie dawać drugiej osobie prawa do zapisu,
- uniknąć przypadkowego `push` do cudzego repo.

## Rozwiązanie

Używamy mechanizmu **Deploy Key** w GitHubie, ale w trybie **read-only**.

Działa to tak:

1. osoba, która ma dostać dostęp, generuje u siebie klucz SSH,
2. klucz prywatny zostaje tylko na jej komputerze,
3. klucz publiczny przekazuje właścicielowi repo,
4. właściciel repo dodaje public key w GitHub:
   `Settings → Deploy keys → Add deploy key`,
5. właściciel repo **nie zaznacza** opcji `Allow write access`.

Efekt:

- repo pozostaje prywatne,
- druga osoba może pobierać kod,
- druga osoba nie może pushować do repo.

## Kto uruchamia skrypt?

Skrypt uruchamia **osoba, która ma dostać dostęp read-only**.

Przykład:

- kolega ma dostać dostęp do Twojego repo,
- kolega uruchamia skrypt u siebie,
- skrypt generuje mu klucz SSH,
- kolega wysyła Ci tylko **public key**,
- Ty dodajesz ten public key w swoim repo jako Deploy Key bez `Allow write access`.

## Szybki start

Wymagania:

- Python 3,
- `ssh-keygen`,
- Git / OpenSSH.

Uruchom:

```bash
python3 generate_readonly_key.py
```

Na Windowsie możesz użyć:

```powershell
py generate_readonly_key.py
```

Skrypt przeprowadzi Cię przez cały proces i wypisze:

- gdzie zapisano klucz prywatny,
- gdzie zapisano klucz publiczny,
- który tekst trzeba przekazać właścicielowi repo,
- gdzie właściciel repo ma wejść na GitHubie,
- jak sklonować repo z użyciem wygenerowanego klucza.

## Najważniejsza zasada

Przekazujesz tylko plik z końcówką:

```text
.pub
```

Przykład:

```text
github_readonly_deploy_key.pub
```

Plik bez `.pub` to klucz prywatny. Tego pliku **nie wysyłasz nikomu**.

## Co ma zrobić właściciel repo?

Po otrzymaniu public key:

1. wejdź w prywatne repozytorium na GitHubie,
2. kliknij `Settings`,
3. kliknij `Deploy keys`,
4. kliknij `Add deploy key`,
5. wklej public key,
6. **nie zaznaczaj** `Allow write access`,
7. kliknij `Add key`.

## Co potem może robić osoba z dostępem?

Może:

```bash
git clone
git fetch
git pull
```

Nie może:

```bash
git push
```

## Schemat

```text
Osoba z dostępem read-only
        │
        │ generuje klucz SSH
        ▼
Klucz prywatny zostaje lokalnie
Klucz publiczny trafia do właściciela repo
        │
        ▼
GitHub → repo → Settings → Deploy keys
        │
        │ Allow write access = OFF
        ▼
Dostęp tylko do odczytu
```

## Ważne ograniczenia

- Skrypt nie łączy się z GitHub API.
- Skrypt nie dodaje automatycznie Deploy Key do repo.
- Właściciel repo nadal musi ręcznie wkleić public key w ustawieniach GitHuba.
- Deploy Key jest przypisany do konkretnego repozytorium.
- Dla kilku repozytoriów najlepiej wygenerować osobne klucze.

## Bezpieczeństwo

Nie wrzucaj do tego repo żadnych realnych kluczy SSH.

To repo zawiera tylko helper. Klucze generowane przez skrypt zapisują się lokalnie w katalogu `~/.ssh` osoby, która uruchamia skrypt.

Jeśli klucz prywatny kiedykolwiek wycieknie, właściciel repo powinien usunąć odpowiadający mu Deploy Key z GitHuba.
