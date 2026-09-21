"""GPU ladder probe (W7 apex).

Rungs, in preference order:
  server-gpu  — CUDA_VISIBLE_DEVICES points at a remote/server GPU endpoint
                (hostname or index list) AND an NVIDIA driver answers.
  cuda-local  — nvidia-smi answers, or torch.cuda / faster-whisper CUDA loads.
  mps-apple   — Apple Silicon (darwin + arm64): Metal Performance Shaders path.
  cpu-base    — always available; the honest fallback. CPU path stays green.

No GPU on this rig class is a normal result, not an error: the probe reports
``selected: cpu-base`` with ``gpu_present: false`` and every rung's evidence.
Upstream `hermes doctor` has no GPU probe, so this is the apex replacement.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from typing import Any, Callable, Dict, List

from ._common import utcnow

RUNGS = ("server-gpu", "cuda-local", "mps-apple", "cpu-base")


def _run(cmd: List[str], timeout: int = 10) -> tuple[bool, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode == 0, (p.stdout or "").strip()[:500]
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"{type(e).__name__}: {e}"


def _smiexists() -> tuple[bool, str]:
    path = shutil.which("nvidia-smi") or "/usr/lib/wsl/lib/nvidia-smi"
    if not shutil.which("nvidia-smi") and not os.path.exists(path):
        return False, "nvidia-smi not on PATH"
    return _run([path, "-L"])


def probe_gpu_ladder(env: Dict[str, str] | None = None,
                     torch_cuda: Callable[[], bool] | None = None,
                     runner: Callable | None = None) -> Dict[str, Any]:
    """Probe every rung, return evidence + selection. Injectables for tests."""
    env = env if env is not None else dict(os.environ)
    run = runner or _run
    evidence: Dict[str, Any] = {}

    smi_ok, smi_out = _smiexists() if runner is None else (False, "injected")
    if runner is not None:
        smi_ok, smi_out = run(["nvidia-smi", "-L"])
    evidence["nvidia_smi"] = {"ok": smi_ok, "out": smi_out}

    if torch_cuda is not None:
        cuda_ok = bool(torch_cuda())
        cuda_how = "injected"
    else:
        try:
            import torch  # type: ignore
            cuda_ok = bool(torch.cuda.is_available())
            cuda_how = "torch.cuda.is_available"
        except (ImportError, OSError, RuntimeError) as e:
            cuda_ok, cuda_how = False, f"torch-unusable: {type(e).__name__}"
    evidence["torch_cuda"] = {"ok": cuda_ok, "how": cuda_how}

    cvd = (env.get("CUDA_VISIBLE_DEVICES") or "").strip()
    evidence["cuda_visible_devices"] = cvd or "(unset)"
    mach = platform.machine().lower()
    evidence["platform"] = {"system": platform.system(), "machine": mach}

    if smi_ok and cvd and not cvd.startswith("-"):
        selected, reason = "server-gpu", "driver answers + CUDA_VISIBLE_DEVICES set"
    elif smi_ok or cuda_ok:
        selected, reason = "cuda-local", "local NVIDIA driver/CUDA answers"
    elif platform.system() == "Darwin" and mach in ("arm64", "aarch64"):
        selected, reason = "mps-apple", "Apple Silicon: MPS path"
    else:
        selected, reason = "cpu-base", "no GPU evidence: CPU path (green)"
    return {
        "rungs": list(RUNGS),
        "evidence": evidence,
        "selected": selected,
        "reason": reason,
        "gpu_present": selected != "cpu-base",
        "probed_at": utcnow(),
        "python": sys.version.split()[0],
    }


def probe_stt_engines(env: Dict[str, str] | None = None,
                      importable: Callable[[str], bool] | None = None) -> Dict[str, Any]:
    """Which transcription engines are actually usable here? Honest-absent."""
    env = env if env is not None else dict(os.environ)

    def _imp(name: str) -> bool:
        if importable is not None:
            return bool(importable(name))
        try:
            __import__(name)
            return True
        except ImportError:
            return False

    engines = {
        "faster-whisper-local": _imp("faster_whisper"),
        "openai-whisper-local": _imp("whisper"),
        "groq-cloud": bool(env.get("GROQ_API_KEY")),
        "openai-cloud": bool(env.get("OPENAI_API_KEY")),
    }
    usable = [k for k, v in engines.items() if v]
    return {
        "engines": engines,
        "usable": usable,
        "preferred": usable[0] if usable else None,
        "note": ("local faster-whisper first, then Groq, then OpenAI "
                 "(PRD STT priority)" if usable else
                 "no STT engine installed/set: partials pipeline runs on "
                 "injected engines only; live transcription honest-absent"),
    }
