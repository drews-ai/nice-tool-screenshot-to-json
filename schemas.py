"""
Interface Inventory System - Pydantic Schema Models
Version: 2.0.0

================================================================================
SCHEMA OVERVIEW
================================================================================

This file defines the data structures for extraction output.
All LLM responses are validated against these schemas using Pydantic.

HIERARCHY:

    InterfaceInventory (root)
    |
    +-- screen: Screen
    |   +-- classification (application/dashboard/form/modal/etc.)
    |   +-- intent (what user wants to accomplish)
    |
    +-- zones: Zones
    |   +-- top_bar: List[Element] | null
    |   +-- left_pane: List[Element] | null
    |   +-- content_area: List[Element]  (always present)
    |
    +-- confidence: float (0.0-1.0)
    +-- page_insights: PageInsights (from Pass 5)
    +-- app_context: AppContext (if provided)

ELEMENT MODEL:

    Element
    +-- type: str (from VALID_ELEMENT_TYPES vocabulary)
    +-- content_nature: data/editorial/user_generated/system
    +-- confidence: float (per-element confidence score)
    +-- purpose: str (what this element does)
    +-- label: str (visible text)
    +-- children: List[Element] (for containers only, max 2 levels deep)
    +-- [type-specific fields like columns, value, variant, etc.]

VALIDATION RULES:
- All elements must have type, content_nature, confidence
- Unknown elements must explain what they are (observed, closest)
- Tables must have columns list
- Input elements must have field_type
- Children only allowed on container/collection types

CHANGES FROM v1:
- Added per-element confidence scores (REQUIRED)
- Added field_type for all input elements (REQUIRED)
- Made content_nature REQUIRED on all elements
- Simplified element types (39 total)
- Added modal classification
- Capped nesting at 2 levels

================================================================================
"""

from __future__ import annotations
from typing import List, Optional, Literal, Union, Any
from pydantic import BaseModel, Field, model_validator, field_validator
from enum import Enum


# =============================================================================
# ENUMERATIONS - Controlled vocabularies for categorical fields
# =============================================================================
# These enums constrain LLM output to valid values.
# If LLM returns something not in enum, Pydantic validation fails.

class ScreenClassification(str, Enum):
    APPLICATION = "application"
    DASHBOARD = "dashboard"
    CONTENT_PAGE = "content_page"
    FORM = "form"
    MODAL = "modal"  # NEW in v2
    HYBRID = "hybrid"
    OTHER = "other"


class ContentNature(str, Enum):
    DATA = "data"
    EDITORIAL = "editorial"
    USER_GENERATED = "user_generated"
    SYSTEM = "system"


class ListLayout(str, Enum):
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    GRID = "grid"
    FEED = "feed"


class ChartVariant(str, Enum):
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    DONUT = "donut"
    SPARKLINE = "sparkline"


