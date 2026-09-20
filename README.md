# TODO: Mod Name

TODO: one or two sentence description of what this mod does.

## Structure
- `src/` — mod source (`manifest.sii`, `description.txt`, and mod content)
- `output/local/` — packed `.scs` for local installation (gitignored)
- `output/workshop/` — staged folder for the SCS Workshop Uploader tool (gitignored)
- `pack.config.json` — optional `packageName` override; version always comes from `src/manifest.sii`
- `logo.png` — branding asset, input to a cover-image generation step

## Building
Follows the `ets2-mod-developer` profile convention — use the `pack-mod` skill against this repo:
- **Local**: produces a versioned `.scs` in `output/local/`.
- **Workshop**: stages a folder in `output/workshop/` for the SCS Workshop Uploader tool.

## Requirements
TODO: list any required base mods/DLC and load order.

## Changelog
See `src/description.txt`.
