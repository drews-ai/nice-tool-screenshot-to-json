/**
 * ELEMENT STUBS - Visual templates for each element type
 * 
 * This is the single source of truth for how each element type renders.
 * Deterministic: same input → same output, every time.
 * 
 * Each stub receives: { el, w, h, svg } where:
 *   - el: the element object (label, variant, field_type, etc.)
 *   - w: width in pixels
 *   - h: height in pixels  
 *   - svg: helper function to create SVG elements
 */

(function(global) {
  'use strict';

  // ============================================================================
  // CONSTANTS
  // ============================================================================
  
  const COLORS = {
    label: '#333333',
    subtle: '#888888',
    muted: '#AAAAAA',
    placeholder: '#9CA3AF',
    border: '#D1D5DB',
    bgLight: '#F3F4F6',
    bgHover: '#E5E7EB',
    primary: '#3B82F6',
    primaryDark: '#2563EB',
    success: '#10B981',
    warning: '#F59E0B',
    error: '#EF4444',
    spark: '#94A3B8',
  };

  const STUB_VALUES = {
    // Deterministic placeholder values based on label/type
    metric: (label) => {
      const map = {
        'health': '87', 'score': '92', 'rating': '7', 'domain': '45',
        'visitors': '12.9K', 'traffic': '5.4K', 'keywords': '825',
        'domains': '381', 'users': '1.2K', 'views': '34K',
        'revenue': '$12.4K', 'sales': '156', 'orders': '89',
        'default': '247'
      };
      const key = Object.keys(map).find(k => (label || '').toLowerCase().includes(k));
      return map[key] || map.default;
    },
    fieldValue: (label) => {
      const map = {
        'name': 'Acme Corp', 'project': 'Smileydental', 'email': 'user@example.com',
        'date': 'Dec 17, 2025', 'status': 'Active', 'type': 'Standard',
        'url': 'example.com', 'phone': '(555) 123-4567', 'default': 'Sample Value'
      };
      const key = Object.keys(map).find(k => (label || '').toLowerCase().includes(k));
      return map[key] || map.default;
    }
  };

  // ============================================================================
  // SVG HELPER
  // ============================================================================
  
  function svg(tag, attrs = {}, children = []) {
    const ns = 'http://www.w3.org/2000/svg';
    const el = document.createElementNS(ns, tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v != null) el.setAttribute(k, v);
    }
    children.forEach(c => {
      if (c) el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    });
    return el;
  }

  function trunc(s, max) {
    if (!s) return '';
    return s.length > max ? s.slice(0, max - 1) + '…' : s;
  }

  // ============================================================================
  // ELEMENT HEIGHTS (for layout calculation)
  // ============================================================================
  
  const ELEMENT_HEIGHTS = {
    // Inputs
    button: 36,
    text_input: 38,
    text_area: 64,
    selector: 38,
    date_input: 38,
    toggle: 32,
    checkbox: 30,
    radio: 30,
    rich_text: 72,
    file_input: 64,
    search_bar: 38,

    // Navigation
    action_link: 34,
    icon_action: 42,
    breadcrumb: 28,

    // Display
    heading: 36,
    field_value: 42,
    metric: 56,
    badge: 28,
    avatar: 44,

    // Content
    text_block: 48,

    // Media
    media: 80,
    chart: 100,
    calendar: 100,

    // Misc
    pagination: 36,
    divider: 16,
    empty_state: 100,
    loading: 60,
    error_state: 80,

    // Containers (null = calculated from children)
    section: null,
    blade: null,
    content_area: null,
    nav_list: null,
    list: null,
    data_table: null,
    action_bar: null,
    tab_group: null,
  };

  // ============================================================================
  // STUBS
  // ============================================================================
  
  const STUBS = {
    
    // -------------------------------------------------------------------------
    // BUTTONS & INPUTS
    // -------------------------------------------------------------------------
    
    button: ({ el, w, h }) => {
      const isPrimary = el.variant === 'primary';
      const isSecondary = el.variant === 'secondary';
      const g = svg('g');
      
      g.appendChild(svg('rect', {
        x: 4, y: 4, width: w - 8, height: h - 8, rx: 6,
        fill: isPrimary ? COLORS.primary : COLORS.bgLight,
        stroke: isPrimary ? COLORS.primaryDark : COLORS.border
      }));
      g.appendChild(svg('text', {
        x: w / 2, y: h / 2 + 4,
        'text-anchor': 'middle',
        'font-size': 12, 'font-weight': 600,
        fill: isPrimary ? '#FFFFFF' : '#374151'
      }, [trunc(el.label || 'Button', 14)]));
      
      return g;
    },

    text_input: ({ el, w, h }) => {
      const g = svg('g');
      const isSearch = el.field_type === 'search';
      const isEmail = el.field_type === 'email';
      const isPassword = el.field_type === 'password';
      
      // Icon
      let iconX = 10;
      if (isSearch) {
        g.appendChild(svg('text', { x: 10, y: h / 2 + 5, 'font-size': 12 }, ['🔍']));
        iconX = 28;
      } else if (isEmail) {
        g.appendChild(svg('text', { x: 10, y: h / 2 + 5, 'font-size': 12 }, ['✉']));
        iconX = 28;
      }
      
      // Placeholder line
      g.appendChild(svg('line', {
        x1: iconX, y1: h / 2 + 4, x2: w - 10, y2: h / 2 + 4,
        stroke: COLORS.border, 'stroke-width': 1
      }));
      
      // Placeholder text
      const placeholder = el.placeholder || el.label || el.field_type || 'Enter text...';
      g.appendChild(svg('text', {
        x: iconX, y: h / 2 + 1,
        'font-size': 11, fill: COLORS.placeholder
      }, [trunc(placeholder, 24)]));
      
      return g;
    },

    text_area: ({ el, w, h }) => {
      const g = svg('g');
      
      // Multiple placeholder lines
      for (let i = 0; i < 3; i++) {
        const lineW = i === 2 ? (w - 20) * 0.6 : w - 20;
        g.appendChild(svg('line', {
          x1: 10, y1: 20 + i * 16, x2: 10 + lineW, y2: 20 + i * 16,
          stroke: COLORS.border, 'stroke-width': 1
        }));
      }
      
      // Label
      if (el.label) {
        g.appendChild(svg('text', {
          x: 10, y: 14, 'font-size': 9, fill: COLORS.subtle
        }, [trunc(el.label, 20)]));
      }
      
      return g;
    },

    selector: ({ el, w, h }) => {
      const g = svg('g');
      
      // Label
      g.appendChild(svg('text', {
        x: 12, y: h / 2 + 4,
        'font-size': 11, fill: COLORS.label
      }, [trunc(el.label || 'Select...', 18)]));
      
      // Dropdown chevron
      g.appendChild(svg('text', {
        x: w - 18, y: h / 2 + 4,
        'font-size': 11, fill: COLORS.muted
      }, ['▾']));
      
      return g;
    },

    date_input: ({ el, w, h }) => {
      const g = svg('g');
      
      // Date value - no icon
      g.appendChild(svg('text', {
        x: 12, y: h / 2 + 4,
        'font-size': 11, fill: COLORS.label
      }, [el.label || 'Select date']));
      
      return g;
    },

    search_bar: ({ el, w, h }) => {
      const g = svg('g');
      
      // Search placeholder text
      g.appendChild(svg('text', {
        x: 12, y: h / 2 + 4,
        'font-size': 11, fill: COLORS.muted
      }, [el.placeholder || el.label || 'Search...']));
      
      return g;
    },

    toggle: ({ el, w, h }) => {
      const g = svg('g');
      const isOn = el.value === true;
      
      // Track
      g.appendChild(svg('rect', {
        x: 8, y: h / 2 - 8, width: 32, height: 16, rx: 8,
        fill: isOn ? COLORS.primary : COLORS.bgLight,
        stroke: isOn ? COLORS.primaryDark : COLORS.border
      }));
      
      // Thumb
      g.appendChild(svg('circle', {
        cx: isOn ? 32 : 16, cy: h / 2, r: 6, fill: '#FFFFFF'
      }));
      
      // Label
      if (el.label) {
        g.appendChild(svg('text', {
          x: 48, y: h / 2 + 4,
          'font-size': 11, fill: COLORS.label
        }, [trunc(el.label, 18)]));
      }
      
      return g;
    },

    checkbox: ({ el, w, h }) => {
      const g = svg('g');
      
      // Box
      g.appendChild(svg('rect', {
        x: 8, y: h / 2 - 7, width: 14, height: 14, rx: 2,
        fill: '#FFFFFF', stroke: COLORS.border
      }));
      
      // Label
      if (el.label) {
        g.appendChild(svg('text', {
          x: 28, y: h / 2 + 4,
          'font-size': 11, fill: COLORS.label
        }, [trunc(el.label, 20)]));
      }
      
      return g;
    },

    radio: ({ el, w, h }) => {
      const g = svg('g');
      
      // Circle
      g.appendChild(svg('circle', {
        cx: 15, cy: h / 2, r: 7,
        fill: '#FFFFFF', stroke: COLORS.border
      }));
      
      // Label
      if (el.label) {
        g.appendChild(svg('text', {
          x: 28, y: h / 2 + 4,
          'font-size': 11, fill: COLORS.label
        }, [trunc(el.label, 20)]));
      }
      
      return g;
    },

    // -------------------------------------------------------------------------
    // NAVIGATION
    // -------------------------------------------------------------------------

    action_link: ({ el, w, h }) => {
      const g = svg('g');
      
      // Simple text link with subtle arrow
      g.appendChild(svg('text', {
        x: 8, y: h / 2 + 4,
        'font-size': 11, fill: COLORS.label
      }, [trunc(el.label || 'Link', 22)]));
      
      g.appendChild(svg('text', {
        x: w - 12, y: h / 2 + 4,
        'font-size': 12, fill: COLORS.muted
      }, ['›']));
      
      return g;
    },

    icon_action: ({ el, w, h }) => {
      const g = svg('g');
      
      // Circle background
      g.appendChild(svg('circle', {
        cx: w / 2, cy: h / 2 - 4, r: 14,
        fill: COLORS.bgLight, stroke: COLORS.border
      }));
      
      // Icon dot (placeholder)
      g.appendChild(svg('circle', {
        cx: w / 2, cy: h / 2 - 4, r: 4, fill: COLORS.subtle
      }));
      
      // Label below
      if (el.label) {
        g.appendChild(svg('text', {
          x: w / 2, y: h - 4,
          'text-anchor': 'middle',
          'font-size': 8, fill: COLORS.subtle
        }, [trunc(el.label, 10)]));
      }
      
      return g;
    },

    // -------------------------------------------------------------------------
    // DISPLAY
    // -------------------------------------------------------------------------

    heading: ({ el, w, h }) => {
      const level = el.level || 1;
      const size = level === 1 ? 18 : level === 2 ? 15 : 13;
      
      return svg('text', {
        x: 8, y: h / 2 + size / 3,
        'font-size': size, 'font-weight': 700, fill: COLORS.label
      }, [trunc(el.label || 'Heading', 28)]);
    },

    field_value: ({ el, w, h }) => {
      const g = svg('g');
      
      // Label
      g.appendChild(svg('text', {
        x: 10, y: 16,
        'font-size': 9, fill: COLORS.subtle
      }, [trunc(el.label || 'Field', 14)]));
      
      // Value
      g.appendChild(svg('text', {
        x: 10, y: 34,
        'font-size': 13, 'font-weight': 500, fill: COLORS.label
      }, [STUB_VALUES.fieldValue(el.label)]));
      
      return g;
    },

    metric: ({ el, w, h }) => {
      const g = svg('g');
      
      // Big number
      g.appendChild(svg('text', {
        x: w / 2, y: 26,
        'text-anchor': 'middle',
        'font-size': 22, 'font-weight': 700, fill: COLORS.label
      }, [STUB_VALUES.metric(el.label)]));
      
      // Label
      g.appendChild(svg('text', {
        x: w / 2, y: 42,
        'text-anchor': 'middle',
        'font-size': 10, fill: COLORS.subtle
      }, [trunc(el.label || 'Metric', 14)]));
      
      // Sparkline
      const sparkY = h - 10;
      g.appendChild(svg('path', {
        d: `M${w * 0.15} ${sparkY} Q${w * 0.35} ${sparkY - 8},${w * 0.5} ${sparkY - 3} T${w * 0.85} ${sparkY - 5}`,
        stroke: COLORS.spark, 'stroke-width': 1.5, fill: 'none'
      }));
      
      return g;
    },

    badge: ({ el, w, h }) => {
      const g = svg('g');
      
      // Pill background
      g.appendChild(svg('rect', {
        x: 4, y: 4, width: w - 8, height: h - 8, rx: (h - 8) / 2,
        fill: COLORS.bgLight
      }));
      
      // Text
      g.appendChild(svg('text', {
        x: w / 2, y: h / 2 + 4,
        'text-anchor': 'middle',
        'font-size': 10, fill: COLORS.subtle
      }, [trunc(el.label || 'Badge', 12)]));
      
      return g;
    },

    avatar: ({ el, w, h }) => {
      const g = svg('g');
      const r = Math.min(w, h) / 2 - 6;
      
      // Circle
      g.appendChild(svg('circle', {
        cx: w / 2, cy: h / 2, r,
        fill: COLORS.bgLight, stroke: COLORS.border
      }));
      
      // Initials
      const initials = (el.label || 'U').charAt(0).toUpperCase();
      g.appendChild(svg('text', {
        x: w / 2, y: h / 2 + 5,
        'text-anchor': 'middle',
        'font-size': 14, 'font-weight': 500, fill: COLORS.subtle
      }, [initials]));
      
      return g;
    },

    // -------------------------------------------------------------------------
    // MEDIA
    // -------------------------------------------------------------------------

    media: ({ el, w, h }) => {
      const g = svg('g');
      
      // Background - no icon, just placeholder box
      g.appendChild(svg('rect', {
        x: 4, y: 4, width: w - 8, height: h - 8, rx: 4,
        fill: COLORS.bgLight, stroke: COLORS.border, 'stroke-dasharray': '4,2'
      }));
      
      // Diagonal lines to indicate media placeholder
      g.appendChild(svg('line', {
        x1: 4, y1: 4, x2: w - 4, y2: h - 4,
        stroke: COLORS.border, 'stroke-width': 1
      }));
      g.appendChild(svg('line', {
        x1: w - 4, y1: 4, x2: 4, y2: h - 4,
        stroke: COLORS.border, 'stroke-width': 1
      }));
      
      return g;
    },

    chart: ({ el, w, h }) => {
      const g = svg('g');
      const variant = el.variant || 'bar';
      
      // Background
      g.appendChild(svg('rect', {
        x: 4, y: 4, width: w - 8, height: h - 8, rx: 4,
        fill: COLORS.bgLight, stroke: COLORS.border, 'stroke-dasharray': '2,2'
      }));
      
      if (variant === 'line' || variant === 'sparkline') {
        // Line chart
        g.appendChild(svg('path', {
          d: `M${w * 0.1} ${h * 0.7} L${w * 0.3} ${h * 0.4} L${w * 0.5} ${h * 0.55} L${w * 0.7} ${h * 0.25} L${w * 0.9} ${h * 0.35}`,
          stroke: COLORS.primary, 'stroke-width': 2, fill: 'none'
        }));
      } else {
        // Bar chart
        const bars = [0.6, 0.85, 0.45, 0.95, 0.55];
        const barW = (w - 40) / bars.length - 8;
        bars.forEach((height, i) => {
          g.appendChild(svg('rect', {
            x: 20 + i * (barW + 8),
            y: h - 15 - height * (h - 40),
            width: barW,
            height: height * (h - 40),
            rx: 2,
            fill: '#93C5FD'
          }));
        });
      }
      
      return g;
    },

    // -------------------------------------------------------------------------
    // CONTENT
    // -------------------------------------------------------------------------

    text_block: ({ el, w, h }) => {
      const g = svg('g');
      
      // Show actual label content if available
      if (el.label) {
        // Wrap text into multiple lines
        const maxCharsPerLine = Math.floor((w - 16) / 6);
        const words = el.label.split(' ');
        let lines = [];
        let currentLine = '';
        
        for (const word of words) {
          if ((currentLine + ' ' + word).length <= maxCharsPerLine) {
            currentLine = currentLine ? currentLine + ' ' + word : word;
          } else {
            if (currentLine) lines.push(currentLine);
            currentLine = word;
          }
        }
        if (currentLine) lines.push(currentLine);
        
        // Limit to 3 lines
        lines = lines.slice(0, 3);
        if (lines.length < words.join(' ').split(' ').length && lines.length === 3) {
          lines[2] = trunc(lines[2], maxCharsPerLine - 3) + '...';
        }
        
        lines.forEach((line, i) => {
          g.appendChild(svg('text', {
            x: 8, y: 16 + i * 14,
            'font-size': 11, fill: COLORS.label
          }, [line]));
        });
      } else {
        // Fallback placeholder lines
        for (let i = 0; i < 2; i++) {
          const lineW = i === 1 ? (w - 16) * 0.65 : w - 16;
          g.appendChild(svg('line', {
            x1: 8, y1: 12 + i * 14, x2: 8 + lineW, y2: 12 + i * 14,
            stroke: COLORS.border, 'stroke-width': 1
          }));
        }
      }

      return g;
    },

    rich_text: ({ el, w, h }) => {
      const g = svg('g');

      // Toolbar
      g.appendChild(svg('rect', {
        x: 4, y: 4, width: w - 8, height: 24, rx: 4,
        fill: COLORS.bgLight, stroke: COLORS.border
      }));

      // Toolbar icons (B, I, U)
      const icons = ['B', 'I', 'U', '≡'];
      icons.forEach((icon, i) => {
        g.appendChild(svg('text', {
          x: 16 + i * 24, y: 20,
          'font-size': 11, 'font-weight': icon === 'B' ? 700 : 400,
          'font-style': icon === 'I' ? 'italic' : 'normal',
          'text-decoration': icon === 'U' ? 'underline' : 'none',
          fill: COLORS.subtle
        }, [icon]));
      });

      // Text area
      for (let i = 0; i < 2; i++) {
        g.appendChild(svg('line', {
          x1: 8, y1: 40 + i * 14, x2: w - 16, y2: 40 + i * 14,
          stroke: COLORS.border, 'stroke-width': 1
        }));
      }

      return g;
    },

    file_input: ({ el, w, h }) => {
      const g = svg('g');

      // Dropzone
      g.appendChild(svg('rect', {
        x: 4, y: 4, width: w - 8, height: h - 8, rx: 6,
        fill: COLORS.bgLight, stroke: COLORS.border, 'stroke-dasharray': '4,2'
      }));

      // Upload icon
      g.appendChild(svg('text', {
        x: w / 2, y: h / 2 - 4,
        'text-anchor': 'middle',
        'font-size': 20, fill: COLORS.muted
      }, ['⬆']));

      // Label
      g.appendChild(svg('text', {
        x: w / 2, y: h / 2 + 16,
        'text-anchor': 'middle',
        'font-size': 10, fill: COLORS.subtle
      }, [el.label || 'Drop files here']));

      return g;
    },

    // -------------------------------------------------------------------------
    // STRUCTURE
    // -------------------------------------------------------------------------

    breadcrumb: ({ el, w, h }) => {
      const g = svg('g');

      // Breadcrumb text
      g.appendChild(svg('text', {
        x: 8, y: h / 2 + 4,
        'font-size': 11, fill: COLORS.subtle
      }, [trunc(el.label || 'Home › Page › Current', 30)]));

      return g;
    },

    calendar: ({ el, w, h }) => {
      const g = svg('g');

      // Calendar container
      g.appendChild(svg('rect', {
        x: 4, y: 4, width: w - 8, height: h - 8, rx: 4,
        fill: COLORS.bgLight, stroke: COLORS.border
      }));

      // Header
      g.appendChild(svg('text', {
        x: w / 2, y: 22,
        'text-anchor': 'middle',
        'font-size': 11, 'font-weight': 600, fill: COLORS.label
      }, [el.label || 'December 2025']));

      // Grid of day cells (simplified)
      const cellW = (w - 24) / 7;
      const cellH = 16;
      for (let row = 0; row < 4; row++) {
        for (let col = 0; col < 7; col++) {
          g.appendChild(svg('rect', {
            x: 12 + col * cellW, y: 32 + row * cellH,
            width: cellW - 2, height: cellH - 2, rx: 2,
            fill: row === 1 && col === 3 ? COLORS.primary : 'transparent'
          }));
        }
      }

      return g;
    },

    // -------------------------------------------------------------------------
    // MISC
    // -------------------------------------------------------------------------

    pagination: ({ el, w, h }) => {
      const g = svg('g');
      
      g.appendChild(svg('text', {
        x: w / 2, y: h / 2 + 4,
        'text-anchor': 'middle',
        'font-size': 12, fill: COLORS.subtle
      }, ['‹  1  2  3  …  ›']));
      
      return g;
    },

    divider: ({ el, w, h }) => {
      return svg('line', {
        x1: 8, y1: h / 2, x2: w - 8, y2: h / 2,
        stroke: COLORS.border, 'stroke-width': 1
      });
    },

    empty_state: ({ el, w, h }) => {
      const g = svg('g');
      
      // Icon
      g.appendChild(svg('text', {
        x: w / 2, y: h / 2 - 10,
        'text-anchor': 'middle',
        'font-size': 28, fill: COLORS.muted
      }, ['📭']));
      
      // Text
      g.appendChild(svg('text', {
        x: w / 2, y: h / 2 + 20,
        'text-anchor': 'middle',
        'font-size': 12, fill: COLORS.subtle
      }, [el.label || 'No items yet']));
      
      return g;
    },

    loading: ({ el, w, h }) => {
      const g = svg('g');
      
      // Spinner placeholder
      g.appendChild(svg('circle', {
        cx: w / 2, cy: h / 2, r: 16,
        fill: 'none', stroke: COLORS.border, 'stroke-width': 3
      }));
      g.appendChild(svg('path', {
        d: `M${w / 2} ${h / 2 - 16} A16 16 0 0 1 ${w / 2 + 16} ${h / 2}`,
        stroke: COLORS.primary, 'stroke-width': 3, fill: 'none'
      }));
      
      return g;
    },

    error_state: ({ el, w, h }) => {
      const g = svg('g');
      
      // Icon
      g.appendChild(svg('text', {
        x: w / 2, y: h / 2 - 8,
        'text-anchor': 'middle',
        'font-size': 24, fill: COLORS.error
      }, ['⚠']));
      
      // Text
      g.appendChild(svg('text', {
        x: w / 2, y: h / 2 + 18,
        'text-anchor': 'middle',
        'font-size': 11, fill: COLORS.error
      }, [trunc(el.label || 'Something went wrong', 24)]));
      
      return g;
    },

    // -------------------------------------------------------------------------
    // DEFAULT FALLBACK
    // -------------------------------------------------------------------------

    _default: ({ el, w, h }) => {
      const g = svg('g');
      
      // Type label
      g.appendChild(svg('text', {
        x: 8, y: 16,
        'font-size': 9, fill: COLORS.subtle
      }, [el.type || 'unknown']));
      
      // Label if present
      if (el.label) {
        g.appendChild(svg('text', {
          x: 8, y: 32,
          'font-size': 11, fill: COLORS.label
        }, [trunc(el.label, 20)]));
      }
      
      return g;
    }
  };

  // ============================================================================
  // EXPORTS
  // ============================================================================
  
  const ElementStubs = {
    COLORS,
    ELEMENT_HEIGHTS,
    STUBS,
    svg,
    trunc,
    
    // Get height for an element type
    getHeight(type, hasChildren) {
      if (hasChildren) return null; // Calculated from children
      return ELEMENT_HEIGHTS[type] || 40;
    },
    
    // Render a stub for an element
    render(el, width, height) {
      const type = el.type || '_default';
      const stub = STUBS[type] || STUBS._default;
      return stub({ el, w: width, h: height, svg });
    },
    
    // Check if type renders children horizontally
    isHorizontal(type, zone) {
      if (['blade', 'action_bar', 'tab_group'].includes(type)) return true;
      if (type === 'nav_list' && zone === 'top_bar') return true;
      return false;
    },
    
    // Check if type is a container
    isContainer(type) {
      return ELEMENT_HEIGHTS[type] === null;
    }
  };

  // Export
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = ElementStubs;
  } else {
    global.ElementStubs = ElementStubs;
  }

})(typeof window !== 'undefined' ? window : this);
