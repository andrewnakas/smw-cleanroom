# Super Mario World clean room: status

**State (2026-10-03 night):** boots and plays in the browser with audio; taint 0; published to
`andrewnakas/smw-cleanroom` + GitHub Pages (see "Publish" below for the last result).

## What works
- **Web route 1**: snesrev/smw C port compiled with Emscripten + SDL2 (`games/smw/build_web.sh`), running from a
  **clean `smw_assets.dat`** (no ROM at run time: the port's `kRom` entry is empty and the game runs in its "mine" mode).
- Title, file select, intro message, overworld, Yoshi's Island 1 checked headlessly (keyboard script), audio level log shows music.
- Keyboard, gamepad (SDL game controller), touch pad (SNES layout, shown on touch devices without a controller), saves in IndexedDB.
- All text readable: HUD, message boxes, file select, level names, credits font re-typeset with our pixel font.
- Taint: `python -m games.smw.taint` = 0 failing.
- `decompgames.json`, `poster.png`, `docs/PLATFORM_SNES.md` written.

## Decisions (please review)
1. **Route**: port + Emscripten (not emulator). Why: the port needs no ROM, only `smw_assets.dat`; fast, small (3 MB), saves and input are native.
   ROM bytes the port reads: none at run time. `smw_assets.dat` holds 178 entries; 21 are assets and are regenerated
   (GFX00-33, 16 palette tables, the SPC sample bank, and the optional ROM image which we leave empty); 114 non-empty entries are kept facts
   (levels, Map16, overworld, text/stripe tilemaps, music banks = sequence data, SPC engine code, tables).
2. **Sprite unit = 16x16** for the colour grid: 4x4 cells per 16x16 unit of a sheet (never per 8x8 tile). Bigger characters
   (big Mario, Yoshi) therefore get one grid per 16x16 part. If you want it coarser (one grid per whole character) say so.
3. **Cell colour** = for sprites, the palette index nearest to the cell's mean colour with the outline colour left out; for opaque background tiles, the commonest index. Plus one outline index per unit.
4. **Palettes** kept at 3 bits per channel (512 colours), rebuilt to 15-bit.
5. **Samples**: per BRR sample length, loop block, level per 64 samples in whole dB, descriptor outline, and for loops the cycle count + 32 harmonic levels in whole dB. Resynthesised and encoded with our BRR encoder; directory and sizes unchanged.
6. **Taint rule (SNES)**, `games/smw/taint.py`:
   - byte runs >= 32 B shared with any retail stream fail (16-byte windows; windows with period <= 4, fewer than 6 distinct bytes, or made only of single-bit bytes are ignored);
   - forms compared: LZ2 blocks, planar tiles, decoded pixels, palettes, BRR bytes, decoded PCM; shipped wasm/js/html scanned whole;
   - a tile that is only kept facts (silhouette + one border colour + one inside colour) is "explained" and breaks a run;
     planar streams fail at two whole adjacent identical tiles (32 B at 2bpp, 48 B at 3bpp);
   - pixels: an identical 16x16 unit with >= 4 colours fails; identical unexplained 8x8 tiles with >= 3 colours are counted as coincidences and fail above 2 % (now 3 of ~4200 = 0.07 %).
   - It caught real things: a bold 5x7 font matched 23 retail message glyphs exactly (replaced by our thin face).
7. The "Nintendo Presents" logo and other white-on-transparent text survive through the kept silhouette (2-bit alpha fact). Say if you want those redrawn instead.
8. No speech in this game: no practice pack, no TTS.

## Publish
- `bash games/smw/publish.sh` (taint gate, then pushes `main` and `gh-pages`). Pushed 3 times on 2026-10-03 night, all with taint 0.
- GitHub's "pages build and deployment" run sat in *queued* for 20+ minutes (their runner queue; each new push cancels the queued run),
  so the live URL returned 404 at the last check. Next loop: wait for one run to finish before pushing again, then run the live headless check.

## Art done so far (own drawings, `games/smw/sprites.py`, `drawn.py`)
- Fonts/HUD/message text; score pop-ups (100..8000, 1UP).
- Mario: own cap, face and big head stamped on every pose whose kept silhouette matches (34 of 51 small, 16 of 37 big); the rest get a simpler eye + moustache.
- Items/enemies: mushroom, flower, star, P switch, shells, round walker, bullet.
- Big sprite words MARIO START ! / LUIGI / GAME OVER / TIME UP ! in our own 8x16 block face (checked offline with `look_letters`).
- Animated tiles: ? block (4 frames), eye block, coin (4 frames), ON / OFF word blocks; dinosaur head (3 units).
- Test harness: `?fkeys= ?fdump= ?turbo=` count game frames, so scripted runs are repeatable (see docs/PLATFORM_SNES.md).

## Title logo plan (next)
- `games/smw/look_vram.py` + the page hook `?fvram=<frame>` snapshot the PPU of the clean build and map every on-screen background
  cell to the sheet tile shown there. Finding: the title logo, the frame border and the copyright line are 2bpp **layer 3** tiles
  (sheets 28/29/2A/2B), each cell with its own palette, and the retail logo reuses tiles between letters.
- So a free redraw cannot go through the retail tile arrangement. Plan: rewrite the logo part of the title-screen stripe image
  (our own tile arrangement and palettes over the same screen area, using the logo's own tile slots), then typeset SUPER MARIO WORLD
  in our block face. Same tool will serve the signs (YOSHI, EXIT, BOWSER, GHOST HOUSE) and the "Nintendo" copyright word.
- The title demo (no key presses, `fdump=700,900,...,2900`) is the standard sprite check: Mario on the dinosaur, Koopas, Pokey all appear.

## Next
- More own sprites: Koopa, dinosaur bodies, berries, ON/OFF block text, signs with text (YOSHI, EXIT, BOWSER, GHOST HOUSE), title logo, bonus-game letters.
- Title logo redraw; overworld details.
- Sample quality pass (instruments are recognisable in pitch and rhythm, timbre is synthetic).

## For the morning
- Play: https://andrewnakas.github.io/smw-cleanroom/ (keyboard: arrows, Z jump, X spin, A run, Enter start).
- Look at Decisions 2, 6, 7.
- Nothing needed from you: the ROM was found at `D:/n64work/smw/rom/`.
