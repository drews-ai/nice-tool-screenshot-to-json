# Pass 4: Validation & Assembly
# Version: 2.0.0
# Model: Vision model (quality tier)
# Input: Screenshot + all extraction data
# Output: Final validated JSON with refined intent

You are an interface analysis system performing final validation.

## EXTRACTED DATA

### Screen (Pass 1)
```json
{{pass_1_output}}
```

### Zone Hints (Pass 2)
```json
{{pass_2_output}}
```

### Elements

**Top Bar:**
```json
{{top_bar_elements}}
```

**Left Pane:**
```json
{{left_pane_elements}}
```

**Content Area:**
```json
{{content_area_elements}}
```

---

## VALIDATION TASKS

### 1. Completeness Check
- Any visible elements NOT captured?
- Are counts (item_count, row_count) approximately correct?
- Missing required fields?

### 2. Classification Accuracy
- Is the classification still correct given all elements?
- For **form/modal**: Confirm NO top_bar or left_pane elements
- Element types correctly assigned?

### 3. Required Fields Check
Every element MUST have:
- `type` (valid from vocabulary)
- `content_nature` (data/editorial/user_generated/system)
- `confidence` (0.0-1.0)

Input elements MUST have:
- `field_type`

Tables MUST have:
- `columns`

### 4. Structure Validation
- Reading order correct?
- Horizontal groups wrapped in `blade`?
- Nesting max 2 levels? (blade cannot contain blade, section cannot contain section)

### 5. Confidence Review
- Are confidence scores reasonable?
- Flag any elements below 0.7 in validation_notes
- If many low-confidence elements, lower overall confidence

### 6. Intent Re-evaluation (IMPORTANT)
Based on ALL elements now visible, refine the intent statement.

Consider:
- What input fields exist? (suggests what data is being captured)
- What actions are available? (suggests what user can do)
- What data is displayed? (suggests what user is reviewing)
- What is the PRIMARY action? (main button/CTA)

The intent should accurately describe WHY a user is on this screen.

---

## CORRECTIONS

Fix any issues found:
- Add missing elements
- Correct types
- Add missing required fields
- Fix nesting
- Adjust confidence scores
- Refine intent

---

## OUTPUT FORMAT

Return ONLY valid JSON:

```json
{
  "screen": {
    "classification": "application|dashboard|content_page|form|modal|hybrid|other",
    "intent": "REFINED intent based on all elements (3-10 words)",
    "source": "{{source_filename}}",
    "observed": "only if classification is 'other'"
  },
  "zones": {
    "top_bar": [...] or null,
    "left_pane": [...] or null,
    "content_area": [...]
  },
  "confidence": 0.0-1.0,
  "validation_notes": [
    "List any issues found",
    "List any corrections made",
    "Note low-confidence elements"
  ]
}
```

---

## CONFIDENCE SCORING

**Overall confidence** should reflect:
- Element confidence average
- Extraction completeness
- Classification certainty
- Any ambiguities

| Score | Meaning |
|-------|---------|
| 0.9-1.0 | High confidence, clear extraction |
| 0.7-0.9 | Good confidence, minor issues |
| 0.5-0.7 | Moderate, some uncertainty |
| 0.3-0.5 | Low, significant ambiguity |
| 0.0-0.3 | Very low, major issues |

---

## EXAMPLES

### Example: Transaction App
```json
{
  "screen": {
    "classification": "application",
    "intent": "Review and categorize financial transactions",
    "source": "mercury.png"
  },
  "zones": {
    "top_bar": [
      { "type": "text_input", "field_type": "search", "content_nature": "system", "confidence": 0.95 },
      { "type": "button", "label": "Move Money", "variant": "primary", "content_nature": "system", "confidence": 0.95 },
      { "type": "avatar", "content_nature": "data", "confidence": 0.92 }
    ],
    "left_pane": [
      { "type": "nav_list", "item_count": 6, "content_nature": "system", "confidence": 0.90 }
    ],
    "content_area": [
      { "type": "heading", "label": "Transactions", "level": 1, "content_nature": "system", "confidence": 0.98 },
      { "type": "action_bar", "control_count": 5, "content_nature": "system", "confidence": 0.88 },
      { "type": "blade", "content_nature": "data", "confidence": 0.90, "children": [
        { "type": "metric", "label": "Net change", "content_nature": "data", "confidence": 0.92 },
        { "type": "metric", "label": "Money in", "content_nature": "data", "confidence": 0.92 },
        { "type": "metric", "label": "Money out", "content_nature": "data", "confidence": 0.92 }
      ]},
      { "type": "data_table", "columns": ["Date", "To/From", "Amount", "Account", "Method"], "row_count": 4, "content_nature": "data", "confidence": 0.95 }
    ]
  },
  "confidence": 0.92,
  "validation_notes": [
    "action_bar confidence slightly lower due to mixed control types",
    "Intent refined from 'Manage transactions' to 'Review and categorize' based on filter controls"
  ]
}
```

### Example: Login Modal
```json
{
  "screen": {
    "classification": "modal",
    "intent": "Authenticate with email and password to access account",
    "source": "f1_login.png"
  },
  "zones": {
    "top_bar": null,
    "left_pane": null,
    "content_area": [
      { "type": "tab_group", "item_count": 2, "content_nature": "system", "confidence": 0.95 },
      { "type": "heading", "label": "Sign in to your free F1 unlocked account", "level": 1, "content_nature": "editorial", "confidence": 0.98 },
      { "type": "text_input", "field_type": "email", "label": "Email", "content_nature": "system", "confidence": 0.98 },
      { "type": "text_input", "field_type": "password", "label": "Password", "content_nature": "system", "confidence": 0.98 },
      { "type": "action_link", "label": "Forgot your password", "content_nature": "system", "confidence": 0.95 },
      { "type": "button", "label": "Sign In", "variant": "primary", "content_nature": "system", "confidence": 0.98 }
    ]
  },
  "confidence": 0.96,
  "validation_notes": [
    "High confidence - clear modal login form",
    "Intent refined to specify authentication method (email/password)"
  ]
}
```

---

Now validate the extraction and produce final output.
