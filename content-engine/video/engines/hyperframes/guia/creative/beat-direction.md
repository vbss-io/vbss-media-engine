# Beat Direction

How to plan and direct individual scenes (beats) in a multi-scene composition. Read before writing any multi-scene video.

## Contents

- Per-beat direction
- Concept
- Mood direction
- Animation choreography
- Transition
- Depth layers
- SFX cues
- Rhythm planning
- Velocity-matched transitions

---

## Per-Beat Direction

Each beat is a WORLD, not a layout. Before writing CSS specs and GSAP instructions, describe what the viewer EXPERIENCES. The difference between a great storyboard and a mediocre one:

**Mediocre:** "Dark navy background. '$1.9T' in white, 280px. Logo top-left. Wave image bottom-right."
**Great:** "Camera is already mid-flight over a vast dark canvas. The gradient wave sweeps across the frame like aurora borealis - alive, shifting. '$1.9T' SLAMS into existence with such force the wave ripples in response. This isn't a slide - it's a moment."

The first describes pixels. The second describes an experience. Write the second, then figure out the pixels.

Each beat should have:

### Concept

The big idea for this beat in 2-3 sentences. What visual WORLD are we in? What metaphor drives it? What should the viewer FEEL? This is the most important part - everything else flows from it.

### Mood direction

Cultural and design references, not hex codes:

- "Geometric, rhythmic, precise. Think Josef Albers or Bauhaus color studies."
- "Warm workspace. Nice notebook energy, not technical blueprint."
- "Cinematic title sequence. The kind of opening where you lean forward."

### Animation choreography

Specific motion verbs per element - not "it animates in" but HOW. Verbs come from the beat's concept and content, not from an energy bucket. A wellness brand's "slow" beat might still have something that DROPS if the content is about letting go. A stats beat might FLOAT if the brand's identity is weightless.

The vocabulary of motion verbs (organized by physical character, not by energy level):

**Impact / weight:** SLAMS, CRASHES, PUNCHES, STAMPS, SHATTERS, DROPS (with force)
**Directional / deliberate:** SLIDES, PUSHES, PULLS, WIPES, CUTS
**Reveals / builds:** DRAWS, FILLS, GROWS, EXPANDS, ASSEMBLES, COUNTS UP
**Organic / ambient:** FLOATS, DRIFTS, BREATHES, PULSES, ORBITS, MORPHS
**Mechanical / precise:** TYPES ON, CLICKS, LOCKS IN, SNAPS, STEPS

Every element gets a verb. If you can't name the verb, the element is not yet designed. The verb should follow from the beat's concept - not from a lookup of what "high energy" or "low energy" beats use.

For text elements specifically, name the effect (e.g. typewriter, center build, soft blur-in) and write its timing explicitly on the GSAP timeline.

### Transition

How this beat hands off to the next. Specify the type and parameters.

In this repo transitions are CSS/GSAP only (no shader transitions: they need engine blocks that are not installed). Choose a hard cut for rapid-fire lists and percussive edits; choose a CSS transition when the scene should feel like one continuous move.

**CSS transitions** - pick based on the energy and feel (write them with GSAP on the composition timeline):

| Category           | Patterns                                                                 | Motion character                                                           |
| ------------------ | ------------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| **Push / slide**   | Push slide, vertical push, elastic push, squeeze                         | Content moves through the frame as if on a continuous surface              |
| **Scale / zoom**   | Zoom through, zoom out                                                   | Perspective shifts - moving toward or away from content                    |
| **Radial / clip**  | Circle iris, diamond iris, diagonal split                                | Geometric reveal - content emerges or is covered by a shape                |
| **3D**             | 3D card flip                                                             | Physical - content flips like a tangible object                            |
| **Dissolve**       | Crossfade, blur crossfade, focus pull, color dip                         | Overlap and blend - both scenes exist simultaneously during the transition |
| **Cover / blinds** | Staggered color blocks, horizontal blinds (6/12 strips), vertical blinds | Structural - content is sliced, layered, or covered                        |
| **Light**          | Light leak overlays, overexposure burn, film burn                        | Organic film - light bleeds across the frame                               |
| **Distortion**     | Glitch (CSS RGB jitter), chromatic aberration, ripple, VHS tape          | Instability - the image itself appears to malfunction                      |
| **Blur**           | Blur through, directional blur                                           | Soft defocus - content blurs in or out                                     |
| **Mechanical**     | Shutter (two-half), clock wipe (9-point wedge)                           | Precision - transitions with visible mechanical logic                      |
| **Grid**           | Grid dissolve (12/120 cells)                                             | Fragmentation - the frame breaks into pieces                               |
| **Destruction**    | Page burn (SVG clip-path + canvas rim)                                   | Dramatic decay - the previous scene is destroyed                           |
| **Other**          | Gravity drop, morph circle                                               | Physical or shape-based motion that doesn't fit other categories           |

