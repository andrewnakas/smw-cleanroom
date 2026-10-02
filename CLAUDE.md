# Super Mario World (SNES) — clean-room web build

You are running **unattended overnight**. The user prompts once and checks in the morning. Work autonomously: decide with the defaults below, log every decision in `STATUS.md`, and never stop to ask unless something is truly blocking (then write the question in STATUS.md and continue with anything else).

## Goal
A playable **web build** of Super Mario World, built from the community decomp / port, where **every retail asset is regenerated** (clean room), published as `andrewnakas/smw-cleanroom` + GitHub Pages (`https://andrewnakas.github.io/smw-cleanroom/`), and ready to be listed on decompgames.com. Same result as the N64 builds (e.g. https://andrewnakas.github.io/sm64-cleanroom/, https://andrewnakas.github.io/dk64-cleanroom/).

**This is one of the first non-N64 games in the fleet.** The harness you were scaffolded with (`cleanroom/`, `ports/`, `docs/DECOMP_PLAYBOOK.md`) was written for N64. The rules, the pipeline shape (dirty tree -> spec of coarse facts -> generate -> taint scan -> build -> headless check -> publish) and the generic code (stroke fonts, facepaint briefs, PNG, outline resynthesis, taint scanner, headless browser tools, EmulatorJS site maker) carry over; the N64 formats do not. Write the SNES format code (tile/palette codecs, compression, sample codec) under `cleanroom/` or `games/smw/` and keep a short `docs/PLATFORM_SNES.md` of formats, traps and commands so the next SNES game can reuse it.

## Priorities
1. Game boots and is playable in the browser (keyboard + gamepad + touch), audio working.
2. **Everything readable**: fonts, HUD, menus, text inside pictures (re-typeset / redrawn).
3. **Characters, sprites, pictures correct**: drawn from briefs so each is recognisable, not a blur.
4. Tiles/backgrounds: kept coarse colour grid + outline by default, better where it matters.
5. Publish, then keep improving in loops.

## Pre-answered scope (same as the N64 builds; do not ask)
- Keep as facts: code, level/map layouts and geometry, text, **note sequences** (music and sound-effect command data), data tables, and per image: format + size + a coarse colour grid (no finer than 4x4 cells per **whole picture or sprite**, never per 8x8 tile, so a tile sheet cannot come out as a near copy) + a 2-bit alpha / silhouette outline; per sample: length, rate, loops, coarse outline, median pitch.
- Regenerate everything else. No retail pixels or samples in outputs. **Taint scan must report 0 failing before publishing**: extend `cleanroom.decomp.taint` to this platform's stored forms (raw planar tiles, compressed blocks, decoded pixels, palettes, sample bytes + decoded PCM). Small low-colour tiles collide by chance: log the rule you settle on (window size, what counts as a coincidence) under Decisions for the user to review.
- **No voice cloning** of real performers, no models trained on retail audio. Placeholders = Piper TTS, only if the game has speech.
- Publish when it boots, plays and taint passes: **the user has asked for these to be uploaded**: create the public repo `andrewnakas/smw-cleanroom` and its `gh-pages` (gh CLI is logged in as andrewnakas) and push updates as you improve. Never publish dirty trees, dev builds, ROMs made from retail assets, or retail clips. If the publish command is refused by the permission check, write "BLOCKED: PUBLISH" at the top of STATUS.md with the exact commands and carry on improving.

## This game
- ROM: not on disk yet. `Super Mario World (USA).sfc` / `.smc` / `.zip` (the port wants the US ROM, sha1 6b47bb75d16514b6a476aa0c73a683a2a4c18765; confirm against the port's README). Look in C:/Users/andre/Downloads and D:/ (root) each loop.
- Decomp / port: https://github.com/snesrev/smw (C reimplementation, SDL2, reads the ROM at run time or extracts assets from it; last pushed 2024)
- **Web route (decide in the first hour, log why):** (1) the snesrev C port compiled with Emscripten + SDL2 (emsdk at `D:/n64work/emsdk`), fed a **clean asset file / clean ROM image** instead of the retail one; otherwise (2) clean ROM + WASM SNES emulator in EmulatorJS (`ports/ejs`, core `snes9x`). Either way the thing that ships contains regenerated assets only. Find out exactly which ROM bytes the port reads (it may keep using ROM code/data tables at run time): code, level data, tables and music sequences are kept facts; graphics and samples are not.
- **What is an asset here:** the GFX files (4bpp/3bpp/2bpp planar tiles, LC_LZ2 compressed: Mario, Yoshi, enemies, tilesets, fonts, title/overworld art), palettes, Mode 7 art, and the SPC700 sample bank (BRR instrument samples: resynthesise from the coarse outline + pitch with your own BRR encoder, keep loop points). Kept: code, level and overworld layouts, Map16 (which tile goes where), text, music/sfx sequence data.
- No speech in this game: skip the practice pack and say so in STATUS.md.

## For decompgames.com (do this when you publish)
- The page must work inside an iframe (the site frames `https://andrewnakas.github.io/smw-cleanroom/`): no top-level navigation, audio starts on the first tap/click, canvas scales to the frame. Look at how the published N64 builds do it (`D:/n64work/dk64-cleanroom`, read-only).
- Touch: on-screen pad for phones when no controller is connected (SNES layout: d-pad, the face buttons, Start, Select, shoulder buttons if the system has them). EmulatorJS has its own virtual pad: enable it.
- Write `decompgames.json` in the repo root: one catalogue entry with exactly these keys: `id, title, aliases, year, genre, kind, mode ("embed"), engine, description, overview, source, engineLicense, assetLicense, assetRequirements ("No original game files needed."), controls (list), saveInstructions, limitations, inputs, downloadMB, complete, color, shelf ("cleanroom"), platform ("SNES"), launch, touch, embedUrl, verification, image`. Copy the style of the entries in `C:/Users/andre/OneDrive/Documents/ChatGPT/Decompolation website/src/data/games.json` (read-only; never edit or push that repo). Also save a 16:9 poster drawn by you (title typeset over a scene from the clean build, no retail art) as `poster.png`.

## Where things are
- This folder: your repo. `cleanroom/` shared library (copy; extend freely here), `ports/` (`ports/ejs` = EmulatorJS site maker, `ports/wasm/` = serve + headless tools), `tools/`, `docs/DECOMP_PLAYBOOK.md` (**read first**: rules and traps; skip the N64-only parts), `reference/sm64/` (a finished game module to copy patterns from: generate.py, drawn.py, briefs).
- Work dirs: `D:/n64work/smw/` (pristine, dirty, clean, build). Everything on D: (C: is nearly full, E: is gone). Emscripten: shared `D:/n64work/emsdk`.
- Toolchain: `tools/setup_winbin.sh` (zig cc as gcc, clang as `as`, llvm-objcopy, hexdump, python3, make). Zig: `~/.local/zig-x86_64-windows-0.16.0`, LLVM: `~/.local/clang+llvm-23.1.2-x86_64-pc-windows-msvc`. Python 3.12 with numpy, scipy, librosa, pyworld, piper-tts, faster-whisper, av, websocket-client.
- Browser checks: `python ports/wasm/serve.py <site> 8483` + `python ports/wasm/headless_shot.py <out> --base http://localhost:8483/index.html --secs 5,10 --query "keys=..." --webgl`; hangs: `ports/wasm/cdp_stack.py`. Your dev port is **8483** (CDP 9483); other sessions own the neighbours.

## How to work (token-minimal)
- Scripts print one-screen summaries; background long jobs and wait for the notification; one contact sheet per question; fixes as patch lists / JSON briefs.
- Clone with `-c core.autocrlf=false -c core.eol=lf --depth 1`.
- Keep `STATUS.md` current: what works, decisions, what's next, and a short "for the morning" list (what to look at, what the user must supply).
- Commit often (end commit messages with `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`).

## Machine budget (many sessions share this PC)
- **Disk:** D: has about 25 GB free for everyone and is 99% full. Keep this game under ~2 GB. Run `df -h /d` before big steps; under 10 GB free: stop heavy work, note "blocked on disk" in STATUS.md, do light work only.
- **D: is an external drive that dropped off once (2026-10-01).** If paths under D:/ stop existing, do not recreate anything elsewhere: wait and re-check every 10 minutes. Commit often so work survives.
- **Memory:** the PC keeps running low on RAM and the harness kills background jobs when it does. Use `make -j2`, one headless browser at a time, close servers when done, never leave emulators or browsers running between loops.
- **ROM missing?** Never download a ROM. Do everything that needs none (clone, toolchain, format code, web route, game module), write "BLOCKED: ROM" plus the exact file / revision / sha1 needed at the top of STATUS.md, and re-check C:/Users/andre/Downloads and D:/ every 20 minutes.
