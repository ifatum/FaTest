import argparse
import json
import os
import shlex
import socket
import statistics
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from rich import box
from rich.align import Align
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from fatest import __version__

console = Console()

HISTORY_PATH = Path.home() / ".fatest_history.json"
CONFIG_PATH = Path.home() / ".fatest_config.json"

LOGO = r"""
[bold cyan] _____    [bold magenta]_____         _   [/bold magenta][/bold cyan]
[bold cyan]|  ___|_ _[bold magenta]|_   _|__  ___| |_ [/bold magenta][/bold cyan]
[bold cyan]| |_ / _` |[bold magenta]| |/ _ \/ __| __|[/bold magenta][/bold cyan]
[bold cyan]|  _| (_| |[bold magenta]| |  __/\__ \ |_ [/bold magenta][/bold cyan]
[bold cyan]|_|  \__,_|[bold magenta]|_|\___||___/\__|[/bold magenta][/bold cyan]
"""


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def show_banner():
    console.print(Align.center(Text.from_markup(LOGO)))
    console.print(Align.center(f"[dim]v{__version__} - network speed, fast, cli[/dim]"))
    console.print()


def human_speed(mbps):
    if mbps >= 1000:
        return f"{mbps / 1000:.2f} Gbps"
    return f"{mbps:.2f} Mbps"


def rating_bar(mbps):
    if mbps < 5:
        return "[red]▮▯▯▯▯[/red] potato"
    elif mbps < 25:
        return "[yellow]▮▮▯▯▯[/yellow] okay-ish"
    elif mbps < 100:
        return "[green]▮▮▮▯▯[/green] solid"
    elif mbps < 300:
        return "[bold green]▮▮▮▮▯[/bold green] fast"
    else:
        return "[bold cyan]▮▮▮▮▮[/bold cyan] blazing"


def load_config():
    default = {"country": None, "server_id": None}
    if not CONFIG_PATH.exists():
        return default
    try:
        data = json.loads(CONFIG_PATH.read_text())
        default.update(data)
        return default
    except Exception:
        return default


def save_config(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


def live_gauge_bar(mbps, peak, width=30):
    if peak <= 0:
        peak = 1
    filled = int(min(mbps / peak, 1.0) * width)
    bar = "█" * filled + "░" * (width - filled)
    return bar


def external_counters():
    import psutil

    nics = psutil.net_io_counters(pernic=True)
    real = [c for name, c in nics.items() if name != "lo"]
    return sum(c.bytes_recv for c in real), sum(c.bytes_sent for c in real)


class NetSpeedMeter:
    """Reads real interface throughput via psutil while a transfer runs."""

    def __init__(self):
        self.running = False
        self.current_mbps = 0.0
        self.peak_mbps = 0.0
        self._thread = None

    def _watch(self, direction):
        last = external_counters()
        last_t = time.monotonic()

        while self.running:
            time.sleep(0.12)
            now = external_counters()
            now_t = time.monotonic()
            dt = now_t - last_t
            if dt <= 0:
                continue

            delta_bytes = now[0] - last[0] if direction == "download" else now[1] - last[1]

            mbps = (delta_bytes * 8 / dt) / 1_000_000
            if mbps < 0:
                mbps = 0.0

            self.current_mbps = mbps
            self.peak_mbps = max(self.peak_mbps, mbps)

            last = now
            last_t = now_t

    def start(self, direction):
        self.running = True
        self.current_mbps = 0.0
        self.peak_mbps = 0.0
        self._thread = threading.Thread(
            target=self._watch, args=(direction,), daemon=True
        )
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=1)


SERVERS_API = "https://www.speedtest.net/api/js/servers"
CANDIDATES = 5


def to_server(raw):
    return {
        "id": str(raw["id"]),
        "url": raw["url"],
        "host": raw.get("host", ""),
        "sponsor": raw.get("sponsor", ""),
        "name": raw.get("name", ""),
        "country": raw.get("country", ""),
        "cc": raw.get("cc", ""),
        "lat": raw.get("lat", ""),
        "lon": raw.get("lon", ""),
        "d": float(raw.get("distance", 0) or 0),
    }


