# Findings — Gemma 4 E4B Widget Art Eval

**Model:** `google/gemma-4-E4B-it` (8B raw / ~4.5B effective, MatFormer)
**Test:** 15 RPG prompts × 3 formats (SVG / ASCII / Braille) = 45 generations on DGX Spark.

## TL;DR

**SVG is the only viable format** for shipping Gemma 4 E4B as a widget-art generator. ASCII underuses its canvas and produces emoji-tier sketches; Braille fails categorically — the model misunderstands the task.

## Per-format read

### SVG — passable

Model genuinely composes primitives (`<rect>`, `<polygon>`, `<circle>`) toward the target. Recognizable-as-Thing at small sizes. Adheres to the `viewBox="0 0 100 100"` constraint.

Sample (`01_rusty_sword`):
```svg
<svg viewBox="0 0 100 100"><rect x="20" y="20" width="60" height="5" fill="#808080"/>...<polygon points="10,45 20,55 30,45" fill="#A9A9A9"/>...</svg>
```

### ASCII — drastically undersized

Allowed 15 lines × 30 chars; model produced 5–9 line, ~15 char doodles. Upper bound is artificial — the model defaults to tiny emoji-tier art regardless of canvas budget.

Sample (`04_goblin_skull`):
```
  .--.
 /    \
|  O  |
 \ -- /
  `--'
```

### Braille — wrong task entirely

The model treats Braille as an alphabet encoding and **spells the prompt word** in Braille letters rather than drawing pixel art with the 2×4 dot grids.

Sample (`01_rusty_sword`) — decodes to "rase" / "rust":
```
⠗⠁⠎⠑
⠗⠁⠎⠑
⠗⠑⠗⠎
```

Fixable with one-shot examples, but as-prompted this is a 0/15 result, not "low quality."

## What this means for the product

- Ship SVG as the widget-art format for the mobile RPG.
- Don't ship ASCII or Braille without prompt-engineering work that wasn't tested here.
- Re-evaluate if you upgrade to a larger Gemma model (E12B+) or move off-edge.
