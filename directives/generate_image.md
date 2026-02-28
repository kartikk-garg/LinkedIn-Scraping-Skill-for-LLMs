# Directive: Generate Infographic Images (Nano Banana)

## Goal
Generate infographic images from text prompts using the Gemini Nano Banana image generation model. Supports both single-prompt mode and batch mode from previously generated infographic prompts.

## When to Use
- Run after `generate_content.py` to create images from the infographic prompts.
- Run standalone with `--prompt` to generate a single image from any prompt.

## Inputs
| Parameter                     | Source         | Description                                          |
|-------------------------------|----------------|------------------------------------------------------|
| `.tmp/generated_posts.json`   | Previous step  | Reads `infographic_prompt` from each post            |
| `--prompt`                    | CLI (optional) | Single prompt — skips batch mode                     |
| `--model`                     | CLI (optional) | Model name (default: `gemini-2.0-flash-preview-image-generation`) |
| `GEMINI_API_KEY`              | `.env`         | Same Gemini API key used for text generation         |

## Tool to Call
```bash
# Batch: generate images for all posts in .tmp/generated_posts.json
python execution/generate_image.py

# Single prompt
python execution/generate_image.py --prompt "A clean infographic about Apache Spark streaming..."

# Use a different model
python execution/generate_image.py --model gemini-2.0-flash-preview-image-generation
```

## Outputs
| File                                        | Description                |
|---------------------------------------------|----------------------------|
| `generated_images/<ts>_post_<n>.png`        | One image per post (batch) |
| `generated_images/<ts>_custom.png`          | Single prompt output       |

## Edge Cases & Learnings
- Uses `response_modalities=["IMAGE"]` in the Gemini API config.
- If a post has no `infographic_prompt`, it is skipped.
- No new dependencies needed — uses the same `google-genai` package and `GEMINI_API_KEY`.
- The image model may refuse prompts that violate safety policies — the script logs and skips those.
