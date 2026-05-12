# gemma4-visual-eval

Throwaway eval of `google/gemma-4-E4B-it` for mobile-RPG widget art (SVG, ASCII, Braille).

## Run on the DGX Spark

```bash
git clone <this-repo>
cd gemma4-visual-eval

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# If the HF model is gated, log in once:
# huggingface-cli login

python generate.py        # ~45 generations, prints progress per item
python build_site.py      # produces index.html
```

Then commit and push:

```bash
git add results/ index.html
git commit -m "results: gemma-4-E4B-it run"
git push
```

## View from your laptop

After pulling the pushed commit, open `index.html` directly — everything is inlined (SVG via sandboxed iframes, ASCII/Braille in `<pre>` blocks). No build step, no server.

For viewing without cloning: enable GitHub Pages on the repo and the URL will be `https://<user>.github.io/<repo>/`.

## Layout

```
prompts.py        15 hardcoded RPG visual prompts
generate.py       Task 2: HF transformers generation loop with TTFT capture
build_site.py     Static HTML grid of all 45 outputs
results/raw/      Per-output .txt (model text) + .json (timing/metadata)
```

Tasks 3 (syntax validation), 4 (rendering + VLM judge), 5 (CSV report) are not implemented yet.