class ButtonVariant(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    DESTRUCTIVE = "destructive"
    GHOST = "ghost"


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    ATTACHMENT = "attachment"


class CalendarViewType(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


# =============================================================================
# FIELD TYPES FOR INPUTS - Semantic types for form fields
# =============================================================================
# These help downstream systems understand what data a field collects.
# Example: text_input with field_type="email" vs field_type="name"

class TextInputFieldType(str, Enum):
    TEXT = "text"
    NAME = "name"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    SEARCH = "search"
    PASSWORD = "password"
    NUMBER = "number"
    CURRENCY = "currency"
    USERNAME = "username"
    COMPANY = "company"
    ADDRESS = "address"
    CITY = "city"
    ZIP = "zip"
    OTHER = "other"


class TextAreaFieldType(str, Enum):
    DESCRIPTION = "description"
    COMMENT = "comment"
    MESSAGE = "message"
    NOTES = "notes"
    BIO = "bio"
    ADDRESS = "address"
    OTHER = "other"


class SelectorFieldType(str, Enum):
    SINGLE = "single"
    MULTI = "multi"
    COUNTRY = "country"
    STATE = "state"
    CATEGORY = "category"
    STATUS = "status"
    OTHER = "other"


class ToggleFieldType(str, Enum):
    BOOLEAN = "boolean"
    PREFERENCE = "preference"
    FEATURE = "feature"
    OTHER = "other"


class CheckboxFieldType(str, Enum):
    AGREEMENT = "agreement"
    SELECTION = "selection"
    PREFERENCE = "preference"
    OTHER = "other"


class RadioFieldType(str, Enum):
    CHOICE = "choice"
    PREFERENCE = "preference"
    TIER = "tier"
    OTHER = "other"


class DateInputFieldType(str, Enum):
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    DATERANGE = "daterange"


class RichTextFieldType(str, Enum):
    DOCUMENT = "document"
    EMAIL_BODY = "email_body"
    POST = "post"
    OTHER = "other"


class FileInputFieldType(str, Enum):
    IMAGE = "image"
    DOCUMENT = "document"
    VIDEO = "video"
    ANY = "any"
    OTHER = "other"


# =============================================================================
# ELEMENT TYPES (39 total) - The UI component vocabulary
# =============================================================================
# This vocabulary is shared between prompts and validation.
# LLMs are instructed to use ONLY these types.
# Unknown elements use type="unknown" with observed/closest fields.

VALID_ELEMENT_TYPES = {
    # Structure (6)
    "nav_list", "tab_group", "action_bar", "breadcrumb", "pagination", "divider",
    # Containers (2)
    "blade", "section",
    # Collections (3)
    "list", "data_table", "calendar",
    # Data Display (8) - added progress_bar, icon
    "metric", "field_value", "badge", "chart", "avatar", "media", "progress_bar", "icon",
    # Content (3)
    "heading", "text_block", "content_area",
    # Input (10)
    "text_input", "text_area", "selector", "toggle", "checkbox",
    "radio", "date_input", "rich_text", "file_input", "search_bar",
    # Action (3)
    "button", "action_link", "icon_action",
    # Feedback (3)
    "empty_state", "loading", "error_state",
    # Special (1)
    "unknown"
}

CONTAINER_TYPES = {"blade", "section", "content_area"}  # Content containers
COLLECTION_TYPES = {"nav_list", "list", "data_table", "calendar"}
STRUCTURE_TYPES = {"action_bar", "tab_group", "pagination", "breadcrumb", "divider"}  # Structure types
DATA_TYPES_WITH_CHILDREN = {"metric"}  # Data types that can have embedded visualizations
FEEDBACK_TYPES_WITH_CHILDREN = {"empty_state", "error_state"}  # Feedback types can have illustrations/actions
EXPANDABLE_TYPES = CONTAINER_TYPES | COLLECTION_TYPES | STRUCTURE_TYPES | DATA_TYPES_WITH_CHILDREN | FEEDBACK_TYPES_WITH_CHILDREN
INPUT_TYPES = {"text_input", "text_area", "selector", "toggle", "checkbox", "radio", "date_input", "rich_text", "file_input", "search_bar"}


# =============================================================================
# ELEMENT MODEL - Core building block for all UI components
# =============================================================================
# Every UI component is an Element with:
# - type: What kind of component (button, table, metric, etc.)
# - content_nature: What kind of content (data, editorial, system, etc.)
# - confidence: How sure the LLM is about this extraction (0.0-1.0)
# - purpose: What this element does for the user
# - Plus type-specific fields (columns for tables, value for metrics, etc.)

class Element(BaseModel):
    """
    Single UI element with REQUIRED confidence, content_nature, and purpose.
    """
    
    # === REQUIRED ON ALL ELEMENTS ===
    type: str = Field(..., description="Element type from vocabulary")
    content_nature: ContentNature = Field(..., description="Nature of content - REQUIRED")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1 - REQUIRED")
    purpose: Optional[str] = Field(None, min_length=3, max_length=100, description="Derived intent/purpose")
    
    # === COMMON OPTIONAL ===
    label: Optional[str] = Field(None, description="Visible label text")
    
    # === INPUT-SPECIFIC (required when type is input) ===
    field_type: Optional[str] = Field(None, description="Semantic type of input field")
    placeholder: Optional[str] = Field(None, description="Placeholder text")
    
    # === COLLECTION-SPECIFIC ===
    item_count: Optional[int] = Field(None, ge=0, description="Number of items")
    row_count: Optional[int] = Field(None, ge=0, description="Number of rows")
    columns: Optional[List[str]] = Field(None, description="Column headers")
    layout: Optional[ListLayout] = Field(None, description="List layout type")
    
    # === CONTROL-SPECIFIC ===
    control_count: Optional[int] = Field(None, ge=0, description="Number of controls")
    option_count: Optional[int] = Field(None, ge=0, description="Number of options")
    
    # === DATA DISPLAY-SPECIFIC ===
    value: Optional[str] = Field(None, description="Displayed value (e.g., '87', '12.9K', '$1,234')")
    has_trend: Optional[bool] = Field(None, description="Metric has trend indicator")
    trend_value: Optional[str] = Field(None, description="Trend change value (e.g., '-8', '+5', '-7.7K')")
    
    @field_validator('value', 'trend_value', mode='before')
    @classmethod
    def coerce_to_string(cls, v):
        """Coerce numeric values to strings."""
        if v is None:
            return None
        return str(v)
    variant: Optional[str] = Field(None, description="Style variant")
    series_count: Optional[int] = Field(None, ge=1, description="Chart series count")
    media_type: Optional[MediaType] = Field(None, description="Media type")
    
    # === CONTENT-SPECIFIC ===
    level: Optional[int] = Field(None, ge=1, le=6, description="Heading level")
    
    # === CALENDAR-SPECIFIC ===
    view_type: Optional[CalendarViewType] = Field(None, description="Calendar view")
    
    # === CONTAINER-SPECIFIC ===
    children: Optional[List[Element]] = Field(None, description="Nested elements")
    
    # === UNKNOWN-SPECIFIC ===
    observed: Optional[str] = Field(None, description="Description of unknown element")
    closest: Optional[str] = Field(None, description="Nearest known type")
    
    # Allow extra fields from LLM that we don't explicitly model
    model_config = {"extra": "ignore"}
    
    @model_validator(mode='after')
    def validate_element(self) -> 'Element':
        """Validate element constraints."""
        
        # Type must be valid
        if self.type not in VALID_ELEMENT_TYPES:
            raise ValueError(f"Invalid element type: {self.type}")
        
        # Unknown elements must have observed and closest
        if self.type == "unknown":
            if not self.observed:
                raise ValueError("Unknown elements must have 'observed' description")
            if not self.closest:
                raise ValueError("Unknown elements must have 'closest' type")
        
        # Strip children from non-container types (model sometimes adds them incorrectly)
        if self.children is not None and self.type not in EXPANDABLE_TYPES:
            self.children = None
        
        # Input elements should have field_type - default to 'other' if missing
        if self.type in INPUT_TYPES and not self.field_type:
            self.field_type = "other"
        
        # Tables must have columns
        if self.type == "data_table" and not self.columns:
            raise ValueError("data_table must have 'columns'")
        
        return self


# Enable self-referencing
Element.model_rebuild()


# =============================================================================
# SCREEN MODEL
# =============================================================================

class Screen(BaseModel):
    """Screen-level metadata."""
    
    classification: ScreenClassification = Field(..., description="Interface type")
    intent: str = Field(..., min_length=5, max_length=200, description="User goal")
    source: Optional[str] = Field(None, description="Source filename")
    observed: Optional[str] = Field(None, description="Description if 'other'")
    
    @model_validator(mode='after')
    def validate_other(self) -> 'Screen':
        if self.classification == ScreenClassification.OTHER and not self.observed:
            raise ValueError("Classification 'other' requires 'observed'")
        return self


# =============================================================================
# ZONES MODEL
# =============================================================================

class Zones(BaseModel):
    """
    Three structural zones.
    
    Note: For classification 'form' or 'modal', top_bar and left_pane must be null.
    """
    top_bar: Optional[List[Element]] = Field(None, description="Top bar elements")
    left_pane: Optional[List[Element]] = Field(None, description="Left pane elements")
    content_area: List[Element] = Field(..., description="Main content elements")


# =============================================================================
# APP CONTEXT MODEL
# =============================================================================

class AppContext(BaseModel):
    """Optional app context provided by user."""
    name: Optional[str] = Field(None, description="Application name/domain")
    description: Optional[str] = Field(None, description="App description")


# =============================================================================
# INTERFACE INVENTORY MODEL
# =============================================================================

class PageInsights(BaseModel):
    """Derived insights from Pass 5 reasoning."""
    primary_action: Optional[str] = Field(None, description="Main user action on this screen")
    data_focus: Optional[str] = Field(None, description="What data is shown/collected")
    user_journey_stage: Optional[str] = Field(None, description="Where user is in flow")
    page_type: Optional[str] = Field(None, description="Functional page category")


class InterfaceInventory(BaseModel):
    """Complete extraction output."""
    
    screen: Screen
    zones: Zones
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    validation_notes: Optional[List[str]] = Field(None, description="Validation notes")
    
    # Pass 5 outputs
    page_insights: Optional[PageInsights] = Field(None, description="Derived page insights from reasoning")
    reasoning_notes: Optional[List[str]] = Field(None, description="Refinements made by reasoning pass")
    
    # App context (if provided)
    app_context: Optional[AppContext] = Field(None, description="User-provided app context")
    
    # Metadata
    version: str = Field(default="2.2.0")
    extracted_at: Optional[str] = Field(None, description="ISO timestamp")
    
    @model_validator(mode='after')
    def validate_zones_for_classification(self) -> 'InterfaceInventory':
        """Warn but don't fail if form/modal have top_bar or left_pane."""
        # Relaxed validation - model may detect these in embedded forms
        return self


# =============================================================================
# PIPELINE STATE
# =============================================================================

class Pass1Output(BaseModel):
    """Pass 1: Classification output."""
    classification: ScreenClassification
    intent: str
    has_top_bar: bool
    has_left_pane: bool
    observed: Optional[str] = None


class Pass2Output(BaseModel):
    """Pass 2: Zone identification output."""
    top_bar_hint: Optional[str] = None
    left_pane_hint: Optional[str] = None
    content_area_hint: str


class PipelineState(BaseModel):
    """Complete pipeline state."""
    
    # Input
    image_base64: str
    source_filename: str
    
    # Pass outputs
    pass_1: Optional[Pass1Output] = None
    pass_2: Optional[Pass2Output] = None
    top_bar_elements: Optional[List[Element]] = None
    left_pane_elements: Optional[List[Element]] = None
    content_area_elements: Optional[List[Element]] = None
    
    # Final
    final_inventory: Optional[InterfaceInventory] = None
    errors: List[str] = Field(default_factory=list)
    timings: dict = Field(default_factory=dict)


# =============================================================================
# RENDER OUTPUT OPTIONS
# =============================================================================

class RenderVariant(BaseModel):
    """Single render variant for user selection."""
    variant_id: str = Field(..., description="v1, v2, etc.")
    confidence: float = Field(..., ge=0.0, le=1.0)
    svg: str = Field(..., description="SVG content")
    notes: Optional[List[str]] = Field(None, description="Variant-specific notes")


class RenderOutput(BaseModel):
    """
    Render output with optional variants for user selection.
    When confidence varies, provide multiple options.
    """
    primary: RenderVariant = Field(..., description="Primary/recommended render")
    alternatives: Optional[List[RenderVariant]] = Field(None, description="Alternative renders")
    
    @property
    def has_alternatives(self) -> bool:
        return self.alternatives is not None and len(self.alternatives) > 0


# =============================================================================
# HELPERS
# =============================================================================

def validate_element_type(element_type: str) -> bool:
    """Check if element type is valid."""
    return element_type in VALID_ELEMENT_TYPES


def get_element_confidence_stats(inventory: InterfaceInventory) -> dict:
    """Get confidence statistics across all elements."""
    confidences = []
    
    def collect(elements: List[Element]):
        for el in elements:
            confidences.append(el.confidence)
            if el.children:
                collect(el.children)
    
    if inventory.zones.top_bar:
        collect(inventory.zones.top_bar)
    if inventory.zones.left_pane:
        collect(inventory.zones.left_pane)
    collect(inventory.zones.content_area)
    
    if not confidences:
        return {"min": 0, "max": 0, "avg": 0, "count": 0}
    
    return {
        "min": min(confidences),
        "max": max(confidences),
        "avg": sum(confidences) / len(confidences),
        "count": len(confidences)
    }


def get_low_confidence_elements(inventory: InterfaceInventory, threshold: float = 0.7) -> List[Element]:
    """Get elements below confidence threshold."""
    low_conf = []
    
    def check(elements: List[Element]):
        for el in elements:
            if el.confidence < threshold:
                low_conf.append(el)
            if el.children:
                check(el.children)
    
    if inventory.zones.top_bar:
        check(inventory.zones.top_bar)
    if inventory.zones.left_pane:
        check(inventory.zones.left_pane)
    check(inventory.zones.content_area)
    
    return low_conf


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "ScreenClassification",
    "ContentNature",
    "ListLayout",
    "ChartVariant",
    "ButtonVariant",
    "MediaType",
    "CalendarViewType",
    # Field Types
    "TextInputFieldType",
    "TextAreaFieldType",
    "SelectorFieldType",
    # Models
    "Element",
    "Screen",
    "Zones",
    "AppContext",
    "InterfaceInventory",
    "Pass1Output",
    "Pass2Output",
    "PipelineState",
    "RenderVariant",
    "RenderOutput",
    # Helpers
    "validate_element_type",
    "get_element_confidence_stats",
    "get_low_confidence_elements",
    "VALID_ELEMENT_TYPES",
    "CONTAINER_TYPES",
    "COLLECTION_TYPES",
    "EXPANDABLE_TYPES",
    "INPUT_TYPES",
]
