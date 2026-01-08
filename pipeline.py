"""
Interface Inventory System - LangGraph Pipeline
Version: 2.0.0

Multi-pass extraction with per-element confidence.
"""

import sys
import json
import time
import base64
from pathlib import Path
from typing import TypedDict, Optional, List
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END
from groq import Groq
from pydantic import ValidationError

from schemas import (
    InterfaceInventory,
    get_element_confidence_stats,
    get_low_confidence_elements,
)
from config import get_config


# =============================================================================
# STATE - Shared context passed through all pipeline passes
# =============================================================================
# GraphState holds everything: inputs, intermediate results, and outputs.
# Each pass reads what it needs and writes its results back to state.
# LangGraph manages the flow between passes.

class GraphState(TypedDict):
    """Pipeline state."""
    
    # Input
    image_base64: str
    source_filename: str
    app_name: Optional[str]           # Application name/domain
    app_description: Optional[str]    # Context paragraph about the app
    
    # Pass 1
    classification: Optional[str]
    intent: Optional[str]
    has_top_bar: Optional[bool]
    has_left_pane: Optional[bool]
    classification_observed: Optional[str]
    
    # Pass 2
    top_bar_hint: Optional[str]
    left_pane_hint: Optional[str]
    content_area_hint: Optional[str]
    
    # Pass 3
    top_bar_elements: Optional[List[dict]]
    left_pane_elements: Optional[List[dict]]
    content_area_elements: Optional[List[dict]]
    
    # Pass 4
    final_json: Optional[dict]
    confidence: Optional[float]
    validation_notes: Optional[List[str]]
    
    # Pass 5 (Reasoning)
    page_insights: Optional[dict]
    reasoning_notes: Optional[List[str]]
    refined_intent: Optional[str]
    
    # Meta
    errors: List[str]
    timings: dict
    progress_callback: Optional[callable]


# =============================================================================
# PROMPT UTILITIES - Template loading and variable substitution
# =============================================================================
# Prompts are stored as Markdown files in /prompts directory.
# Each pass has its own prompt file (pass_1_classify.md, etc.)
# Templates use {{variable}} syntax for dynamic values.

def load_prompt(name: str) -> str:
    """Load prompt template."""
    config = get_config()
    path = config.prompts_dir / f"{name}.md"
    return path.read_text()


def render_prompt(template: str, **kwargs) -> str:
    """Render template with variables."""
    for key, value in kwargs.items():
        placeholder = "{{" + key + "}}"
        if value is None:
            rendered = "null"
        elif isinstance(value, (dict, list)):
            rendered = json.dumps(value, indent=2)
        elif isinstance(value, bool):
            rendered = str(value).lower()
        else:
            rendered = str(value)
        template = template.replace(placeholder, rendered)
    return template


# =============================================================================
# GROQ CLIENT - Llama 4 Vision models via Groq API
# =============================================================================
# Groq provides fast inference for Llama models.
# Two tiers: Scout (fast, cheaper) and Maverick (quality, slower)
# Passes 1-2 use Scout, Passes 3-4 use Maverick for detail.

class GroqVisionClient:
    """Groq API client for vision."""
    
    def __init__(self, api_key: str = None):
        config = get_config()
        self.client = Groq(api_key=api_key or config.groq.api_key)
    
    def analyze(
        self,
        image_base64: str,
        prompt: str,
        model: str = None,
        max_tokens: int = None,
    ) -> str:
        """Analyze image with prompt."""
        config = get_config()
        model = model or config.groq.model_quality
        max_tokens = max_tokens or config.groq.max_tokens

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                    },
                    {"type": "text", "text": prompt}
                ]
            }
        ]

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=config.groq.temperature,
            response_format={"type": "json_object"}
        )

        return response.choices[0].message.content
    
    def analyze_with_retry(
        self,
        image_base64: str,
        prompt: str,
        model: str,
        max_tokens: int = None,
    ) -> tuple[str, Optional[str]]:
        """Analyze with retry using exponential backoff, returns (response, error)."""
        config = get_config()
        for attempt in range(config.retry.max_retries):
            try:
                response = self.analyze(image_base64, prompt, model, max_tokens)
                return response, None
            except Exception as e:
                if attempt < config.retry.max_retries - 1:
                    # Exponential backoff: delay * (multiplier ^ attempt)
                    delay_ms = config.retry.retry_delay_ms * (config.retry.backoff_multiplier ** attempt)
                    time.sleep(delay_ms / 1000)
                else:
                    return "", str(e)
        return "", "Max retries exceeded"


