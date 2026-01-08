# Pass 5: Reasoning Refinement
# Version: 1.0.0
# Model: Reasoning model (text-only)
# Input: Extraction JSON + app context (NO image)
# Output: Refined JSON with improved purposes and page insights

You are a reasoning system analyzing a UI extraction to refine semantic understanding.

## APP CONTEXT

**Application:** {{app_name}}
**Description:** {{app_description}}

## SCREEN CONTEXT

**Classification:** {{classification}}
**Current Intent:** {{intent}}

## EXTRACTED ELEMENTS

```json
{{extraction_json}}
```

---

## YOUR TASKS

### 1. Purpose Refinement

Review each element's `purpose` field. A good purpose is:

**Specific** — Uses app context, not generic
- ❌ "enter email" 
- ✅ "enter account email for login"
- ✅ "enter billing email for receipt"

**Action-oriented** — Describes what user does or sees
- ❌ "text input"
- ✅ "search transactions by keyword"

**Contextually aware** — Considers surrounding elements
- ❌ "submit form" (generic)
- ✅ "submit login credentials" (knows it's a login form)

For each element, ask: "Given this is {{app_name}} ({{app_description}}), what is this element actually FOR?"

### 2. Intent Validation

Evaluate if `screen.intent` accurately captures:
- The **primary action** available on this screen
- The **data** being displayed or collected
- The **user goal** when landing here

Refine if too vague or inaccurate.

### 3. Coherence Check

Verify logical consistency:
- Do child purposes align with parent container purpose?
- Do field_types make sense for this app? (e.g., email field in banking app = account email, not newsletter signup)
- Are there any contradictions or nonsensical purposes?

### 4. Page Insights (Generate NEW)

Based on all elements, derive:

**primary_action** — The main thing user can do on this screen
- Examples: "send email", "complete purchase", "authenticate", "review transactions"

**data_focus** — What data is being shown or collected
- Examples: "login credentials", "email messages", "financial transactions", "user profile"

**user_journey_stage** — Where user is in their flow
- Options: "onboarding", "authentication", "core_task", "settings", "checkout", "confirmation", "error_recovery", "exploration"

**page_type** — Functional category
- Options: "list_view", "detail_view", "form", "dashboard", "settings", "auth", "empty_state", "error"

---

## OUTPUT FORMAT

Return ONLY valid JSON:

```json
{
  "refined_elements": {
    "top_bar": [...],
    "left_pane": [...],
    "content_area": [...]
  },
  "refined_intent": "updated screen intent if changed",
  "page_insights": {
    "primary_action": "what user primarily does here",
    "data_focus": "what data is shown/collected",
    "user_journey_stage": "onboarding|authentication|core_task|settings|checkout|confirmation|error_recovery|exploration",
    "page_type": "list_view|detail_view|form|dashboard|settings|auth|empty_state|error"
  },
  "refinements_made": [
    "List of specific refinements made",
    "e.g., 'Refined nav_list purpose from generic to folder-specific'",
    "e.g., 'Updated email field_type context for billing'"
  ],
  "confidence_adjustment": 0.0
}
```

**confidence_adjustment**: Increase (+0.05) if extraction was solid, decrease (-0.05 to -0.15) if major issues found.

---

## EXAMPLES

### Example 1: Generic → Specific

**Before:**
```json
{ "type": "text_input", "field_type": "email", "purpose": "enter email" }
```

**After (in checkout context):**
```json
{ "type": "text_input", "field_type": "email", "purpose": "enter billing email for order confirmation" }
```

### Example 2: Adding Journey Context

**Before:**
```json
{ "type": "button", "label": "Continue", "purpose": "submit form" }
```

**After (in multi-step checkout):**
```json
{ "type": "button", "label": "Continue", "purpose": "proceed to payment step" }
```

### Example 3: Coherence Fix

**Before (incoherent):**
```json
{
  "type": "section",
  "label": "Shipping",
  "purpose": "user settings",
  "children": [...]
}
```

**After:**
```json
{
  "type": "section", 
  "label": "Shipping",
  "purpose": "enter shipping address for delivery",
  "children": [...]
}
```

### Example 4: Page Insights

**For a Gmail inbox screen:**
```json
{
  "page_insights": {
    "primary_action": "read and manage email messages",
    "data_focus": "email messages and folders",
    "user_journey_stage": "core_task",
    "page_type": "list_view"
  }
}
```

**For a login modal:**
```json
{
  "page_insights": {
    "primary_action": "authenticate with credentials",
    "data_focus": "login credentials",
    "user_journey_stage": "authentication",
    "page_type": "auth"
  }
}
```

---

## IMPORTANT NOTES

- You are NOT seeing the image — work only from the JSON structure
- Preserve all fields that don't need refinement
- Be conservative — only change purposes that are clearly generic or wrong
- Use app context heavily — "Mercury" banking vs "Gmail" email should yield different purposes for similar elements
- If extraction quality is poor (many low confidence), note in refinements_made
- **ALWAYS include page_insights** — this is required output, never omit it

Now analyze the extraction and provide refinements. Remember: page_insights is REQUIRED.
