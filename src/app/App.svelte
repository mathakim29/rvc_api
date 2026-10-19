<script>
  import { onMount } from 'svelte';
  import { AudioLines, Download, Moon, Pause, Play, RefreshCw, Sun, Upload, WandSparkles } from '@lucide/svelte';
  import WaveSurfer from 'wavesurfer.js';
  import Hover from 'wavesurfer.js/dist/plugins/hover.esm.js';

  let models = $state([]);
  let model = $state('');
  let audio = $state(null);
  let convertedUrl = $state('');
  let loading = $state(false);
  let message = $state('');
  let darkMode = $state(false);
  let sourceUrl = $state('');
  let sourceWaveform = $state();
  let outputWaveform = $state();
  let sourcePlayer;
  let outputPlayer;
  let sourcePlaying = $state(false);
  let outputPlaying = $state(false);
  let settings = $state({ pitch: 0, f0method: 'rmvpe', index_rate: 0.7, protect: 0.33, hop_length: 128, rms_mix_rate: 0.25 });

  function createPlayer(container, url, kind) {
    if (!container || !url) return null;
    const player = WaveSurfer.create({
      container,
      url,
      height: 72,
      waveColor: darkMode ? '#585b70' : '#c4b5fd',
      progressColor: darkMode ? '#cba6f7' : '#7c3aed',
      cursorColor: darkMode ? '#f5c2e7' : '#7c3aed',
      barWidth: 2,
      barGap: 2,
      barRadius: 3,
      plugins: [Hover.create({ lineColor: darkMode ? '#f5c2e7' : '#7c3aed', lineWidth: 1, labelBackground: darkMode ? '#11111b' : '#292524', labelColor: darkMode ? '#cdd6f4' : '#fff' })],
    });
    player.on('error', () => { message = `Could not load ${kind} audio.`; });
    player.on('finish', () => {
      if (kind === 'source') sourcePlaying = false;
      else outputPlaying = false;
    });
    return player;
  }

  $effect(() => {
    sourcePlayer?.destroy();
    sourcePlayer = createPlayer(sourceWaveform, sourceUrl, 'source');
  });

  $effect(() => {
    outputPlayer?.destroy();
    outputPlayer = createPlayer(outputWaveform, convertedUrl, 'converted');
  });

  async function loadModels() {
    try {
      const response = await fetch('/api/models');
      if (!response.ok) throw new Error('Could not load models');
      models = await response.json();
      if (!models.includes(model)) model = models[0] ?? '';
      message = models.length ? '' : 'No models found. Add a model ZIP below.';
    } catch {
      message = 'Could not connect to the API. Make sure it is running.';
    }
  }

  onMount(() => {
    loadModels();
    return () => {
      sourcePlayer?.destroy();
      outputPlayer?.destroy();
      if (sourceUrl) URL.revokeObjectURL(sourceUrl);
      if (convertedUrl) URL.revokeObjectURL(convertedUrl);
    };
  });

  function chooseAudio(event) {
    audio = event.currentTarget.files?.[0] ?? null;
    if (sourceUrl) URL.revokeObjectURL(sourceUrl);
    sourceUrl = audio ? URL.createObjectURL(audio) : '';
  }

  function togglePlayer(kind) {
    const player = kind === 'source' ? sourcePlayer : outputPlayer;
    if (!player) return;
    player.playPause();
    if (kind === 'source') sourcePlaying = !sourcePlaying;
    else outputPlaying = !outputPlaying;
  }

  async function convert() {
    if (!audio || !model) return;
    loading = true;
    message = 'Converting audio…';
    if (convertedUrl) URL.revokeObjectURL(convertedUrl);
    convertedUrl = '';
    const body = new FormData();
    body.append('audio', audio);
    body.append('model', model);
    Object.entries(settings).forEach(([key, value]) => body.append(key, String(value)));
    try {
      const response = await fetch('/api/convert', { method: 'POST', body });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail ?? 'Conversion failed');
      }
      convertedUrl = URL.createObjectURL(await response.blob());
      message = 'Done. Your converted audio is ready.';
    } catch (error) {
      message = error.message;
    } finally {
      loading = false;
    }
  }

  async function uploadModel(event) {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!file) return;
    const body = new FormData();
    body.append('file', file);
    message = 'Uploading model…';
    try {
      const response = await fetch('/api/models', { method: 'POST', body });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail ?? 'Upload failed');
      await loadModels();
      model = result.uploaded;
      message = `Added ${result.uploaded}.`;
    } catch (error) {
      message = error.message;
    } finally {
      input.value = '';
    }
  }