class GroqReasoningClient:
    """Groq API client for reasoning models (no vision)."""
    
    def __init__(self, api_key: str = None):
        config = get_config()
        self.client = Groq(api_key=api_key or config.groq.api_key)
    
    def reason(
        self,
        prompt: str,
        model: str = None,
        max_tokens: int = None,
    ) -> tuple[str, Optional[str], Optional[str]]:
        """
        Run reasoning on text prompt (no image).
        Returns: (response_content, reasoning_content, error)
        """
        config = get_config()
        model = model or config.groq.pass_5_model
        max_tokens = max_tokens or config.groq.pass_5_max_tokens

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=config.groq.reasoning_temperature,
                response_format={"type": "json_object"}
            )
            
            message = response.choices[0].message
            content = message.content
            # Reasoning trace not available in standard Groq API
            reasoning = None
            
            return content, reasoning, None
            
        except Exception as e:
            return "", None, str(e)
    
    def reason_with_retry(
        self,
        prompt: str,
        model: str = None,
    ) -> tuple[str, Optional[str], Optional[str]]:
        """Reason with retry using exponential backoff, returns (response, reasoning, error)."""
        config = get_config()
        for attempt in range(config.retry.max_retries):
            try:
                content, reasoning, error = self.reason(prompt, model)
                if not error:
                    return content, reasoning, None
                if attempt < config.retry.max_retries - 1:
                    # Exponential backoff: delay * (multiplier ^ attempt)
                    delay_ms = config.retry.retry_delay_ms * (config.retry.backoff_multiplier ** attempt)
                    time.sleep(delay_ms / 1000)
            except Exception as e:
                if attempt < config.retry.max_retries - 1:
                    # Exponential backoff: delay * (multiplier ^ attempt)
                    delay_ms = config.retry.retry_delay_ms * (config.retry.backoff_multiplier ** attempt)
                    time.sleep(delay_ms / 1000)
                else:
                    return "", None, str(e)
        return "", None, "Max retries exceeded"


# =============================================================================
# OPENROUTER CLIENT - Qwen2.5-VL via OpenRouter API
# =============================================================================
# OpenRouter provides access to Qwen2.5-VL-72B, which excels at:
# - Dense UI element detection
# - Reliable JSON output
# - Understanding complex layouts
# This is the default provider for best quality results.

class OpenRouterVisionClient:
    """OpenRouter API client for Qwen2.5-VL vision model."""
    
    def __init__(self, api_key: str = None):
        import openai
        config = get_config()
        self.client = openai.OpenAI(
            base_url=config.openrouter.base_url,
            api_key=api_key or config.openrouter.api_key,
            default_headers={
                "HTTP-Referer": "https://interface-inventory.local",
                "X-Title": "Interface Inventory System"
            }
        )
    
    def analyze(
        self,
        image_base64: str,
        prompt: str,
        model: str = None,
        max_tokens: int = None,
    ) -> str:
        """Analyze image with prompt using Qwen2.5-VL."""
        config = get_config()
        model = model or config.openrouter.vision_model
        max_tokens = max_tokens or config.openrouter.max_tokens

        print(f"  [API] Calling {model} (max_tokens={max_tokens})...", file=sys.stderr, flush=True)
        start = time.time()

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                    },
                    {"type": "text", "text": prompt}
                ]
            }
        ]

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=config.openrouter.temperature,
            response_format={"type": "json_object"},
            timeout=120  # 2 minute timeout
        )

        elapsed = time.time() - start
        print(f"  [API] Response in {elapsed:.1f}s", file=sys.stderr, flush=True)

        return response.choices[0].message.content
    
    def analyze_with_retry(
        self,
        image_base64: str,
        prompt: str,
        model: str = None,
        max_tokens: int = None,
    ) -> tuple[str, Optional[str]]:
        """Analyze with retry using exponential backoff, returns (response, error)."""
        config = get_config()
        model = model or config.openrouter.vision_model
        for attempt in range(config.retry.max_retries):
            try:
                response = self.analyze(image_base64, prompt, model, max_tokens)
                return response, None
            except Exception as e:
                if attempt < config.retry.max_retries - 1:
                    delay_ms = config.retry.retry_delay_ms * (config.retry.backoff_multiplier ** attempt)
                    time.sleep(delay_ms / 1000)
                else:
                    return "", str(e)
        return "", "Max retries exceeded"


