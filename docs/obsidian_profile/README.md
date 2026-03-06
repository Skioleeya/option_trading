# Obsidian Profile Snapshot

Source vault: `E:\Obsidian_us.markrt`  
Snapshot date: `2026-03-06`

This folder stores a reusable Obsidian configuration profile for `Option_v3`.

## Included
- `.obsidian/app.json`
- `.obsidian/appearance.json`
- `.obsidian/community-plugins.json`
- `.obsidian/core-plugins.json`
- `.obsidian/workspace.json`
- `.obsidian/plugins/obsidian-git/data.json`
- `.obsidian/plugins/obsidian-git/manifest.json`
- `.obsidian/plugins/obsidian-custom-attachment-location/data.json`
- `.obsidian/plugins/obsidian-custom-attachment-location/manifest.json`

## Excluded
- Plugin runtime bundles (`main.js`, `styles.css`, shell helpers)
- Vault content files outside `.obsidian`

## How To Apply In Option_v3 Vault
1. Ensure your vault root is `e:\US.market\Option_v3`.
2. Copy `docs/obsidian_profile/.obsidian/*` into vault root `.obsidian/`.
3. In Obsidian, install required community plugins if not already installed:
   - `obsidian-git`
   - `obsidian-custom-attachment-location`

Notes:
- `workspace.json` contains personal panel/layout state.
- `obsidian-custom-attachment-location` is configured to place attachments in:
  `./assets/${noteFileName}`.
