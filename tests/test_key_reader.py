"""Unit tests for KeyReader lifecycle behavior."""

from __future__ import annotations

import main


class _FakeStdin:  # pylint: disable=too-few-public-methods
    """Minimal stdin test double with a stable file descriptor."""

    def fileno(self) -> int:
        """Return a deterministic fake fd."""

        return 99


class _FakeThread:  # pylint: disable=too-few-public-methods
    """Thread test double that tracks start/join calls."""

    def __init__(self, target, daemon: bool) -> None:  # noqa: ANN001
        self.target = target
        self.daemon = daemon
        self.started = False
        self.alive = True
        self.join_timeout: float | None = None

    def start(self) -> None:
        """Mark the thread as started."""

        self.started = True

    def is_alive(self) -> bool:
        """Expose fake liveness state."""

        return self.alive

    def join(self, timeout: float) -> None:
        """Record join timeout and mark thread as not alive."""

        self.join_timeout = timeout
        self.alive = False


def test_key_reader_start_sets_cbreak_and_starts_thread(monkeypatch) -> None:
    """start() should configure terminal mode and launch the reader thread."""

    calls: dict[str, object] = {}

    monkeypatch.setattr(main.sys, "stdin", _FakeStdin())
    monkeypatch.setattr(main.termios, "tcgetattr", lambda fd: ["attrs", fd])

    def _fake_setcbreak(fd: int) -> None:
        calls["cbreak_fd"] = fd

    monkeypatch.setattr(main.tty, "setcbreak", _fake_setcbreak)

    def _fake_thread(*, target, daemon: bool):  # noqa: ANN001
        fake = _FakeThread(target=target, daemon=daemon)
        calls["thread"] = fake

        return fake

    monkeypatch.setattr(main.threading, "Thread", _fake_thread)

    reader = main.KeyReader()
    reader.start()

    fake_thread = calls["thread"]
    assert calls["cbreak_fd"] == 99
    assert reader._old == ["attrs", 99]  # pylint: disable=protected-access
    assert isinstance(fake_thread, _FakeThread)
    assert fake_thread.started
    assert fake_thread.daemon
    assert callable(fake_thread.target)


def test_key_reader_stop_stops_thread_and_restores_terminal(monkeypatch) -> None:
    """stop() should signal shutdown, join thread, and restore terminal settings."""

    calls: dict[str, object] = {}
    fake_thread = _FakeThread(target=lambda: None, daemon=True)

    monkeypatch.setattr(main.sys, "stdin", _FakeStdin())

    def _fake_tcsetattr(fd: int, when: int, attrs) -> None:  # noqa: ANN001
        calls["tcsetattr"] = (fd, when, attrs)

    monkeypatch.setattr(main.termios, "tcsetattr", _fake_tcsetattr)

    reader = main.KeyReader()
    reader._thread = fake_thread  # pylint: disable=protected-access
    reader._old = ["saved"]  # pylint: disable=protected-access

    reader.stop()

    assert reader._stop_event.is_set()  # pylint: disable=protected-access
    assert fake_thread.join_timeout == 0.2
    assert calls["tcsetattr"] == (99, main.termios.TCSADRAIN, ["saved"])
    assert reader._thread is None  # pylint: disable=protected-access
