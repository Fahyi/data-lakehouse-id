# Design Document: Data Lakehouse Indonesia

## 1. Profile Baseline Declaration
- **Profile selection**: `profiles/academic.md`
- **Selection rationale**: Presentasi ini adalah proyek akhir Data Engineering dengan karakter akademik/technical — memerlukan struktur yang jelas, data-driven, dan profesional.
- **Referenced dimensions**: Design philosophy (content is king), information density (high), color guidance (restrained, professional), font guidance (sans-serif hierarchy), content expression techniques (flowcharts, bullet lists, data tables).
- **Deviation notes**: Tidak ada logo universitas yang disebutkan; tidak ada daftar pustaka formal karena ini adalah project report bukan thesis defense. Lebih fokus pada arsitektur sistem dan sumber data.

## 2. Style Baseline Declaration
- **Style anchor**: Nature/Science journal figure style + McKinsey report clarity
- **Referenced dimensions**: Referensi dari Nature/Science untuk chart styling dan data presentation; referensi dari McKinsey untuk layout bersih dan hierarki informasi yang jelas.
- **Explanation**: Presentasi ini menggabungkan kerapihan akademik dengan kejelasan consulting report untuk menjelaskan arsitektur data lakehouse.

## 3. Style Details

### Color Design Principles
- **Overall tendency**: Conservative & steady — cocok untuk technical/academic presentation
- **Temperature**: Cool-neutral, mineral tone
- **Primary color**: #1B4D3E (deep forest green) — merepresentasikan data, growth, Indonesia (green landscape), professionalism
- **Background**: #F5F5F0 (warm off-white) — menghindari white yang terlalu plain, memberikan kesan papery academic
- **Text color**: #1A1A1A (near-black) — high contrast untuk readability
- **Secondary**: #6B7B6E (muted sage) — untuk dividers, secondary info, subtle decorations
- **Accent**: #C49A3B (warm gold) — digunakan sangat restrain untuk highlight key data points only

### Font Usage Principles
- **Title font**: "QuattrocentoSans, MiSans" — clean, academic, highly legible
- **Body font**: "QuattrocentoSans, MiSans" — consistent dengan title
- **Font size hierarchy**:
  - Cover title: 40px
  - Page title: 28px
  - Subtitle/section headers: 22px
  - Body text: 18-20px
  - Footnotes/annotations: 12-14px

### Text Box and Container Styles
- Content separation menggunakan whitespace dan font size hierarchy
- Cards dengan sharp corners, no border, subtle fill (#E8E8E0) untuk grouping informasi
- Decorative elements: thin horizontal lines (1-2px) menggunakan secondary color

### Image Style
- **Icons**: Solid icons (fas), used sparingly untuk section markers
- **Tables**: Minimal style, three-line table aesthetic, header dengan primary color fill
- **Charts**: Clean, minimal, flat style dengan distinguishable colors dari palette
- **Diagrams**: Flat geometric shapes untuk arsitektur flow

## 4. Layout System

### Global Layout Characteristics
- **Page size**: 1280 x 720 (16:9)
- **Page margins**: 60px left/right, 50px top, 40px bottom
- **Unified elements**: 
  - Thin top accent line (4px, primary color) spanning full width at y=0
  - Page number bottom-right corner (12px, secondary color)
  - Section label top-left (12px, secondary color) untuk content pages

### Special Page Layouts
- **Cover**: Centered layout with large title, subtitle below, clean and spacious
- **Closing**: Centered layout with team member information

### Content Page Layout Patterns
- **Slide 2 (Rencana Analisis)**: Three-column card layout untuk Background, Problem, Solution
- **Slide 3 (Sumber Data)**: Two-column layout — left for WikiData, right for BPS
- **Slide 4 (Arsitektur)**: Top title + diagram/flowchart area (dominant) + bottom annotations

## 5. Style Usage Rules
- `$title` style: Cover title, page titles
- `$subtitle` style: Subtitles, section headers within pages
- `$body` style: All body text, bullet points, descriptions
- `$caption` style: Footnotes, annotations, page numbers, source citations
- `$primary` color: Title text, headers, accent lines, key highlights
- `$secondary` color: Subtitles, dividers, secondary text, page numbers
- `$accent` color: Key data points, important metrics only (restrained use)
- `$background` color: Page backgrounds
- `$surface` color: Card backgrounds, table alternate rows
- `$text` color: Body text

## 6. Risk Prohibitions
- [ ] NO gradient backgrounds or flashy textures
- [ ] NO decorative illustrations — only data-driven diagrams
- [ ] NO font sizes below 12px for any text
- [ ] NO body text below 18px
- [ ] NO excessive use of accent color (gold) — max 2-3 elements per page
- [ ] NO blue/purple/cyan color schemes
- [ ] NO left-right misaligned layouts
- [ ] NO text-only pages without visual structure
- [ ] NO missing data source annotations on data slides
- [ ] NO overly dense text — max 4-5 bullet points per section

## 7. Theme Definition

```yaml
theme:
  colors:
    primary: "#1B4D3E"
    secondary: "#6B7B6E"
    accent: "#C49A3B"
    background: "#F5F5F0"
    surface: "#E8E8E0"
    text: "#1A1A1A"
  textStyles:
    title:
      fontSize: 40
      color: "$primary"
      fontFamily: "QuattrocentoSans, MiSans"
      fontStyle: normal
      lineHeight: 1.2
    subtitle:
      fontSize: 22
      color: "$secondary"
      fontFamily: "QuattrocentoSans, MiSans"
      lineHeight: 1.3
    body:
      fontSize: 18
      color: "$text"
      fontFamily: "QuattrocentoSans, MiSans"
      lineHeight: 1.6
    caption:
      fontSize: 12
      color: "$secondary"
      fontFamily: "QuattrocentoSans, MiSans"
      lineHeight: 1.4
  tableStyles:
    default:
      fontSize: 16
      fontFamily: "QuattrocentoSans, MiSans"
      headerFill: "$primary"
      headerColor: "#FFFFFF"
      headerBold: true
      bodyFill: ["$background", "$surface"]
      bodyColor: "$text"
      border:
        style: solid
        width: 1
        color: "$secondary"
```
