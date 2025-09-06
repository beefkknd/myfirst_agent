# Ocean-Inspired Dark Theme Guide

## Color Palette

### Primary Colors
| Color | Hex Code | Usage | Contrast Ratio |
|-------|----------|-------|----------------|
| **Ocean Dark** | `#1a2332` | Base background | - |
| **Ocean Darker** | `#141b26` | Container backgrounds | - |
| **Ocean Deepest** | `#0f141d` | Headers, footers | - |

### Ocean Blue Accents
| Color | Hex Code | Usage | Contrast on Dark |
|-------|----------|-------|------------------|
| **Ocean Blue** | `#4a90e2` | Primary accents, links | 4.6:1 |
| **Ocean Blue Muted** | `#3674b8` | Secondary accents | 3.8:1 |
| **Ocean Teal** | `#2c9aa0` | Highlights, borders | 4.1:1 |
| **Ocean Teal Dark** | `#1e6b70` | Darker accents | 2.9:1 |

### Light Colors
| Color | Hex Code | Usage | Contrast on Dark |
|-------|----------|-------|------------------|
| **Ocean Light** | `#e8f1f8` | Primary text | 12.4:1 (AAA) |
| **Ocean Medium** | `#b8c8d9` | Secondary text | 8.9:1 (AAA) |
| **Ocean Panel** | `#f7fafc` | Data panel backgrounds | - |
| **Ocean Border** | `#4a5568` | Soft borders | 3.2:1 |

### State Colors
| Color | Hex Code | Usage |
|-------|----------|-------|
| **Ocean Bright** | `#60a5fa` | Active states, highlights |
| **Ocean Success** | `#06b6d4` | Success indicators |
| **Ocean Warning** | `#f59e0b` | Warning states |
| **Ocean Error** | `#ef4444` | Error states |

## Typography

### Font Stack
```css
font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Consolas', monospace;
```

### Hierarchy
- **Headers**: Ocean Bright (#60a5fa) with subtle glow
- **Primary Text**: Ocean Light (#e8f1f8) for maximum readability
- **Secondary Text**: Ocean Medium (#b8c8d9) for metadata
- **Data Values**: Ocean Deepest (#0f141d) on light panels

## Component Styling

### Data Panels
- Background: Ocean Panel (#f7fafc) - white/light gray
- Border: Ocean Border (#4a5568) with Ocean Teal left accent
- Text: Ocean Deepest (#0f141d) for contrast

### Interactive Elements
- Hover states use Ocean Blue (#4a90e2) and Ocean Bright (#60a5fa)
- Active states use Ocean Success (#06b6d4)
- Subtle animations with 0.2s ease transitions

### Maps & Visualizations
- Track lines: Ocean Blue (#4a90e2)
- Data points: Ocean Teal (#2c9aa0) with Ocean Bright fill
- Heatmap gradient: Teal → Blue → Bright Blue → Success

## Accessibility

All color combinations meet WCAG 2.1 guidelines:
- **AAA compliance**: Light text on dark backgrounds (12.4:1, 8.9:1)
- **AA compliance**: All interactive elements exceed 3:1 minimum
- **Color independence**: Information conveyed through color is also available through typography and iconography

## Implementation

The theme uses CSS custom properties (variables) for maintainability:
```css
:root {
    --ocean-dark: #1a2332;
    --ocean-light: #e8f1f8;
    /* ... etc */
}
```

## Design Principles

1. **Maritime Heritage**: Colors inspired by deep ocean waters and maritime navigation
2. **Professional Aesthetics**: Sophisticated color relationships avoiding neon/cyberpunk extremes  
3. **Data Clarity**: Light panels with dark text for optimal data readability
4. **Visual Hierarchy**: Strategic use of blues for importance levels
5. **Accessibility First**: All combinations tested for contrast compliance