# Linux Environment Setup Guide (Windows 11 → WSL2 Ubuntu)

Complete, in-order instructions to go from a fresh Windows 11 Pro machine to
building, running, and testing the MiniLang compiler in the environment the
instructor recommends. Every team member should follow this identically.

Why WSL2 and not native Windows or a VM: the course FAQ explicitly accepts
WSL if Flex, Bison, GCC, and Make work; WSL2 runs a real Ubuntu kernel, so
the compiler behaves byte-for-byte the way it will when the instructor
builds it on Linux, with none of a VM's overhead.

---

## Part 1 — Install WSL2 with Ubuntu

1. Open **PowerShell as Administrator** (Win+X → "Terminal (Admin)").
2. Run:

   ```powershell
   wsl --install -d Ubuntu-24.04
   ```

   This enables the WSL feature, installs the WSL2 kernel, and downloads
   Ubuntu 24.04 LTS in one step.
3. **Reboot** when prompted.
4. After reboot, an Ubuntu terminal opens automatically (if not: Start menu
   → "Ubuntu"). Create your Linux username and password when asked.
   The password is asked again by `sudo`; typing it shows nothing — that is
   normal.
5. Verify you are on WSL **2** (matters for performance):

   ```powershell
   wsl -l -v          # in PowerShell; VERSION column must say 2
   wsl --set-version Ubuntu-24.04 2    # only if it said 1
   ```

If `wsl --install` reports that virtualization is disabled, enable
**Intel VT-x / AMD-V** in your BIOS/UEFI (usually under CPU or Advanced
settings), then repeat step 2.

---

## Part 2 — First-time Ubuntu configuration

Open the Ubuntu terminal. All remaining commands run there.

```bash
# 1. Bring the package index and system up to date
sudo apt update && sudo apt upgrade -y

# 2. Install the complete course toolchain
sudo apt install -y build-essential flex bison git make gdb valgrind

# 3. Verify every tool the manual's §7 stack requires
gcc --version      # GNU C compiler
g++ --version      # GNU C++ compiler (we use C++17)
make --version
flex --version     # expect 2.6.x
bison --version    # expect 3.8.x
git --version
```

`build-essential` bundles gcc, g++, make, and the standard headers.
`gdb` and `valgrind` are optional but invaluable for debugging the parser
and hunting memory leaks — good material for the report's Challenges
chapter.

---

## Part 3 — Git identity and GitHub access

Each member does this once, with **their own** GitHub account (the
instructor checks that commits come from every member's account).

```bash
# Identity that appears on your commits — use the email registered
# on your GitHub account so commits are attributed to your profile
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"

# Prevent Windows line-ending corruption of shell scripts and test files
git config --global core.autocrlf input

# Sensible default branch name
git config --global init.defaultBranch main
```

Authenticate to GitHub with SSH (recommended — no password prompts):

```bash
ssh-keygen -t ed25519 -C "you@example.com"     # Enter through the prompts
cat ~/.ssh/id_ed25519.pub                       # copy the whole line
```

GitHub → Settings → **SSH and GPG keys** → New SSH key → paste → save.
Test it:

```bash
ssh -T git@github.com      # expect: "Hi <username>! You've successfully authenticated"
```

(Alternative: `sudo apt install gh && gh auth login` and follow the
browser flow.)

---

## Part 4 — Fork and clone the instructor repository

Per the instructor's workflow (mandatory):

1. In a browser, open the instructor repository and click **Fork**
   (top-right). Do **not** request write access to the original.
2. On **your fork**: Settings → General → rename the repository to
   `CC-Lab-Project-GroupXX` (your group number, e.g.
   `CC-Lab-Project-Group05`).
3. Settings → Collaborators → add **every** team member.
4. Keep the repository **Public**; never delete it after submission.
5. Clone **your fork** inside WSL, into the Linux filesystem:

   ```bash
   cd ~
   mkdir -p projects && cd projects
   git clone git@github.com:<your-username>/CC-Lab-Project-GroupXX.git
   cd CC-Lab-Project-GroupXX
   ```

**Critical performance rule:** keep the project under the Linux home
directory (`~/projects/...`), never under `/mnt/c/...`. The Windows-mounted
drive is dramatically slower and occasionally breaks file permissions on
Flex/Bison generated files. Your Windows files are reachable at `/mnt/c/`
when you need them (e.g. copying a downloaded zip):

```bash
cp /mnt/c/Users/<WindowsUser>/Downloads/minilang-phase2-lexer.zip ~/projects/
cd ~/projects && unzip minilang-phase2-lexer.zip -d minilang-staging
```

Then merge the compiler tree into your fork's working copy (keep the
instructor's original `.gitignore`, `tests/*.md`, and `examples/*.md`
files — they are the grading reference; our runnable `.mc` tests live
alongside them).

