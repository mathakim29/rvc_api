import './index.css'
import { mount } from 'svelte'
import App from './src/app/App.svelte'

const app = mount(App, {
  target: document.getElementById('app'),
})

export default app