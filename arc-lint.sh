#!/bin/bash

# ============================================================================
# ARC Linter — Agent-Readable Content Validator
# ============================================================================
#
# HERE: Validates markdown files against agent-readability standards.
# THIS: Checks structure, size, and attention-zone compliance.
#
# Based on "Lost in the Middle" research (Liu et al., 2023)
#
# Usage:
#   ./arc-lint.sh [file.md]           # Lint single file
#   ./arc-lint.sh [directory]         # Lint all .md files in directory
#   ./arc-lint.sh                     # Lint current directory
#   ./arc-lint.sh --fix [file.md]     # Show fix suggestions
#   ./arc-lint.sh --generate-llms     # Generate llms.txt
#
# ============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Thresholds
MAX_TOKENS=4000
MAX_HEADER_WORDS=150
MAX_SECTION_WORDS=800
MAX_SENTENCE_WORDS=25
WARN_SENTENCE_WORDS=20

# Counters
TOTAL_FILES=0
PASSED_FILES=0
FAILED_FILES=0
WARNINGS=0
ERRORS=0

# ============================================================================
# Utility Functions
# ============================================================================

count_words() {
    echo "$1" | wc -w | tr -d ' '
}

count_tokens() {
    # Rough estimate: tokens ≈ words * 1.3
    local words=$(count_words "$1")
    echo $(( words * 13 / 10 ))
}

print_pass() {
    echo -e "  ${GREEN}✓${NC} $1"
}

print_fail() {
    echo -e "  ${RED}✗${NC} $1"
    ((ERRORS++)) || true
}

print_warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
    ((WARNINGS++)) || true
}

print_info() {
    echo -e "  ${BLUE}ℹ${NC} $1"
}

# ============================================================================
# Lint Checks
# ============================================================================

check_header_block() {
    local file="$1"
    local content="$2"
    
    # Check for H1 title
    if ! echo "$content" | head -20 | grep -q "^# "; then
        print_fail "Missing H1 title in first 20 lines"
        return 1
    fi
    
    # Check for blockquote summary after title
    local has_summary=$(echo "$content" | head -10 | grep -c "^>" || true)
    if [[ $has_summary -eq 0 ]]; then
        print_warn "Missing one-line summary (> blockquote after title)"
    else
        print_pass "Has summary blockquote"
    fi
    
    # Check for TL;DR section
    if echo "$content" | head -30 | grep -qi "## TL;DR\|## TLDR\|## Summary"; then
        print_pass "Has TL;DR section"
    else
        print_warn "Missing TL;DR section in header"
    fi
    
    # Check header word count (first section before second H2)
    local header_content=$(echo "$content" | awk '/^## /{if(n++)exit}1')
    local header_words=$(count_words "$header_content")
    
    if [[ $header_words -le $MAX_HEADER_WORDS ]]; then
        print_pass "Header block: $header_words words (max $MAX_HEADER_WORDS)"
    else
        print_fail "Header block too long: $header_words words (max $MAX_HEADER_WORDS)"
    fi
    
    # Check for CCA annotations in header
    if echo "$header_content" | grep -qE "^(HERE:|THIS:|KEEP:|WAIT:|ASK:|LINK:)"; then
        print_pass "Has CCA annotations in header"
    else
        print_warn "Missing CCA annotations (HERE:, THIS:) in header"
    fi
}

check_footer_block() {
    local file="$1"
    local content="$2"
    
    # Check for Links section
    if echo "$content" | tail -50 | grep -qi "## Links\|## Related\|## See Also"; then
        print_pass "Has Links section in footer"
    else
        print_warn "Missing Links section in footer zone"
    fi
    
    # Check for LINK: annotations
    local link_count=$(echo "$content" | tail -50 | grep -c "^LINK:" || true)
    if [[ $link_count -gt 0 ]]; then
        print_pass "Has $link_count LINK: references in footer"
    else
        print_warn "No LINK: references in footer"
    fi
}

check_file_size() {
    local file="$1"
    local content="$2"
    
    local words=$(count_words "$content")
    local tokens=$(count_tokens "$content")
    
    if [[ $tokens -le $MAX_TOKENS ]]; then
        print_pass "File size: ~$tokens tokens ($words words)"
    else
        print_fail "File too large: ~$tokens tokens (max $MAX_TOKENS)"
        print_info "Consider splitting into smaller documents"
    fi
}

