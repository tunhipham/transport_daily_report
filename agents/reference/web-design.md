# Web Design — Reference

> Chỉ đọc file này khi tạo mới hoặc sửa dashboard UI (index.html). Không đọc khi chạy report bình thường.

---

## Design System & Tokens

- **Color palette**: HSL-based token system — không hardcode hex rời rạc
  - Primary: `hsl(220, 85%, 55%)` (xanh dương chuyên nghiệp)
  - Semantic: `--color-success`, `--color-warning`, `--color-danger`
  - Surface layers: `--bg-primary`, `--bg-secondary`, `--bg-elevated`
  - Dark mode: Override biến CSS duy nhất
- **Typography**: Modular scale (1.25 ratio) — `--fs-xs` → `--fs-3xl`
  - Font: `Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`
  - Monospace: `'JetBrains Mono', 'Fira Code', 'Consolas', monospace`
  - Tabular nums: `font-variant-numeric: tabular-nums`
- **Spacing**: 4px grid — `--space-1` (4px) → `--space-8` (32px)
- **Border radius**: `--radius-sm` (4px), `--radius-md` (8px), `--radius-lg` (12px)
- **Shadows**: `--shadow-sm`, `--shadow-md`, `--shadow-lg`

## Data Table Design

- Compact: line-height 1.4, padding `6px 12px`
- Zebra: `:nth-child(even)` với opacity thấp
- Sticky header: `position: sticky; top: 0` + `backdrop-filter: blur(8px)`
- Numbers: `text-align: right`, `tabular-nums`
- Conditional formatting: gradient colors (xanh=tốt, đỏ=chú ý)
- Status badges: pill shape `border-radius: 99px`
- Responsive: `overflow-x: auto` wrapper

## Chart Style (Chart.js)

- Dùng `datalabels` plugin — hiện số trên chart
- Grid lines: `rgba(0,0,0,0.06)`
- Font kế thừa design system
- `maintainAspectRatio: false` + container height cố định
- Palette 6-8 màu colorblind-safe
- Highlight: đậm item focus, mờ còn lại

## KPI Cards

- Grid: `auto-fill, minmax(200px, 1fr)`
- Hero metric: `font-size: 2rem; font-weight: 700`
- Trend: `▲ +5.2%` (xanh) / `▼ -3.1%` (đỏ)

## Layout

- Grid: `repeat(auto-fit, minmax(300px, 1fr))`
- Card: `padding: 24px`, `border-radius: 12px`, `box-shadow: var(--shadow-sm)`
- Max-width: `1400px; margin: 0 auto`
- Tab: horizontal + `border-bottom: 2px solid` active

## Polish

- Loading: skeleton placeholder (pulsing gray)
- Transitions: `all 0.2s ease`
- Hover cards: `translateY(-2px)` + shadow tăng
- Tooltip: `backdrop-filter: blur(12px)`
- Print: `@media print` ẩn nav, full-width, high-contrast

## Performance & Accessibility

- Critical CSS inline trong `<style>`
- Self-contained HTML (CSS + JS + data inline)
- Image-free: CSS gradient, SVG icon, emoji
- Semantic HTML: `<table>`, `<thead>`, `<th scope="col">`
- Color contrast ≥ 4.5:1 (WCAG AA)

## Color Coding (toàn hệ thống)

- KRC = `#2196F3` (blue), DRY = `#FF9800` (orange), ĐÔNG MÁT = `#00BCD4` (cyan)
- THỊT CÁ = `#E91E63` (pink), KFM = `#4CAF50` (green)

## Output Conventions

- Email HTML: inline CSS (không `<style>` block)
- Dashboard HTML: self-contained, mở offline được
- Vietnamese text: UTF-8, dấu đầy đủ
- Số: dùng dấu `,` (toLocaleString)