def fetch_servers(search=None, limit=100, retries=3, delay=2):
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    query = {"engine": "js", "https_functional": "true", "limit": limit}
    if search:
        query["search"] = search
    request = Request(
        f"{SERVERS_API}?{urlencode(query)}", headers={"User-Agent": f"fatest/{__version__}"}
    )
    last_err = None
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=10) as response:
                raw = json.loads(response.read().decode("utf-8"))
            servers = [to_server(s) for s in raw if s.get("url") and s.get("id")]
            return sorted(servers, key=lambda s: s["d"])
        except Exception as e:
            last_err = e
            if "429" in str(e):
                time.sleep(delay * (attempt + 1))
                continue
            raise
    raise last_err


def resolve_target(args, cfg):
    if getattr(args, "country", None) or getattr(args, "server", None):
        return args.country, args.server
    return cfg.get("country"), cfg.get("server_id")


def choose_candidates(country=None, server_id=None, warn=None):
    warn = warn or (lambda msg: None)
    if server_id:
        match = [s for s in fetch_servers() if s["id"] == str(server_id)]
        if match:
            return match
        warn(f"Server {server_id} is not among the nearby servers, picking the best one instead.")

    if country:
        cc = country.upper()
        matches = [s for s in fetch_servers(search=cc) if s["cc"].upper() == cc]
        if matches:
            return matches[:CANDIDATES]
        warn(f"No servers found for country '{cc}', falling back to auto-detect.")

    return fetch_servers(limit=CANDIDATES * 2)[:CANDIDATES]


def pick_server(st, country=None, server_id=None, warn=None):
    try:
        candidates = choose_candidates(country, server_id, warn)
    except Exception as e:
        (warn or (lambda msg: None))(f"Server list unavailable ({e}), using the legacy list.")
        candidates = []
    if candidates:
        st.get_best_server(candidates)
    else:
        st.get_best_server()


def cmd_list_servers(args):
    console.print("[dim]fetching server list...[/dim]")

    if args.country:
        cc = args.country.upper()
        all_servers = [s for s in fetch_servers(search=cc) if s["cc"].upper() == cc]
    else:
        all_servers = fetch_servers(limit=max(args.limit, 1))

    all_servers = all_servers[: args.limit]

    if not all_servers:
        console.print("[yellow]No servers matched.[/yellow]")
        return

    table = Table(box=box.SIMPLE_HEAVY, border_style="cyan")
    table.add_column("ID", style="dim")
    table.add_column("Sponsor")
    table.add_column("City")
    table.add_column("Country")
    table.add_column("Distance", justify="right")

    for s in all_servers:
        table.add_row(
            str(s["id"]),
            s["sponsor"],
            s["name"],
            f"{s['country']} ({s['cc']})",
            f"{float(s['d']):.0f} km",
        )

    console.print(table)
    console.print(
        "\n[dim]use --server ID or set a default with: fatest config --server ID[/dim]"
    )


def run_test(country=None, server_id=None):
    import speedtest

    result = {}
    st = speedtest.Speedtest()

    with console.status("[bold cyan]locating server...", spinner="dots"):
        pick_server(st, country=country, server_id=server_id, warn=lambda m: console.print(f"[yellow]{m}[/yellow]"))

    server = st.results.server
    result["server"] = f"{server['sponsor']} ({server['name']}, {server['country']})"
    result["ping"] = round(st.results.ping, 1)

    console.print(
        f"[dim]server:[/dim] {result['server']}  [dim]· ping[/dim] {result['ping']} ms\n"
    )

    meter = NetSpeedMeter()

    def render_gauge(direction, mbps, peak, style):
        bar = live_gauge_bar(mbps, max(peak, 10), width=32)
        label = "DOWN" if direction == "download" else " UP "
        text = Text()
        text.append(f" {label} ", style=f"bold {style} reverse")
        text.append(f"  {bar}  ", style=style)
        text.append(f"{mbps:6.1f} Mbps", style=f"bold {style}")
        text.append(f"   peak {peak:.1f}", style="dim")
        return Align.center(text)

    down_mbps = 0.0
    with Live(
        render_gauge("download", 0, 1, "green"), console=console, refresh_per_second=12
    ) as live:
        meter.start("download")
        holder = {}

        def worker():
            holder["value"] = st.download() / 1_000_000

        t = threading.Thread(target=worker)
        t.start()
        while t.is_alive():
            live.update(
                render_gauge("download", meter.current_mbps, meter.peak_mbps, "green")
            )
            time.sleep(0.08)
        t.join()
        meter.stop()
        down_mbps = holder["value"]
        live.update(
            render_gauge(
                "download", down_mbps, max(meter.peak_mbps, down_mbps), "green"
            )
        )

    result["download"] = down_mbps
    console.print()

    up_mbps = 0.0
    with Live(
        render_gauge("upload", 0, 1, "yellow"), console=console, refresh_per_second=12
    ) as live:
        meter.start("upload")
        holder = {}

        def worker():
            holder["value"] = st.upload() / 1_000_000

        t = threading.Thread(target=worker)
        t.start()
        while t.is_alive():
            live.update(
                render_gauge("upload", meter.current_mbps, meter.peak_mbps, "yellow")
            )
            time.sleep(0.08)
        t.join()
        meter.stop()
        up_mbps = holder["value"]
        live.update(
            render_gauge("upload", up_mbps, max(meter.peak_mbps, up_mbps), "yellow")
        )

    result["upload"] = up_mbps
    console.print()

    result["timestamp"] = datetime.now().isoformat(timespec="seconds")
    try:
        result["client_ip"] = st.results.client.get("ip", "unknown")
    except Exception:
        result["client_ip"] = "unknown"

    return result


