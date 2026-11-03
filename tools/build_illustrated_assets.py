"""Generate original, lightweight SVG illustrations and subject graphics for the Pi UI.

Design Language:
- Editorial, warm, tactile educational device UI
- Paper-cut / printed-book & field naturalist influence
- Palette: Deep Ink (#23302D), Paper (#F5EFE3), Warm Surface (#FBF7EF),
  Forest Teal (#27685E), Soft Sage (#A9C4B1), Terracotta (#C76848),
  Warm Gold (#D5A64A), Soft Sky (#A9C7CF), Border (#D8D0C1).
- Ultra-lightweight vectors optimized for Raspberry Pi Zero 2 W QML rendering.
"""

from pathlib import Path

ASSET_ROOT = Path("app/ui_qt/assets")
ILLUST_DIR = ASSET_ROOT / "illustrations"
SUBJECT_DIR = ASSET_ROOT / "subjects"
DECOR_DIR = ASSET_ROOT / "decorative"

ILLUST_DIR.mkdir(parents=True, exist_ok=True)
SUBJECT_DIR.mkdir(parents=True, exist_ok=True)
DECOR_DIR.mkdir(parents=True, exist_ok=True)

GRAPHICS = {
    # -------------------------------------------------------------------------
    # HERO ILLUSTRATIONS
    # -------------------------------------------------------------------------
    ILLUST_DIR / "home_hero.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180" width="320" height="180">
  <defs>
    <clipPath id="paper-cut">
      <rect x="0" y="0" width="320" height="180" rx="14"/>
    </clipPath>
  </defs>
  <g clip-path="url(#paper-cut)">
    <!-- Soft landscape background hill layers -->
    <path d="M-20 190 Q60 110 160 145 T340 130 L340 190 Z" fill="#E8F1EC"/>
    <path d="M0 190 Q90 135 200 160 T340 150 L340 190 Z" fill="#DDE9E2"/>
    
    <!-- Warm sun / celestial orb -->
    <circle cx="250" cy="55" r="26" fill="#FAF0D7"/>
    <circle cx="250" cy="55" r="20" fill="#F4E2B2"/>
    <circle cx="250" cy="55" r="14" fill="#D5A64A" opacity="0.85"/>
    <circle cx="250" cy="55" r="4" fill="#FBF7EF"/>

    <!-- Distant constellation stars -->
    <circle cx="65" cy="35" r="2" fill="#D5A64A"/>
    <circle cx="110" cy="25" r="1.5" fill="#D5A64A"/>
    <circle cx="160" cy="40" r="2.5" fill="#D5A64A"/>
    <path d="M65 35 L110 25 L160 40" stroke="#D5A64A" stroke-width="0.8" stroke-dasharray="2,2" fill="none" opacity="0.6"/>

    <!-- Botanical laurel & ferns on left -->
    <path d="M15 175 Q35 125 45 95 Q52 110 50 140 Q45 165 40 180" fill="#27685E"/>
    <path d="M35 120 Q55 105 70 112 Q60 125 40 130" fill="#A9C4B1"/>
    <path d="M25 145 Q45 135 60 140 Q50 155 30 155" fill="#A9C4B1"/>
    <path d="M38 100 Q50 85 62 90 Q55 105 40 108" fill="#78A690"/>

    <!-- Study desk & book pedestal -->
    <ellipse cx="165" cy="165" rx="100" ry="16" fill="#D5CBBB" opacity="0.7"/>

    <!-- Large Open Field Notebook / Study Book -->
    <!-- Left page -->
    <path d="M165 155 C145 153 115 145 95 130 L100 85 C120 100 148 108 165 110 Z" fill="#FBF7EF" stroke="#23302D" stroke-width="2"/>
    <!-- Right page -->
    <path d="M165 155 C185 153 215 145 235 130 L230 85 C210 100 182 108 165 110 Z" fill="#FBF7EF" stroke="#23302D" stroke-width="2"/>
    <!-- Book spine & bookmark ribbon -->
    <path d="M165 110 L165 156" stroke="#23302D" stroke-width="2.5"/>
    <path d="M165 155 Q168 168 178 172 Q182 165 172 155" fill="#C76848"/>

    <!-- Text line impressions on pages -->
    <path d="M110 102 Q130 112 155 118 M108 112 Q128 122 155 128 M106 122 Q126 132 155 138" stroke="#A9C4B1" stroke-width="1.5" stroke-linecap="round"/>
    <path d="M175 118 Q200 112 220 102 M175 128 Q200 122 218 112 M175 138 Q200 132 216 122" stroke="#A9C4B1" stroke-width="1.5" stroke-linecap="round"/>

    <!-- Brass Field Telescope on wooden tripod (Right side) -->
    <!-- Tripod legs -->
    <line x1="215" y1="110" x2="195" y2="165" stroke="#23302D" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="215" y1="110" x2="240" y2="165" stroke="#23302D" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="215" y1="110" x2="218" y2="160" stroke="#68716B" stroke-width="2" stroke-linecap="round"/>
    <!-- Mount -->
    <circle cx="215" cy="108" r="4" fill="#D5A64A" stroke="#23302D" stroke-width="1.5"/>
    <!-- Barrel pointing up-right toward sun/stars -->
    <path d="M190 125 L245 80 L250 86 L195 131 Z" fill="#D5A64A" stroke="#23302D" stroke-width="2"/>
    <path d="M243 78 L255 68 L260 74 L248 84 Z" fill="#27685E" stroke="#23302D" stroke-width="1.5"/>
    <ellipse cx="258" cy="71" rx="2" ry="4" fill="#A9C7CF" stroke="#23302D" stroke-width="1"/>

    <!-- Scientific Atom / Learning Compass Accent (Floating) -->
    <ellipse cx="90" cy="55" rx="16" ry="6" fill="none" stroke="#27685E" stroke-width="1.5" transform="rotate(-25 90 55)"/>
    <ellipse cx="90" cy="55" rx="16" ry="6" fill="none" stroke="#27685E" stroke-width="1.5" transform="rotate(35 90 55)"/>
    <circle cx="90" cy="55" r="3" fill="#C76848"/>
  </g>
</svg>""",

    ILLUST_DIR / "home_resume.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 140" width="160" height="140">
  <!-- Subtle warm badge backing -->
  <rect x="10" y="10" width="140" height="120" rx="18" fill="#F4EDE0" stroke="#D8D0C1" stroke-width="1.5"/>
  <rect x="16" y="16" width="128" height="108" rx="14" fill="#FBF7EF"/>

  <!-- Botanical branch curving behind book -->
  <path d="M35 110 Q45 60 75 35" fill="none" stroke="#27685E" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M48 75 Q60 65 65 72 Q55 82 48 75" fill="#A9C4B1" stroke="#23302D" stroke-width="1"/>
  <path d="M58 55 Q72 45 78 52 Q68 62 58 55" fill="#A9C4B1" stroke="#23302D" stroke-width="1"/>
  <path d="M70 38 Q84 28 90 35 Q80 45 70 38" fill="#27685E" stroke="#23302D" stroke-width="1"/>

  <!-- Thick Bound Textbook -->
  <rect x="52" y="42" width="68" height="74" rx="4" fill="#27685E" stroke="#23302D" stroke-width="2"/>
  <path d="M52 42 L60 36 L128 36 L120 42 Z" fill="#1F554D" stroke="#23302D" stroke-width="1.5"/>
  <path d="M120 42 L128 36 L128 110 L120 116 Z" fill="#E8DEC9" stroke="#23302D" stroke-width="1.5"/>

  <!-- Gold Embossed Crest on cover -->
  <circle cx="86" cy="74" r="14" fill="#FBF7EF" stroke="#D5A64A" stroke-width="1.5"/>
  <polygon points="86 64 90 71 98 71 92 76 94 83 86 79 78 83 80 76 74 71 82 71" fill="#D5A64A"/>

  <!-- Bookmark Ribbon hanging out -->
  <path d="M82 116 L82 128 L86 124 L90 128 L90 116 Z" fill="#C76848" stroke="#23302D" stroke-width="1"/>
</svg>""",

    ILLUST_DIR / "laurel_achievement.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 140" width="180" height="140">
  <!-- Sunburst glow rays -->
  <g stroke="#FAF0D7" stroke-width="2" stroke-linecap="round" opacity="0.8">
    <line x1="90" y1="35" x2="90" y2="18"/>
    <line x1="110" y1="40" x2="122" y2="28"/>
    <line x1="125" y1="55" x2="140" y2="48"/>
    <line x1="70" y1="40" x2="58" y2="28"/>
    <line x1="55" y1="55" x2="40" y2="48"/>
  </g>

  <!-- Central Academic Medallion -->
  <circle cx="90" cy="65" r="34" fill="#FBF7EF" stroke="#23302D" stroke-width="2"/>
  <circle cx="90" cy="65" r="28" fill="#F9F3E5" stroke="#D5A64A" stroke-width="2" stroke-dasharray="3,2"/>
  <!-- Wisdom 5-Point Star -->
  <polygon points="90 48 94 59 105 59 97 66 100 77 90 70 80 77 83 66 75 59 86 59" fill="#D5A64A" stroke="#23302D" stroke-width="1.5"/>

  <!-- Laurel Wreath Leaves (Left Branch) -->
  <path d="M90 118 C55 115 32 85 40 45" fill="none" stroke="#27685E" stroke-width="2.5" stroke-linecap="round"/>
  <!-- Left laurel pairs -->
  <ellipse cx="38" cy="52" rx="7" ry="4" transform="rotate(-30 38 52)" fill="#A9C4B1" stroke="#23302D" stroke-width="1.2"/>
  <ellipse cx="44" cy="68" rx="8" ry="4" transform="rotate(-15 44 68)" fill="#27685E" stroke="#23302D" stroke-width="1.2"/>
  <ellipse cx="54" cy="85" rx="8" ry="4" transform="rotate(10 54 85)" fill="#A9C4B1" stroke="#23302D" stroke-width="1.2"/>
  <ellipse cx="68" cy="102" rx="8" ry="4" transform="rotate(35 68 102)" fill="#27685E" stroke="#23302D" stroke-width="1.2"/>

  <!-- Laurel Wreath Leaves (Right Branch) -->
  <path d="M90 118 C125 115 148 85 140 45" fill="none" stroke="#27685E" stroke-width="2.5" stroke-linecap="round"/>
  <!-- Right laurel pairs -->
  <ellipse cx="142" cy="52" rx="7" ry="4" transform="rotate(30 142 52)" fill="#A9C4B1" stroke="#23302D" stroke-width="1.2"/>
  <ellipse cx="136" cy="68" rx="8" ry="4" transform="rotate(15 136 68)" fill="#27685E" stroke="#23302D" stroke-width="1.2"/>
  <ellipse cx="126" cy="85" rx="8" ry="4" transform="rotate(-10 126 85)" fill="#A9C4B1" stroke="#23302D" stroke-width="1.2"/>
  <ellipse cx="112" cy="102" rx="8" ry="4" transform="rotate(-35 112 102)" fill="#27685E" stroke="#23302D" stroke-width="1.2"/>

  <!-- Tied Silk Ribbon at bottom -->
  <path d="M72 118 C82 112 98 112 108 118 L114 134 L102 128 L94 136 L90 122 L86 136 L78 128 L66 134 Z" fill="#C76848" stroke="#23302D" stroke-width="1.5"/>
  <circle cx="90" cy="118" r="4" fill="#D5A64A" stroke="#23302D" stroke-width="1"/>
</svg>""",

    ILLUST_DIR / "empty_shelf.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 130" width="180" height="130">
  <!-- Wooden bookshelf tier -->
  <rect x="15" y="98" width="150" height="12" rx="2" fill="#D8D0C1" stroke="#23302D" stroke-width="2"/>
  <path d="M25 110 L25 125 M155 110 L155 125" stroke="#23302D" stroke-width="2.5" stroke-linecap="round"/>

  <!-- Left Bookend and Books -->
  <rect x="25" y="45" width="12" height="53" rx="2" fill="#27685E" stroke="#23302D" stroke-width="1.5"/>
  <rect x="39" y="52" width="10" height="46" rx="2" fill="#C76848" stroke="#23302D" stroke-width="1.5"/>
  <rect x="51" y="40" width="14" height="58" rx="2" fill="#D5A64A" stroke="#23302D" stroke-width="1.5"/>

  <!-- Antique Table Globe (Middle right) -->
  <circle cx="125" cy="55" r="22" fill="#EBF3F5" stroke="#23302D" stroke-width="1.5"/>
  <!-- Continents in sage -->
  <path d="M115 48 Q125 45 130 52 Q125 62 115 58 Z" fill="#A9C4B1"/>
  <path d="M128 60 Q138 65 132 72 Q122 70 128 60 Z" fill="#A9C4B1"/>
  <!-- Axis and Stand -->
  <path d="M102 55 A24 24 0 0 0 138 78 L138 88 L112 88 L112 98 L138 98" fill="none" stroke="#23302D" stroke-width="2"/>

  <!-- Warm sparkling star indicating open space to fill -->
  <g transform="translate(82, 50)">
    <polygon points="0 -12 3 -3 12 0 3 3 0 12 -3 3 -12 0 -3 -3" fill="#D5A64A"/>
    <circle cx="0" cy="0" r="2" fill="#FBF7EF"/>
  </g>
</svg>""",

    ILLUST_DIR / "recovery_guide.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 140" width="160" height="140">
  <!-- Soft warm lantern glow -->
  <circle cx="80" cy="65" r="42" fill="#FAF3E4" opacity="0.8"/>
  <circle cx="80" cy="65" r="28" fill="#F5E4B8" opacity="0.9"/>

  <!-- Field Study Lantern -->
  <!-- Top ring and cap -->
  <ellipse cx="80" cy="30" rx="14" ry="4" fill="#C76848" stroke="#23302D" stroke-width="2"/>
  <path d="M74 30 C74 18 86 18 86 30" fill="none" stroke="#23302D" stroke-width="2.5"/>
  <!-- Glass globe with glowing flame -->
  <path d="M68 34 L64 78 Q80 88 96 78 L92 34 Z" fill="#FAF6EC" stroke="#23302D" stroke-width="2"/>
  <!-- Candle flame -->
  <path d="M80 50 Q85 62 80 68 Q75 62 80 50 Z" fill="#D5A64A" stroke="#C76848" stroke-width="1"/>
  <circle cx="80" cy="64" r="3" fill="#C76848"/>
  <!-- Lantern base -->
  <rect x="62" y="78" width="36" height="10" rx="2" fill="#C76848" stroke="#23302D" stroke-width="2"/>

  <!-- Open Field Map / Journal underneath -->
  <path d="M35 110 L75 98 L125 106 L85 120 Z" fill="#FBF7EF" stroke="#23302D" stroke-width="1.8"/>
  <line x1="75" y1="98" x2="85" y2="120" stroke="#D8D0C1" stroke-width="1.5"/>
</svg>""",

    ILLUST_DIR / "device_pairing.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 130" width="180" height="130">
  <!-- Radiating connection wave arches -->
  <path d="M90 70 A30 30 0 0 1 140 70" fill="none" stroke="#A9C7CF" stroke-width="2" stroke-dasharray="3,3"/>
  <path d="M85 70 A45 45 0 0 1 155 70" fill="none" stroke="#27685E" stroke-width="2" stroke-dasharray="4,4" opacity="0.7"/>

  <!-- Raspberry Pi Study Buddy Device (Left) -->
  <rect x="25" y="45" width="58" height="42" rx="6" fill="#FBF7EF" stroke="#23302D" stroke-width="2"/>
  <rect x="30" y="50" width="48" height="32" rx="3" fill="#27685E"/>
  <!-- Screen illustration -->
  <rect x="34" y="54" width="30" height="4" rx="1" fill="#FBF7EF"/>
  <rect x="34" y="62" width="22" height="4" rx="1" fill="#A9C4B1"/>
  <circle cx="68" cy="74" r="4" fill="#D5A64A"/>

  <!-- Cloud / Web Knowledge Hub (Right) -->
  <path d="M125 65 A12 12 0 0 1 145 55 A16 16 0 0 1 168 65 A10 10 0 0 1 162 82 L125 82 A10 10 0 0 1 125 65 Z" fill="#FBF7EF" stroke="#23302D" stroke-width="2"/>
  <!-- Keyhole icon inside cloud -->
  <circle cx="145" cy="68" r="3" fill="#27685E"/>
  <polygon points="144 69 146 69 147 74 143 74" fill="#27685E"/>
</svg>""",

    # -------------------------------------------------------------------------
    # SUBJECT GRAPHICS
    # -------------------------------------------------------------------------
    SUBJECT_DIR / "biology.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="80" height="80">
  <!-- Subtle circular badge background -->
  <circle cx="40" cy="40" r="38" fill="#EDF5F1" stroke="#A9C4B1" stroke-width="1.5"/>

  <!-- Stylized Botanical Leaf -->
  <path d="M22 62 C22 35 48 18 60 16 C58 35 45 58 22 62 Z" fill="#27685E" stroke="#23302D" stroke-width="1.8"/>
  <!-- Leaf veins -->
  <path d="M24 60 C38 45 48 32 58 18" stroke="#A9C4B1" stroke-width="1.5" fill="none"/>
  <path d="M34 49 Q42 45 46 48" stroke="#A9C4B1" stroke-width="1.2" fill="none"/>
  <path d="M42 38 Q50 34 54 37" stroke="#A9C4B1" stroke-width="1.2" fill="none"/>

  <!-- Plant/Animal Cell Structure with Nucleus (Bottom Left) -->
  <circle cx="28" cy="30" r="14" fill="#FBF7EF" stroke="#23302D" stroke-width="1.5"/>
  <circle cx="28" cy="30" r="6" fill="#A9C4B1" stroke="#23302D" stroke-width="1.2"/>
  <circle cx="29" cy="29" r="2" fill="#27685E"/>

  <!-- Small DNA double helix rungs (Right side) -->
  <g stroke="#C76848" stroke-width="1.5" stroke-linecap="round">
    <line x1="52" y1="50" x2="64" y2="46"/>
    <line x1="54" y1="58" x2="66" y2="54"/>
    <line x1="56" y1="66" x2="68" y2="62"/>
    <circle cx="52" cy="50" r="1.5" fill="#C76848"/>
    <circle cx="64" cy="46" r="1.5" fill="#C76848"/>
    <circle cx="54" cy="58" r="1.5" fill="#C76848"/>
    <circle cx="66" cy="54" r="1.5" fill="#C76848"/>
  </g>
</svg>""",

    SUBJECT_DIR / "chemistry.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="80" height="80">
  <circle cx="40" cy="40" r="38" fill="#FDF3EE" stroke="#E6B8A5" stroke-width="1.5"/>

  <!-- Bohr Model Atomic Orbit Rings -->
  <ellipse cx="40" cy="40" rx="32" ry="12" fill="none" stroke="#D5A64A" stroke-width="1.2" stroke-dasharray="3,2" transform="rotate(-30 40 40)"/>
  <ellipse cx="40" cy="40" rx="32" ry="12" fill="none" stroke="#D5A64A" stroke-width="1.2" stroke-dasharray="3,2" transform="rotate(30 40 40)"/>
  <!-- Orbiting electrons -->
  <circle cx="16" cy="28" r="2.5" fill="#D5A64A"/>
  <circle cx="64" cy="52" r="2.5" fill="#D5A64A"/>

  <!-- Erlenmeyer Chemistry Flask -->
  <path d="M34 16 L46 16 L46 28 L58 56 C60 62 56 66 48 66 L32 66 C24 66 20 62 22 56 L34 28 Z" fill="#FBF7EF" stroke="#23302D" stroke-width="2"/>
  <!-- Flask Lip -->
  <line x1="32" y1="16" x2="48" y2="16" stroke="#23302D" stroke-width="2" stroke-linecap="round"/>
  <!-- Liquid Solution in Terracotta -->
  <path d="M26 48 Q40 46 54 48 L57 56 C58 60 55 64 48 64 L32 64 C25 64 22 60 23 56 Z" fill="#C76848"/>
  
  <!-- Effervescent chemical reaction bubbles -->
  <circle cx="36" cy="54" r="2" fill="#FBF7EF"/>
  <circle cx="44" cy="56" r="3" fill="#FBF7EF"/>
  <circle cx="39" cy="38" r="2" fill="#C76848"/>
  <circle cx="42" cy="24" r="2.5" fill="#D5A64A"/>

  <!-- Molecular Hexagonal Bond Node -->
  <circle cx="62" cy="24" r="4" fill="#C76848" stroke="#23302D" stroke-width="1.5"/>
  <line x1="62" y1="28" x2="62" y2="38" stroke="#23302D" stroke-width="1.5"/>
  <circle cx="62" cy="40" r="3" fill="#27685E" stroke="#23302D" stroke-width="1.5"/>
</svg>""",

    SUBJECT_DIR / "mathematics.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="80" height="80">
  <circle cx="40" cy="40" r="38" fill="#FBF6E9" stroke="#E5CE93" stroke-width="1.5"/>

  <!-- Cartesian Coordinate Axes & Parabola Function -->
  <line x1="14" y1="58" x2="68" y2="58" stroke="#D8D0C1" stroke-width="1.5"/>
  <line x1="22" y1="14" x2="22" y2="68" stroke="#D8D0C1" stroke-width="1.5"/>
  <!-- Smooth quadratic curve -->
  <path d="M22 58 Q42 58 62 18" fill="none" stroke="#27685E" stroke-width="2" stroke-linecap="round"/>

  <!-- Drafting Compass (Brass / Ink) -->
  <!-- Top pivot hinge -->
  <circle cx="44" cy="20" r="5" fill="#D5A64A" stroke="#23302D" stroke-width="2"/>
  <circle cx="44" cy="20" r="2" fill="#23302D"/>
  <line x1="44" y1="12" x2="44" y2="15" stroke="#23302D" stroke-width="2.5" stroke-linecap="round"/>
  <!-- Compass left needle leg -->
  <line x1="42" y1="24" x2="28" y2="62" stroke="#23302D" stroke-width="2.5" stroke-linecap="round"/>
  <!-- Compass right lead leg -->
  <line x1="46" y1="24" x2="60" y2="62" stroke="#D5A64A" stroke-width="2.5" stroke-linecap="round"/>
  <!-- Adjustment arc rule -->
  <path d="M33 46 A18 18 0 0 1 55 46" fill="none" stroke="#23302D" stroke-width="1.5"/>

  <!-- Geometry Triangle / Pi Symbol Motif -->
  <polygon points="56 36 68 56 46 56" fill="none" stroke="#C76848" stroke-width="1.5" stroke-dasharray="2,2"/>
</svg>""",

    SUBJECT_DIR / "science.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="80" height="80">
  <circle cx="40" cy="40" r="38" fill="#F0F6F7" stroke="#B8D5DB" stroke-width="1.5"/>

  <!-- Ringed Planet (Saturn) -->
  <circle cx="52" cy="28" r="11" fill="#D5A64A" stroke="#23302D" stroke-width="1.5"/>
  <ellipse cx="52" cy="28" rx="20" ry="5" fill="none" stroke="#27685E" stroke-width="2" transform="rotate(-18 52 28)"/>

  <!-- Optical Prism refracting light -->
  <polygon points="32 38 18 64 46 64" fill="#FBF7EF" stroke="#23302D" stroke-width="2"/>
  <!-- Incoming white beam -->
  <line x1="8" y1="46" x2="25" y2="52" stroke="#68716B" stroke-width="2"/>
  <!-- Refracted colored rays -->
  <line x1="39" y1="54" x2="66" y2="50" stroke="#C76848" stroke-width="1.5"/>
  <line x1="40" y1="57" x2="68" y2="56" stroke="#D5A64A" stroke-width="1.5"/>
  <line x1="41" y1="60" x2="68" y2="62" stroke="#27685E" stroke-width="1.5"/>

  <!-- Constellation stars -->
  <circle cx="20" cy="22" r="2" fill="#D5A64A"/>
  <circle cx="34" cy="18" r="1.5" fill="#D5A64A"/>
</svg>""",

    SUBJECT_DIR / "english.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="80" height="80">
  <circle cx="40" cy="40" r="38" fill="#F6F3ED" stroke="#D8D0C1" stroke-width="1.5"/>

  <!-- Open hardback book -->
  <path d="M40 58 C30 55 18 50 14 42 L14 24 C20 30 32 34 40 36 Z" fill="#FBF7EF" stroke="#23302D" stroke-width="1.8"/>
  <path d="M40 58 C50 55 62 50 66 42 L66 24 C60 30 48 34 40 36 Z" fill="#FBF7EF" stroke="#23302D" stroke-width="1.8"/>
  <line x1="40" y1="36" x2="40" y2="58" stroke="#23302D" stroke-width="2"/>

  <!-- Quill Pen in deep forest ink -->
  <path d="M52 14 C48 24 38 42 36 50 L40 51 C42 43 54 26 56 16 Z" fill="#27685E" stroke="#23302D" stroke-width="1.2"/>
  <!-- Feather vane details -->
  <line x1="50" y1="22" x2="58" y2="24" stroke="#A9C4B1" stroke-width="1"/>
  <line x1="46" y1="30" x2="54" y2="32" stroke="#A9C4B1" stroke-width="1"/>

  <!-- Ink droplet -->
  <circle cx="35" cy="54" r="2" fill="#23302D"/>
</svg>""",

    SUBJECT_DIR / "general.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="80" height="80">
  <circle cx="40" cy="40" r="38" fill="#FBF7EF" stroke="#D8D0C1" stroke-width="1.5"/>

  <!-- Terrestrial Globe with graduation band -->
  <circle cx="38" cy="38" r="22" fill="#EBF3F5" stroke="#23302D" stroke-width="2"/>
  <!-- Latitude / Longitude arcs -->
  <ellipse cx="38" cy="38" rx="10" ry="22" fill="none" stroke="#A9C7CF" stroke-width="1.2"/>
  <line x1="16" y1="38" x2="60" y2="38" stroke="#A9C7CF" stroke-width="1.2"/>
  <!-- Stand & Base -->
  <path d="M38 12 A26 26 0 0 1 58 48 L64 56 L38 56" fill="none" stroke="#23302D" stroke-width="2"/>
  <rect x="30" y="60" width="22" height="6" rx="2" fill="#D5A64A" stroke="#23302D" stroke-width="1.5"/>
</svg>""",

    # -------------------------------------------------------------------------
    # DECORATIVE & CONFIDENCE SYMBOLS
    # -------------------------------------------------------------------------
    DECOR_DIR / "confidence_sure.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <!-- Solid Bullseye & 5-pointed star indicating absolute confidence -->
  <circle cx="32" cy="32" r="28" fill="#EEF5F0" stroke="#27685E" stroke-width="2"/>
  <circle cx="32" cy="32" r="19" fill="#27685E"/>
  <polygon points="32 18 35 27 44 27 37 32 40 41 32 36 24 41 27 32 20 27 29 27" fill="#FBF7EF"/>
</svg>""",

    DECOR_DIR / "confidence_not_sure.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <!-- Balanced dual scales indicating narrowed options -->
  <circle cx="32" cy="32" r="28" fill="#FAF5E9" stroke="#D5A64A" stroke-width="2"/>
  <!-- Fulcrum and beam -->
  <line x1="32" y1="20" x2="32" y2="44" stroke="#23302D" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="18" y1="25" x2="46" y2="25" stroke="#23302D" stroke-width="2.5" stroke-linecap="round"/>
  <circle cx="32" cy="22" r="3" fill="#D5A64A" stroke="#23302D" stroke-width="1.5"/>
  <!-- Left Pan -->
  <path d="M18 25 L14 36 L22 36 Z" fill="#D5A64A" stroke="#23302D" stroke-width="1.2"/>
  <!-- Right Pan -->
  <path d="M46 25 L42 36 L50 36 Z" fill="#D5A64A" stroke="#23302D" stroke-width="1.2"/>
  <rect x="24" y="44" width="16" height="5" rx="2" fill="#23302D"/>
</svg>""",

    DECOR_DIR / "confidence_guessing.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <!-- Exploratory compass rose indicating guess/untested -->
  <circle cx="32" cy="32" r="28" fill="#FDF3EE" stroke="#C76848" stroke-width="2"/>
  <!-- Compass 4-point star -->
  <polygon points="32 16 35 30 48 32 35 34 32 48 29 34 16 32 29 30" fill="#C76848" stroke="#23302D" stroke-width="1.5"/>
  <circle cx="32" cy="32" r="4" fill="#FBF7EF" stroke="#23302D" stroke-width="1.5"/>
</svg>""",

    DECOR_DIR / "paper_divider.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 16" width="240" height="16">
  <line x1="10" y1="8" x2="105" y2="8" stroke="#D8D0C1" stroke-width="1.5" stroke-linecap="round"/>
  <polygon points="120 2 125 8 120 14 115 8" fill="#27685E"/>
  <circle cx="109" cy="8" r="2" fill="#D5A64A"/>
  <circle cx="131" cy="8" r="2" fill="#D5A64A"/>
  <line x1="135" y1="8" x2="230" y2="8" stroke="#D8D0C1" stroke-width="1.5" stroke-linecap="round"/>
</svg>""",

    DECOR_DIR / "book_spine.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 12 80" width="12" height="80">
  <rect x="1" y="0" width="10" height="80" rx="3" fill="#27685E"/>
  <!-- Gold embossed ribs -->
  <line x1="1" y1="12" x2="11" y2="12" stroke="#D5A64A" stroke-width="2"/>
  <line x1="1" y1="38" x2="11" y2="38" stroke="#D5A64A" stroke-width="2"/>
  <line x1="1" y1="68" x2="11" y2="68" stroke="#D5A64A" stroke-width="2"/>
</svg>""",
}


def build_all():
    print(f"Building {len(GRAPHICS)} vector assets in {ASSET_ROOT}...")
    for path, content in GRAPHICS.items():
        path.write_text(content.strip(), encoding="utf-8")
        print(f"  + {path.relative_to(ASSET_ROOT)} ({len(content)} bytes)")
    print("Done! All original assets generated.")


if __name__ == "__main__":
    build_all()
