import type { PanelSection } from '../types.js'

export const SETUP_REQUIRED_TITLE = 'Welcome to MyAIOne Agent'

export const buildSetupRequiredSections = (): PanelSection[] => [
  {
    text: "You're almost ready. MyAIOne needs one model provider — bring your own API key, or sign in to a provider that hosts its own — before the first session can start."
  },
  {
    text: 'Quickest path: run /model, pick a provider, drop in a key. You can add or swap providers any time later.'
  },
  {
    rows: [
      ['/model', 'pick a provider + model (recommended)'],
      ['/setup', 'full guided wizard — providers, tools, integrations'],
      ['Ctrl+C', 'exit; you can re-run `myai` any time']
    ],
    title: 'Actions'
  }
]
