import shutil
import tempfile
import zipfile
import os
import shutil
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
import uvicorn
load_dotenv()
API_PORT = os.getenv("API_PORT", '8000')

from .engine import MODELS_DIR, safe_name, get_model_paths, rvc, current_model, lock

app = FastAPI()

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


def _detect_models() -> list[str]:
    """Return model names found under the configured models directory."""
    if not MODELS_DIR.exists():
        return []

    found: set[str] = set()
    for path in MODELS_DIR.rglob("*.pth"):
        if path.is_file():
            # Models are normally stored in one directory per model. Also
            # accept .pth files placed directly in MODELS_DIR.
            found.add(path.parent.name if path.parent != MODELS_DIR else path.stem)
    return sorted(found)


@app.get("/models")
def list_models():
    return _detect_models()


@app.post("/convert")
def convert(
    background: BackgroundTasks,
    audio: UploadFile = File(...),
    model: str = Form(...),
    pitch: int = Form(0),
    f0method: str = Form("rmvpe"),
    index_rate: float = Form(0.7),
    protect: float = Form(0.33),
    hop_length: int = Form(128),
    rms_mix_rate: float = Form(0.25),
):
    global current_model
    pth_path, index_path = get_model_paths(model)

    with tempfile.TemporaryDirectory() as tmp:
        in_path = Path(tmp) / "in.wav"
        out_path = Path(tmp) / "out.wav"
        in_path.write_bytes(audio.file.read())

        with lock:
            if current_model != model:
                rvc.load_model(str(pth_path))
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
    """Run the API and its Svelte development client together."""
    client = run_client()
    try:
        uvicorn.run(
            "rvc_api:app",
            host="0.0.0.0",
            port=int(API_PORT),
            reload=True,
        )
    finally:
        if client and client.poll() is None:
            client.terminate()
            try:
                client.wait(timeout=5)
            except subprocess.TimeoutExpired:
                client.kill()


def run_client():
    """Start Vite for the Svelte client, if a JS package runner is available."""
    project_root = Path(__file__).resolve().parents[2]
    runner = shutil.which("bun")
    command = [runner, "run", "dev", "--", "--host", "0.0.0.0"] if runner else None
    if command is None:
        runner = shutil.which("npm")
        command = [runner, "run", "dev", "--", "--host", "0.0.0.0"] if runner else None
    if command is None:
        print("Svelte client not started: install Bun or npm and run `npm install`.")
        return None

    return subprocess.Popen(command, cwd=project_root)


def client_main():
    """Run only the Svelte development client until interrupted."""
    client = run_client()
    if client is None:
        return
    try:
        client.wait()
    except KeyboardInterrupt:
        client.terminate()
        try:
            client.wait(timeout=5)
        except subprocess.TimeoutExpired:
            client.kill()

def live(): 
    from .live import main
    main()

