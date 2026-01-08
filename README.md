# Screenshot to JSON

> Extract structured UI metadata from screenshots using vision LLMs.

A poem by [nicetools.ai](https://nicetools.ai) — Drew Prescott

HERE: This is a semantic UI extraction pipeline for screenshots.
THIS: 5-pass LLM pipeline that outputs structured JSON with purposes, confidence scores, and page insights.

---

## TL;DR

- Upload screenshot → get structured JSON of every UI element
- Per-element confidence scores + semantic purposes
- 5-pass LLM pipeline with validation to reduce hallucinations
- Supports web apps, dashboards, forms, modals, marketing pages
- Open source, self-hostable, MIT license

```bash
make install && node server.js
# Open http://localhost:3456
```

---

## The Problem

LLMs can "see" screenshots but existing tools have gaps:

| Approach | What You Get | What's Missing |
|----------|--------------|----------------|
| **Screenshot → Code** | HTML/React code | No semantic understanding—just renders pixels |
| **CV Detection** | Bounding boxes | A "button" is just a rectangle, not "submit login" |
| **Design Tool Export** | Figma JSON | Requires source files—can't analyze competitors |

**The gap**: No tool extracts *semantic UI inventory*—what each element *is*, what it *does*, and *why* it exists.

---

## What This Project Does Differently

**Screenshot to JSON** is a **semantic UI extraction pipeline** that produces structured inventory data, not code or bounding boxes.

| Feature | This Project | Alternatives |
|---------|--------------|---------------|
| **Semantic purposes** | Every element has a `purpose` field: "submit login credentials", "filter transactions by date" | Just type labels: "button", "input" |
| **Confidence scores** | Per-element confidence (0.0-1.0) for downstream filtering | Binary detection or none |
| **Page insights** | Derives `primary_action`, `data_focus`, `user_journey_stage` | None |
| **Hierarchical structure** | Nested zones (top_bar, left_pane, content_area) with parent-child relationships | Flat element lists |
| **App context aware** | Provide app name/description for domain-specific extraction | Context-blind |
| **Multi-pass validation** | 5-pass pipeline catches hallucinations via re-validation against image | Single-shot inference |
| **Open source** | MIT license, self-hostable, no vendor lock-in | Many are SaaS-only |

---

## Use Cases

- **Design System Audits**: Inventory all UI patterns across an application
- **Competitive Analysis**: Extract structured data from competitor screenshots
- **Accessibility Testing**: Identify elements missing semantic context
- **UI Test Generation**: Feed structured inventory to test automation
- **Design Handoff**: Generate component inventories from mockups
- **User Research**: Analyze screenshots from usability sessions
- **LLM Agent Training**: Structured UI data for training web agents

---

## What It Does

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│   Screenshot    │────▶│  5-Pass LLM      │────▶│  Structured JSON    │
│   (PNG/JPG)     │     │  Pipeline        │     │  + Wireframe SVG    │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
```

**Input:** Screenshot of any web UI + optional app context  
**Output:** 
- JSON inventory of all UI elements with types, labels, purposes, confidence scores
- Interactive wireframe visualization
- Page-level insights (what user is trying to do, data focus, etc.)

## Quick Start

### 1. Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for web UI)
- **API Key** from one of:
  - [OpenRouter](https://openrouter.ai) (recommended, uses Qwen2.5-VL)
  - [Groq](https://console.groq.com) (free, uses Llama 4)

### 2. Installation

```bash
# Clone and enter directory
cd screenshot-to-json

# One-command setup (creates venv, installs Python deps)
make install

# Node setup (for web UI)
npm install

# Configure API key
cp .env.example .env
# Edit .env and add your API key:
#   OPENROUTER_API_KEY=sk-or-v1-...
#   or GROQ_API_KEY=gsk_...
```

### 3. Run the Web UI

```bash
node server.js
# Open http://localhost:3456
```

### 4. Use It

1. Enter app name (e.g., "mercury.com")
2. Optionally describe the app for better results
3. Upload 1-2 screenshots
4. Click **Extract Interface**
5. View JSON output and interactive wireframe

---

## Architecture

### 5-Pass Extraction Pipeline

The system uses **LangGraph** to orchestrate a multi-pass LLM analysis:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PIPELINE FLOW                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [Screenshot]                                                       │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────┐                                                │
│  │ PASS 1: CLASSIFY│  Identify screen type (app/dashboard/form)    │
│  │                 │  Detect user intent                            │
│  │                 │  Check for top bar / left sidebar              │
│  └────────┬────────┘                                                │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────┐                                                │
│  │ PASS 2: ZONES   │  Describe contents of each zone               │
│  │                 │  (top bar, left pane, content area)            │
│  └────────┬────────┘                                                │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────┐                                                │
│  │ PASS 3: EXTRACT │  Extract UI elements from each zone           │
│  │ (PARALLEL x3)   │  ◀── Runs 3 extractions concurrently          │
│  └────────┬────────┘                                                │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────┐                                                │
│  │ PASS 4: VALIDATE│  Validate against image, assign confidence    │
│  │                 │  Assemble into InterfaceInventory schema       │
│  └────────┬────────┘                                                │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────┐                                                │
│  │ PASS 5: REASON  │  Text-only refinement (no vision)             │
│  │                 │  Improve purposes, derive page insights        │
│  └────────┬────────┘                                                │
│           │                                                         │
│           ▼                                                         │
│  [InterfaceInventory JSON]                                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Why Multi-Pass?

1. **Accuracy**: Each pass focuses on one task, reducing hallucinations
2. **Speed**: Pass 3 runs zone extractions in parallel (3x speedup)
3. **Validation**: Pass 4 catches errors by re-checking against the image
4. **Semantic Depth**: Pass 5 adds reasoning without vision cost

---

## Project Structure

```
screenshot-to-json/
├── server.js              # Express server for web UI
├── extract.py             # CLI entry point (stdin/stdout JSON)
├── pipeline.py            # 5-pass LangGraph extraction pipeline
├── schemas.py             # Pydantic models for output validation
├── config.py              # API keys, model selection, parameters
├── requirements.txt       # Python dependencies
├── package.json           # Node dependencies
├── Makefile               # Auto-install: `make install`
│
├── prompts/               # LLM prompt templates (Markdown)
│   ├── pass_1_classify.md
│   ├── pass_2_zones.md
│   ├── pass_3_extract.md
│   ├── pass_4_validate.md
│   └── pass_5_reasoning.md
│
├── rendering_engine/      # Client-side wireframe renderer
│   ├── wireframe-renderer.js
│   └── element-stubs.js
│
├── config/                # Configuration files
│   └── vocabulary.yaml    # Element type definitions (39 types)
│
└── .env                   # API keys (not committed)
```

---

## Output Schema

```json
{
  "screen": {
    "classification": "application",
    "intent": "Review and categorize financial transactions"
  },
  "zones": {
    "top_bar": [
      {"type": "search_bar", "purpose": "Search transactions", "confidence": 0.95},
      {"type": "avatar", "purpose": "Access user menu", "confidence": 0.90}
    ],
    "left_pane": [
      {"type": "nav_list", "item_count": 8, "purpose": "Navigate app sections", "confidence": 0.92}
    ],
    "content_area": [
      {"type": "heading", "label": "Transactions", "level": 1, "confidence": 0.98},
      {"type": "data_table", "columns": ["Date", "Description", "Amount"], "row_count": 25, "confidence": 0.88}
    ]
  },
  "confidence": 0.91,
  "page_insights": {
    "primary_action": "Review transaction details",
    "data_focus": "Financial transaction history",
    "user_journey_stage": "Active use"
  },
  "version": "2.2.0"
}
```

### Element Types (39 total)

| Category | Types |
|----------|-------|
| **Structure** | `nav_list`, `tab_group`, `action_bar`, `breadcrumb`, `pagination`, `divider` |
| **Containers** | `blade`, `section` |
| **Collections** | `list`, `data_table`, `calendar` |
| **Data Display** | `metric`, `field_value`, `badge`, `chart`, `avatar`, `media`, `progress_bar`, `icon` |
| **Content** | `heading`, `text_block`, `content_area` |
| **Input** | `text_input`, `text_area`, `selector`, `toggle`, `checkbox`, `radio`, `date_input`, `rich_text`, `file_input`, `search_bar` |
| **Action** | `button`, `action_link`, `icon_action` |
| **Feedback** | `empty_state`, `loading`, `error_state` |

---

## Configuration

### Environment Variables (.env)

```bash
# Choose ONE provider:

# Option 1: OpenRouter (recommended, best quality)
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Option 2: Groq (free, faster but less accurate)
GROQ_API_KEY=gsk_your_key_here
```

### Provider Selection

Edit `config.py` to switch providers:

```python
provider: str = "openrouter"  # or "groq"
```

### Model Configuration

**OpenRouter (default):**
- Vision: `qwen/qwen2.5-vl-72b-instruct` - Best for dense UI extraction
- Reasoning: `qwen/qwen2.5-72b-instruct` - Text-only for Pass 5

**Groq:**
- Vision: `meta-llama/llama-4-maverick-17b-128e-instruct`
- Fast: `meta-llama/llama-4-scout-17b-16e-instruct`

---

## Usage

### Web UI

```bash
node server.js
# Open http://localhost:3456
```

### Command Line

```bash
# Extract from file
python pipeline.py screenshot.png output.json

# Pipe to jq for pretty print
python pipeline.py screenshot.png | jq .
```

### Python API

```python
from pipeline import extract_interface_inventory_with_context

inventory = extract_interface_inventory_with_context(
    image_path="screenshot.png",
    app_name="mercury.com",
    app_description="Business banking platform for startups"
)

# Access structured data
print(inventory.screen.classification)  # "application"
print(inventory.screen.intent)          # "Review financial transactions"
print(inventory.confidence)             # 0.91

# Get all low-confidence elements
from schemas import get_low_confidence_elements
uncertain = get_low_confidence_elements(inventory, threshold=0.7)

# Export to JSON
json_str = inventory.model_dump_json(indent=2)
```

---

## Performance

| Metric | Value |
|--------|-------|
| **Extraction Time** | 8-15 seconds per screenshot |
| **Cost (OpenRouter)** | ~$0.01-0.02 per screenshot |
| **Cost (Groq)** | Free tier available |
| **Accuracy** | 85-95% element detection |

---

## How It Works (Detailed)

### Pass 1: Classification
- Identifies screen type: `application`, `dashboard`, `form`, `modal`, `content_page`, `hybrid`
- Determines user intent (what they're trying to accomplish)
- Detects structural zones (top bar, left sidebar)

### Pass 2: Zone Identification
- Describes contents of each zone in natural language
- These "hints" guide Pass 3's element extraction

### Pass 3: Zone Extraction (Parallel)
- Extracts individual UI elements from each zone
- Runs 3 API calls concurrently for speed
- Each element gets: type, label, purpose, confidence, type-specific fields

### Pass 4: Validation
- Re-checks extraction against original image
- Catches hallucinations and errors
- Assigns overall confidence score
- Assembles final JSON structure

### Pass 5: Reasoning
- Text-only analysis (no vision API cost)
- Improves element purposes
- Derives page insights (primary action, data focus, user journey stage)
- Adjusts confidence based on coherence

---

## How It Compares

| Tool | Output | Semantic Understanding | Open Source | Confidence Scores |
|------|--------|----------------------|-------------|-------------------|
| **This Project** | Structured JSON inventory | ✅ Purpose per element | ✅ MIT | ✅ Per-element |
| screenshot-to-code | HTML/React/Vue code | ❌ Just renders | ✅ | ❌ |
| Codia VisualStruct | JSON + SVG + Figma | ⚠️ Types only | ❌ SaaS | ❌ |
| UIED | Bounding boxes + types | ❌ | ✅ | ❌ |
| GPT-4V direct | Unstructured text | ⚠️ Inconsistent | N/A | ❌ |

---

## Links

LINK: See [TODO.md](TODO.md) for roadmap (marketing vocabulary expansion)
LINK: See [config/vocabulary.yaml](config/vocabulary.yaml) for element type definitions
LINK: [OpenRouter](https://openrouter.ai) for API access (recommended)
LINK: [Groq](https://console.groq.com) for free tier API

---

## Metadata

- **Version**: 2.2.0
- **License**: MIT
- **Element Types**: 39
- **Pipeline Passes**: 5

---

## About

A nice tool to extract structured UI inventory from screenshots using vision LLMs. Semantic purposes, confidence scores, and page insights—not just bounding boxes.