Common quick-picks:

- **Velocity-matched upward**: exit `y:-150, blur:30px, 0.33s power2.in` → entry `y:150→0, blur:30px→0, 1.0s power2.out`
- **Whip pan**: exit `x:-400, blur:24px, 0.3s power3.in` → entry `x:400→0, blur:24px→0, 0.3s power3.out`
- **Blur through**: exit `blur:20px, 0.3s` → entry `blur:20px→0, 0.25s power3.out`
- **Zoom through**: exit `scale:1→1.2, blur:20px, 0.2s power3.in` → entry `scale:0.75→1, blur:20px→0, 0.5s expo.out`
- **Hard cut / smash cut**: instant, for rapid-fire sequences

Timing presets: snappy (0.2s), smooth (0.4s), gentle (0.6s), dramatic (0.5s), instant (0.15s), luxe (0.7s).

If the storyboard calls for an effect that is not listed, build it with clip-path, transforms and filters on the GSAP timeline. Never fetch shader or effect code from the internet: everything the composition uses must be a local file.

### Depth layers

What's in foreground, midground, and background. Every beat should have at least 2 layers:

- "BG: dark navy fill + subtle radial glow. MG: stat cards with drop shadow. FG: brand logo bottom-right."

### SFX cues

What sounds at what moment:

- "On the capture pulse - a soft, warm analog shutter click."
- "Left side carries a faint low drone. On fold: drone cuts. Silence. Then a single clean chime."

---

## Rhythm Planning

Before writing HTML, declare your scene rhythm: which scenes are quick hits, which are holds, where does energy peak. Name the pattern - fast-fast-SLOW-fast-hold - before implementing.

**Derive the rhythm from the storyboard and the brand, not from a lookup.** A 15-second social ad for an architectural firm and a 15-second social ad for a gaming brand have different rhythms - both are 15 seconds, but one is slow-reveal-hold-CTA and the other is rapid-fire-SLAM-hook. Video type sets constraints (duration, approximate beat count); the brand and content determine whether those beats are slow or fast, sparse or dense, dramatic or controlled.

Questions that drive rhythm decisions:

- What emotional journey should the viewer take? Where is the peak moment?
- Where does the narration land its heaviest emphasis? That's usually where energy should peak.
- What does the brand's own visual pacing suggest - unhurried or urgent?
- How many beats can the duration actually support without feeling rushed or padded?

A social ad that tries to hook in 2s, showcase 3 features, and end with a CTA in 15s will feel like noise. Sometimes "hook-hold-CTA" with one strong feature is the right rhythm for 15 seconds. Name the rhythm you've planned before implementing.

---

## Velocity-Matched Transitions

Exit the outgoing beat with an accelerating ease (power2.in or power3.in) plus a blur ramp. Enter the incoming beat with a decelerating ease (power2.out or power3.out) plus blur clear. The fastest point of both easing curves meets at the cut - the viewer perceives continuous camera motion, not two discrete animations. Match exit velocity to entry velocity within ~5% tolerance.

<!-- Adaptado da documentacao de skills do HyperFrames (https://github.com/heygen-com/hyperframes), Copyright 2026 HeyGen, Inc., licenca Apache-2.0. Este arquivo foi modificado em relacao ao original. Ver guia/NOTICE.md. -->
