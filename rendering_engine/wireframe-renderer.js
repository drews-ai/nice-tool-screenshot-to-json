/**
 * WireframeRenderer - Lightweight SVG wireframe renderer
 * 
 * Requires: element-stubs.js
 * 
 * Usage:
 *   <script src="element-stubs.js"></script>
 *   <script src="wireframe-renderer.js"></script>
 *   <script>
 *     const wf = new WireframeRenderer('#container');
 *     wf.render(inventoryJson);
 *   </script>
 */

(function(global) {
  'use strict';

  // Get stubs library
  const Stubs = global.ElementStubs;
  if (!Stubs) {
    throw new Error('WireframeRenderer requires ElementStubs (element-stubs.js)');
  }

  // ============================================================================
  // THEME
  // ============================================================================
  
  const THEME = {
    bg: '#FAFAFA',
    brandHeight: 44,
    topBarHeight: 56,
    leftPaneWidth: 200,
    padding: 12,
    gap: 8,
    radius: 6,
    
    // Colors
    zoneBg: '#FFFFFF',
    zoneStroke: '#E8E8E8',
    zoneLabel: '#AAAAAA',
    elementFill: '#FFFFFF',
    elementStroke: '#E0E0E0',
    elementHover: '#EDF4FF',
    containerFill: '#F8FAFB',
    accentColor: '#3B82F6',
    lowConfColor: '#EF4444',
  };

  // ============================================================================
  // ELEMENT RENDERER
  // ============================================================================
  
  function renderElement(el, width, zone, events, path) {
    const type = el.type || 'unknown';
    const children = el.children || [];
    const hasChildren = children.length > 0;
    const isContainer = hasChildren && Stubs.isContainer(type);
    const isHorizontal = Stubs.isHorizontal(type, zone);

    // Calculate height - for containers, we calculate after rendering children
    let height = Stubs.getHeight(type, hasChildren);
    
    // For non-containers, height is already set
    if (!isContainer && height === null) {
      height = 40; // fallback
    }

    const confidence = el.confidence || 1;
    const isLowConf = confidence < 0.7;

    // Create group
    const g = Stubs.svg('g', { 'data-path': path, style: 'cursor:pointer' });

    // Background rect - height may be updated later for containers
    const bg = Stubs.svg('rect', {
      width, height: height || 40, rx: THEME.radius,
      fill: isContainer ? THEME.containerFill : THEME.elementFill,
      stroke: isLowConf ? THEME.lowConfColor : THEME.elementStroke,
      'stroke-dasharray': isLowConf ? '4,2' : null
    });
    g.appendChild(bg);

    // Hover events
    g.addEventListener('mouseenter', () => {
      bg.setAttribute('fill', THEME.elementHover);
      bg.setAttribute('stroke', THEME.accentColor);
      bg.setAttribute('stroke-width', '2');
      events.emit('hover', el, path);
    });
    g.addEventListener('mouseleave', () => {
      bg.setAttribute('fill', isContainer ? THEME.containerFill : THEME.elementFill);
      bg.setAttribute('stroke', isLowConf ? THEME.lowConfColor : THEME.elementStroke);
      bg.setAttribute('stroke-width', '1');
      events.emit('hover', null, null);
    });
    g.addEventListener('click', (e) => {
      e.stopPropagation();
      events.emit('click', el, path);
    });

    if (isContainer) {
      // Render children first to get actual heights
      const childGroup = Stubs.svg('g', { transform: `translate(${THEME.gap}, 26)` });
      const innerWidth = width - THEME.gap * 2;
      let childrenHeight = 0;

      if (isHorizontal) {
        const childWidth = (innerWidth - (children.length - 1) * THEME.gap) / children.length;
        let maxChildH = 36;
        children.forEach((child, i) => {
          const childG = renderElement(child, childWidth, zone, events, `${path}.children[${i}]`);
          childG.setAttribute('transform', `translate(${i * (childWidth + THEME.gap)}, 0)`);
          childGroup.appendChild(childG);
          maxChildH = Math.max(maxChildH, childG._height || 40);
        });
        childrenHeight = maxChildH;
      } else {
        let y = 0;
        children.forEach((child, i) => {
          const childG = renderElement(child, innerWidth, zone, events, `${path}.children[${i}]`);
          childG.setAttribute('transform', `translate(0, ${y})`);
          childGroup.appendChild(childG);
          
          // Use actual rendered height (supports nested containers)
          const childH = childG._height || 40;
          y += childH + THEME.gap;
        });
        childrenHeight = y > 0 ? y - THEME.gap : 0;
      }

      // Now calculate container height
      height = 28 + childrenHeight + THEME.padding;
      
      // Update background rect with correct height
      bg.setAttribute('height', height);
      
      // Container label
      g.appendChild(Stubs.svg('text', {
        x: 10, y: 18,
        'font-size': 10, 'font-weight': 600, fill: THEME.zoneLabel
      }, [`${type} (${children.length})`]));

      g.appendChild(childGroup);
    } else {
      // Leaf element - use stub from library
      const stub = Stubs.render(el, width, height);
      g.appendChild(stub);
    }

    // Store height for layout calculations
    g._height = height;
    return g;
  }

  // ============================================================================
  // ZONE RENDERER
  // ============================================================================
  
  function renderZone(elements, width, zone, events) {
    if (!elements || elements.length === 0) return { group: Stubs.svg('g'), height: 40 };

    const g = Stubs.svg('g', { transform: `translate(${THEME.padding}, 28)` });
    let y = 0;

    elements.forEach((el, i) => {
      const elG = renderElement(el, width - THEME.padding * 2, zone, events, `${zone}[${i}]`);
      elG.setAttribute('transform', `translate(0, ${y})`);
      g.appendChild(elG);
      y += elG._height + THEME.gap;
    });

    return { group: g, height: y + 28 };
  }

  function calcZoneHeight(elements, zone) {
    if (!elements || elements.length === 0) return 100;
    
    return elements.reduce((sum, el) => {
      const children = el.children || [];
      const hasChildren = children.length > 0;
      
      if (!hasChildren) {
        return sum + (Stubs.getHeight(el.type) || 40) + THEME.gap;
      }
      
      const isHorizontal = Stubs.isHorizontal(el.type, zone);
      let childrenH;
      
      if (isHorizontal) {
        childrenH = Math.max(...children.map(c => Stubs.getHeight(c.type, c.children?.length > 0) || 40), 36);
      } else {
        childrenH = children.reduce((s, c) => s + (Stubs.getHeight(c.type, c.children?.length > 0) || 40) + THEME.gap, -THEME.gap);
      }
      
      return sum + 28 + childrenH + THEME.padding + THEME.gap;
    }, 40);
  }

  // ============================================================================
  // TOOLTIP
  // ============================================================================
  
  function createTooltip() {
    const tip = document.createElement('div');
    tip.className = 'wf-tooltip';
    tip.style.cssText = `
      position: fixed; display: none; background: #1F2937; color: #FFF;
      padding: 10px 14px; border-radius: 8px; font-size: 12px; max-width: 280px;
      z-index: 10000; pointer-events: none; font-family: system-ui, -apple-system, sans-serif;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3); line-height: 1.4;
    `;
    document.body.appendChild(tip);
    return tip;
  }

  function updateTooltip(tip, el, x, y) {
    if (!el) {
      tip.style.display = 'none';
      return;
    }
    
    const conf = Math.round((el.confidence || 1) * 100);
    const isLow = conf < 70;
    
    tip.innerHTML = `
      <div style="font-weight:700;font-size:13px;margin-bottom:4px">
        ${el.type}${el.field_type ? ': ' + el.field_type : ''}${el.variant ? ' (' + el.variant + ')' : ''}
      </div>
      ${el.label ? `<div style="color:#93C5FD;margin-bottom:4px">"${Stubs.trunc(el.label, 30)}"</div>` : ''}
      ${el.purpose ? `<div style="color:#D1D5DB;font-style:italic">${el.purpose}</div>` : ''}
      <div style="margin-top:8px;padding-top:8px;border-top:1px solid #374151;font-size:11px;color:${isLow ? '#F87171' : '#9CA3AF'}">
        Confidence: ${conf}%${isLow ? ' ⚠️' : ''}
        ${el.content_nature ? `<span style="margin-left:12px">• ${el.content_nature}</span>` : ''}
      </div>
    `;
    
    // Position tooltip
    const viewportW = window.innerWidth;
    const viewportH = window.innerHeight;
    let left = x + 16;
    let top = y - 10;
    
    // Keep in viewport
    if (left + 280 > viewportW) left = x - 290;
    if (top + 150 > viewportH) top = viewportH - 160;
    if (top < 10) top = 10;
    
    tip.style.display = 'block';
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }

  // ============================================================================
  // MAIN CLASS
  // ============================================================================
  
  class WireframeRenderer {
    constructor(container, options = {}) {
      this.container = typeof container === 'string' 
        ? document.querySelector(container) 
        : container;
      
      this.options = {
        width: 800,
        brandColor: '#3B82F6',
        showTooltip: true,
        showZoneLabels: true,
        ...options
      };
      
      this.listeners = { hover: [], click: [] };
      this.tooltip = this.options.showTooltip ? createTooltip() : null;
      this.svg = null;
      this._mouseX = 0;
      this._mouseY = 0;
    }

    render(inventory) {
      this.container.innerHTML = '';

      const zones = inventory.zones || {};
      const screen = inventory.screen || {};
      const app = inventory.app_context || {};
      const W = this.options.width;
      const brand = this.options.brandColor;

      const hasTopBar = zones.top_bar?.length > 0;
      const hasLeftPane = zones.left_pane?.length > 0;

      // Event emitter
      const events = {
        emit: (type, el, path) => {
          this.listeners[type]?.forEach(fn => fn(el, path));
          if (type === 'hover' && this.tooltip) {
            updateTooltip(this.tooltip, el, this._mouseX, this._mouseY);
          }
        }
      };

      // Pre-render zones to get actual heights
      const leftPaneW = hasLeftPane ? THEME.leftPaneWidth : 0;
      const contentW = W - leftPaneW;
      
      const topBarRendered = hasTopBar ? renderZone(zones.top_bar, W, 'top_bar', events) : null;
      const leftPaneRendered = hasLeftPane ? renderZone(zones.left_pane, leftPaneW, 'left_pane', events) : null;
      const contentRendered = renderZone(zones.content_area, contentW, 'content_area', events);
      
      // Use actual rendered heights
      const topBarH = hasTopBar ? Math.max(topBarRendered.height, THEME.topBarHeight) : 0;
      const leftH = leftPaneRendered ? leftPaneRendered.height : 0;
      const contentH = contentRendered.height;
      const mainH = Math.max(leftH, contentH, 150);
      
      // Calculate positions
      const topBarY = THEME.brandHeight;
      const mainY = topBarY + topBarH;
      const totalH = mainY + mainH + THEME.padding;

      // Create SVG with correct height
      const svg = Stubs.svg('svg', {
        width: W, height: totalH,
        style: `background:${THEME.bg};border-radius:8px;border:1px solid #E0E0E0;font-family:system-ui,-apple-system,sans-serif`
      });

      // Track mouse
      svg.addEventListener('mousemove', (e) => {
        this._mouseX = e.clientX;
        this._mouseY = e.clientY;
      });

      // Brand header - NO ICONS, just text
      svg.appendChild(Stubs.svg('rect', { width: W, height: THEME.brandHeight, fill: brand }));
      svg.appendChild(Stubs.svg('text', { x: 16, y: 28, 'font-size': 15, 'font-weight': 700, fill: '#FFF' }, [app.name || 'App']));
      svg.appendChild(Stubs.svg('text', { x: W - 16, y: 28, 'font-size': 10, fill: 'rgba(255,255,255,0.7)', 'text-anchor': 'end' }, [Stubs.trunc(screen.intent, 50)]));

      // Top bar
      if (hasTopBar && topBarRendered) {
        const topG = Stubs.svg('g', { transform: `translate(0, ${topBarY})` });
        topG.appendChild(Stubs.svg('rect', { width: W, height: topBarH, fill: THEME.zoneBg, stroke: THEME.zoneStroke }));
        
        if (this.options.showZoneLabels) {
          topG.appendChild(Stubs.svg('text', { x: THEME.padding, y: 14, 'font-size': 8, 'font-weight': 600, fill: THEME.zoneLabel }, ['TOP BAR']));
        }
        
        topG.appendChild(topBarRendered.group);
        svg.appendChild(topG);
      }

      // Left pane
      if (hasLeftPane && leftPaneRendered) {
        const leftG = Stubs.svg('g', { transform: `translate(0, ${mainY})` });
        leftG.appendChild(Stubs.svg('rect', { width: leftPaneW, height: mainH, fill: THEME.zoneBg, stroke: THEME.zoneStroke }));
        
        if (this.options.showZoneLabels) {
          leftG.appendChild(Stubs.svg('text', { x: THEME.padding, y: 18, 'font-size': 8, 'font-weight': 600, fill: THEME.zoneLabel }, ['NAVIGATION']));
        }
        
        leftG.appendChild(leftPaneRendered.group);
        svg.appendChild(leftG);
      }

      // Content area
      const contentG = Stubs.svg('g', { transform: `translate(${leftPaneW}, ${mainY})` });
      contentG.appendChild(Stubs.svg('rect', { width: contentW, height: mainH, fill: THEME.zoneBg, stroke: THEME.zoneStroke }));
      
      if (this.options.showZoneLabels) {
        contentG.appendChild(Stubs.svg('text', { x: THEME.padding, y: 18, 'font-size': 8, 'font-weight': 600, fill: THEME.zoneLabel }, ['CONTENT']));
      }
      
      contentG.appendChild(contentRendered.group);
      svg.appendChild(contentG);

      this.container.appendChild(svg);
      this.svg = svg;
      
      return this;
    }

    // Event handling
    on(event, fn) {
      if (this.listeners[event]) this.listeners[event].push(fn);
      return this;
    }

    off(event, fn) {
      if (this.listeners[event]) {
        this.listeners[event] = this.listeners[event].filter(f => f !== fn);
      }
      return this;
    }

    // Export
    toSVG() {
      return this.svg?.outerHTML || '';
    }

    // Cleanup
    destroy() {
      this.container.innerHTML = '';
      if (this.tooltip) this.tooltip.remove();
      this.listeners = { hover: [], click: [] };
    }
  }

  // Export
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = WireframeRenderer;
  } else {
    global.WireframeRenderer = WireframeRenderer;
  }

})(typeof window !== 'undefined' ? window : this);
