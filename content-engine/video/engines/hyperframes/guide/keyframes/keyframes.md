---
name: hyperframes-keyframes
description: >
  Use when a HyperFrames composition needs a punch-in, punch-out, zoom, reframe,
  Ken Burns treatment, camera move, visual match/whip handoff, or other seek-safe
  2D/3D keyframes; also for GSAP, CSS keyframes, Anime.js, WAAPI, FLIP, paths,
  masks, SVG morph/draw, text trails or 3D depth.
  Don't use for broad scene strategy, brand design, media sourcing, captions, or
  general video planning.
---


# HyperFrames Keyframes

Keyframes are a pose contract: visible states, continuous subject identity, seek-safe runtime, verified pixels.

Use `../animation/` for broad scene recipes. Use `keyframe-patterns.md` only when choosing implementation mechanisms, not visual style. In this repo every engine command is wrapped by `content-engine/video/*.py`.

## Creator editing boundary

Keyframes own visual motion, not clip assembly. Cuts and ordering are done with clip `data-start`/`data-duration` (see `../core/`). Keyframes only animate the visible handoff, crop or camera move on wrappers inside those clips.

| Creator request | Truthful mechanism |
| --- | --- |
| Punch-in / punch-out | Keyframe `scale` with `x`/`y` or percentage translation on a non-timed visual/crop wrapper inside the clip. Use a set/short tween for a hard punch and a tween for a smooth move. |
| Smooth multi-state zoom or reframe | Keep one subject wrapper alive and author multiple zoom/reframe states as a pose ladder with per-segment easing. |
| Pan, reframe, or Ken Burns camera move | Animate wrapper translation plus scale. Geometry is authored; this is not face tracking or automatic semantic reframing. |
| Chained camera moves | Chain labeled transform beats on one registered seek-safe timeline. |
| Crop and mask reframe | Interpolate `clip-path` or a mask on an inner visual wrapper to crop/reframe. |
| Directional wipe or iris/reveal cut | Animate a mask/clip boundary across overlapping visual clips. |

## Procedure

1. Identify the animated subject, visible states, final state, and runtime.
2. Choose the smallest mechanism that proves the prompt. Read `keyframe-patterns.md` only if the mechanism is unclear.
3. Author seek-safe keyframes in the declared runtime. Register the runtime instance only after the build completes; building inside `document.fonts.ready` is fine.
4. Verify: render with `python content-engine/video/render.py <composition-dir> <out.mp4>` (lint runs in strict mode), then extract frames at the proof times with `python content-engine/video/frames.py <video.mp4> <out-dir> --at <times>` and look at them.
5. If proof fails, fix the source keyframes and rerun the smallest failing diagnostic before rendering.

## Contract

- Name the moving subject.
- Name the poses needed to prove the intended motion, including the final state.
- Keyframe visible channels, not hidden helper state.
- Preserve object identity when continuity matters.
- Crossfade only when the intended motion is replacement or dissolve.
- Hold readable or semantic states long enough to see.
- Final frame is part of the animation, not cleanup.
- Do not reset to rest unless requested.
- Do not end on black unless requested.
- If editing a starter scene, preserve layout, copy, assets, colors, and final state unless asked to redesign.

## Runtime Rules

GSAP:

- build at page load or inside `document.fonts.ready`, and register only after the build completes
- use `gsap.timeline({ paused: true })`
- register as `window.__timelines[compositionId]`
- registry key must match `data-composition-id`
- do not call `tl.play()` for render-critical motion
- keep repeats finite

CSS keyframes:

- finite duration and iteration count
- deterministic delay
- `animation-fill-mode: both`
- use `data-start` when timing belongs to a clip

Anime.js:

- create synchronously
- `autoplay: false`
- finite duration and loops
- push every instance to `window.__hfAnime`

WAAPI:

- finite `duration`
- `fill: "both"`
- deterministic construction
- verify with extracted frames at proof times

Never use for render-critical motion:

- `Date.now()`
- `performance.now()`
- unseeded `Math.random()`
- hover/scroll triggers
- timers
- a timeline registered before its async build finishes
- unregistered `requestAnimationFrame`
- infinite loops

## GSAP Skeleton

```js
const root = document.querySelector("[data-composition-id]");
const compositionId = root.dataset.compositionId;
const tl = gsap.timeline({ paused: true });

tl.addLabel("state-a", 0);
tl.to(".subject", {
  keyframes: [
    { x: 0, opacity: 1, duration: 0.2 },
    { x: 120, opacity: 1, duration: 0.4, ease: "power2.out" },
    { x: 100, opacity: 1, duration: 0.2, ease: "power2.inOut" },
  ],
  ease: "none",
});

window.__timelines[compositionId] = tl;
```

Use labels for semantic states. Use position parameters instead of chained delays. Use `immediateRender: false` for later `from()`/`fromTo()` tweens touching the same property.

## Keyframe Forms

- Array keyframes: pose ladder with per-step duration/ease.
- Percentage keyframes: exact timing inside one tween.
- Property arrays: compact multi-stop changes.
- `ease: "none"` on the parent when each stop carries its own easing.
- `easeEach` when every segment should share the same feel.