</script>

<svelte:head>
  <title>RVC Studio</title>
  <meta name="description" content="A simple interface for RVC voice conversion." />
</svelte:head>

<main class="min-h-screen px-5 py-10 transition-colors sm:py-16" class:catppuccin-dark={darkMode} style:background-color={darkMode ? '#1e1e2e' : '#eff1f5'} style:color={darkMode ? '#cdd6f4' : '#4c4f69'}>
  <section class="mx-auto max-w-xl">
    <header class="mb-8 flex items-center justify-between gap-3">
      <div class="flex items-center gap-3">
      <div class="rounded-xl p-3 text-white" style:background-color={darkMode ? '#cba6f7' : '#8839ef'} style:color={darkMode ? '#1e1e2e' : '#ffffff'}><AudioLines size={22} /></div>
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.2em]" style:color={darkMode ? '#cba6f7' : '#8839ef'}>RVC API</p>
        <h1 class="text-2xl font-bold tracking-tight">Voice converter</h1>
      </div>
      </div>
      <button onclick={() => darkMode = !darkMode} class="rounded-lg border p-2 transition-colors hover:border-[#8839ef]" style:border-color={darkMode ? '#585b70' : '#ccd0da'} style:color={darkMode ? '#cdd6f4' : '#4c4f69'} aria-label="Toggle dark mode">
        {#if darkMode}<Sun size={18} />{:else}<Moon size={18} />{/if}
      </button>
    </header>

    <div class="space-y-6 rounded-2xl border p-6 shadow-sm transition-colors sm:p-8" style:background-color={darkMode ? '#181825' : '#e6e9ef'} style:border-color={darkMode ? '#45475a' : '#ccd0da'}>
      <div>
        <label for="audio" class="mb-2 block text-sm font-semibold">1. Choose audio</label>
        <input id="audio" type="file" accept="audio/*,.wav" onchange={chooseAudio}
          class="block w-full rounded-lg border text-sm file:mr-4 file:border-0 file:px-4 file:py-3 file:font-medium" style:background-color={darkMode ? '#313244' : '#e6e9ef'} style:border-color={darkMode ? '#585b70' : '#ccd0da'} style:color={darkMode ? '#cdd6f4' : '#4c4f69'} />
        <p class="mt-2 text-xs" style:color={darkMode ? '#a6adc8' : '#6c6f85'}>Pick an audio file to convert.</p>
        {#if sourceUrl}
          <div class="mt-3 flex items-center gap-2">
            <div bind:this={sourceWaveform} class="min-w-0 flex-1 rounded-lg px-2 py-1" style:background-color={darkMode ? '#313244' : '#dce0e8'}></div>
            <button onclick={() => togglePlayer('source')} class="flex h-[80px] w-[80px] shrink-0 items-center justify-center rounded-lg border p-2 transition-colors" style:border-color={darkMode ? '#585b70' : '#ccd0da'} style:background-color={darkMode ? '#313244' : '#e6e9ef'} style:color={darkMode ? '#cba6f7' : '#8839ef'} aria-label={sourcePlaying ? 'Pause source audio' : 'Play source audio'}>
              {#if sourcePlaying}<Pause size={17} />{:else}<Play size={17} />{/if}
            </button>
          </div>
        {/if}
      </div>

      <details class="rounded-lg border p-4" style:border-color={darkMode ? '#45475a' : '#ccd0da'}>
        <summary class="cursor-pointer text-sm font-semibold">Conversion settings</summary>
        <div class="mt-4 grid grid-cols-2 gap-3 text-sm">
          <label>Pitch<input type="number" bind:value={settings.pitch} class="theme-field mt-1 w-full rounded border p-2" /></label>
          <label>F0 method<select bind:value={settings.f0method} class="theme-field mt-1 w-full rounded border p-2"><option>rmvpe</option><option>harvest</option><option>pm</option><option>crepe</option></select></label>
          <label>Index rate<input type="number" min="0" max="1" step="0.05" bind:value={settings.index_rate} class="theme-field mt-1 w-full rounded border p-2" /></label>
          <label>Protect<input type="number" min="0" max="0.5" step="0.01" bind:value={settings.protect} class="theme-field mt-1 w-full rounded border p-2" /></label>
          <label>Hop length<input type="number" bind:value={settings.hop_length} class="theme-field mt-1 w-full rounded border p-2" /></label>
          <label>RMS mix<input type="number" min="0" max="1" step="0.05" bind:value={settings.rms_mix_rate} class="theme-field mt-1 w-full rounded border p-2" /></label>
        </div>
      </details>

      <div>
        <div class="mb-2 flex items-center justify-between">
          <label for="model" class="text-sm font-semibold">2. Select a model</label>
          <button onclick={loadModels} class="inline-flex items-center gap-1 text-xs hover:text-violet-700" style:color={darkMode ? '#a6adc8' : '#6c6f85'} aria-label="Refresh models">
            <RefreshCw size={13} /> Refresh
          </button>
        </div>
        <select id="model" bind:value={model} disabled={!models.length}
          class="theme-field w-full rounded-lg border px-3 py-3 text-sm">
          {#if !models.length}<option value="">No models available</option>{/if}
          {#each models as item}<option value={item}>{item}</option>{/each}
        </select>
      </div>

      <button onclick={convert} disabled={!audio || !model || loading}
        class="flex w-full items-center justify-center gap-2 rounded-lg px-4 py-3 font-semibold transition" style:background-color={darkMode ? '#cba6f7' : '#8839ef'} style:color={darkMode ? '#1e1e2e' : '#ffffff'}>
        <WandSparkles size={18} /> {loading ? 'Working…' : 'Convert audio'}
      </button>

      {#if convertedUrl}
        <div class="space-y-3 rounded-xl p-4" style:background-color={darkMode ? '#302b45' : '#e6e9ef'}>
          <p class="text-sm font-semibold">Converted audio</p>
          <div class="flex items-center gap-2">
            <div bind:this={outputWaveform} class="min-w-0 flex-1 rounded-lg px-2 py-1" style:background-color={darkMode ? '#313244' : '#dce0e8'}></div>
            <button onclick={() => togglePlayer('output')} class="flex h-[80px] w-[80px] shrink-0 items-center justify-center rounded-lg border p-2 transition-colors" style:border-color={darkMode ? '#585b70' : '#ccd0da'} style:background-color={darkMode ? '#313244' : '#e6e9ef'} style:color={darkMode ? '#cba6f7' : '#8839ef'} aria-label={outputPlaying ? 'Pause converted audio' : 'Play converted audio'}>
              {#if outputPlaying}<Pause size={17} />{:else}<Play size={17} />{/if}
            </button>
          </div>
          <a href={convertedUrl} download="converted.wav" class="inline-flex items-center gap-2 text-sm font-semibold" style:color={darkMode ? '#cba6f7' : '#8839ef'}>
            <Download size={16} /> Download WAV
          </a>
        </div>
      {/if}

      {#if message}<p class="text-sm" style:color={darkMode ? '#a6adc8' : '#6c6f85'} aria-live="polite">{message}</p>{/if}
    </div>

    <div class="mt-5 rounded-2xl border border-dashed p-5" style:background-color={darkMode ? '#181825' : '#e6e9ef'} style:border-color={darkMode ? '#45475a' : '#ccd0da'}>
      <div class="flex items-start gap-3">
        <Upload size={18} class="mt-0.5" color={darkMode ? '#a6adc8' : '#6c6f85'} />
        <div class="flex-1">
          <h2 class="text-sm font-semibold">Add a model</h2>
          <p class="mb-3 mt-1 text-xs" style:color={darkMode ? '#a6adc8' : '#6c6f85'}>Upload a ZIP containing a .pth file (and optionally an .index file).</p>
          <input type="file" accept=".zip,application/zip" onchange={uploadModel}
            class="theme-file block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:px-3 file:py-2 file:text-xs file:font-semibold" />
        </div>
      </div>
    </div>
  </section>
</main>

<style>
  .theme-field {
    background-color: #eff1f5;
    border-color: #ccd0da;
    color: #4c4f69;
  }

  .catppuccin-dark .theme-field {
    background-color: #313244;
    border-color: #585b70;
    color: #cdd6f4;
  }

  .theme-file::file-selector-button {
    background-color: #ccd0da;
    color: #4c4f69;
  }

  .catppuccin-dark .theme-file::file-selector-button {
    background-color: #45475a;
    color: #cdd6f4;
  }
</style>
