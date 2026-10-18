import re
import os
import threading
from pathlib import Path

import torch
from fairseq.data.dictionary import Dictionary
from fastapi import HTTPException
from rvc_python.infer import RVCInference

torch.serialization.add_safe_globals([Dictionary])

MODELS_DIR = Path(os.getenv("RVC_MODELS_DIR", "~/.local/rvc_app")).expanduser()
MODELS_DIR.mkdir(parents=True, exist_ok=True)
NAME_RE = r"[\w.\- ]+"

# Initialize global engine and locks
rvc = RVCInference(device="cuda:0")
current_model = None
lock = threading.Lock()

def safe_name(name: str) -> str:
    name = Path(name).name
    if not re.fullmatch(NAME_RE, name):
        raise HTTPException(400, "Invalid name")
    return name

def get_model_paths(model: str):
    folder = MODELS_DIR / safe_name(model)
    if folder.is_file() and folder.suffix == ".pth":
        return folder, ""
    pths = sorted(folder.glob("*.pth")) if folder.is_dir() else []
    if not pths:
        raise HTTPException(404, "Model not found")
    indexes = sorted(folder.glob("*.index"))
    index_path = str(indexes[0]) if indexes else ""
    return pths[0], index_path