Do not copy numeric distances or timing from examples. Derive them from the actual composition geometry and duration.

For one subject moving between two boxes, prefer one continuous transform tween or FLIP. Split `x/y/scale` into multiple eased keyframes only when the viewer should feel distinct beats; every segment changes velocity and can read as a hitch.

## Channels

Prefer compositor/visual channels: `x/y/z`, `xPercent/yPercent`, `scale`, `rotationX/Y/Z`, `skew`, `transformOrigin`, `svgOrigin`, `opacity`, `autoAlpha`, `clip-path`, masks, CSS vars, SVG path/dash values, camera transforms, shader uniforms.

Avoid layout/lifecycle channels: `top/left/right/bottom`, `width/height`, `margin/padding`, `display`, `visibility`, late DOM creation, helper overlays doing subject motion.

For visibility changes, use `autoAlpha` on the registered seekable GSAP timeline, or a zero-duration `tl.set()` at an explicit boundary. Target only a non-clip element or a wrapper inside the clip; never target `.clip` itself. Never duration-tween raw `visibility`, and never tween `display`.

## Mechanism Choice

Choose the smallest mechanism that proves the prompt:

| Need                                  | Mechanism                                          |
| ------------------------------------- | -------------------------------------------------- |
| Same subject changes box or hierarchy | shared element / FLIP                              |
| Subject travels a visible route       | path travel                                        |
| Stroke grows or traces                | stroke draw                                        |
| Shape becomes another shape           | shape interpolation                                |
| Reveal boundary is visible            | clip, mask, or shader uniform                      |
| Many items move with order            | stagger / indexed delay                            |
| Text itself moves                     | line, word, character, or band subdivision         |
| Surface bends, stretches, or crops    | parent/child counter-transform                     |
| UI has states                         | explicit state machine                             |
| Scene has depth                       | DOM 3D, Three.js, or WebGL camera/object keyframes |

Mechanisms can combine, but each one must clarify the idea. Decoration is not proof.

## Timing

- Anticipation only when it clarifies cause or direction.
- Acceleration leaves rest.
- Peak proof shows the mechanism unmistakably.
- Follow-through sells energy and direction.
- Overshoot only when the subject should feel elastic or tactile.
- Constant-speed path travel usually needs `ease: "none"`.
- Discrete UI states usually need a sharp ease-out.
- Repeated elements need ordered offsets, not identical timing.
- Final lockups need longer holds than transition poses.
- Smoothness means continuous velocity on the same subject.
- Do not overlap tweens that write the same transform property unless the overlap is intentional and verified.
- Avoid animating large `clip-path`/mask changes while the same hero surface is also scaling or traveling; use nested reveals after the main move settles.

## Text

Preserve line boxes, word spacing, readability, and final fit. If text moves internally, move the glyphs or masked bands, not only decorations around the text. Extract and check readable frames.

## SVG

For stroke growth prefer `DrawSVGPlugin`, then `stroke-dasharray`/`stroke-dashoffset`. For shape interpolation prefer `MorphSVGPlugin`; convert primitives to paths when needed and split complex silhouettes into simpler parts.

## 3D

Scale alone is fake depth. Use perspective on a stable parent, `transform-style: preserve-3d`, z travel, rotation, camera/world motion, occlusion, and layer order when objects cross.

Use one or two diagnostic angles that expose the depth relationship. If angled proof shows no depth crossing, improve z/camera/occlusion.

## Canvas / WebGL

Keyframe camera position, camera target, object transform, material opacity, shader uniforms, and postprocess intensity through deterministic state. Render from HyperFrames time. Prove it with extracted frames: marker boxes cannot see internal canvas motion.

## Frame Proof

Render with `python content-engine/video/render.py <composition-dir> <out.mp4>`, then extract frames with `python content-engine/video/frames.py <video.mp4> <out-dir> --at <times>`. Choose `<times>` for the first frame, the proof poses, final-minus-hold and the exact final frame. Open every PNG. Trust painted pixels over logs: if a pose looks wrong, find the element that actually moves, fix its keyframes and re-render.

## Error Handling

| Failure            | Fix                                                                                |
| ------------------ | ---------------------------------------------------------------------------------- |
| endpoint-only      | add middle poses, hold peak proof, re-render and re-extract frames                 |
| identity break     | keep one element alive, use shared source/final boxes, remove substitute crossfade |
| fake 3D            | add z/camera travel, occlusion, angled proof                                       |
| wrong final        | add final hold, extract final-minus-hold and exact final frames                    |
| unseekable runtime | pause autoplay, remove timers, register the instance after the build completes     |
| unreadable text    | preserve line boxes, reduce displacement, add final hold, re-check text frames     |

## Done

Render with `render.py`, extract the proof frames with `frames.py`, and confirm: first frame, proof poses, final-minus-hold, exact final, subject-owned motion, and no debug overlays.

<!-- Adaptado da documentacao de skills do HyperFrames (https://github.com/heygen-com/hyperframes), Copyright 2026 HeyGen, Inc., licenca Apache-2.0. Este arquivo foi modificado em relacao ao original. Ver guide/NOTICE.md. -->
