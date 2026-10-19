# RVC API

A small FastAPI service and Svelte web client for managing RVC models and converting audio.

## Requirements

- Python 3.10
- [uv](https://docs.astral.sh/uv/)
- [Bun](https://bun.sh/) (or Node.js with npm) for the Svelte client

## Setup

Install the Python and JavaScript dependencies:

```bash
uv sync
bun install
```

The client uses WaveSurfer.js for waveform playback and its hover timeline
plugin. If you use npm instead of Bun, run `npm install` before starting the
client.

Models are read from `~/.local/rvc_app/models` by default. Set a different
directory and API port in `.env`:

```env
API_PORT=7000
```

Store each model in its own folder with at least one `.pth` file. An optional
`.index` file is also detected. A `.pth` file may be placed directly in the
configured directory.

## Run the app

Start both the API and Svelte development client with:

```bash
uv run rvc-api
```

Open the Vite URL printed in the terminal (usually <http://localhost:5173>).
The client lists available models, accepts an audio file for conversion, and
lets you upload a model ZIP containing a `.pth` file and optionally an `.index`
file. API requests are proxied through Vite to the port configured by
`API_PORT`.

To run just the Svelte client, use `uv run rvc-client`. It serves the client
on Vite's usual port and proxies `/api` requests to the API. Start the API
separately when you need conversion features:

```bash
uv run uvicorn rvc_api:app --app-dir src --host 0.0.0.0 --port 7000
```

For API-only use, the API can still be started directly with:

```bash
uv run uvicorn rvc_api:app --app-dir src --host 0.0.0.0 --port 7000
```

Upload and convert:

```bash
curl -F "file=@my-model.zip" http://localhost:7000/models
curl -o output.wav -F "audio=@input.wav" -F "model=MyModel" \
  http://localhost:7000/convert
```

Start live mode with `uv run rvc-live`. It requires a working audio device and
an installed RVC runtime.
