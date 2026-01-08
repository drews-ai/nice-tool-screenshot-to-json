#!/usr/bin/env python3
"""
Interface Inventory - Extraction Entry Point

================================================================================
PROCESS FLOW
================================================================================

This script is the CLI/stdin interface to the extraction pipeline.
It's called by server.js for web UI requests.

    [server.js]
         |
         | spawns process, pipes JSON to stdin
         v
    [extract.py]
         |
         | parses input, calls pipeline
         v
    [pipeline.py]
         |
         | 5-pass LLM extraction
         v
    [InterfaceInventory JSON]
         |
         | written to stdout
         v
    [server.js reads and returns to browser]

INPUT (JSON via stdin):
{
  "image_base64": "...",              // Base64 encoded screenshot (REQUIRED)
  "filename": "screenshot.png",       // Original filename for metadata
  "app_name": "mercury.com",          // App context helps LLM understand domain
  "app_description": "Banking for...", // Detailed app description
  "sequence": 1,                       // For multi-frame state sequences
  "total_frames": 2                    // Total frames in sequence
}

OUTPUT (JSON via stdout):
{
  "screen": {"classification": "application", "intent": "..."},
  "zones": {"top_bar": [...], "left_pane": [...], "content_area": [...]},
  "confidence": 0.92,
  "page_insights": {...},
  "timing_ms": 8500
}

PROGRESS EVENTS (via stderr):
  PROGRESS:{"type":"progress","pass":"Pass 1: Classification","status":"running"}
  These are parsed by server.js for SSE streaming to the browser.

================================================================================
"""

import sys
import json
import time
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from pipeline import extract_interface_inventory_with_context




def main():
    # Read input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON input: {e}"}), file=sys.stdout)
        sys.exit(1)
    
    # Extract fields
    image_base64 = input_data.get("image_base64")
    filename = input_data.get("filename", "screenshot.png")
    app_name = input_data.get("app_name")
    app_description = input_data.get("app_description")
    sequence = input_data.get("sequence", 1)
    total_frames = input_data.get("total_frames", 1)
    
    if not image_base64:
        print(json.dumps({"error": "image_base64 is required"}), file=sys.stdout)
        sys.exit(1)
    
    # Log to stderr (visible in server console)
    print(f"  App: {app_name or 'Not specified'}", file=sys.stderr)
    print(f"  File: {filename}", file=sys.stderr)
    if total_frames > 1:
        print(f"  Frame: {sequence}/{total_frames}", file=sys.stderr)
    
    start_time = time.time()
    
    try:
        # Progress callback - outputs JSON progress events to stderr
        def progress_callback(pass_name, status):
            progress = {
                "type": "progress",
                "pass": pass_name,
                "status": status,
                "elapsed_ms": int((time.time() - start_time) * 1000)
            }
            print(f"PROGRESS:{json.dumps(progress)}", file=sys.stderr, flush=True)
        
        # Run extraction with context
        inventory = extract_interface_inventory_with_context(
            image_base64=image_base64,
            filename=filename,
            app_name=app_name,
            app_description=app_description,
            progress_callback=progress_callback
        )
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        print(f"  Completed in {elapsed_ms}ms", file=sys.stderr)
        print(f"  Confidence: {inventory.confidence:.0%}", file=sys.stderr)
        
        # Output result (exclude nulls for cleaner JSON)
        result = inventory.model_dump(exclude_none=True)
        result["timing_ms"] = elapsed_ms
        
        print(json.dumps(result), file=sys.stdout)
        
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
        print(json.dumps({"error": str(e)}), file=sys.stdout)
        sys.exit(1)


if __name__ == "__main__":
    main()