def emit(event, **data):
    sys.stdout.write(json.dumps(dict(event=event, **data)) + "\n")
    sys.stdout.flush()


def measure(st, direction, tick=0.25):
    meter = NetSpeedMeter()
    holder = {}

    def worker():
        try:
            run = st.download if direction == "download" else st.upload
            holder["value"] = run() / 1_000_000
        except Exception as e:
            holder["error"] = e

    meter.start(direction)
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    while t.is_alive():
        t.join(tick)
        emit(direction, mbps=round(meter.current_mbps, 2))
    meter.stop()
    if "error" in holder:
        raise holder["error"]
    return holder["value"]


def stream_test(country=None, server_id=None, save=True, speedtest_module=None):
    try:
        st = (speedtest_module or __import__("speedtest")).Speedtest()
        emit("status", phase="server")
        pick_server(st, country=country, server_id=server_id, warn=lambda m: emit("warning", message=m))
        server = st.results.server
        result = {
            "server": f"{server['sponsor']} ({server['name']}, {server['country']})",
            "ping": round(st.results.ping, 1),
        }
        emit("server", server=result["server"], id=str(server.get("id", "")), ping=result["ping"])
        result["download"] = measure(st, "download")
        emit("download", mbps=round(result["download"], 2), done=True)
        result["upload"] = measure(st, "upload")
        emit("upload", mbps=round(result["upload"], 2), done=True)
        result["timestamp"] = datetime.now().isoformat(timespec="seconds")
        try:
            result["client_ip"] = st.results.client.get("ip", "unknown")
        except Exception:
            result["client_ip"] = "unknown"
        if save:
            save_history(result)
        emit("result", result=result)
    except Exception as e:
        emit("error", message=str(e) or e.__class__.__name__)
        sys.exit(1)


def print_result(result):
    console.print()
    table = Table(
        box=box.ROUNDED, show_header=False, border_style="cyan", padding=(0, 2)
    )
    table.add_column(style="bold white")
    table.add_column(style="white")

    table.add_row("Server", result["server"])
    table.add_row("Ping", f"{result['ping']} ms")
    table.add_row(
        "Download",
        f"[bold green]{human_speed(result['download'])}[/bold green]  {rating_bar(result['download'])}",
    )
    table.add_row(
        "Upload",
        f"[bold yellow]{human_speed(result['upload'])}[/bold yellow]  {rating_bar(result['upload'])}",
    )
    table.add_row("Your IP", result.get("client_ip", "unknown"))

    console.print(
        Panel(
            table,
            title="[bold magenta]Results[/bold magenta]",
            border_style="magenta",
            expand=False,
        )
    )
    console.print()


def save_history(result):
    history = []
    if HISTORY_PATH.exists():
        try:
            history = json.loads(HISTORY_PATH.read_text())
        except Exception:
            history = []
    history.append(result)
    HISTORY_PATH.write_text(json.dumps(history, indent=2))


def load_history():
    if not HISTORY_PATH.exists():
        return []
    try:
        return json.loads(HISTORY_PATH.read_text())
    except Exception:
        return []


