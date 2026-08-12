# Design QA — canonical Elephant artwork

- Source visual truth: `/Users/visheshyadav/Downloads/Group 197.png`
- Rendered desktop evidence: `site/implementation-desktop.png`
- Rendered mobile evidence: `site/implementation-mobile.png`
- Source pixels: 2994 × 2994, sRGB, RGBA
- Desktop full-page capture: 1425 × 3204 pixels at a 1440 × 900 CSS viewport, device scale factor 1
- Desktop focused capture: 1440 × 900 pixels at the same CSS viewport and density
- Mobile full-page capture: 375 × 5288 pixels at a 390 × 844 CSS viewport, device scale factor 1
- Mobile focused capture: 390 × 1200 pixels at the same CSS viewport and density
- State: landing page, top route; default Claude Code tab in visual evidence

## Findings

No actionable P0, P1, or P2 differences remain.

- Fonts and typography: unchanged from the approved landing page. The artwork replacement does not alter heading hierarchy, wrapping, optical weight, or small-label legibility.
- Spacing and layout rhythm: the square source is framed inside the existing hero slot without changing the page grid. The desktop image is shifted 8% upward and the mobile image 17% upward so the complete feet clear the section boundary. Both breakpoints retain their established spacing and have no horizontal overflow.
- Colors and visual tokens: the original black engraving remains full black. All `invert`, `grayscale`, `contrast`, and brightness-affecting filters were removed. `mix-blend-mode: multiply` only lets the source's white canvas adopt the cream paper color; it does not brighten the black ink.
- Image quality and asset fidelity: `site/public/elephant.png` and `assets/elephant.png` are byte-for-byte copies of the supplied `Group 197.png` (SHA-256 `9e39c19480534e1b34915c0661104118c83601c642a0ecfe0800865836ea8b32`). The hero, header mark, checkpoint, footer, README, and social preview now use the same canonical source.
- Copy and content: unchanged.

## Comparison evidence

- Full-view comparison: the source, 1440-pixel desktop capture, and 390-pixel mobile capture were opened together. The elephant's engraving is crisp and dark at both breakpoints, with no gray wash or glow from the previous asset.
- Focused region comparison: `site/implementation-hero.png` and `site/implementation-mobile-hero.png` isolate the responsive hero against the supplied source. The subject, raised trunk, toes, line work, and black tonal density remain visible; the section below no longer clips the feet.

## Interaction and runtime checks

- “Install Elephant” navigates to `#install`.
- The Codex install tab becomes selected and shows `codex plugin marketplace add vishesh9131/elephant`.
- Copy transitions to the visible “Copied” state.
- Browser console: no warnings or errors.
- Production build and all four Sites hosting tests pass.

## Comparison history

1. Initial P1: the landing page used the older dark-gradient elephant and CSS `invert(1) grayscale(1) contrast(...)`, producing the brightened/washed appearance. Fixed by replacing both canonical assets with the supplied original and deleting the filters.
2. Initial P2: the first direct replacement rendered too large in the desktop hero because the supplied canvas is square. Fixed by reducing the hero maximum width to 610px and shifting it 2% upward; post-fix desktop and mobile captures preserve the subject without changing surrounding layout.
3. Follow-up P2: the feet still touched and visually disappeared behind the next section. Fixed with an 8% upward desktop offset and a breakpoint-specific 17% mobile offset. Post-fix focused captures show the complete feet and toes above the section boundary.

## Follow-up polish

None required for this correction.

final result: passed
