from functools import lru_cache
import os
import tempfile
from pathlib import Path
import shutil


def _ensure_ffmpeg_available():
    if shutil.which("ffmpeg"):
        return

    try:
        import imageio_ffmpeg
        import whisper.audio as whisper_audio

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_exe_path = Path(ffmpeg_exe)

        if not getattr(whisper_audio, "_acadclarifier_ffmpeg_patched", False):
            original_run = whisper_audio.run

            def run_with_bundled_ffmpeg(cmd, *args, **kwargs):
                if isinstance(cmd, (list, tuple)) and cmd:
                    executable = str(cmd[0]).lower()
                    if executable == "ffmpeg":
                        cmd = [str(ffmpeg_exe_path), *cmd[1:]]
                return original_run(cmd, *args, **kwargs)

            whisper_audio.run = run_with_bundled_ffmpeg
            whisper_audio._acadclarifier_ffmpeg_patched = True

        shim_dir = Path(tempfile.gettempdir()) / "acadclarifier-ffmpeg"
        shim_dir.mkdir(parents=True, exist_ok=True)

        if os.name == "nt":
            shim_path = shim_dir / "ffmpeg.cmd"
            if not shim_path.exists():
                shim_path.write_text(
                    f'@echo off\r\n"{ffmpeg_exe_path}" %*\r\n',
                    encoding="utf-8",
                )
        else:
            shim_path = shim_dir / "ffmpeg"
            if not shim_path.exists():
                shim_path.write_text(
                    f'#!/bin/sh\n"{ffmpeg_exe_path}" "$@"\n',
                    encoding="utf-8",
                )
                shim_path.chmod(0o755)

        current_path = os.environ.get("PATH", "")
        shim_dir_str = str(shim_dir)
        if shim_dir_str not in current_path:
            os.environ["PATH"] = f"{shim_dir_str}{os.pathsep}{current_path}"
    except Exception:
        # Fall back to whatever ffmpeg is already on PATH.
        pass


@lru_cache(maxsize=1)
def get_whisper_model():
    import whisper

    model_name = os.getenv("WHISPER_MODEL_NAME", "base")
    return whisper.load_model(model_name)


def transcribe_audio_bytes(audio_bytes):
    if not audio_bytes:
        raise ValueError("audio is required")

    _ensure_ffmpeg_available()

    import whisper

    temp_audio = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
    temp_audio_path = Path(temp_audio.name)
    try:
        temp_audio.write(audio_bytes)
        temp_audio.flush()
        temp_audio.close()
        audio_data = whisper.load_audio(temp_audio.name)
    finally:
        try:
            temp_audio.close()
        except Exception:
            pass
        if temp_audio_path.exists():
            temp_audio_path.unlink(missing_ok=True)

    result = get_whisper_model().transcribe(audio_data, fp16=False)
    transcript = (result.get("text") or "").strip()

    return {
        "text": transcript,
        "language": result.get("language"),
        "model": os.getenv("WHISPER_MODEL_NAME", "base"),
    }
