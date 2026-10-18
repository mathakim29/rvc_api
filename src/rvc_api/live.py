import argparse
import queue
import tempfile
import threading
from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
import sounddevice as sd
from scipy.signal import resample_poly

from .engine import rvc, MODELS_DIR, lock
from . import engine

SAMPLE_RATE = 44100
BLOCK_SECONDS = 0.5
FADE_MS = 10
SILENCE_RMS = 0.002
MAX_QUEUE = 4


SEARCH_DIRS = [
    MODELS_DIR,
    Path("~/.local/rvc_api").expanduser(),
]


def find_models(extra_dir=None):
    """Return {name: (pth_path, index_path)} scanning recursively."""
    dirs = ([Path(extra_dir).expanduser()] if extra_dir else []) + SEARCH_DIRS
    models = {}
    for d in dirs:
        if not d.exists():
            continue
        print(f"Scanning: {d}")
        for pth in sorted(d.rglob("*.pth")):
            idx = sorted(pth.parent.glob("*.index"))
            models.setdefault(pth.parent.name, (pth, str(idx[0]) if idx else ""))
    return models


def load_rvc(pth, index_path):
    with lock:
        rvc.load_model(str(pth))
        rvc.set_params(
            f0method="rmvpe",
            f0up_key=0,
            index_rate=0.7,
            protect=0.33,
            rms_mix_rate=0.25,
        )
        if index_path:
            rvc.index_path = index_path


def convert(chunk, tmp):
    n = len(chunk)
    in_path, out_path = tmp / "in.wav", tmp / "out.wav"
    sf.write(in_path, chunk, SAMPLE_RATE)

    with lock:
        rvc.infer_file(str(in_path), str(out_path))

    out, sr = sf.read(out_path, dtype="float32")
    if out.ndim > 1:
        out = out.mean(axis=1)
    if sr != SAMPLE_RATE:
        g = gcd(sr, SAMPLE_RATE)
        out = resample_poly(out, SAMPLE_RATE // g, sr // g).astype(np.float32)

    out = np.pad(out, (0, max(0, n - len(out))))[:n]

    f = int(SAMPLE_RATE * FADE_MS / 1000)
    ramp = np.linspace(0, 1, f, dtype=np.float32)
    out[:f] *= ramp
    out[-f:] *= ramp[::-1]
    return out


def run_live_audio(in_dev=None, out_dev=None):
    block = int(SAMPLE_RATE * BLOCK_SECONDS)
    in_q = queue.Queue(maxsize=MAX_QUEUE)
    out_q = queue.Queue()
    stop = threading.Event()
    state = {"in_buf": np.zeros(0, dtype=np.float32),
             "out_buf": np.zeros(0, dtype=np.float32),
             "level": 0.0, "converted": 0}

    def input_cb(indata, frames, time, status):
        if status:
            print("IN:", status)
        mono = indata[:, 0]
        state["level"] = float(np.sqrt(np.mean(mono ** 2)))
        buf = np.concatenate([state["in_buf"], mono])
        while len(buf) >= block:
            try:
                in_q.put_nowait(buf[:block].copy())
            except queue.Full:
                pass
            buf = buf[block:]
        state["in_buf"] = buf

    def output_cb(outdata, frames, time, status):
        if status:
            print("OUT:", status)
        buf = state["out_buf"]
        while len(buf) < frames:
            try:
                buf = np.concatenate([buf, out_q.get_nowait()])
            except queue.Empty:
                break
        n = min(frames, len(buf))
        outdata[:, 0] = 0
        outdata[:n, 0] = buf[:n]
        state["out_buf"] = buf[n:]

    def worker():
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            while not stop.is_set():
                try:
                    chunk = in_q.get(timeout=0.2)
                except queue.Empty:
                    continue
                try:
                    if engine.current_model is None:
                        out_q.put(chunk)  # passthrough
                    elif np.sqrt(np.mean(chunk ** 2)) < SILENCE_RMS:
                        out_q.put(np.zeros_like(chunk))
                    else:
                        out_q.put(convert(chunk, tmp))
                        state["converted"] += 1
                except Exception as e:
                    print(f"Live processing error: {e!r}")
                    out_q.put(chunk)

    threading.Thread(target=worker, daemon=True).start()

    print(f"Input device:  {sd.query_devices(in_dev, 'input')['name']}")
    print(f"Output device: {sd.query_devices(out_dev, 'output')['name']}")
    print("Running (use headphones). Ctrl+C to stop.\n")

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                        blocksize=1024, device=in_dev, callback=input_cb), \
         sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                         blocksize=1024, device=out_dev, callback=output_cb):
        try:
            while not stop.wait(2):
                print(f"mic level: {state['level']:.4f} | converted chunks: {state['converted']}")
        except KeyboardInterrupt:
            pass
    stop.set()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", help="Model folder name (default: first found)")
    parser.add_argument("--in-device", help="Input device index or name")
    parser.add_argument("--out-device", help="Output device index or name")
    parser.add_argument("--list-devices", action="store_true")
    args = parser.parse_args()

    if args.list_devices:
        print(sd.query_devices())
        raise SystemExit

    def dev(v):
        return int(v) if v and v.isdigit() else v

    print(f"Scanning: {MODELS_DIR}")
    models = find_models()
    print(f"Found models: {list(models) or 'NONE'}")

    name = args.model if args.model in models else (next(iter(models), None))
    if args.model and args.model not in models:
        print(f"'{args.model}' not found, using {name}")

    if name:
        print(f"-> Loading: {name}")
        load_rvc(*models[name])
    engine.current_model = name

    run_live_audio(dev(args.in_device), dev(args.out_device))
    print("Stopped.")

# uv run python -m rvc_api.live --in-device pulse --out-device pulse