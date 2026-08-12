# Design QA — canonical Elephant artwork

- Source visual truth: `/Users/visheshyadav/Downloads/Group 197.png`
- Rendered desktop evidence: `site/implementation-desktop.png`
- Rendered mobile evidence: `site/implementation-mobile.png`
- Source pixels: 2994 × 2994, sRGB, RGBA
- Desktop capture: 1440 × 3267 pixels at a 1440 × 900 CSS viewport, device scale factor 1
- Mobile capture: 390 × 3453 pixels at a 390 × 844 CSS viewport, device scale factor 1
- State: landing page, top route; Codex install tab selected in final full-page captures

## Findings

No actionable P0, P1, or P2 differences remain.

- Fonts and typography: unchanged from the approved landing page. The artwork replacement does not alter heading hierarchy, wrapping, optical weight, or small-label legibility.
- Spacing and layout rhythm: the square source is framed inside the existing hero slot without changing the page grid. Desktop and mobile retain their established spacing and have no horizontal overflow.
- Colors and visual tokens: the original black engraving remains full black. All `invert`, `grayscale`, `contrast`, and brightness-affecting filters were removed. `mix-blend-mode: multiply` only lets the source's white canvas adopt the cream paper color; it does not brighten the black ink.
- Image quality and asset fidelity: `site/public/elephant.png` and `assets/elephant.png` are byte-for-byte copies of the supplied `Group 197.png` (SHA-256 `9e39c19480534e1b34915c0661104118c83601c642a0ecfe0800865836ea8b32`). The hero, header mark, checkpoint, footer, README, and social preview now use the same canonical source.
- Copy and content: unchanged.

## Comparison evidence

- Full-view comparison: the source, 1440-pixel desktop capture, and 390-pixel mobile capture were opened together. The elephant's engraving is crisp and dark at both breakpoints, with no gray wash or glow from the previous asset.
- Focused region comparison: `site/implementation-hero.png` isolates the desktop hero against the supplied source. The subject, line work, raised trunk, and black tonal density match; the page applies only responsive scale and crop.

## Interaction and runtime checks

- “Install Elephant” navigates to `#install`.
- The Codex install tab becomes selected and shows `codex plugin marketplace add vishesh9131/elephant`.
- Copy transitions to the visible “Copied” state.
- Browser console: no warnings or errors.
- Production build and all four Sites hosting tests pass.

## Comparison history

1. Initial P1: the landing page used the older dark-gradient elephant and CSS `invert(1) grayscale(1) contrast(...)`, producing the brightened/washed appearance. Fixed by replacing both canonical assets with the supplied original and deleting the filters.
2. Initial P2: the first direct replacement rendered too large in the desktop hero because the supplied canvas is square. Fixed by reducing the hero maximum width to 610px and shifting it 2% upward; post-fix desktop and mobile captures preserve the subject without changing surrounding layout.

## Follow-up polish

None required for this correction.

final result: passed
