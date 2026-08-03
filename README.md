# FaTest

A speedtest tool for your terminal. Fast, clean, no clutter.

![python](https://img.shields.io/badge/python-3.8+-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![version](https://img.shields.io/badge/version-2.0.0-cyan)

```
$ fatest

     ______    ______        _
    |  ___|_ _|_   _|__  ___| |_
    | |_ / _` || |/ _ \/ __| __|
    |  _| (_| || |  __/\__ \ |_
    |_|  \__,_||_|\___||___/\__|

              v2.0.0 - network speed, fast, cli

  ╭──────────────────────────── Menu ────────────────────────────╮
  │  [1]  test            run a speed test                       │
  │  [2]  servers         list nearby servers                    │
  │  [3]  history         show past results                      │
  │  [4]  clear-history   wipe stored history                    │
  │  [5]  monitor         repeat testing on a loop                │
  │  [6]  config          view or set default country/server     │
  │  [7]  help            show all commands and flags            │
  │  [0]  exit            quit fatest                            │
  ╰─────────────────────────────────────────────────────────────╯
  Type a number, a command name, or a full command with flags.
  Examples:  2   |  servers --country PL   |  test --json

  fatest>
```

## What's new in v2.0

Launching FaTest - whether by typing `fatest` in a terminal or by clicking its
desktop/menu shortcut - now opens an interactive command menu instead of
immediately firing off a test. It's still a pure command-line tool: nothing to
click, no mouse required. You either type the number next to an option, the
command name itself, or a full command with its flags (e.g. `servers
--country PL`), and FaTest runs it right there in the same window.

All the old direct subcommands still work exactly as before, so existing
scripts and muscle memory aren't affected - see [Usage](#usage) below.

## What it does

- Runs a real download/upload/ping test against a nearby server
- Shows a **live gauge** while it measures - actual real-time Mbps read straight off your network interface, not a fake progress bar
- Lets you pick which server or country to test against, instead of trusting auto-detect blindly
- Keeps a local history of every run (`~/.fatest_history.json`)
- `monitor` mode - runs on a loop, good for babysitting a flaky connection
- An interactive command menu on launch, plus full direct-subcommand support for scripting
- Everything colored and readable, nothing dumped as raw text walls

## Install

### Build from source (any OS)

```bash
git clone https://github.com/naxce/fatest
cd fatest
pip install -e .
fatest
```

This works the same way on Linux, macOS, and Windows - clone the repo, build
it locally, and the `fatest` command is on your `PATH`.

### NixOS / Nix

Clone the repo, then either drop into a dev shell (this builds `fatest` via `default.nix` and puts it straight on your PATH):

```bash
git clone https://github.com/naxce/fatest
cd fatest
nix-shell
fatest
```

or build it standalone:

```bash
nix-build
./result/bin/fatest
```

To use it as a flake input or add it to your system config, package it from `default.nix` the way you would any other Python application in your `overlays` or `packages`.

## Desktop icon / shortcut

Once `fatest` is built (see above), you can add it as a regular application
with an icon that opens your default terminal and launches FaTest - straight
into its interactive menu.

### Linux

```bash
./packaging/linux/install-desktop-entry.sh
```

Adds a `FaTest` entry with an icon to your application menu (`~/.local/share/applications`).
Clicking it opens the default terminal for your desktop environment (GNOME, KDE, XFCE, etc.)
and launches `fatest` in it - exactly like any other terminal app (e.g. htop in your menu).

### Windows

```powershell
.\packaging\windows\install-shortcut.ps1
```

(or just double-click `packaging\windows\install-shortcut.bat`)

Creates a `FaTest` shortcut with an icon on the Desktop and in the Start Menu.
Clicking it opens `cmd.exe` and immediately runs `fatest` in it; the window
stays open after a test finishes so you can see the result.

> Requirement: `fatest` must already be built and available on your `PATH` (see the Install section above).

## Usage

```bash
fatest                    # opens the interactive command menu
fatest test                # run a test directly
fatest test --json         # run a test, also dump raw JSON
fatest test --no-save      # run a test without saving to history
fatest history              # show your last 10 results
fatest history --last 30    # show more
fatest clear-history         # wipe saved history
fatest monitor                # repeat every 5 minutes until you ctrl+c
fatest monitor --interval 60   # repeat every 60 seconds
fatest --version
```

Every one of these also works from inside the interactive menu - just type
the part after `fatest`, e.g. `test --json` or `history --last 30`.

## Picking a server

By default the tool auto-detects "the best" server, which sometimes isn't the closest one geographically - it's just whichever answered fastest during detection, and that list can be thin in some regions. If you keep landing on a server in another country, pin one yourself:

```bash
fatest servers                # list nearby servers with their IDs
fatest servers --country PL   # filter to a specific country
fatest test --server 12345    # run a test against a specific server ID
fatest test --country PL      # run a test against the nearest match in that country
```

Tired of typing the flag every time? Save a default:

```bash
fatest config --country PL     # always prefer Polish servers from now on
fatest config --server 12345   # or pin one exact server
fatest config --show           # see current defaults
fatest config --country none   # clear the default
```

`test` and `monitor` both respect the saved config, and an explicit `--country`/`--server` flag on the command line always overrides it for that one run.

## Why another speedtest tool

Most terminal speedtest wrappers either look like they're stuck in 2009 or dump ten lines of unreadable text at you. This one tries to actually be pleasant to look at while doing the same job.

## Requirements

- Python 3.8 or newer
- `rich`, `speedtest-cli`, and `psutil` (installed automatically as dependencies)

## License

MIT - see [LICENSE](LICENSE).
