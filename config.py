"""
Interface Inventory System - Configuration
Version: 2.0.0
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import yaml

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")


@dataclass
class GroqConfig:
    """Groq API configuration."""
    api_key: str = field(default_factory=lambda: os.environ.get("GROQ_API_KEY", ""))

    # Groq vision models (Llama 4)
    model_fast: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    model_quality: str = "meta-llama/llama-4-maverick-17b-128e-instruct"

    pass_1_model: str = None
    pass_2_model: str = None
    pass_3_model: str = None
    pass_4_model: str = None
    pass_5_model: str = "llama-3.3-70b-versatile"  # Reasoning model (text-only)

    # Per-pass max_tokens (optimized for each pass's output size)
    max_tokens: int = 4096  # Default fallback
    pass_1_max_tokens: int = 512   # Classification is simple
    pass_2_max_tokens: int = 1024  # Zone hints need detail for complex layouts
    pass_3_max_tokens: int = 4096  # Element extraction needs MORE for dense dashboards
    pass_4_max_tokens: int = 4096  # Validation assembly for full inventory
    pass_5_max_tokens: int = 2048  # Reasoning refinement

    temperature: float = 0.1
    reasoning_temperature: float = 0.6  # Higher temp for reasoning

    def __post_init__(self):
        self.pass_1_model = self.pass_1_model or self.model_fast
        self.pass_2_model = self.pass_2_model or self.model_fast
        self.pass_3_model = self.pass_3_model or self.model_quality
        self.pass_4_model = self.pass_4_model or self.model_quality


@dataclass
class OpenRouterConfig:
    """OpenRouter API configuration for Qwen2.5-VL."""
    api_key: str = field(default_factory=lambda: os.environ.get("OPENROUTER_API_KEY", ""))
    base_url: str = "https://openrouter.ai/api/v1"
    
    # Qwen2.5-VL-72B (best value, most reliable JSON output)
    vision_model: str = "qwen/qwen2.5-vl-72b-instruct"
    reasoning_model: str = "qwen/qwen2.5-72b-instruct"  # Text-only for Pass 5
    
    # Per-pass max_tokens
    max_tokens: int = 4096
    pass_1_max_tokens: int = 512
    pass_2_max_tokens: int = 1024
    pass_3_max_tokens: int = 4096
    pass_4_max_tokens: int = 4096
    pass_5_max_tokens: int = 2048
    
    temperature: float = 0.1
    reasoning_temperature: float = 0.6


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_retries: int = 3
    retry_delay_ms: int = 1000
    backoff_multiplier: float = 2.0


@dataclass
class RenderConfig:
    """Renderer configuration."""
    width: int = 1200
    height: int = 800
    
    background_color: str = "#E5E5E5"
    element_color: str = "#9E9E9E"
    element_stroke: str = "#757575"
    label_color: str = "#333333"
    
    label_font: str = "monospace"
    label_size: int = 10
    
    zone_padding: int = 16
    element_gap: int = 8
    border_radius: int = 4
    
    top_bar_height: int = 56
    left_pane_ratio: float = 0.333


@dataclass
class ConfidenceConfig:
    """Confidence thresholds."""
    high: float = 0.9
    medium: float = 0.7
    low: float = 0.5
    
    # Generate alternative renders below this threshold
    alternative_threshold: float = 0.8


@dataclass  
class PipelineConfig:
    """Complete pipeline configuration."""
    # Provider selection: "openrouter" or "groq"
    provider: str = "openrouter"
    
    groq: GroqConfig = field(default_factory=GroqConfig)
    openrouter: OpenRouterConfig = field(default_factory=OpenRouterConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    render: RenderConfig = field(default_factory=RenderConfig)
    confidence: ConfidenceConfig = field(default_factory=ConfidenceConfig)
    
    config_dir: Path = field(default_factory=lambda: Path(__file__).parent)
    output_dir: Path = field(default_factory=lambda: Path("./output"))
    
    schema_version: str = "2.2.0"
    
    @property
    def prompts_dir(self) -> Path:
        # Prompts are in the prompts/ subdirectory
        return self.config_dir / "prompts"

    @property
    def vocabulary_path(self) -> Path:
        return self.config_dir / "config" / "vocabulary.yaml"
    
    @classmethod
    def from_yaml(cls, path: Path) -> "PipelineConfig":
        """Load from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        
        config = cls()
        
        if "groq" in data:
            for k, v in data["groq"].items():
                if hasattr(config.groq, k):
                    setattr(config.groq, k, v)
        
        if "retry" in data:
            for k, v in data["retry"].items():
                if hasattr(config.retry, k):
                    setattr(config.retry, k, v)
        
        if "render" in data:
            for k, v in data["render"].items():
                if hasattr(config.render, k):
                    setattr(config.render, k, v)
        
        if "confidence" in data:
            for k, v in data["confidence"].items():
                if hasattr(config.confidence, k):
                    setattr(config.confidence, k, v)
        
        return config
    
    def to_yaml(self, path: Path):
        """Save to YAML file."""
        data = {
            "groq": {
                "model_fast": self.groq.model_fast,
                "model_quality": self.groq.model_quality,
                "pass_1_model": self.groq.pass_1_model,
                "pass_2_model": self.groq.pass_2_model,
                "pass_3_model": self.groq.pass_3_model,
                "pass_4_model": self.groq.pass_4_model,
                "max_tokens": self.groq.max_tokens,
                "temperature": self.groq.temperature,
            },
            "retry": {
                "max_retries": self.retry.max_retries,
                "retry_delay_ms": self.retry.retry_delay_ms,
                "backoff_multiplier": self.retry.backoff_multiplier,
            },
            "render": {
                "width": self.render.width,
                "height": self.render.height,
                "background_color": self.render.background_color,
                "element_color": self.render.element_color,
                "label_font": self.render.label_font,
                "label_size": self.render.label_size,
            },
            "confidence": {
                "high": self.confidence.high,
                "medium": self.confidence.medium,
                "low": self.confidence.low,
                "alternative_threshold": self.confidence.alternative_threshold,
            },
        }
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)


# Global config
_config: Optional[PipelineConfig] = None


def get_config() -> PipelineConfig:
    global _config
    if _config is None:
        _config = PipelineConfig()
    return _config


def set_config(config: PipelineConfig):
    global _config
    _config = config


def load_config(path: Path) -> PipelineConfig:
    config = PipelineConfig.from_yaml(path)
    set_config(config)
    return config