---

## Part 5 — Editor: VS Code with the WSL extension

1. Install VS Code **on Windows** (code.visualstudio.com).
2. Inside VS Code, install the extension **"WSL"** (ms-vscode-remote.remote-wsl).
3. From the Ubuntu terminal, open the project:

   ```bash
   cd ~/projects/CC-Lab-Project-GroupXX
   code .
   ```

   VS Code opens in Windows, but its terminal, IntelliSense, Git, and
   build tasks all execute inside Ubuntu. The bottom-left corner shows
   `WSL: Ubuntu-24.04`.
4. Recommended extensions (installed "in WSL" when prompted):
   **C/C++** (ms-vscode.cpptools) and **Yash** or **Lex Flex Yacc Bison**
   syntax highlighting for `.l`/`.y` files.

---

## Part 6 — Building and running the compiler

From the project root:

```bash
make                # builds everything into build/mcc
make test           # runs the regression suite (scripts/run_tests.sh)
make clean          # removes all generated files

# Run the compiler
./build/mcc examples/sample.mc              # full pipeline (current phases)
./build/mcc examples/sample.mc --tokens     # dump the token stream
./build/mcc --help                          # list available options
```

Expected at the current project phase: `make test` prints a PASS line per
test and ends with `... passed, 0 failed`.

---

## Part 7 — Daily Git workflow (what the instructor inspects)

```bash
git pull                          # start of every session
# ... work ...
make && make test                 # never commit red
git add <files>
git commit -m "Add scope handling to symbol table"   # meaningful message
git push
```

Rules the instructor grades directly:

- Commit **regularly** (multiple small commits per work session), spread
  across the whole project timeline — a single huge commit near the
  deadline is penalized even if the compiler works.
- Every member commits from their **own** account.
- Messages describe the change ("Implement parser grammar",
  "Fix dangling-else conflict") — never "update", "fix", "final".
- Optional but professional: feature branches (`feature/parser`,
  `feature/semantic`) merged into `main` after `make test` passes.
- Commits after the deadline are treated as late work — stop pushing
  before the cutoff.

---

## Part 8 — Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `wsl --install` does nothing / errors | Old Windows build: run `wsl --update` in admin PowerShell, or enable "Virtual Machine Platform" + "Windows Subsystem for Linux" in *Turn Windows features on or off*, reboot, retry |
| `bash: flex: command not found` after install | You opened a new terminal into a different distro; run `wsl -l -v` and set the default: `wsl --set-default Ubuntu-24.04` |
| `run_tests.sh: /bin/bash^M: bad interpreter` | CRLF line endings from a Windows editor. Fix the file: `sed -i 's/\r$//' scripts/run_tests.sh`; prevent recurrence with `git config --global core.autocrlf input` and VS Code's status-bar "LF" setting |
| Build is very slow / `make` takes ages | Project is under `/mnt/c/`. Move it: `mv /mnt/c/.../project ~/projects/` |
| `Permission denied` running `./scripts/run_tests.sh` | Executable bit lost in transit: `chmod +x scripts/run_tests.sh` |
| `sudo: command not found` inside container-like shells | You are not in your Ubuntu WSL session; open the "Ubuntu" app from the Start menu |
| apt errors about unrelated repositories (e.g. nodesource) | Harmless for this project as long as `apt install flex bison` succeeds; the offending third-party repo can be removed from `/etc/apt/sources.list.d/` |
| Clock skew warnings from `make` after laptop sleep | `sudo hwclock -s` or just re-run `make` |
| GitHub push asks for username/password repeatedly | You cloned over HTTPS; either switch to SSH (`git remote set-url origin git@github.com:<user>/<repo>.git`) or use `gh auth login` |

---

## Part 9 — Team checklist (each member, once)

- [ ] WSL2 + Ubuntu 24.04 installed, `wsl -l -v` shows VERSION 2
- [ ] `flex`, `bison`, `g++`, `make`, `git` all report versions
- [ ] Git identity configured with own GitHub email; `autocrlf input` set
- [ ] SSH key added to own GitHub account; `ssh -T git@github.com` succeeds
- [ ] Added as collaborator on the group fork; can push
- [ ] Project cloned under `~/projects/`, `make && make test` green locally
- [ ] VS Code opens the project via the WSL extension
