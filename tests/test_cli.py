import io
import json
import types
import unittest
from contextlib import redirect_stdout
from unittest import mock

from fatest import cli

RAW = [
    {"id": "2", "url": "http://b/speedtest/upload.php", "sponsor": "B", "name": "Berlin", "country": "Germany", "cc": "DE", "distance": 300},
    {"id": "1", "url": "http://a/speedtest/upload.php", "sponsor": "A", "name": "Warsaw", "country": "Poland", "cc": "PL", "distance": 19},
    {"id": "3", "url": "", "sponsor": "C", "name": "Broken", "country": "Poland", "cc": "PL", "distance": 1},
]


def servers(search=None, limit=100):
    out = sorted((cli.to_server(s) for s in RAW if s["url"]), key=lambda s: s["d"])
    return out[:limit]


class FakeSpeedtest:
    def __init__(self):
        self.results = types.SimpleNamespace(server=None, ping=0.0, client={"ip": "1.2.3.4"})
        self.picked = None

    def get_best_server(self, servers=None):
        self.picked = servers
        self.results.server = servers[0] if servers else {"id": "9", "sponsor": "Legacy", "name": "X", "country": "Y"}
        self.results.ping = 12.345

    def download(self):
        return 250_000_000

    def upload(self):
        return 50_000_000


class ResolveTarget(unittest.TestCase):
    def test_cli_country_beats_config_server(self):
        args = types.SimpleNamespace(country="de", server=None)
        self.assertEqual(cli.resolve_target(args, {"country": None, "server_id": "1"}), ("de", None))

    def test_config_used_without_flags(self):
        args = types.SimpleNamespace(country=None, server=None)
        self.assertEqual(cli.resolve_target(args, {"country": "PL", "server_id": "7"}), ("PL", "7"))


class ChooseCandidates(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(cli, "fetch_servers", side_effect=servers)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_auto_picks_nearest_first(self):
        self.assertEqual([s["id"] for s in cli.choose_candidates()], ["1", "2"])

    def test_country_filters_by_code(self):
        self.assertEqual([s["id"] for s in cli.choose_candidates(country="de")], ["2"])

    def test_known_server_id(self):
        self.assertEqual([s["id"] for s in cli.choose_candidates(server_id=2)], ["2"])

    def test_unknown_server_warns_and_falls_back(self):
        warnings = []
        picked = cli.choose_candidates(server_id="42", warn=warnings.append)
        self.assertEqual(picked[0]["id"], "1")
        self.assertEqual(len(warnings), 1)


class StreamTest(unittest.TestCase):
    def test_events_in_order_and_history_saved(self):
        fake = types.SimpleNamespace(Speedtest=FakeSpeedtest)
        out = io.StringIO()
        with mock.patch.object(cli, "fetch_servers", side_effect=servers), \
                mock.patch.object(cli, "external_counters", return_value=(0, 0)), \
                mock.patch.object(cli, "save_history") as saved, redirect_stdout(out):
            cli.stream_test(speedtest_module=fake)
        events = [json.loads(line) for line in out.getvalue().splitlines()]
        kinds = [e["event"] for e in events]
        self.assertEqual(kinds[0], "status")
        self.assertEqual(kinds[1], "server")
        self.assertEqual(events[1]["id"], "1")
        self.assertEqual(events[1]["ping"], 12.3)
        self.assertLess(kinds.index("download"), kinds.index("upload"))
        result = events[-1]["result"]
        self.assertEqual(kinds[-1], "result")
        self.assertEqual((result["download"], result["upload"]), (250.0, 50.0))
        saved.assert_called_once_with(result)

    def test_failure_is_an_error_event(self):
        broken = types.SimpleNamespace(Speedtest=mock.Mock(side_effect=RuntimeError("offline")))
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit):
            cli.stream_test(speedtest_module=broken)
        self.assertEqual(json.loads(out.getvalue().splitlines()[-1]), {"event": "error", "message": "offline"})


if __name__ == "__main__":
    unittest.main()
