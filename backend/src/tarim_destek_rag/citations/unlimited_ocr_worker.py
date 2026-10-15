"""Isolated opt-in worker for Baidu Unlimited-OCR. NEVER an evidence signer.

Launched only by unlimited_ocr_review with a locally audited model directory
and an explicit operator acknowledgment. Does not download any model itself.
This Python process runs Hugging Face model custom code; operating-system-level
sandboxing and code/license audits remain the deployer's responsibility.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    # Force offline even if the parent environment was misconfigured.
    for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE"):
        os.environ[name] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

    if (not args.model_dir.is_absolute() or not args.model_dir.is_dir()
            or not (args.model_dir / "config.json").is_file()
            or not args.image.is_file() or args.image.stat().st_size > 25_000_000
            or args.result.exists()):
        return 2
    args.output_dir.mkdir(parents=True, exist_ok=False)
    try:
        import torch
        from transformers import AutoTokenizer, AutoModel

        if not torch.cuda.is_available():
            return 3  # No official, validated CPU recipe claimed.
        model_dir = str(args.model_dir)
        tokenizer = AutoTokenizer.from_pretrained(
            model_dir, trust_remote_code=True, local_files_only=True,
        )
        model = AutoModel.from_pretrained(
            model_dir,
            trust_remote_code=True,
            local_files_only=True,
            use_safetensors=True,
            torch_dtype=torch.bfloat16,
        ).eval().cuda()
        with torch.inference_mode():
            response = model.infer(
                tokenizer,
                prompt="<image>document parsing.",
                image_file=str(args.image),
                output_path=str(args.output_dir),
                base_size=1024,
                image_size=640,
                crop_mode=True,
                max_length=8192,
                no_repeat_ngram_size=35,
                ngram_window=128,
                save_results=True,
            )
        raw_text = response if isinstance(response, str) else ""
        if isinstance(response, dict):
            for key in ("text", "content", "markdown"):
                if isinstance(response.get(key), str):
                    raw_text = response[key]
                    break
        # Official examples save_results=True; accept only bounded plain text
        # produced within this invocation's private directory.
        if not raw_text.strip():
            for ext in ("*.mmd", "*.md", "*.txt"):
                for path in sorted(args.output_dir.rglob(ext)):
                    if path.is_file() and not path.is_symlink() and path.stat().st_size <= 250_000:
                        data = path.read_text(encoding="utf-8", errors="replace").strip()
                        if data:
                            raw_text = data
                            break
                if raw_text.strip():
                    break
        if not isinstance(raw_text, str) or not raw_text.strip():
            return 4
        raw_text = raw_text[:200_000]
        args.result.write_text(
            json.dumps({
                "schema_version": 1,
                "engine": "baidu/Unlimited-OCR",
                "status": "OCR_UNREVIEWED",
                "text": raw_text,
            }, ensure_ascii=False),
            encoding="utf-8",
        )
        return 0
    except Exception:
        # Never echo raw model exceptions or filesystem paths to the GUI.
        return 5


if __name__ == "__main__":
    sys.exit(main())
