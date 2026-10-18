# RVC API

Service for uploading RVC models and converting audio.

## Setup

Requires Python 3.10 and `uv`:

```bash
uv sync
```

Models are read from `~/.local/rvc_app/models` by default. Set a different
directory with `RVC_MODELS_DIR` in `.env`:

```env
RVC_MODELS_DIR=/absolute/path/to/models
API_PORT=7000
```

Store each model in its own folder with at least one `.pth` file. An optional
`.index` file is also detected. A `.pth` file may be placed directly in the
configured directory.

## Run

```bash
uv run rvc-api
```

List detected models:

```bash
curl http://localhost:7000/model
```

`GET /models` is an alias. The directory is scanned on every request, so new
models appear without restarting the API.

Upload and convert:

```bash
curl -F "file=@my-model.zip" http://localhost:7000/models
curl -o output.wav -F "audio=@input.wav" -F "model=MyModel" \
  http://localhost:7000/convert
```

Start live mode with `uv run rvc-live`. It requires a working audio device and
an installed RVC runtime.