class OpenRouterReasoningClient:
    """OpenRouter API client for reasoning models (no vision)."""
    
    def __init__(self, api_key: str = None):
        import openai
        config = get_config()
        self.client = openai.OpenAI(
            base_url=config.openrouter.base_url,
            api_key=api_key or config.openrouter.api_key,
            default_headers={
                "HTTP-Referer": "https://interface-inventory.local",
                "X-Title": "Interface Inventory System"
            }
        )
    
    def reason(
        self,
        prompt: str,
        model: str = None,
        max_tokens: int = None,
    ) -> tuple[str, Optional[str], Optional[str]]:
        """Run reasoning on text prompt (no image)."""
        config = get_config()
        model = model or config.openrouter.reasoning_model
        max_tokens = max_tokens or config.openrouter.pass_5_max_tokens

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=config.openrouter.reasoning_temperature,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return content, None, None
            
        except Exception as e:
            return "", None, str(e)
    
    def reason_with_retry(
        self,
        prompt: str,
        model: str = None,
    ) -> tuple[str, Optional[str], Optional[str]]:
        """Reason with retry using exponential backoff."""
        config = get_config()
        for attempt in range(config.retry.max_retries):
            try:
                content, reasoning, error = self.reason(prompt, model)
                if not error:
                    return content, reasoning, None
                if attempt < config.retry.max_retries - 1:
                    delay_ms = config.retry.retry_delay_ms * (config.retry.backoff_multiplier ** attempt)
                    time.sleep(delay_ms / 1000)
            except Exception as e:
                if attempt < config.retry.max_retries - 1:
                    delay_ms = config.retry.retry_delay_ms * (config.retry.backoff_multiplier ** attempt)
                    time.sleep(delay_ms / 1000)
                else:
                    return "", None, str(e)
        return "", None, "Max retries exceeded"


# =============================================================================
# GLOBAL CLIENTS - Provider selection and initialization
# =============================================================================
# Provider is set in config.py (default: "openrouter")
# Clients are lazily initialized on first use.
# Both vision and reasoning clients support the same interface.

def get_vision_client():
    """Get the appropriate vision client based on config."""
    config = get_config()
    if config.provider == "openrouter":
        return OpenRouterVisionClient()
    return GroqVisionClient()

def get_reasoning_client():
    """Get the appropriate reasoning client based on config."""
    config = get_config()
    if config.provider == "openrouter":
        return OpenRouterReasoningClient()
    return GroqReasoningClient()

# Initialize clients (will be re-created if provider changes)
vision_client = None
reasoning_client = None

def _ensure_clients():
    """Ensure clients are initialized."""
    global vision_client, reasoning_client
    if vision_client is None:
        vision_client = get_vision_client()
    if reasoning_client is None:
        reasoning_client = get_reasoning_client()


# =============================================================================
# PIPELINE PASSES - The 5-stage extraction process
# =============================================================================
# Each pass is a function that:
# 1. Takes GraphState as input
# 2. Loads its prompt template
# 3. Calls the vision/reasoning model
# 4. Parses response and updates state
# 5. Returns modified state
#
# Pass execution order: classify -> zones -> extract_zones -> validate -> reasoning

