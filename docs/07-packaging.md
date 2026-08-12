# 07 — Packaging and distribution

## The decision: standalone expansion pack

We ship a **single self-contained Workshop item**: our maps, their terrain, and the
pack's own shared assets. No dependencies on other Workshop items — subscribing to the
pack is all a player needs.

### How maps resolve their scripts

Each map's `.lua` uses the standard boilerplate:

```lua
RequireFix = require("RequireFix")
RequireFix.Initialize("<our workshop ID>")   -- filled in after the item is created
```

`RequireFix.Initialize(id)` resolves the user's Steam workshop directory and appends
`<workshop>/<id>/?.lua` and `?.dll` to `package.path` / `package.cpath`. Every map can
therefore `require` the shared Lua modules that ship at the pack's own item root.

`RequireFix` also handles GOG installs by falling back to `mods/` and `packaged_mods/`.

### What this means in practice

- The pack contains our maps, their terrain, and every shared asset they need — Lua
  modules, ODFs and any helper DLLs — at the item root. Nothing is resolved from
  another Workshop item.
- **No external dependencies:** a player who subscribes to this pack alone gets
  working maps.
- Keep the shared-asset surface minimal — use the boilerplate as-is and add nothing
  the maps do not need.

---

## Pack layout

BZ98R workshop items are **flat** — no subdirectories for map content. All files sit at
the item root.

```
build/Expansion-Pack/
├── <map1>.trn  <map1>.hg2  <map1>.mat  <map1>.lgt  <map1>.vxt
├── <map1>.bzn  <map1>_S.bzn  <map1>_SW.bzn  [<map1>_ST.bzn]
├── <map1>.ini  <map1>.des  <map1>.odf  <map1>.lua
├── <map1>.BMP             per-map thumbnail — see note below
├── ... × 10 maps
├── <shared Lua modules / ODFs / DLLs the maps require>
└── preview.png            workshop item thumbnail
```

#### Per-map thumbnail is `.BMP`, not `.png` **[CORRECTED 2026-08-11]**

This listing previously said each map ships `<map>.png` *and* `<map>.bmp`. Measured
against the pinned snapshot of the reference corpus of community Workshop maps, that
is wrong (AGENTS.md rule 1 — reality wins):

- The corpus ships **24** `*.BMP` map thumbnails across its 36 maps — so the thumbnail
  is optional, not required. All are RGB; 512×512 is the most common size (8 of 24),
  with the rest ranging from 108×89 to 1024×1024.
- The corpus ships **no** `<mapname>.png`. Its 323 `.png` files are textures and UI
  art, not map thumbnails.
- The extension is uppercase `.BMP` on every one.

**[AMENDED 2026-08-11, same day]** The "no `<mapname>.png`" claim above was itself
a measurement error: 3 of the corpus's 30 maps (`uexmap10` among them) *do* ship a
`<map>.png` at 1024×1024, and in-game testing showed a blank minimap with only the
`.BMP` present. The packer therefore writes both: `<map>.BMP` at 512×512 RGB (the
shell/lobby thumbnail) and `<map>.png` at 1024×1024 (the uexmap10 precedent for
the in-game map image). The top-level `preview.png` is a different thing — the
Steam item thumbnail.

### Terrain naming — `xx<nn><slug>` **[DECIDED]**

Terrain names are **globally flat across all loaded mods**. A collision with the
base game or any other subscribed item breaks both maps.

**The expansion pack uses the `xx` prefix**, in the form:

```
xx<nn><slug>      8 characters total
                  nn   = 01..99, the map number
                  slug = 4-char mnemonic

xx01ridg   xx02cany   xx03basn   xx04mesa   xx05delt   ...
```

**Verified clear (2026-08-10)** against **211** terrain names:
- 109 loose `.trn` files — base game `Edit/trn/`, all 10 subscribed workshop items
  (including the corpus's 36), `mods/`, `packaged_mods/`
- 102 more extracted from the packed archives `bzone.zfs` (78) and `tro_cam.zfs` (24)

**Zero begin with `x`.** Fifty distinct two-character prefixes are in use across the
corpus; `x*` is entirely unclaimed.

Length also matches convention: **93 of 109** loose terrain names are exactly 8
characters, and `xx` + `nn` + 4-char slug is exactly 8.

**[CONFIRMED LOAD-BEARING 2026-08-11]** The 8-character length is not a
convention but an engine limit: a 9-character stem made the engine
truncate its entry-script lookup (dropping the final character), and the map
loaded with **no script at all** — no SBP layer, no chat markers, nothing, with
no error dialog. The packer now refuses stems longer than 8.

**Residual risk:** this proves `xx` is clear against *installed* content, not against
every Workshop item in existence. It cannot be proven exhaustively. The 211-name sample
plus the total absence of any `x` prefix makes collision very unlikely, and `nn` gives
99 slots before the scheme needs revisiting.

Add a collision check to Tier 1 validation anyway: assert no generated terrain name
matches any name found in the installed game or workshop directories at build time.

---

## Publishing

The game ships `Edit/UploaderApp.exe` for Workshop uploads. Per `Edit/ReadMe.txt`:

> run the UploaderApp.exe and follow it's instructions. Use the create button to create
> a new item. Select an item from the list and use the Update button to update an
> existing item

Notes:
- It is a Windows GUI app; on this Linux machine it needs Proton.
- **Publishing is a human step.** The agent assembles and validates the pack; a human
  reviews and uploads. Do not automate the upload — it is public, outward-facing, and
  hard to walk back.
- `mapType = "multiplayer"` in each map's `.ini` is what puts maps in the multiplayer
  browser.

### Workshop description should state

1. Maps are **AI-generated** — say so plainly
2. Map list with sizes, player counts and supported modes
3. Where to report problems

---

## Local testing install

**Never test by copying into another Workshop item's directory.** Install to a separate
location so subscribed content stays pristine and Steam does not overwrite or revalidate
your work:

```
~/.steam/steam/steamapps/common/Battlezone 98 Redux/mods/<test-id>/
```

`RequireFix`'s GOG path already searches `mods/` and `packaged_mods/`, and `modEnabled.dat`
controls which mod is active. Snapshot `modEnabled.dat` before changing it and restore
it afterwards.