check_section_lengths() {
    local file="$1"
    local content="$2"
    
    local oversized=0
    local section_num=0
    local current_section=""
    local current_header=""
    
    while IFS= read -r line; do
        if [[ "$line" =~ ^##\  ]]; then
            # Process previous section
            if [[ -n "$current_section" ]]; then
                local words=$(count_words "$current_section")
                if [[ $words -gt $MAX_SECTION_WORDS ]]; then
                    print_warn "Section '$current_header' is $words words (max $MAX_SECTION_WORDS)"
                    ((oversized++)) || true
                fi
            fi
            current_header="$line"
            current_section=""
            ((section_num++)) || true
        else
            current_section="$current_section $line"
        fi
    done <<< "$content"
    
    # Check last section
    if [[ -n "$current_section" ]]; then
        local words=$(count_words "$current_section")
        if [[ $words -gt $MAX_SECTION_WORDS ]]; then
            print_warn "Section '$current_header' is $words words (max $MAX_SECTION_WORDS)"
            ((oversized++)) || true
        fi
    fi
    
    if [[ $oversized -eq 0 ]]; then
        print_pass "All sections within size limits"
    fi
    
    # Check H2 frequency
    local h2_count=$(echo "$content" | grep -c "^## " || true)
    local expected_h2=$(( $(count_words "$content") / 400 ))
    
    if [[ $h2_count -ge $expected_h2 ]] || [[ $h2_count -ge 3 ]]; then
        print_pass "Good section density: $h2_count H2 headers"
    else
        print_warn "Low section density: $h2_count H2s (suggest $expected_h2+ for this file size)"
    fi
}

check_sentence_lengths() {
    local file="$1"
    local content="$2"
    
    local long_sentences=0
    local very_long_sentences=0
    
    # Extract sentences (rough: split on . ? !)
    while IFS= read -r sentence; do
        # Skip code blocks, headers, and short lines
        [[ "$sentence" =~ ^[\`\#\-\*\|] ]] && continue
        [[ ${#sentence} -lt 10 ]] && continue
        
        local words=$(count_words "$sentence")
        if [[ $words -gt $MAX_SENTENCE_WORDS ]]; then
            ((very_long_sentences++)) || true
        elif [[ $words -gt $WARN_SENTENCE_WORDS ]]; then
            ((long_sentences++)) || true
        fi
    done < <(echo "$content" | grep -v '^\s*$' | grep -v '^\s*```' | sed 's/[.!?]/\n/g')
    
    if [[ $very_long_sentences -eq 0 ]] && [[ $long_sentences -lt 3 ]]; then
        print_pass "Sentence lengths OK"
    elif [[ $very_long_sentences -gt 0 ]]; then
        print_warn "$very_long_sentences sentences over $MAX_SENTENCE_WORDS words"
    else
        print_info "$long_sentences sentences between $WARN_SENTENCE_WORDS-$MAX_SENTENCE_WORDS words"
    fi
}

check_dead_zone() {
    local file="$1"
    local content="$2"
    
    local total_lines=$(echo "$content" | wc -l)
    local start_dead=$(( total_lines * 25 / 100 ))
    local end_dead=$(( total_lines * 75 / 100 ))
    
    # Extract middle 50%
    local dead_zone=$(echo "$content" | sed -n "${start_dead},${end_dead}p")
    
    # Check for danger patterns in dead zone
    local danger_patterns="IMPORTANT|CRITICAL|MUST|REQUIRED|WARNING|NEVER|ALWAYS"
    local danger_count=$(echo "$dead_zone" | grep -ciE "$danger_patterns" || true)
    
    if [[ $danger_count -eq 0 ]]; then
        print_pass "No critical keywords buried in dead zone"
    else
        print_warn "$danger_count critical keywords found in dead zone (lines $start_dead-$end_dead)"
        print_info "Consider moving IMPORTANT/CRITICAL content to header or footer"
    fi
}

check_cca_usage() {
    local file="$1"
    local content="$2"
    
    local cca_count=$(echo "$content" | grep -cE "^(HERE:|THIS:|KEEP:|WAIT:|ASK:|LINK:)" || true)
    
    if [[ $cca_count -ge 3 ]]; then
        print_pass "Good CCA annotation usage: $cca_count annotations"
    elif [[ $cca_count -gt 0 ]]; then
        print_info "Light CCA usage: $cca_count annotations (consider adding more)"
    else
        print_warn "No CCA annotations found"
    fi
}

# ============================================================================
# Main Lint Function
# ============================================================================

lint_file() {
    local file="$1"
    
    if [[ ! -f "$file" ]]; then
        echo -e "${RED}Error: File not found: $file${NC}"
        return 1
    fi
    
    ((TOTAL_FILES++)) || true
    
    local content=$(cat "$file")
    local filename=$(basename "$file")
    local errors_before=$ERRORS
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Linting:${NC} $file"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Run all checks
    check_header_block "$file" "$content"
    check_footer_block "$file" "$content"
    check_file_size "$file" "$content"
    check_section_lengths "$file" "$content"
    check_sentence_lengths "$file" "$content"
    check_dead_zone "$file" "$content"
    check_cca_usage "$file" "$content"
    
    # Tally result
    if [[ $ERRORS -eq $errors_before ]]; then
        ((PASSED_FILES++)) || true
        echo ""
        echo -e "  ${GREEN}PASSED${NC}"
    else
        ((FAILED_FILES++)) || true
        echo ""
        echo -e "  ${RED}FAILED${NC}"
    fi
}

# ============================================================================
# Generate llms.txt
# ============================================================================

generate_llms_txt() {
    local dir="${1:-.}"
    local output="$dir/llms.txt"
    
    echo "Generating llms.txt in $dir..."
    
    # Try to extract project name from README or first md file
    local project_name="Project"
    if [[ -f "$dir/README.md" ]]; then
        project_name=$(head -1 "$dir/README.md" | sed 's/^# //')
    fi
    
    cat > "$output" << EOF
# $project_name
> Documentation optimized for AI agent consumption

## Core Documentation
EOF
    
    # Find all .md files and categorize
    local core_docs=()
    local optional_docs=()
    
    while IFS= read -r file; do
        local basename=$(basename "$file" .md)
        local relpath="${file#$dir/}"
        local summary=""
        
        # Try to extract summary from file
        if [[ -f "$file" ]]; then
            summary=$(grep "^>" "$file" | head -1 | sed 's/^> //' | head -c 80)
        fi
        
        # Categorize based on name patterns
        if [[ "$basename" =~ ^(README|architecture|api|getting-started|overview) ]]; then
            core_docs+=("- [$basename](./$relpath): $summary")
        else
            optional_docs+=("- [$basename](./$relpath): $summary")
        fi
    done < <(find "$dir" -maxdepth 2 -name "*.md" -type f | sort)
    
    # Write core docs
    for doc in "${core_docs[@]:-}"; do
        echo "$doc" >> "$output"
    done
    
    # Write optional docs
    if [[ ${#optional_docs[@]} -gt 0 ]]; then
        echo "" >> "$output"
        echo "## Optional" >> "$output"
        for doc in "${optional_docs[@]}"; do
            echo "$doc" >> "$output"
        done
    fi
    
    echo ""
    echo -e "${GREEN}Generated:${NC} $output"
    echo "Files indexed: $((${#core_docs[@]} + ${#optional_docs[@]}))"
}

# ============================================================================
# Print Summary
# ============================================================================

print_summary() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}ARC Lint Summary${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  Total files:  $TOTAL_FILES"
    echo -e "  ${GREEN}Passed:${NC}       $PASSED_FILES"
    echo -e "  ${RED}Failed:${NC}       $FAILED_FILES"
    echo -e "  ${YELLOW}Warnings:${NC}     $WARNINGS"
    echo -e "  ${RED}Errors:${NC}       $ERRORS"
    echo ""
    
    if [[ $FAILED_FILES -eq 0 ]]; then
        echo -e "  ${GREEN}All files passed!${NC}"
        return 0
    else
        echo -e "  ${RED}Some files need attention.${NC}"
        return 1
    fi
}

# ============================================================================
# Main Entry Point
# ============================================================================

main() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  ARC Linter — Agent-Readable Content Validator           ║${NC}"
    echo -e "${BLUE}║  Based on 'Lost in the Middle' research                  ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
    
    local target="${1:-.}"
    
    # Handle special flags
    case "${1:-}" in
        --generate-llms|--llms)
            generate_llms_txt "${2:-.}"
            exit 0
            ;;
        --help|-h)
            echo ""
            echo "Usage:"
            echo "  arc-lint.sh [file.md]           Lint single file"
            echo "  arc-lint.sh [directory]         Lint all .md files"
            echo "  arc-lint.sh                     Lint current directory"
            echo "  arc-lint.sh --generate-llms     Generate llms.txt"
            echo ""
            exit 0
            ;;
    esac
    
    # Lint files
    if [[ -f "$target" ]]; then
        lint_file "$target"
    elif [[ -d "$target" ]]; then
        while IFS= read -r file; do
            lint_file "$file"
        done < <(find "$target" -name "*.md" -type f | sort)
    else
        echo -e "${RED}Error: $target is not a file or directory${NC}"
        exit 1
    fi
    
    print_summary
}

main "$@"
