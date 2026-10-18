<script>
  import { Sparkles } from '@lucide/svelte';
  let count = $state(0);
</script>

<main class="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6">
  <div class="bg-slate-900 border border-slate-800 p-8 rounded-2xl shadow-2xl flex flex-col items-center gap-4">
    <div class="flex items-center gap-2 text-indigo-400">
      <Sparkles size={32} />
      <h1 class="text-2xl font-bold tracking-tight">Vite + Svelte + Tailwind</h1>
    </div>
    <p class="text-slate-400 text-sm">Powered by Bun</p>
    
    <button 
      onclick={() => count++}
      class="mt-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-indigo-600/30 cursor-pointer">
      Clicks: {count}
    </button>
  </div>
</main>