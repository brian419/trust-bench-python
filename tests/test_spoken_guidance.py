"""Local speech stays opt-in, interruptible and independent of GUI/evaluation."""

from queue import Empty
from threading import Event
from unittest.mock import MagicMock, patch

from pytest import raises

from spoken_guidance import MAX_SPEECH_CHARACTERS, SpokenGuidance


def available_guidance():
    narrator = SpokenGuidance()
    narrator.available = True
    return narrator


def test_disabled_by_default_does_not_launch_threads_or_processes():
    with patch("spoken_guidance.Thread") as thread, patch("spoken_guidance.Popen") as launch:
        narrator = SpokenGuidance()
        narrator.speak("Hello")
        narrator.close()
    thread.assert_not_called()
    launch.assert_not_called()


def test_unavailable_backend_does_not_enable_or_start_worker():
    narrator = SpokenGuidance()
    narrator.available = False
    with patch("spoken_guidance.Thread") as worker:
        assert narrator.set_enabled(True) is False
    assert narrator.enabled is False
    worker.assert_not_called()


def test_thread_start_failure_recovers_to_disabled_state():
    narrator = available_guidance()
    with patch("spoken_guidance.Thread") as worker:
        worker.return_value.start.side_effect = RuntimeError("failed")
        assert narrator.set_enabled(True) is False
    assert narrator.failed is True and narrator.enabled is False


def test_only_latest_bounded_hint_is_queued_and_stop_discards_it():
    narrator = available_guidance()
    with patch("spoken_guidance.Thread"):
        narrator.set_enabled(True)
        narrator.speak("old")
        narrator.speak("x" * (MAX_SPEECH_CHARACTERS + 100))
    generation, text = narrator._queue.get_nowait()
    assert generation == 2 and len(text) == MAX_SPEECH_CHARACTERS
    with raises(Empty):
        narrator._queue.get_nowait()
    narrator.speak("pending")
    narrator.stop()
    assert narrator._queue.empty()
    narrator.close()
    assert narrator.set_enabled(True) is False


def test_real_worker_thread_uses_stdin_and_stops_only_its_owned_process():
    narrator = available_guidance()
    entered, released = Event(), Event()
    process = MagicMock()
    process.poll.return_value = None
    process.returncode = -15

    def communicate(**kwargs):
        entered.set()
        assert released.wait(3)

    process.communicate.side_effect = communicate
    process.terminate.side_effect = released.set
    text = "Do not execute: $(echo unsafe); --voice arbitrary"
    try:
        with patch("spoken_guidance.Popen", return_value=process) as launch:
            assert narrator.set_enabled(True)
            narrator.speak(text)
            assert entered.wait(2)
            narrator.close()
            narrator._worker.join(timeout=2)
            assert not narrator._worker.is_alive()
        assert launch.call_args.args[0] == ["/usr/bin/say", "-f", "-"]
        assert "shell" not in launch.call_args.kwargs
        process.communicate.assert_called_once_with(input=text, timeout=120)
        process.terminate.assert_called_once()
    finally:
        released.set()
        narrator.close()


def test_launch_failure_is_reported_and_worker_can_close():
    narrator = available_guidance()
    attempted = Event()

    def fail(*args, **kwargs):
        attempted.set()
        raise OSError("speech unavailable")

    with patch("spoken_guidance.Popen", side_effect=fail):
        narrator.set_enabled(True)
        narrator.speak("Hello")
        assert attempted.wait(2)
        narrator.close()
        narrator._worker.join(timeout=2)
    assert not narrator._worker.is_alive()
    assert narrator.failed is True
    assert narrator.enabled is False
