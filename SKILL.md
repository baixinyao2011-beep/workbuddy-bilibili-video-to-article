---
name: bilibili-video-to-article
description: "Convert Bilibili technical video to WordPress article with embedded screenshots. Use when user wants to transform a Bilibili video into a published English article on BYDToday or any WordPress site, including audio extraction, local Whisper transcription, keyframe capture, and post creation. Triggers: B站视频转图文, Bilibili视频转文章, video to article."
agent_created: true
---

# Bilibili Video to Article (B站视频→图文)

## Purpose

Convert a Bilibili video into a fully published WordPress article with:
- Local Whisper transcription (Chinese audio → text)
- Video keyframe screenshots embedded as article images
- Structured English article with H2/H3, tables, FAQ, sources
- WordPress post creation with SEO metadata

## When to Use

Use this skill when the user:
- Shares a Bilibili video link (b23.tv or bilibili.com/video/BVxxx)
- Asks to "转成图文", "变成文章", or "convert to article"
- Wants the video content published on BYDToday.com or another WordPress site
- Needs a Chinese technical video transcribed and summarized in English

## Prerequisites

Before starting, verify:
1. `ffmpeg` and `ffprobe` are available on PATH
2. Python venv exists at `~/.workbuddy/binaries/python/envs/default/` with `faster-whisper` installed
3. `yt-dlp` is available (in the same venv)
4. WordPress MCP connector is connected for the target site
5. Bilibili cookies file is available (for yt-dlp access to restricted videos)

## Workflow

### Phase 1: Download & Extract Audio

**Get video info:**
```bash
# Resolve b23.tv short link to BV ID
curl -sL -w "%{url_effective}" -o /dev/null "LINK"
```

**Fetch metadata from Bilibili API:**
```
GET https://api.bilibili.com/x/web-interface/view?bvid=BVID
```
Extract: title, duration, cid, subtitle availability, author name.

**Check for existing download first** — search `temp/bilibili_*/` for previously downloaded video files.

**Download audio directly (best quality):**
```bash
yt-dlp --cookies COOKIES_FILE -f "bestaudio[ext=m4a]/bestaudio" -o "OUTPUT_DIR/audio_best.%(ext)s" "BILIBILI_URL"
```

**Alternative: download full video:**
```bash
yt-dlp --cookies COOKIES_FILE -f "best" -o "OUTPUT_DIR/video.%(ext)s" "BILIBILI_URL"
```

**Extract 16kHz mono WAV for Whisper:**
```bash
ffmpeg -y -i INPUT -vn -acodec pcm_s16le -ar 16000 -ac 1 OUTPUT_DIR/audio_16k.wav
```

### Phase 2: Transcribe with faster-whisper

Use the transcribe script at `scripts/transcribe.py`:

```bash
python scripts/transcribe.py AUDIO_WAV OUTPUT_TXT [--model medium|large-v3]
```

**Model selection:**
| Model | Chinese Accuracy | CPU Speed | Use Case |
|-------|-----------------|-----------|----------|
| medium | ~85-90% | ~1.3x realtime | Quick draft, informal content |
| large-v3 | ~92-95% | ~0.8x realtime | Technical content, publication quality |

**Recommended settings:**
- `language="zh"`, `beam_size=5`
- `vad_filter=False` — capture ALL content, don't risk missing segments
- `compute_type="int8"` for CPU
- Output format: `[MM:SS] text` per segment

**Key constraint:** Bilibili videos often lack AI subtitles (CC). Always check `subtitle.list` in the Bilibili API response first. If non-empty, prefer extracting Bilibili's own AI subtitles (download subtitle JSON from the subtitle URL) — they are more accurate for Chinese technical terms than Whisper. Fall back to Whisper only when subtitles are unavailable.

### Phase 3: Extract Keyframes

Use `scripts/extract_frames.py` or direct ffmpeg:

```bash
python scripts/extract_frames.py VIDEO_PATH OUTPUT_DIR [--interval 60|--timestamps "00:10,01:30,02:45,..."]
```

