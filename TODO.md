# TODO

## v2.3.0 - Marketing/Content Website Vocabulary Expansion

Expand element vocabulary to better support marketing websites, landing pages, and content-heavy sites.

### Proposed New Element Types

**Marketing Sections**
- `hero` - Hero section with headline, subtext, CTA
- `testimonial` - Customer quote/review block
- `pricing_table` - Pricing tiers comparison
- `feature_grid` - Feature showcase (icon + title + description)
- `social_proof` - Logos, stats, trust badges
- `faq` - FAQ accordion/list
- `cta_banner` - Call-to-action banner

**Content Elements**
- `blockquote` - Styled quote
- `code_block` - Code snippet display
- `video_embed` - Embedded video player
- `carousel` - Image/content slider
- `accordion` - Collapsible content sections
- `timeline` - Chronological display

**E-commerce**
- `product_card` - Product with image, price, CTA
- `cart_summary` - Shopping cart overview
- `review_stars` - Star rating display

### Classification Updates

Consider adding:
- `landing_page` - Marketing landing page (hero + features + CTA)
- `pricing_page` - Pricing comparison page
- `blog_post` - Article/blog content

### Implementation Steps

1. [ ] Add types to `config/vocabulary.yaml`
2. [ ] Add types to `schemas.py` VALID_ELEMENT_TYPES
3. [ ] Update `prompts/pass_3_extract.md` vocabulary table
4. [ ] Add examples to prompts for new types
5. [ ] Test with marketing website screenshots