def cmd_history(args):
    history = load_history()
    if not history:
        console.print("[dim]No history yet. Run a test first.[/dim]")
        return

    table = Table(box=box.SIMPLE_HEAVY, border_style="cyan")
    table.add_column("When", style="dim")
    table.add_column("Ping", justify="right")
    table.add_column("Download", justify="right", style="green")
    table.add_column("Upload", justify="right", style="yellow")
    table.add_column("Server")

    entries = history[-args.last :]
    for r in entries:
        table.add_row(
            r["timestamp"].replace("T", " "),
            f"{r['ping']} ms",
            human_speed(r["download"]),
            human_speed(r["upload"]),
            r["server"][:40],
        )

    console.print(table)

    if len(entries) > 1:
        downs = [r["download"] for r in entries]
        ups = [r["upload"] for r in entries]
        console.print()
        console.print(
            f"[dim]avg download {human_speed(statistics.mean(downs))} · avg upload {human_speed(statistics.mean(ups))}[/dim]"
        )


def cmd_clear_history(args):
    if HISTORY_PATH.exists():
        HISTORY_PATH.unlink()
        console.print("[green]History wiped.[/green]")
    else:
        console.print("[dim]Nothing to clear.[/dim]")


def cmd_monitor(args):
    clear()
    show_banner()
    country, server_id = resolve_target(args, load_config())
    console.print(f"[dim]watching every {args.interval}s - ctrl+c to stop[/dim]\n")
    try:
        while True:
            result = run_test(country=country, server_id=server_id)
            print_result(result)
            save_history(result)
            console.print(f"[dim]next run in {args.interval}s...[/dim]\n")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        console.print("\n[bold magenta]Stopped.[/bold magenta]")


def cmd_test(args):
    country, server_id = resolve_target(args, load_config())
    if args.stream:
        stream_test(country, server_id, save=not args.no_save)
        return
    clear()
    show_banner()
    result = run_test(country=country, server_id=server_id)
    print_result(result)
    if not args.no_save:
        save_history(result)
    if args.json:
        console.print_json(json.dumps(result))


def cmd_config(args):
    cfg = load_config()

    if args.show:
        console.print_json(json.dumps(cfg))
        return

    changed = False
    if args.country is not None:
        cfg["country"] = (
            args.country.upper() if args.country.lower() != "none" else None
        )
        changed = True
    if args.server is not None:
        cfg["server_id"] = args.server if args.server.lower() != "none" else None
        changed = True

    if changed:
        save_config(cfg)
        console.print("[green]Saved.[/green]")
        console.print_json(json.dumps(cfg))
    else:
        console.print_json(json.dumps(cfg))


MENU_ITEMS = [
    ("1", "test", "run a speed test"),
    ("2", "servers", "list nearby servers"),
    ("3", "history", "show past results"),
    ("4", "clear-history", "wipe stored history"),
    ("5", "monitor", "repeat testing on a loop"),
    ("6", "config", "view or set default country/server"),
    ("7", "help", "show all commands and flags"),
    ("0", "exit", "quit fatest"),
]

MENU_ALIASES = {num: name for num, name, _ in MENU_ITEMS}
EXIT_WORDS = {"0", "exit", "quit", "q"}
HELP_WORDS = {"help", "?", "h"}


def show_menu():
    table = Table(
        box=box.SIMPLE, show_header=False, border_style="cyan", padding=(0, 1)
    )
    table.add_column(style="bold cyan", justify="right")
    table.add_column(style="bold white")
    table.add_column(style="dim")

    for num, name, desc in MENU_ITEMS:
        table.add_row(f"[{num}]", name, desc)

    console.print(
        Panel(
            table,
            title="[bold magenta]Menu[/bold magenta]",
            border_style="magenta",
            expand=False,
        )
    )
    console.print(
        "[dim]Type a number, a command name, or a full command with flags.[/dim]"
    )
    console.print(
        "[dim]Examples:[/dim]  2   [dim]|[/dim]  servers --country PL   [dim]|[/dim]  test --json\n"
    )


def show_help(parser):
    console.print()
    parser.print_help()
    console.print()
    console.print("[dim]Press enter to return to the menu...[/dim]")
    try:
        console.input()
    except (EOFError, KeyboardInterrupt):
        pass