**Frame selection strategy:**
- Prefer timestamps with on-screen diagrams/text (Whisper output can hint when "图上" or "大家看" is said)
- Avoid timestamps where the speaker is just talking with static background
- 10-12 screenshots for a 15-minute technical video
- For talking-head videos: accept that ~40-60% of frames will be speaker-only and supplement with high-quality diagrams from other sources if needed

**Quality check (optional):** Use `scripts/review_frames.py` to run each frame through local VLM (qwen3-vl) for relevance verification.

### Phase 4: Compose Article

Write the article in English following BYDToday conventions:

**Structure:**
1. **Quick Answer** section (wrapped in HTML comment tags: quick-answer)
2. 3-5 H2 sections with technical depth
3. At least 1 comparison table with "Source" column
4. 3-5 FAQ items
5. 3-5 sources cited (original Bilibili video + official BYD/industry sources)
6. 2-4 internal links to related BYDToday articles (verify 200 status)

**Content rules:**
- Title: 50-65 English characters
- Rank Math keyword: single phrase, 4-6 words (e.g., "BYD YunNian suspension guide")
- Meta description: 120-160 characters
- Use real technical terminology (DiSus, not "YunNian" alone — provide bilingual)
- Cite the video author and Bilibili link as primary source
- Never use AI-generated cover images; use video screenshots

### Phase 5: Upload & Publish

**Upload images to WordPress:**
Use `mcp__wordpress-bydtoday__wordpress-upload-local-image` for each screenshot:
```json
{"file_path": "ABSOLUTE_PATH", "filename": "descriptive_name.jpg", "alt_text": "SEO alt text"}
```

**Create WordPress post:**
Use `mcp__wordpress-bydtoday__mcp-adapter-execute-ability` with `ability_name: "ewpa/create-post"`:
```json
{
  "title": "...",
  "slug": "...",
  "content": "HTML with embedded images",
  "status": "draft",
  "categories": [14],
  "tags": ["...", "..."],
  "featured_image_id": ATTACHMENT_ID
}
```

**Set Rank Math SEO:**
Use `ability_name: "ewpa/update-rankmath"`:
```json
{"post_id": POST_ID, "title": "...", "description": "...", "keywords": "...", "robots": ["index","follow"]}
```

**Publish:**
Use `ability_name: "ewpa/update-post"` with `{"post_id": POST_ID, "status": "publish"}`.

**Verify:**
- Frontend HTML loads with cache-buster query parameter (e.g. `?v=TIMESTAMP`)
- og:image, og:title, og:description present
- All images load correctly
- Category and tags displayed correctly

## Common Pitfalls

1. **Subtitle extraction failure**: Most Bilibili videos return empty `subtitle.list`. Fall back to Whisper.
2. **VAD filter data loss**: Disable VAD filtering (`vad_filter=False`) — the default can miss content.
3. **Empty VLM responses**: qwen3-vl:2b may return empty for video frame images. Use `qwen3-vl:8b` for better results, or skip VLM review for simple frames.
4. **Rank Math field names**: Use `ewpa/update-rankmath` with `post_id`, not `ewpa/update-post` with meta fields. Field names: `title`, `description`, `keywords`, `robots`.
5. **Talking-head video limitations**: Technical Bilibili videos are often 80%+ speaker-facing. Accept that ~50% of screenshots will be speaker-only; supplement with official BYD press images if needed.
6. **yt-dlp 412 error**: Use cookies file from a logged-in Bilibili session.

## Output Artifacts

After completion, the working directory contains:
```
temp/bilibili_TOPIC/
├── audio_best.m4a          # Best quality audio download
├── audio_16k.wav           # 16kHz mono for Whisper
├── transcript.txt          # Raw transcription with timestamps
├── transcript_v2.txt       # Higher quality re-run (large-v3)
├── video.mp4               # Full video (if downloaded)
├── article_screenshots/    # Extracted keyframes
├── article_byd_TOPIC.md    # Structured article draft
└── transcribe.py           # Transcription script (copy)
```