def _report_progress(state: GraphState, pass_name: str, status: str):
    """Report progress if callback is available."""
    # Always log to stderr for console visibility
    print(f"[PIPELINE] {pass_name}: {status}", file=sys.stderr, flush=True)
    cb = state.get("progress_callback")
    if cb:
        cb(pass_name, status)


def pass_1_classify(state: GraphState) -> GraphState:
    """
    PASS 1: CLASSIFICATION
    
    Purpose: Identify what kind of interface this is and what the user wants to do.
    
    Inputs from state:
        - image_base64: The screenshot to analyze
        - app_name, app_description: Optional context about the app
    
    Outputs to state:
        - classification: "application", "dashboard", "form", "modal", etc.
        - intent: What the user is trying to accomplish (3-10 words)
        - has_top_bar: Whether there's a top navigation bar
        - has_left_pane: Whether there's a left sidebar
    
    Model: Fast model (Llama 4 Scout or Qwen) for quick initial classification
    """
    _report_progress(state, "Pass 1: Classification", "running")
    start = time.time()
    config = get_config()
    _ensure_clients()
    
    template = load_prompt("pass_1_classify")
    prompt = render_prompt(
        template,
        app_name=state.get("app_name") or "Not specified",
        app_description=state.get("app_description") or "No description provided"
    )
    
    # Get max_tokens based on provider
    max_tokens = config.openrouter.pass_1_max_tokens if config.provider == "openrouter" else config.groq.pass_1_max_tokens
    
    response, error = vision_client.analyze_with_retry(
        state["image_base64"], prompt, None, max_tokens
    )
    
    if error:
        state["errors"].append(f"Pass 1: {error}")
        return state
    
    try:
        result = json.loads(response)
        state["classification"] = result.get("classification")
        state["intent"] = result.get("intent")
        state["has_top_bar"] = result.get("has_top_bar", False)
        state["has_left_pane"] = result.get("has_left_pane", False)
        state["classification_observed"] = result.get("observed")
        
        # Form/modal cannot have zones
        if state["classification"] in ["form", "modal"]:
            state["has_top_bar"] = False
            state["has_left_pane"] = False
            
    except json.JSONDecodeError as e:
        state["errors"].append(f"Pass 1 parse: {e}. Response: {response[:200] if response else 'empty'}")

    state["timings"]["pass_1_ms"] = int((time.time() - start) * 1000)
    return state


def pass_2_zones(state: GraphState) -> GraphState:
    """
    PASS 2: ZONE IDENTIFICATION
    
    Purpose: Describe what's in each zone to guide element extraction.
    
    Inputs from state:
        - image_base64: The screenshot
        - classification, intent: From Pass 1
        - has_top_bar, has_left_pane: Which zones exist
    
    Outputs to state:
        - top_bar_hint: Description of top bar contents (if present)
        - left_pane_hint: Description of sidebar contents (if present)
        - content_area_hint: Description of main content area
    
    These hints help Pass 3 focus on the right elements in each zone.
    """
    _report_progress(state, "Pass 2: Zone Identification", "running")
    start = time.time()
    config = get_config()
    _ensure_clients()
    
    template = load_prompt("pass_2_zones")
    prompt = render_prompt(
        template,
        app_name=state.get("app_name") or "Not specified",
        app_description=state.get("app_description") or "No description provided",
        classification=state["classification"],
        intent=state["intent"],
        has_top_bar=state["has_top_bar"],
        has_left_pane=state["has_left_pane"]
    )
    
    max_tokens = config.openrouter.pass_2_max_tokens if config.provider == "openrouter" else config.groq.pass_2_max_tokens
    
    response, error = vision_client.analyze_with_retry(
        state["image_base64"], prompt, None, max_tokens
    )
    
    if error:
        state["errors"].append(f"Pass 2: {error}")
        return state
    
    try:
        result = json.loads(response)
        state["top_bar_hint"] = result.get("top_bar_hint")
        state["left_pane_hint"] = result.get("left_pane_hint")
        state["content_area_hint"] = result.get("content_area_hint")
    except json.JSONDecodeError as e:
        state["errors"].append(f"Pass 2 parse: {e}. Response: {response[:200] if response else 'empty'}")

    state["timings"]["pass_2_ms"] = int((time.time() - start) * 1000)
    return state


