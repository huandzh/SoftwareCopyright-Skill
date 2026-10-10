from __future__ import annotations

import shutil
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import workdir_lock  # noqa: E402


class WorkdirLockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parent / ".tmp-workdir-lock"
        if self.root.exists():
            shutil.rmtree(self.root)
        (self.root / "草稿").mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_acquire_release_round_trip(self) -> None:
        path = workdir_lock.acquire(self.root, "test-owner")

        self.assertTrue(path.is_file())
        lock = workdir_lock.read_lock(self.root)
        assert lock is not None
        self.assertEqual(lock["owner"], "test-owner")
        self.assertTrue(workdir_lock.is_active(lock))

        workdir_lock.release(self.root)
        self.assertFalse(path.exists())

    def test_second_run_stops_while_the_first_still_holds_the_lock(self) -> None:
        workdir_lock.acquire(self.root, "first")

        with self.assertRaises(SystemExit) as raised:
            workdir_lock.acquire(self.root, "second")

        self.assertIn("正被另一个会话写入", str(raised.exception))
        workdir_lock.release(self.root)

    def test_stale_lock_from_a_dead_process_is_taken_over(self) -> None:
        lock = {
            "pid": 999_999_999,
            "owner": "ghost",
            "host": workdir_lock.socket.gethostname(),
            "started_at": "2026-01-01T00:00:00",
            "started_ts": time.time() - 10,
        }
        workdir_lock.lock_path(self.root).write_text(
            workdir_lock.json.dumps(lock, ensure_ascii=False), encoding="utf-8"
        )

        path = workdir_lock.acquire(self.root, "me")

        current = workdir_lock.read_lock(self.root)
        assert current is not None
        self.assertEqual(current["owner"], "me")
        workdir_lock.release(self.root)
        self.assertFalse(path.exists())

    def test_lock_from_another_host_uses_freshness(self) -> None:
        fresh = {"pid": 1, "owner": "remote", "host": "another-host", "started_ts": time.time()}
        old = {"pid": 1, "owner": "remote", "host": "another-host", "started_ts": time.time() - 10 * 60 * 60}

        self.assertTrue(workdir_lock.is_active(fresh))
        self.assertFalse(workdir_lock.is_active(old))

    def test_hold_context_releases_on_exception(self) -> None:
        with self.assertRaises(RuntimeError):
            with workdir_lock.hold(self.root, "boom"):
                raise RuntimeError("boom")

        self.assertFalse(workdir_lock.lock_path(self.root).exists())

    def test_force_ignores_an_active_lock(self) -> None:
        workdir_lock.acquire(self.root, "first")

        with patch.object(workdir_lock, "is_active", return_value=True):
            path = workdir_lock.acquire(self.root, "forced", force=True)

        self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()