def interactive_menu(parser):
    """Command-driven menu: still pure CLI, still controlled only by typed
    commands - this just gives you a discoverable list of what fatest can do
    instead of making you remember every subcommand and flag."""
    while True:
        clear()
        show_banner()
        show_menu()

        try:
            line = console.input("[bold cyan]fatest[/bold cyan][dim]>[/dim] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]bye.[/dim]")
            break

        if not line:
            continue

        try:
            tokens = shlex.split(line)
        except ValueError as e:
            console.print(f"[bold red]Couldn't parse that:[/bold red] {e}")
            continue

        if not tokens:
            continue

        head = tokens[0].lower()

        if head in EXIT_WORDS:
            console.print("[dim]bye.[/dim]")
            break

        if head in HELP_WORDS:
            show_help(parser)
            continue

        if head in MENU_ALIASES:
            tokens[0] = MENU_ALIASES[head]

        try:
            args = parser.parse_args(tokens)
        except SystemExit:
            console.print("[dim]Press enter to return to the menu...[/dim]")
            try:
                console.input()
            except (EOFError, KeyboardInterrupt):
                break
            continue

        if not getattr(args, "func", None):
            continue

        try:
            args.func(args)
        except socket.gaierror:
            console.print("[bold red]No network connection found.[/bold red]")
        except KeyboardInterrupt:
            console.print("\n[dim]Cancelled.[/dim]")
        except Exception as e:
            console.print(f"[bold red]Something went wrong:[/bold red] {e}")

        console.print("\n[dim]Press enter to return to the menu...[/dim]")
        try:
            console.input()
        except (EOFError, KeyboardInterrupt):
            break


def build_parser():
    parser = argparse.ArgumentParser(
        prog="fatest",
        description="FaTest - a fast, clean terminal speedtest.",
    )
    parser.add_argument("--version", action="version", version=f"FaTest {__version__}")

    sub = parser.add_subparsers(dest="command")

    p_test = sub.add_parser("test", help="run a speed test")
    p_test.add_argument(
        "--json", action="store_true", help="also print raw JSON result"
    )
    p_test.add_argument(
        "--no-save", action="store_true", help="don't store this run in history"
    )
    p_test.add_argument(
        "--stream",
        action="store_true",
        help="print progress and the result as JSON lines, for other programs",
    )
    p_test.add_argument(
        "--country", type=str, default=None, help="two-letter country code, e.g. PL"
    )
    p_test.add_argument(
        "--server", type=str, default=None, help="specific speedtest.net server ID"
    )
    p_test.set_defaults(func=cmd_test)

    p_hist = sub.add_parser("history", help="show past results")
    p_hist.add_argument("--last", type=int, default=10, help="how many entries to show")
    p_hist.set_defaults(func=cmd_history)

    p_clear = sub.add_parser("clear-history", help="wipe stored history")
    p_clear.set_defaults(func=cmd_clear_history)

    p_mon = sub.add_parser("monitor", help="run tests repeatedly at an interval")
    p_mon.add_argument(
        "--interval", type=int, default=300, help="seconds between runs (default 300)"
    )
    p_mon.add_argument(
        "--country", type=str, default=None, help="two-letter country code, e.g. PL"
    )
    p_mon.add_argument(
        "--server", type=str, default=None, help="specific speedtest.net server ID"
    )
    p_mon.set_defaults(func=cmd_monitor)

    p_servers = sub.add_parser("servers", help="list nearby speedtest servers")
    p_servers.add_argument(
        "--country",
        type=str,
        default=None,
        help="filter by two-letter country code, e.g. PL",
    )
    p_servers.add_argument("--limit", type=int, default=15, help="how many to show")
    p_servers.set_defaults(func=cmd_list_servers)

    p_cfg = sub.add_parser("config", help="view or set default country/server")
    p_cfg.add_argument(
        "--country",
        type=str,
        default=None,
        help="set default country code (or 'none' to clear)",
    )
    p_cfg.add_argument(
        "--server",
        type=str,
        default=None,
        help="set default server ID (or 'none' to clear)",
    )
    p_cfg.add_argument("--show", action="store_true", help="print current config")
    p_cfg.set_defaults(func=cmd_config)

    return parser


def main():
    parser = build_parser()

    if not sys.argv[1:]:
        interactive_menu(parser)
        return

    args = parser.parse_args()

    if not getattr(args, "func", None):
        interactive_menu(parser)
        return

    try:
        args.func(args)
    except socket.gaierror:
        console.print("[bold red]No network connection found.[/bold red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Cancelled.[/dim]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[bold red]Something went wrong:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
