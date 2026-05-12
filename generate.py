"""
Task 2: Run google/gemma-4-E4B-it over the 15 prompts via HuggingFace
transformers, producing SVG / ASCII / Braille outputs each. Raw text +
timing metadata are saved under results/raw/.

Designed to run on an NVIDIA DGX Spark (or any CUDA box). Falls back to
MPS/CPU if CUDA isn't present, but generation will be slow.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

from prompts import FORMATS, PROMPTS

load_dotenv()

MODEL_ID = os.getenv("GEMMA_MODEL_ID", "google/gemma-4-E4B-it")
RESULTS_DIR = Path(__file__).parent / "results" / "raw"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MAX_NEW_TOKENS = 1024


# --- Prompt construction -----------------------------------------------------

SYSTEM_PROMPTS = {
    "svg": (
        "You are a precise SVG illustrator for a mobile RPG game. "
        "When the user names an item, reply with ONLY a single <svg> code block. "
        "The <svg> tag MUST include viewBox=\"0 0 100 100\". "
        "Do not include explanations, markdown fences, or any text outside the <svg>...</svg> element."
    ),
    "ascii": (
        "You are an ASCII artist for a mobile RPG game. "
        "When the user names an item, reply with ONLY ASCII art depicting it. "
        "Hard constraints: AT MOST 15 lines, AT MOST 30 characters per line. "
        "Use only printable ASCII (no Unicode). No prose, no fences, no commentary."
    ),
    "braille": (
        "You are a Unicode Braille (U+2800-U+28FF) artist for a mobile RPG game. "
        "When the user names an item, reply with ONLY Braille-block art depicting it. "
        "Hard constraints: AT MOST 15 lines, AT MOST 30 characters per line. "
        "Use ONLY characters in the Unicode Braille Patterns block plus newlines. "
        "No prose, no fences, no commentary."
    ),
}


def build_messages(system: str, user: str) -> list[dict]:
    """Gemma 4 native chat format with system role."""
    return [
        {"role": "system", "content": [{"type": "text", "text": system}]},
        {"role": "user", "content": [{"type": "text", "text": user}]},
    ]


# --- Model setup -------------------------------------------------------------

def load_model():
    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor

    print(f"[boot] torch={torch.__version__} cuda={torch.cuda.is_available()}", flush=True)
    if torch.cuda.is_available():
        print(f"[boot] gpu={torch.cuda.get_device_name(0)}", flush=True)

    print(f"[boot] loading processor for {MODEL_ID}", flush=True)
    processor = AutoProcessor.from_pretrained(MODEL_ID)

    print(f"[boot] loading model weights (this can take a minute)", flush=True)
    t0 = time.perf_counter()
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        dtype="auto",
        device_map="auto",
    )
    model.eval()
    print(f"[boot] model ready in {time.perf_counter() - t0:.1f}s", flush=True)
    return model, processor


# --- Single-generation with TTFT capture ------------------------------------

def run_once(model, processor, messages: list[dict]) -> dict:
    import torch
    from transformers import TextIteratorStreamer

    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)

    tokenizer = getattr(processor, "tokenizer", processor)
    streamer = TextIteratorStreamer(
        tokenizer,
        skip_prompt=True,
        skip_special_tokens=True,
    )

    gen_kwargs = dict(
        **inputs,
        max_new_tokens=MAX_NEW_TOKENS,
        do_sample=True,
        temperature=0.8,
        top_k=40,
        streamer=streamer,
    )

    start = time.perf_counter()
    first_token_at: list[float | None] = [None]
    chunks: list[str] = []
    err: list[str | None] = [None]

    def _generate():
        try:
            with torch.inference_mode():
                model.generate(**gen_kwargs)
        except Exception as e:
            err[0] = repr(e)

    t = threading.Thread(target=_generate, daemon=True)
    t.start()

    for piece in streamer:
        if first_token_at[0] is None and piece:
            first_token_at[0] = time.perf_counter()
        chunks.append(piece)
    t.join()
    end = time.perf_counter()

    if err[0]:
        return {"text": "".join(chunks), "ttft_s": None, "total_s": None, "error": err[0]}

    return {
        "text": "".join(chunks),
        "ttft_s": (first_token_at[0] - start) if first_token_at[0] else None,
        "total_s": end - start,
    }


# --- Main loop ---------------------------------------------------------------

def main() -> None:
    model, processor = load_model()

    total = len(PROMPTS) * len(FORMATS)
    i = 0
    for entry in PROMPTS:
        for fmt in FORMATS:
            i += 1
            tag = f"{entry['id']}/{fmt}"
            print(f"[{i:02d}/{total}] {tag} -> generating...", flush=True)

            messages = build_messages(SYSTEM_PROMPTS[fmt], entry["target"])
            try:
                result = run_once(model, processor, messages)
            except Exception as e:
                print(f"  ! generation error: {e}", flush=True)
                result = {"text": "", "ttft_s": None, "total_s": None, "error": repr(e)}

            base = RESULTS_DIR / f"{entry['id']}__{fmt}"
            base.with_suffix(".txt").write_text(result["text"], encoding="utf-8")
            base.with_suffix(".json").write_text(
                json.dumps(
                    {
                        "id": entry["id"],
                        "target": entry["target"],
                        "format": fmt,
                        "model_id": MODEL_ID,
                        "ttft_s": result.get("ttft_s"),
                        "total_s": result.get("total_s"),
                        "error": result.get("error"),
                        "char_count": len(result["text"]),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            ttft = result.get("ttft_s")
            total_s = result.get("total_s")
            ttft_str = f"{ttft:.2f}s" if ttft is not None else "n/a"
            total_str = f"{total_s:.2f}s" if total_s is not None else "n/a"
            print(
                f"  ok {len(result['text'])} chars  ttft={ttft_str}  total={total_str}",
                flush=True,
            )

    print("[done] all outputs written to results/raw/", flush=True)


if __name__ == "__main__":
    main()
