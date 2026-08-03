# FaTest

A speedtest tool for your terminal. Fast, clean, no clutter.

![python](https://img.shields.io/badge/python-3.8+-blue)
![license](https://img.shields.io/badge/license-MIT-green)

```
$ fatest

     ______    ______        _
    |  ___|_ _|_   _|__  ___| |_
    | |_ / _` || |/ _ \/ __| __|
    |  _| (_| || |  __/\__ \ |_
    |_|  \__,_||_|\___||___/\__|

  server: Orange PL (Warsaw, Poland)  · ping 12.3 ms

   DOWN   ███████████████████████░░░░░░░░░   287.4 Mbps   peak 340.1
    UP    ████████████████░░░░░░░░░░░░░░░░    45.2 Mbps   peak 46.8

  ╭──────────── Results ────────────╮
  │ Server     Orange PL (Warsaw)    │
  │ Ping       12.3 ms               │
  │ Download   340.10 Mbps  blazing  │
  │ Upload     46.80 Mbps   solid    │
  │ Your IP    1.2.3.4               │
  ╰───────────────────────────────────╯
```

## What it does

- Runs a real download/upload/ping test against a nearby server
- Shows a **live gauge** while it measures — actual real-time Mbps read straight off your network interface, not a fake progress bar
- Lets you pick which server or country to test against, instead of trusting auto-detect blindly
- Keeps a local history of every run (`~/.fatest_history.json`)
- `monitor` mode — runs on a loop, good for babysitting a flaky connection
- Everything colored and readable, nothing dumped as raw text walls

## Install

### From source (Windows, Linux, macOS, any OS)

```bash
git clone https://github.com/naxce/fatest
cd fatest
pip install -e .
```

### NixOS / Nix

Clone the repo, then either drop into a dev shell (this builds `fatest` via `default.nix` and puts it straight on your PATH, no `pip` needed):

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

## Usage

```bash
fatest                    # run a test
fatest test --json        # run a test, also dump raw JSON
fatest test --no-save     # run a test without saving to history
fatest history            # show your last 10 results
fatest history --last 30  # show more
fatest clear-history      # wipe saved history
fatest monitor            # repeat every 5 minutes until you ctrl+c
fatest monitor --interval 60   # repeat every 60 seconds
fatest --version
```

## Picking a server

By default the tool auto-detects "the best" server, which sometimes isn't the closest one geographically — it's just whichever answered fastest during detection, and that list can be thin in some regions. If you keep landing on a server in another country, pin one yourself:

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

MIT — see [LICENSE](LICENSE).
