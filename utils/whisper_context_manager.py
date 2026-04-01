import sys
from contextlib import contextmanager
from utils.whisper_progress import WhisperProgressRedirector

@contextmanager
def capture_whisper_progress(send_progress_fn=None):
    old_stderr = sys.stderr
    redirector = WhisperProgressRedirector(
        original_stream=old_stderr,
        send_progress_fn=send_progress_fn
    )
    sys.stderr = redirector
    try:
        yield
    finally:
        sys.stderr = old_stderr