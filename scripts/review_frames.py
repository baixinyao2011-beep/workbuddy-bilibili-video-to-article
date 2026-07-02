#!/usr/bin/env python3
"""
Review extracted frames using local VLM (Ollama qwen3-vl) for article relevance.
Each frame is evaluated against its intended section context.
Output: JSON report with KEEP/REPLACE/REMOVE verdicts.

Usage: python review_frames.py FRAMES_DIR MAPPING_JSON [--model qwen3-vl:2b]
"""
import argparse, json, os, sys
from pathlib import Path

PROMPT_TEMPLATE = """You are reviewing screenshots from a Bilibili technical video about {topic} for use in an English technical article.

For this image, evaluate:
1. What does the image actually show? (title card, person speaking, diagram, on-screen text, car footage?)
2. Is the visual content RELEVANT to its intended section: "{expected}"?
3. Is the image quality acceptable for a web article? (blurry? too dark? text readable?)
4. Should this image be KEPT, REPLACED, or REMOVED from the article?

Answer ONLY in this JSON format, no other text:
{{"shows":"...","relevant":"yes/no/partially","quality":"good/acceptable/poor","verdict":"KEEP/REPLACE/REMOVE","reason":"..."}}"""

def main():
    parser = argparse.ArgumentParser(description="Review frames with local VLM")
    parser.add_argument("frames_dir", help="Directory containing extracted frames")
    parser.add_argument("mapping", help="JSON file mapping filename to expected section context")
    parser.add_argument("--model", default="qwen3-vl:2b")
    parser.add_argument("--topic", default="BYD electric vehicles")
    args = parser.parse_args()

    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        os.environ.pop(k, None)

    try:
        import ollama
    except ImportError:
        print("Error: pip install ollama", file=sys.stderr)
        sys.exit(1)

    with open(args.mapping, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    results = {}
    total = len(mapping)
    for i, (filename, expected) in enumerate(mapping.items()):
        filepath = os.path.join(args.frames_dir, filename)
        if not os.path.exists(filepath):
            results[filename] = {"error": "file not found"}
            continue

        prompt = PROMPT_TEMPLATE.format(topic=args.topic, expected=expected)
        try:
            resp = ollama.chat(
                model=args.model,
                messages=[{"role": "user", "content": prompt, "images": [filepath]}],
                options={"temperature": 0.1, "num_predict": 512},
            )
            text = resp["message"]["content"].strip()
            if "{" in text and "}" in text:
                s, e = text.index("{"), text.rindex("}") + 1
                results[filename] = json.loads(text[s:e])
            else:
                results[filename] = {"verdict": "UNKNOWN", "raw": text[:200]}
        except Exception as ex:
            results[filename] = {"verdict": "UNKNOWN", "error": str(ex)[:200]}

        print(f"  [{i+1}/{total}] {filename}: {results[filename].get('verdict', '?')}", flush=True)

    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
