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

### Phase 3: Image Sourcing (Proactive, NOT Reactive)

**Critical mindset shift**: Don't ask "what images does the video have?" Ask "what images does each article section need?" — then source accordingly. Video frames are ONE possible source, not the default.

#### Step 1: Build Image Requirements Map

After reviewing the transcript but BEFORE writing the article, map each planned H2/H3 section to its ideal image type:

| Image Type Needed | Best Source | Fallback |
|------------------|-------------|----------|
| Vehicle exterior / Hero shots | Wikimedia Commons (CC-licensed) | BYD Global press image |
| Technical diagrams / schematics | Video frames with on-screen charts | BYD official tech briefs |
| Action demonstrations | Video frames at key moments | BYD official video |
| Architecture comparisons | Self-made table/SVG | — (tables don't need images) |
| Engineering close-ups | BYD press materials | Wikimedia (detailed shots) |

#### Step 2: Identify Gaps

Mark sections where the video CANNOT provide quality images:
- Vehicle exterior shots (video is mostly interior/diagrams/speaker)
- High-resolution system overviews (video resolution limited to 1080p)
- Specific model variants not shown in the video

#### Step 3: Source Externally for Gaps

Search priority:
1. **P0: BYD Global press releases / product pages** — highest authority, no copyright risk
2. **P1: Wikimedia Commons** — search model name + filter CC license (e.g., "Yangwang U9 Wikimedia CC")
3. **P2: Video frames with diagrams/demos** — only when they actually show technical content
4. **P3: Industry media** — cite source explicitly

**Wikimedia image download:**
```bash
# Search and download CC-licensed vehicle photos
curl -L -o OUTPUT_PATH "WIKIMEDIA_FILE_URL"
```
Always record: photographer/uploader name + CC license type + Wikimedia file page URL.

#### Step 4: Extract Video Frames (only for P2)

Use `scripts/extract_frames.py`:
```bash
python scripts/extract_frames.py VIDEO_PATH OUTPUT_DIR [--timestamps "00:10,01:30,..."]
```

**Frame quality gate — REJECT any frame that is:**
- ❌ Speaker's face filling >50% of frame (talking-head = NOT an image)
- ❌ Blurred, transition frame, or text illegible
- ❌ Static background with no technical content

**Quality check:** Use `scripts/review_frames.py` with qwen3-vl for automated relevance scoring.

#### Step 5: Compile Final Image Set

For a 15-min technical video article, target 8-10 images:
- 2-3 Wikimedia/BYD official real-car photos
- 4-5 video frames with technical content (diagrams, demos)
- 1-2 BYD press / external source images
- 0 talking-head frames (zero tolerance)

Each image must: (a) serve a specific article section, (b) have source attribution + license.

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

### Phase 4.5: Transformation Checklist (Chinese Draft → Publishable English Article)

**IMPORTANT**: The Chinese structured draft from Phase 4 is a **working scaffold**, not the final article. Before proceeding to upload, apply these transformations. Skipping this phase produces "translated notes" not "published articles."

#### A. Add Quick Answer (mandatory)
- 150 words max, 5 bullet points covering key systems/models
- 1-sentence "Rule of thumb" for non-technical readers (e.g., "DiSus-P for off-road, DiSus-X for performance, DiSus-Z for luxury")
- Reading time estimate (e.g., "12 min read")
- This is the "5-second skimmer" entry point — without it, the article has no funnel

#### B. Build FAQ Section (mandatory)
- Extract 5-6 questions from the draft's natural "reader confusion points"
- Each FAQ: H3 question + 2-4 sentence answer
- Target: these are Google snippet candidates — each must be independently understandable
- Never skip FAQ even if the draft didn't plan for it; FAQ is mandatory for SEO

#### C. Rebuild Tables for Multi-Dimensional Comparison (mandatory)
- Merge single-dimension tables into at least 1 "complete system comparison" table
- Each table must answer one clear question (not just dump features)
- Minimum 4 columns; add "Best Use Case" or "Application" column where meaningful
- Check: can a reader understand the landscape from the table alone?

#### D. Source Upgrade (mandatory)
- The Bilibili video is the **starting point**, not the only source
- Add at least 1 official BYD source (press release, global site, product page)
- Add at least 1 industry/third-party source for cross-verification
- Image sources: label each non-original image with attribution + license (CC BY, etc.)
- Target: 5-9 cited sources total

#### E. Tone Audit (mandatory)
- Remove or rephrase ALL of these patterns common in Chinese tech videos:
  - Absolute claims: "最好的"→"among the leading", "独一份"→delete, describe feature instead
  - Fan language: "含金量最高"→"the critical component is...", "吊打"→"exceeds"
  - Partisan framing: "被带偏了"→present both sides, "仅此而已"→delete
- For controversial topics: dedicate a separate H2 section presenting BOTH sides
- Golden rule: describe what the system DOES, not what category it BELONGS to

#### F. Metaphor Audit (mandatory)
- Replace ALL military/defense analogies (fighter jets, aircraft carriers, missile systems) with civil/industrial equivalents
- Acceptable: Pascal's Principle, aircraft hydraulics, industrial robotics, Formula 1
- Why: military analogies alienate global readers and reduce credibility in technical contexts

#### G. Clean Metadata (mandatory)
- Delete ALL work-process artifacts from the final article:
  - Transcription tool name and version
  - Timestamp formats (`[00:10]`)
  - "可用于BYDToday文章的角度" (internal planning notes)
  - UP主 name in text body (cite in Sources section instead)
  - Speed/segment counts ("1.3x realtime", "531 segments")
- The reader should see a self-contained publication, not a converted draft

#### H. SEO Element Injection (mandatory)
- Natural keyword placement in H1, first paragraph, at least 2 H2s
- 2-4 internal links to related BYDToday articles (verify HTTP 200)
- Tags: 5-8 human-readable English tags (no Chinese, no internal codes)
- Primary category: match content type (Technology=14 for tech breakdowns)

#### I. Image Gate — Proactive Sourcing (mandatory)
**DO NOT publish with talking-head frames or "video screenshots only."**

Before upload, audit every image in the article:
- ❌ Zero tolerance for: speaker-facing frames, blurry screenshots, transition frames
- ✅ Each image must have: clear technical purpose + matches its parent section
- ✅ Mix required: at least 2 external images (Wikimedia CC / BYD official) beyond video frames
- ✅ Attribution: every non-original image must cite source name + license type + URL

If any section lacks a good image, source externally (Phase 3 priority system) before proceeding. A missing image is better than a bad one — but a good sourced image is best.

#### Checklist Gate
Before Phase 5, confirm ALL 9 items (A-I) are done. If any is missing, return to the draft — do not upload.

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
5. **Talking-head video limitations**: Technical Bilibili videos are often 80%+ speaker-facing. This is a known reality — DO NOT accept low-quality frames. Source real-car photos and diagrams externally. Phase 3 requires proactive image sourcing before writing.
6. **yt-dlp 412 error**: Use cookies file from a logged-in Bilibili session.
7. **Translation vs. rewriting gap**: The Chinese draft from Phase 4 is a scaffold, NOT the final article. Direct translation/language-swap produces "translated notes" — low credibility, missing reader structure. Codex comparison (2026-07-02) showed 10 major transformation dimensions needed: Quick Answer, FAQ, table rebuild, source upgrade, tone audit, metaphor audit, metadata cleanup, SEO injection, controversy neutralization, and reader guidance. Always run Phase 4.5 transformation before upload.

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
