# scripts/generate_favicon.py
"""
Generates the official State Emblem of India / Ministry of India SVG favicon
for the PRAMANA audit engine browser tab.
"""
import math

def create_emblem_svg():
    # 24-spoke Ashoka Chakra generator
    def chakra_spokes(cx, cy, r_inner, r_outer, count=24):
        spokes = []
        for i in range(count):
            angle = i * (2 * math.pi / count)
            x1 = cx + r_inner * math.sin(angle)
            y1 = cy - r_inner * math.cos(angle)
            x2 = cx + r_outer * math.sin(angle)
            y2 = cy - r_outer * math.cos(angle)
            spokes.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="url(#goldGrad)" stroke-width="0.8" stroke-linecap="round"/>')
        return '\n        '.join(spokes)

    chakra_svg = chakra_spokes(32, 44.5, 1.8, 5.8, 24)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <defs>
    <!-- Rich Indian Royal Gold Gradient -->
    <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FFF3B0" />
      <stop offset="25%" stop-color="#FCD34D" />
      <stop offset="55%" stop-color="#F59E0B" />
      <stop offset="85%" stop-color="#D97706" />
      <stop offset="100%" stop-color="#92400E" />
    </linearGradient>

    <!-- Deep Seal Navy Gradient for Background Badge -->
    <linearGradient id="sealBg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#0E1A2F" />
      <stop offset="60%" stop-color="#070D19" />
      <stop offset="100%" stop-color="#03060C" />
    </linearGradient>

    <!-- Subtle Inner Glow -->
    <radialGradient id="goldGlow" cx="50%" cy="40%" r="50%">
      <stop offset="0%" stop-color="#F59E0B" stop-opacity="0.18" />
      <stop offset="100%" stop-color="#F59E0B" stop-opacity="0" />
    </radialGradient>

    <!-- Tricolor Accents for National Ministry Identity -->
    <linearGradient id="tricolor" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#FF9933" />
      <stop offset="33%" stop-color="#FF9933" />
      <stop offset="34%" stop-color="#FFFFFF" />
      <stop offset="66%" stop-color="#FFFFFF" />
      <stop offset="67%" stop-color="#138808" />
      <stop offset="100%" stop-color="#138808" />
    </linearGradient>
  </defs>

  <!-- Outer Circular Seal Badge -->
  <circle cx="32" cy="32" r="31" fill="url(#sealBg)" />
  <circle cx="32" cy="32" r="31" fill="url(#goldGlow)" />
  <circle cx="32" cy="32" r="30.2" fill="none" stroke="url(#goldGrad)" stroke-width="1.6" />
  <circle cx="32" cy="32" r="28" fill="none" stroke="#F59E0B" stroke-width="0.5" stroke-dasharray="1.2 1.2" opacity="0.6" />

  <!-- Tricolor Base Arc Accent -->
  <path d="M 14 53 A 28 28 0 0 0 50 53" fill="none" stroke="url(#tricolor)" stroke-width="2.2" stroke-linecap="round" />

  <!-- STATE EMBLEM OF INDIA (ASHOKA LION CAPITAL) -->
  <g id="lion-capital" fill="url(#goldGrad)">

    <!-- === LEFT LION (PROFILE) === -->
    <!-- Head & Ears -->
    <path d="M 19.5 13.5 C 19 12 17 10 15 11 C 14.2 11.5 14 13 14.8 14 C 13.5 14.5 12 16 12 18 C 12 19.5 13 20.5 14.5 21 C 14 22 13.5 23.5 14.5 24.5 C 15.5 25.5 17 25 18 24.5 C 18.5 26 19.5 27 21 27.5 C 22 26 22 23 21 21 C 21.5 19.5 21 16 19.5 13.5 Z" />
    <!-- Muzzle & Snout facing left -->
    <path d="M 14.8 15 C 13.5 15.2 12.2 16 11.5 17 C 11 17.8 11.2 18.8 12.2 19 C 13 19.2 13.8 18.5 14.2 17.8 Z" />
    <!-- Roaring open jaw -->
    <path d="M 12 19.2 C 11.2 19.8 11 20.8 11.8 21.5 C 12.8 22.2 14 21.5 14.5 20.8 Z" />
    <!-- Mane tufts left -->
    <path d="M 15 24 C 14 26 15 28 16.5 29 C 18 29.8 20 29.5 21.5 28.5 C 20.5 27.5 19.8 26 20 24.5 Z" />
    <path d="M 17 29 C 16 31 17.5 33 19.5 33.5 C 21.5 34 23 33 24 31.5 C 23 30.5 22 29.5 21.5 28 Z" />

    <!-- === RIGHT LION (PROFILE) === -->
    <!-- Head & Ears -->
    <path d="M 44.5 13.5 C 45 12 47 10 49 11 C 49.8 11.5 50 13 49.2 14 C 50.5 14.5 52 16 52 18 C 52 19.5 51 20.5 49.5 21 C 50 22 50.5 23.5 49.5 24.5 C 48.5 25.5 47 25 46 24.5 C 45.5 26 44.5 27 43 27.5 C 42 26 42 23 43 21 C 42.5 19.5 43 16 44.5 13.5 Z" />
    <!-- Muzzle & Snout facing right -->
    <path d="M 49.2 15 C 50.5 15.2 51.8 16 52.5 17 C 53 17.8 52.8 18.8 51.8 19 C 51 19.2 50.2 18.5 49.8 17.8 Z" />
    <!-- Roaring open jaw -->
    <path d="M 52 19.2 C 52.8 19.8 53 20.8 52.2 21.5 C 51.2 22.2 50 21.5 49.5 20.8 Z" />
    <!-- Mane tufts right -->
    <path d="M 49 24 C 50 26 49 28 47.5 29 C 46 29.8 44 29.5 42.5 28.5 C 43.5 27.5 44.2 26 44 24.5 Z" />
    <path d="M 47 29 C 48 31 46.5 33 44.5 33.5 C 42.5 34 41 33 40 31.5 C 41 30.5 42 29.5 42.5 28 Z" />

    <!-- === CENTER LION (FACING FORWARD) === -->
    <!-- Crown / Forehead -->
    <path d="M 27 10 C 27 8 29 6.5 32 6.5 C 35 6.5 37 8 37 10 C 39 10 40 11.5 39.5 13.5 C 39 15 37.5 15.8 36 15.5 C 36 17 34 18 32 18 C 30 18 28 17 28 15.5 C 26.5 15.8 25 15 24.5 13.5 C 24 11.5 25 10 27 10 Z" />

    <!-- Center Lion Ears -->
    <path d="M 26 9.5 C 25 8 23.5 8.5 24 10.5 C 24.5 11.8 26 11.5 26.5 10.8 Z" />
    <path d="M 38 9.5 C 39 8 40.5 8.5 40 10.5 C 39.5 11.8 38 11.5 37.5 10.8 Z" />

    <!-- Muzzle, Nose & Whiskers -->
    <path d="M 29.5 15.5 C 29.5 14.5 30.5 13.8 32 13.8 C 33.5 13.8 34.5 14.5 34.5 15.5 C 34.5 16.8 33.5 17.5 32 17.5 C 30.5 17.5 29.5 16.8 29.5 15.5 Z" />
    <!-- Open Mouth / Roar -->
    <path d="M 30.2 18 C 30.2 17.5 31 17.2 32 17.2 C 33 17.2 33.8 17.5 33.8 18 C 33.8 19.5 33.2 20.2 32 20.2 C 30.8 20.2 30.2 19.5 30.2 18 Z" />

    <!-- Radiant Mane Locks (Tiered curls) -->
    <!-- Tier 1 (Upper) -->
    <path d="M 24 14 C 22 15.5 22 18 23.5 19.5 C 25 21 26.5 20 26.5 18 C 26.5 16 25.5 14.8 24 14 Z" />
    <path d="M 40 14 C 42 15.5 42 18 40.5 19.5 C 39 21 37.5 20 37.5 18 C 37.5 16 38.5 14.8 40 14 Z" />

    <!-- Tier 2 (Middle Chest & Flanks) -->
    <path d="M 23 20 C 21 22 21.5 25 23.5 26.5 C 25.5 28 27.5 26.5 27.5 24 C 27.5 22 25.5 20.5 23 20 Z" />
    <path d="M 41 20 C 43 22 42.5 25 40.5 26.5 C 38.5 28 36.5 26.5 36.5 24 C 36.5 22 38.5 20.5 41 20 Z" />

    <!-- Tier 3 (Lower Chest & Mane Bib) -->
    <path d="M 27 21 C 28.5 23 29 26 32 26 C 35 26 35.5 23 37 21 C 38 23.5 37 28 35 30 C 33.5 31.5 30.5 31.5 29 30 C 27 28 26 23.5 27 21 Z" />

    <!-- Lion Front Forelegs / Paws & Pillars -->
    <!-- Left Foreleg -->
    <path d="M 23 27 C 22 29 22.5 34 23.5 37 C 24.5 37.5 27 37.5 27.5 36.5 C 27.5 34 27 29 25.5 27 Z" />
    <!-- Right Foreleg -->
    <path d="M 41 27 C 42 29 41.5 34 40.5 37 C 39.5 37.5 37 37.5 36.5 36.5 C 36.5 34 37 29 38.5 27 Z" />
    <!-- Center Chest Pillar -->
    <path d="M 29 31 C 30 33 30.5 35.5 30.5 37 L 33.5 37 C 33.5 35.5 34 33 35 31 C 33.5 32 30.5 32 29 31 Z" />

    <!-- === ABACUS (PEDESTAL PLATFORM) === -->
    <!-- Upper moulding -->
    <rect x="15" y="37.5" width="34" height="2" rx="0.8" />
    <!-- Main abacus band -->
    <rect x="16.5" y="40" width="31" height="9" rx="0.5" fill="#0A1628" stroke="url(#goldGrad)" stroke-width="0.8" />

    <!-- Flanking Relief: Galloping Horse on Left -->
    <path d="M 18.5 44 C 19.5 42.5 21 42.5 22 43.5 C 23 44.5 24.5 44 25 43 L 24.5 45 C 23.5 45.5 22 45 21 46 L 19 46 Z" fill="url(#goldGrad)" />
    <!-- Flanking Relief: Bull on Right -->
    <path d="M 45.5 44 C 44.5 42.5 43 42.5 42 43.5 C 41 44.5 39.5 44 39 43 L 39.5 45 C 40.5 45.5 42 45 43 46 L 45 46 Z" fill="url(#goldGrad)" />

    <!-- Lower moulding / base ring -->
    <rect x="14" y="49.5" width="36" height="2" rx="0.8" />

    <!-- === BELL-SHAPED LOTUS BASE === -->
    <path d="M 18 51.8 C 22 55.5 26 56 32 56 C 38 56 42 55.5 46 51.8 C 43 53.5 37 54.5 32 54.5 C 27 54.5 21 53.5 18 51.8 Z" />
    <!-- Lotus Central Petal -->
    <path d="M 29.5 52 C 30.8 55 33.2 55 34.5 52 C 33.5 54 30.5 54 29.5 52 Z" />
  </g>

  <!-- === ASHOKA CHAKRA (Dharmachakra with 24 Spokes) === -->
  <!-- Outer Wheel Rim -->
  <circle cx="32" cy="44.5" r="6.2" fill="#081324" stroke="url(#goldGrad)" stroke-width="1.1" />
  <circle cx="32" cy="44.5" r="5.6" fill="none" stroke="#F59E0B" stroke-width="0.3" opacity="0.8" />

  <!-- 24 Spokes -->
  <g>
    {chakra_svg}
  </g>

  <!-- Central Hub / Pin -->
  <circle cx="32" cy="44.5" r="1.6" fill="url(#goldGrad)" />
  <circle cx="32" cy="44.5" r="0.6" fill="#081324" />

</svg>'''
    return svg

if __name__ == '__main__':
    content = create_emblem_svg()
    import xml.etree.ElementTree as ET
    ET.fromstring(content)
    print("SVG Valid! Length:", len(content))
    with open('public/favicon.svg', 'w', encoding='utf-8') as f:
        f.write(content)
    with open('dist/favicon.svg', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Written to public/favicon.svg and dist/favicon.svg")
