# Keyframe Mechanism Reference

Use this after `SKILL.md` when choosing a concrete implementation mechanism. It is a parts shelf, not a style guide. Start with one primary mechanism; add supporting motion only when it clarifies the idea.

## Runtime Skeletons

GSAP:

```js
const root = document.querySelector("[data-composition-id]");
const id = root.dataset.compositionId;
const tl = gsap.timeline({ paused: true });
tl.to("<selector>", {
  keyframes: [
    /* derive poses from the scene */
  ],
  ease: "none",
});
window.__timelines = window.__timelines || {};
window.__timelines[id] = tl;
```

CSS:

```css
.<subject > {
  animation: <name> <duration> <ease> both;
  animation-iteration-count: 1;
}
@keyframes <name> {
  0% {
    transform: <pose-a>;
    opacity: <a>;
  }
  100% {
    transform: <pose-b>;
    opacity: <b>;
  }
}
```

Anime.js:

```js
const animation = anime.createTimeline({ autoplay: false });
animation.add("<selector>", {
  /* derived channels */
});
window.__hfAnime = window.__hfAnime || [];
window.__hfAnime.push(animation);
```

Three/WebGL:

```js
const state = { progress: 0 };
tl.to(state, {
  progress: 1,
  duration: <duration>,
  onUpdate: () => {
    // derive camera/object/material values from state.progress
    renderer.render(scene, camera);
  },
});
```

## Mechanisms

| Mechanism           | Solves                                         | Keyframe                                                           | Runtime                                    | Verify                                         |
| ------------------- | ---------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------ | ---------------------------------------------- |
| Path travel         | Subject must visibly follow a route            | path progress, tangent rotation, follower offset, trail opacity    | GSAP MotionPath or sampled x/y/z           | strip shot at bends; final extracted frame            |
| Stroke draw         | A line, ring, or outline appears over time     | dash/draw range, stroke opacity, endpoint state                    | DrawSVG or SVG dash fallback               | partial mid extracted frame; complete final           |
| Shape interpolation | One silhouette becomes another                 | source path, middle path, target path, fill/stroke                 | MorphSVG or path tween                     | first/mid/final extracted frames                      |
| Shared element      | Same subject changes box or hierarchy          | source box, target box, x/y, scale, radius, context opacity        | GSAP Flip or manual FLIP                   | one identity moves; no substitute crossfade    |
| Clip/mask reveal    | Animated boundary exposes content              | clip path, mask position/size, edge softness, inner counter-motion | CSS, SVG, GSAP, or shader                  | extracted frame edge frames and final unclipped state |
| Ordered repetition  | Many items enter, leave, or transform in order | indexed delay, x/y, scale, opacity, final alignment                | GSAP stagger, Anime stagger, CSS vars      | check first/middle/last item timing            |
| Text subdivision    | Text motion needs readable internal timing     | line/word/char/band wrappers, y/x, opacity, final fit              | SplitText, authored spans, Anime splitText | strip shot plus final readability extracted frame     |
| Surface transform   | Image/card stretches, crops, or changes shape  | parent scale/skew/clip, child counter-scale, transform origin      | GSAP/CSS keyframes                         | no accidental warped final                     |
| UI state machine    | Interface passes through semantic states       | closed, active, loading, success/error, final                      | GSAP/CSS/Anime                             | extracted frames hit states in order                  |
| DOM depth           | HTML elements need 3D separation               | perspective, z, rotationX/Y, opacity, crossing layer order         | CSS 3D + GSAP/CSS/Anime                    | angled `--shot`; overlap extracted frame              |
| Camera/object 3D    | Canvas/WebGL scene moves in depth              | camera, target, object transform, material opacity                 | Three.js/WebGL + GSAP proxy                | frame extraction; extracted frames at proof poses            |
| Shader uniform      | Pixel effect is driven by scalar progress      | progress, edge width, noise, color mix, opacity                    | ShaderMaterial/WebGL uniforms              | frame extraction; extracted frame 0/edge/mid/final           |
| Instanced system    | Many 3D objects move as one system             | instance transforms, scale, color/opacity, camera                  | Three InstancedMesh                        | extracted frames, because DOM boxes miss internals    |
| Imported model      | Model animation must scrub deterministically   | `AnimationMixer.setTime`, camera, material, lights                 | Three AnimationMixer                       | drive from HyperFrames time; frame extraction         |

## Runtimes available in this repo

Only GSAP (with its plugins under `_motor/`) and CSS animations are vendored locally. Anime.js and Three.js rows above are background only: their libraries are not installed and must not be fetched from the internet.

<!-- Adaptado da documentacao de skills do HyperFrames (https://github.com/heygen-com/hyperframes), Copyright 2026 HeyGen, Inc., licenca Apache-2.0. Este arquivo foi modificado em relacao ao original. Ver guia/NOTICE.md. -->
