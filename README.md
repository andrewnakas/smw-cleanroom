# Super Mario World: clean-room web build

Play: https://andrewnakas.github.io/smw-cleanroom/

The game logic is the community C reimplementation [snesrev/smw](https://github.com/snesrev/smw) (MIT),
compiled to WebAssembly with Emscripten + SDL2. It runs from an asset file instead of a ROM.
In this build that asset file is **regenerated**:

- kept as facts: code-side data tables, level and overworld layouts, Map16, text, music and sound-effect sequence data;
- regenerated: every graphics file (drawn again from each 16x16 sprite unit's silhouette, a 4x4 colour grid and an
  outline colour, plus our own pixel font and hand-drawn sprites), every palette (kept at 3 bits per channel) and
  every instrument sample (resynthesised from length, loop point, a coarse level outline and pitch, then encoded with our own BRR encoder).

No ROM, no retail pixels and no retail samples are in this repository or in the published site.
`python -m games.smw.taint` compares every stored form (LZ2 blocks, planar tiles, decoded pixels, palettes, BRR bytes, decoded PCM)
of the clean build with the retail data and must report 0 failing before anything is published.

Layout: `games/smw/` (spec extractor, generator, drawings, web port patches, taint), `cleanroom/snes/` (LZ2, tile, BRR codecs),
`docs/PLATFORM_SNES.md` (formats, traps, commands), `STATUS.md` (state and decisions).

Controls: arrows move, Z jump (B), X spin jump (A), A/S run (Y/X), C/V L/R, Enter Start, Right Shift Select. Gamepads and touch work.
