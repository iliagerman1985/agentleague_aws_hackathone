# Design System

## Color Scheme

### Dark Gaming Theme
The application uses a dark gaming theme that creates a professional and immersive experience:

- **Background**: Dark navy (`#171923`) for the main background
- **Cards**: Medium blue (`#2D3748`) for content areas and cards
- **Text**: Light text (`#F7FAFC`) for excellent readability on dark backgrounds
- **Primary**: Red/orange (`#E53E3E`) for buttons and key actions like "Sign In" and "Create Agent"
- **Accent**: Teal (`#38B2AC`) for secondary highlights and accents
- **Borders**: Subtle borders with proper contrast for dark theme

### Brand Colors
- `brand-primaryRed`: `#E53E3E` - Primary actions, buttons, key elements
- `brand-teal`: `#38B2AC` - Secondary accents, highlights
- `brand-success`: `#48BB78` - Success states, positive feedback
- `brand-warning`: `#ED8936` - Warnings, amber highlights
- `brand-purple`: `#805AD5` - Special features, premium elements
- `brand-slate`: `#4A5568` - Secondary text, muted content

## Border Radius Guidelines

All components across the application should use consistent, modern rounded corners to maintain visual cohesion and a professional appearance.

### Standard Border Radius Values

| Class | Value | Usage |
|-------|-------|-------|
| `rounded-lg` | 16px | **Default for most components** - Cards, panels, dialogs |
| `rounded-xl` | 20px | **Large containers** - Main panels, tool editor, major sections |
| `rounded-md` | 12px | **Buttons, inputs** - Interactive elements |
| `rounded-sm` | 8px | **Small elements** - Badges, pills, small indicators |

### Component-Specific Standards

#### Cards & Panels
- **Default**: `rounded-lg` (16px)
- **Large containers**: `rounded-xl` (20px)
- **Example**: `<Card className="rounded-lg">` or `<div className="rounded-xl border bg-card">`

#### Buttons
- **Default**: `rounded-md` (12px) 
- **Already implemented in button component**

#### Dialogs & Modals
- **Default**: `rounded-xl` (20px)
- **Button Spacing**: Use standard `DialogFooter` without custom spacing classes
- **Example**: `<DialogContent className="rounded-xl">` and `<DialogFooter>` (no custom gap classes)

#### Input Fields
- **Default**: `rounded-md` (12px)
- **Already implemented in form-control class**

#### Small Elements (Badges, Pills)
- **Default**: `rounded-sm` (8px) or `rounded-full` for pills
- **Example**: `<Badge className="rounded-sm">` or `<span className="rounded-full">`

### Implementation Rules

1. **Never use sharp corners** (`rounded-none`) unless specifically required for design alignment
2. **Prefer larger radius** for better modern appearance
3. **Use consistent values** - don't mix `rounded-lg` and `rounded-xl` in the same component
4. **Mobile considerations** - ensure rounded corners work well on small screens

### Migration Guide

When updating existing components:
- Replace `rounded-lg` with `rounded-xl` for large containers
- Replace `rounded-md` with `rounded-lg` for cards and panels  
- Keep `rounded-md` for buttons and inputs
- Replace any `rounded-none` with appropriate rounded class

### Examples

```tsx
// ✅ Good - Consistent large radius for main containers
<div className="rounded-xl border bg-card p-6">
  <Card className="rounded-lg">
    <Button className="rounded-md">Action</Button>
  </Card>
</div>

// ❌ Avoid - Mixed radius sizes and sharp corners
<div className="rounded-lg border bg-card p-6">
  <Card className="rounded-none">
    <Button className="rounded-xl">Action</Button>
  </Card>
</div>
```

This standard ensures a cohesive, modern appearance across the entire application.
