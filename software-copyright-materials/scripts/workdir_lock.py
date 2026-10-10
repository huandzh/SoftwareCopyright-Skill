#!/usr/bin/env python3
"""Guard a material workdir against two skill runs writing it at once.

两个会话同时对同一个 ``软件著作权申请资料`` 目录跑抽取／生成时，后写的会覆盖
先写的，而两边看到的生成报告都还是自己的字节数（实测：同一份 docx 在复核期间
被另一个会话重写，报告里的尺寸对不上磁盘）。所以重写的脚本在开工前先抢一个
锁，发现锁的主人还活着就直接停下并提示，而不是两边互相覆盖。
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

LOCK_NAME = ".workdir.lock"
LOCK_DIR_NAME = "草稿"
STALE_SECONDS = 6 * 60 * 60


def lock_path(workdir: Path) -> Path:
    return workdir / LOCK_DIR_NAME / LOCK_NAME


def _pid_alive(pid: int) -> bool:
    """Return True when the process is still running (best effort per platform)."""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == still_active
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def read_lock(workdir: Path) -> dict[str, Any] | None:
    path = lock_path(workdir)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"pid": -1, "owner": "<无法解析>", "started_at": "", "unreadable": True}
    return data if isinstance(data, dict) else None


def describe(lock: dict[str, Any] | None) -> str:
    if not lock:
        return "无锁"
    pid = lock.get("pid")
    alive = _pid_alive(int(pid)) if isinstance(pid, int) else False
    state = "仍在运行" if alive else "已退出（陈旧锁）"
    return (
        f"pid={pid}（{state}） owner={lock.get('owner', '?')} "
        f"host={lock.get('host', '?')} started={lock.get('started_at', '?')}"
    )


def is_active(lock: dict[str, Any] | None) -> bool:
    if not lock:
        return False
    pid = lock.get("pid")
    if not isinstance(pid, int) or pid <= 0:
        return False
    if lock.get("host") and lock.get("host") != socket.gethostname():
        # 别的机器上的锁无法判断进程，按新鲜度处理
        try:
            started = float(lock.get("started_ts") or 0)
        except (TypeError, ValueError):
            started = 0
        return bool(started) and (time.time() - started) < STALE_SECONDS
    return _pid_alive(pid)


def acquire(workdir: Path, owner: str, *, force: bool = False) -> Path:
    """Take the workdir lock, or stop with a readable message."""
    path = lock_path(workdir)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_lock(workdir)
    if existing and not force:
        if is_active(existing):
            raise SystemExit(
                "STOP_FOR_USER\n"
                "NEXT_ACTION: 同一个工作目录正被另一个会话写入，已停止本次运行以免互相覆盖。\n"
                f"- 目录：{workdir}\n"
                f"- 当前锁：{describe(existing)}\n"
                "- 等对方跑完再重试；确认对方已不在写（或进程已退出）时，可以运行\n"
                f"  python <SKILL_DIR>/scripts/workdir_lock.py --workdir {workdir} --clear\n"
                "  清除陈旧锁，或本次显式加 --ignore-lock 继续（风险自负）。"
            )
        print(f"[lock] 发现陈旧锁，已接管：{describe(existing)}", file=sys.stderr)
    payload = {
        "pid": os.getpid(),
        "owner": owner,
        "host": socket.gethostname(),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "started_ts": time.time(),
        "argv": " ".join(sys.argv[:6]),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def release(workdir: Path) -> None:
    path = lock_path(workdir)
    current = read_lock(workdir)
    if current and current.get("pid") not in (os.getpid(), None):
        # 别把别人的锁删掉（例如 force 接管后原主人收尾）
        return
    path.unlink(missing_ok=True)


@contextmanager
def hold(workdir: Path, owner: str, *, force: bool = False) -> Iterator[Path]:
    path = acquire(workdir, owner, force=force)
    try:
        yield path
    finally:
        release(workdir)


def main() -> int:
    parser = argparse.ArgumentParser(description="查看／清除工作目录锁")
    parser.add_argument("--workdir", default="软件著作权申请资料")
    parser.add_argument("--status", action="store_true", help="只打印锁的状态")
    parser.add_argument("--clear", action="store_true", help="删除锁文件（含陈旧锁）")
    args = parser.parse_args()

    workdir = Path(args.workdir)
    lock = read_lock(workdir)
    print(f"锁文件：{lock_path(workdir)}")
    print(f"状态：{describe(lock)}")
    if args.clear:
        lock_path(workdir).unlink(missing_ok=True)
        print("已删除锁文件。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