def _extract_zone(state: GraphState, zone: str, hint: Optional[str]) -> tuple[Optional[List[dict]], Optional[str]]:
    """Extract elements from one zone."""
    if hint is None and zone != "content_area":
        return None, None
    
    config = get_config()
    _ensure_clients()
    
    template = load_prompt("pass_3_extract")
    prompt = render_prompt(
        template,
        app_name=state.get("app_name") or "Not specified",
        app_description=state.get("app_description") or "No description provided",
        classification=state["classification"],
        intent=state["intent"],
        zone_name=zone,
        zone_hint=hint or "Main content area"
    )
    
    max_tokens = config.openrouter.pass_3_max_tokens if config.provider == "openrouter" else config.groq.pass_3_max_tokens
    
    response, error = vision_client.analyze_with_retry(
        state["image_base64"], prompt, None, max_tokens
    )
    
    if error:
        return None, error
    
    try:
        elements = json.loads(response)
        if not isinstance(elements, list):
            elements = elements.get("elements", [elements])
        return elements, None
    except json.JSONDecodeError as e:
        return None, f"{e}. Response: {response[:200] if response else 'empty'}"


def pass_3_parallel(state: GraphState) -> GraphState:
    """
    PASS 3: ZONE EXTRACTION (PARALLEL)
    
    Purpose: Extract individual UI elements from each zone.
    
    KEY OPTIMIZATION: Runs 3 extractions concurrently using ThreadPoolExecutor.
    This is the slowest pass, so parallelization provides ~3x speedup.
    
    Inputs from state:
        - image_base64: The screenshot
        - top_bar_hint, left_pane_hint, content_area_hint: Zone descriptions
    
    Outputs to state:
        - top_bar_elements: List of elements (buttons, search, nav items, etc.)
        - left_pane_elements: List of elements (nav list, filters, etc.)
        - content_area_elements: List of elements (tables, forms, metrics, etc.)
    
    Each element has: type, label, purpose, confidence, and type-specific fields.
    Model: Quality model (Llama 4 Maverick or Qwen2.5-VL-72B) for accuracy.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    _report_progress(state, "Pass 3: Zone Extraction (parallel)", "running")
    start = time.time()
    
    def extract_top_bar():
        if not state["has_top_bar"]:
            return ("top_bar", None, None)
        elements, error = _extract_zone(state, "top_bar", state["top_bar_hint"])
        return ("top_bar", elements, error)
    
    def extract_left_pane():
        if not state["has_left_pane"]:
            return ("left_pane", None, None)
        elements, error = _extract_zone(state, "left_pane", state["left_pane_hint"])
        return ("left_pane", elements, error)
    
    def extract_content():
        elements, error = _extract_zone(state, "content_area", state["content_area_hint"])
        return ("content_area", elements, error)
    
    # Run all 3 extractions in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(extract_top_bar),
            executor.submit(extract_left_pane),
            executor.submit(extract_content),
        ]
        
        for future in as_completed(futures):
            zone, elements, error = future.result()
            if zone == "top_bar":
                state["top_bar_elements"] = elements
                if error:
                    state["errors"].append(f"Pass 3 top_bar: {error}")
            elif zone == "left_pane":
                state["left_pane_elements"] = elements
                if error:
                    state["errors"].append(f"Pass 3 left_pane: {error}")
            elif zone == "content_area":
                state["content_area_elements"] = elements or []
                if error:
                    state["errors"].append(f"Pass 3 content: {error}")
    
    state["timings"]["pass_3_ms"] = int((time.time() - start) * 1000)
    return state


def pass_4_validate(state: GraphState) -> GraphState:
    """
    PASS 4: VALIDATION AND ASSEMBLY
    
    Purpose: Validate extracted elements against the original image and
             assemble into final InterfaceInventory JSON structure.
    
    Inputs from state:
        - image_base64: Original screenshot for validation
        - All Pass 1-3 outputs
    
    Outputs to state:
        - final_json: Complete inventory matching InterfaceInventory schema
        - confidence: Overall confidence score (0.0-1.0)
        - validation_notes: Any issues or adjustments made
    
    This pass catches hallucinations by comparing extraction against image.
    """
    _report_progress(state, "Pass 4: Validation", "running")
    start = time.time()
    config = get_config()
    _ensure_clients()
    
    pass_1 = {
        "classification": state["classification"],
        "intent": state["intent"],
        "has_top_bar": state["has_top_bar"],
        "has_left_pane": state["has_left_pane"],
    }
    if state["classification_observed"]:
        pass_1["observed"] = state["classification_observed"]
    
    pass_2 = {
        "top_bar_hint": state["top_bar_hint"],
        "left_pane_hint": state["left_pane_hint"],
        "content_area_hint": state["content_area_hint"],
    }
    
    template = load_prompt("pass_4_validate")
    prompt = render_prompt(
        template,
        app_name=state.get("app_name") or "Not specified",
        app_description=state.get("app_description") or "No description provided",
        pass_1_output=pass_1,
        pass_2_output=pass_2,
        top_bar_elements=state["top_bar_elements"],
        left_pane_elements=state["left_pane_elements"],
        content_area_elements=state["content_area_elements"],
        source_filename=state["source_filename"]
    )
    
    max_tokens = config.openrouter.pass_4_max_tokens if config.provider == "openrouter" else config.groq.pass_4_max_tokens
    
    response, error = vision_client.analyze_with_retry(
        state["image_base64"], prompt, None, max_tokens
    )
    
    if error:
        state["errors"].append(f"Pass 4: {error}")
        state["final_json"] = _fallback_assembly(state)
        state["confidence"] = 0.5
        state["validation_notes"] = ["Validation failed, using unvalidated extraction"]
    else:
        try:
            result = json.loads(response)
            state["final_json"] = result
            state["confidence"] = result.get("confidence", 0.5)
            state["validation_notes"] = result.get("validation_notes", [])
        except json.JSONDecodeError as e:
            state["errors"].append(f"Pass 4 parse: {e}. Response: {response[:200] if response else 'empty'}")
            state["final_json"] = _fallback_assembly(state)
            state["confidence"] = 0.5
    
    state["timings"]["pass_4_ms"] = int((time.time() - start) * 1000)
    return state


def _fallback_assembly(state: GraphState) -> dict:
    """Fallback assembly without validation."""
    return {
        "screen": {
            "classification": state["classification"],
            "intent": state["intent"],
            "source": state["source_filename"],
        },
        "zones": {
            "top_bar": state["top_bar_elements"],
            "left_pane": state["left_pane_elements"],
            "content_area": state["content_area_elements"] or [],
        },
        "confidence": 0.5,
        "validation_notes": ["Unvalidated fallback assembly"],
    }


def pass_5_reasoning(state: GraphState) -> GraphState:
    """
    PASS 5: REASONING REFINEMENT (TEXT-ONLY)
    
    Purpose: Improve element purposes, derive page insights, and refine confidence.
    
    KEY DIFFERENCE: This pass does NOT use vision - it only sees the extracted JSON.
    Uses a reasoning model (Llama 3.3 70B or Qwen2.5-72B) for deeper analysis.
    
    Inputs from state:
        - final_json: Extraction from Pass 4
        - classification, intent: For context
    
    Outputs to state:
        - page_insights: Derived metadata (primary_action, data_focus, etc.)
        - reasoning_notes: List of refinements made
        - refined_intent: Possibly improved intent statement
        - Adjusted confidence based on coherence
    
    This pass adds semantic understanding on top of visual extraction.
    """
    _report_progress(state, "Pass 5: Reasoning", "running")
    start = time.time()
    _ensure_clients()
    
    # Skip if no final_json from Pass 4
    if not state["final_json"]:
        state["errors"].append("Pass 5: No extraction to refine")
        state["timings"]["pass_5_ms"] = int((time.time() - start) * 1000)
        return state
    
    # Build extraction JSON for reasoning
    extraction_json = {
        "zones": state["final_json"].get("zones", {}),
    }
    
    template = load_prompt("pass_5_reasoning")
    prompt = render_prompt(
        template,
        app_name=state.get("app_name") or "Not specified",
        app_description=state.get("app_description") or "No description provided",
        classification=state["classification"],
        intent=state["intent"],
        extraction_json=json.dumps(extraction_json, indent=2)
    )
    
    # Call reasoning model (no image)
    response, reasoning, error = reasoning_client.reason_with_retry(prompt)
    
    if error:
        state["errors"].append(f"Pass 5: {error}")
        state["timings"]["pass_5_ms"] = int((time.time() - start) * 1000)
        return state
    
    try:
        result = json.loads(response)
        
        # Apply refined elements if present
        if "refined_elements" in result:
            refined = result["refined_elements"]
            if refined.get("top_bar"):
                state["final_json"]["zones"]["top_bar"] = refined["top_bar"]
            if refined.get("left_pane"):
                state["final_json"]["zones"]["left_pane"] = refined["left_pane"]
            if refined.get("content_area"):
                state["final_json"]["zones"]["content_area"] = refined["content_area"]
        
        # Apply refined intent
        if result.get("refined_intent"):
            state["refined_intent"] = result["refined_intent"]
            state["final_json"]["screen"]["intent"] = result["refined_intent"]
        
        # Store page insights
        if result.get("page_insights"):
            state["page_insights"] = result["page_insights"]
            state["final_json"]["page_insights"] = result["page_insights"]
        
        # Store reasoning notes
        if result.get("refinements_made"):
            state["reasoning_notes"] = result["refinements_made"]
            state["final_json"]["reasoning_notes"] = result["refinements_made"]
        
        # Adjust confidence (bounded to prevent extreme LLM values)
        if result.get("confidence_adjustment"):
            raw_adjustment = result["confidence_adjustment"]
            # Bound adjustment to reasonable range: -0.15 to +0.05
            adjustment = max(-0.15, min(0.05, raw_adjustment))
            new_confidence = max(0.0, min(1.0, state["confidence"] + adjustment))
            state["confidence"] = new_confidence
            state["final_json"]["confidence"] = new_confidence
        
        # Log reasoning if present
        if reasoning:
            print(f"Reasoning trace: {len(reasoning)} chars", file=sys.stderr)

    except json.JSONDecodeError as e:
        state["errors"].append(f"Pass 5 parse: {e}. Response: {response[:200] if response else 'empty'}")
    
    state["timings"]["pass_5_ms"] = int((time.time() - start) * 1000)
    return state


# =============================================================================
# GRAPH CONSTRUCTION - LangGraph workflow definition
# =============================================================================
# LangGraph manages the state machine: nodes are passes, edges are transitions.
# The graph is compiled once at module load and reused for all extractions.

def build_graph() -> StateGraph:
    """Build LangGraph pipeline."""
    graph = StateGraph(GraphState)

    graph.add_node("classify", pass_1_classify)
    graph.add_node("zones", pass_2_zones)
    graph.add_node("extract_zones", pass_3_parallel)  # Parallel extraction
    graph.add_node("validate", pass_4_validate)
    graph.add_node("reasoning", pass_5_reasoning)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "zones")
    graph.add_edge("zones", "extract_zones")  # Single parallel step
    graph.add_edge("extract_zones", "validate")
    graph.add_edge("validate", "reasoning")
    graph.add_edge("reasoning", END)

    return graph.compile()


# Pre-compiled graph (cached at module level for performance)
_compiled_graph = build_graph()


# =============================================================================
# PUBLIC API - Main entry points for extraction
# =============================================================================
# Two functions:
# - extract_interface_inventory(): Basic extraction without app context
# - extract_interface_inventory_with_context(): Full extraction with app metadata
#
# Both return a validated InterfaceInventory Pydantic model.

def extract_interface_inventory(
    image_path: str = None,
    image_base64: str = None,
    filename: str = None,
) -> InterfaceInventory:
    """
    Extract interface inventory from screenshot (no app context).
    
    For context-aware extraction, use extract_interface_inventory_with_context().
    """
    return extract_interface_inventory_with_context(
        image_path=image_path,
        image_base64=image_base64,
        filename=filename,
        app_name=None,
        app_description=None
    )


def extract_interface_inventory_with_context(
    image_path: str = None,
    image_base64: str = None,
    filename: str = None,
    app_name: str = None,
    app_description: str = None,
    progress_callback: callable = None,
) -> InterfaceInventory:
    """
    Extract interface inventory from screenshot with app context.
    
    Args:
        image_path: Path to image file
        image_base64: Base64 encoded image
        filename: Source filename
        app_name: Application name/domain (e.g., "mercury.com")
        app_description: Context paragraph describing the app's purpose
    
    Returns:
        Validated InterfaceInventory with per-element confidence.
    """
    if image_path:
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")
        filename = filename or Path(image_path).name
    elif not image_base64:
        raise ValueError("Provide image_path or image_base64")
    
    filename = filename or "unknown.png"
    
    initial_state: GraphState = {
        "image_base64": image_base64,
        "source_filename": filename,
        "app_name": app_name,
        "app_description": app_description,
        "classification": None,
        "intent": None,
        "has_top_bar": None,
        "has_left_pane": None,
        "classification_observed": None,
        "top_bar_hint": None,
        "left_pane_hint": None,
        "content_area_hint": None,
        "top_bar_elements": None,
        "left_pane_elements": None,
        "content_area_elements": None,
        "final_json": None,
        "confidence": None,
        "validation_notes": None,
        "page_insights": None,
        "reasoning_notes": None,
        "refined_intent": None,
        "errors": [],
        "timings": {},
    }
    
    # Store progress callback in state for passes to use
    initial_state["progress_callback"] = progress_callback
    
    start = time.time()
    final_state = _compiled_graph.invoke(initial_state)
    final_state["timings"]["total_ms"] = int((time.time() - start) * 1000)
    
    if final_state["errors"]:
        print(f"Warnings: {final_state['errors']}", file=sys.stderr)
    
    if final_state["final_json"]:
        final_state["final_json"]["version"] = "2.2.0"
        final_state["final_json"]["extracted_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        # Add app context to output if provided
        if app_name or app_description:
            final_state["final_json"]["app_context"] = {
                "name": app_name,
                "description": app_description
            }
        
        try:
            inventory = InterfaceInventory(**final_state["final_json"])
            
            # Log confidence stats
            stats = get_element_confidence_stats(inventory)
            print(f"Element confidence: min={stats['min']:.2f}, avg={stats['avg']:.2f}, max={stats['max']:.2f}", file=sys.stderr)
            
            low_conf = get_low_confidence_elements(inventory, threshold=0.7)
            if low_conf:
                print(f"Low confidence elements: {len(low_conf)}", file=sys.stderr)
            
            return inventory
            
        except ValidationError as e:
            raise RuntimeError(f"Schema validation failed: {e}")
    else:
        raise RuntimeError(f"Pipeline failed: {final_state['errors']}")


def extract_batch(image_paths: List[str]) -> List[InterfaceInventory]:
    """Extract from multiple screenshots."""
    results = []
    for i, path in enumerate(image_paths):
        print(f"[{i+1}/{len(image_paths)}] {path}")
        try:
            inventory = extract_interface_inventory(image_path=path)
            results.append(inventory)
        except Exception as e:
            print(f"  Error: {e}")
            results.append(None)
    return results


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <image> [output.json]")
        sys.exit(1)
    
    image = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Extracting: {image}")
    inventory = extract_interface_inventory(image_path=image)
    
    result = inventory.model_dump_json(indent=2)
    
    if output:
        Path(output).write_text(result)
        print(f"Saved: {output}")
    else:
        print(result)
    
    print(f"\nConfidence: {inventory.confidence}")
