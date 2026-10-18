# main.py
import re
import shutil
import tempfile
import threading
import zipfile
from pathlib import Path

import torch
from fairseq.data.dictionary import Dictionary
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from rvc_python.infer import RVCInference

torch.serialization.add_safe_globals([Dictionary])

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)
MAX_ZIP_BYTES = 1024 * 1024 * 1024  # 1 GB uncompressed cap
NAME_RE = r"[\w.\- ]+"

app = FastAPI()
rvc = RVCInference(device="cuda:0")
current_model = None
lock = threading.Lock()


def safe_name(name: str) -> str:
    name = Path(name).name
    if not re.fullmatch(NAME_RE, name):
        raise HTTPException(400, "Invalid name")
    return name


@app.post("/models")
def upload_model(file: UploadFile = File(...)):
    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "Must be a .zip file")

    folder = MODELS_DIR / safe_name(Path(file.filename).stem)
    if folder.exists():
        raise HTTPException(409, "Model already exists")

    with tempfile.TemporaryFile() as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp.seek(0)
        try:
            zf = zipfile.ZipFile(tmp)
        except zipfile.BadZipFile:
            raise HTTPException(400, "Invalid zip")

        with zf:
            members = [
                m for m in zf.infolist()
                if not m.is_dir() and Path(m.filename).suffix in (".pth", ".index")
            ]
            if not any(m.filename.endswith(".pth") for m in members):
                raise HTTPException(400, "Zip contains no .pth file")
            if sum(m.file_size for m in members) > MAX_ZIP_BYTES:
                raise HTTPException(400, "Zip too large")

            folder.mkdir()
            try:
                for m in members:
                    target = folder / safe_name(m.filename)
                    with zf.open(m) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
            except Exception:
                shutil.rmtree(folder, ignore_errors=True)
                raise

    return {"uploaded": folder.name, "files": sorted(p.name for p in folder.iterdir())}


@app.get("/models")
def list_models():
    return sorted(p.name for p in MODELS_DIR.iterdir() if p.is_dir())


@app.post("/convert")
def convert(
    background: BackgroundTasks,
    audio: UploadFile = File(...),
    model: str = Form(...),
    pitch: int = Form(0),
    f0method: str = Form("rmvpe"),
    # --- New Settings ---
    index_rate: float = Form(0.7),
    protect: float = Form(0.33),
    hop_length: int = Form(128),
    rms_mix_rate: float = Form(0.25),
    # --------------------
):
    global current_model

    folder = MODELS_DIR / safe_name(model)
    pths = sorted(folder.glob("*.pth")) if folder.is_dir() else []
    if not pths:
        raise HTTPException(404, "Model not found")

    # Automatically look for a matching .index file in the model folder
    indexes = sorted(folder.glob("*.index"))
    index_path = str(indexes[0]) if indexes else ""

    with tempfile.TemporaryDirectory() as tmp:
        in_path = Path(tmp) / "in.wav"
        out_path = Path(tmp) / "out.wav"
        in_path.write_bytes(audio.file.read())

        with lock:
            if current_model != model:
                rvc.load_model(str(pths[0]))
                current_model = model
            
            rvc.set_params(
                f0method=f0method,
                f0up_key=pitch,
                index_path=index_path,
                index_rate=index_rate,
                protect=protect,
                hop_length=hop_length,
                rms_mix_rate=rms_mix_rate,
            )
            rvc.infer_file(str(in_path), str(out_path))

        final = Path(tempfile.mkstemp(suffix=".wav")[1])
        final.write_bytes(out_path.read_bytes())

    background.add_task(final.unlink, missing_ok=True)
    return FileResponse(final, media_type="audio/wav", filename="output.wav")

def main():
    import uvicorn
    """Launched via `uv run rvc-api`"""
    uvicorn.run(
        "rvc_api:app", 
        host="0.0.0.0", 
        port=7000, 
        reload=True
    )