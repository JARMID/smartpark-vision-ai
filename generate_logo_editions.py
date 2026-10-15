"""
Refined SVG generation for the 5 Editions of Logo 1: The Quantum Gate.
All gradients use gradientUnits="userSpaceOnUse" to avoid zero-width bounding box clipping.
All stems use geometric rects or complete paths for guaranteed rendering across all SVG engines.
"""
import os

EDITIONS = [
    {
        "id": "edition_1",
        "title": "Edition 1: The Dynamic Lift",
        "subtitle": "Kinetic Rising Barrier + Pedestal P",
        "desc": "A structural barrier gate pedestal forms the tall vertical stem of 'P'. From the mechanical pivot, a high-luminance barrier arm rises at a 40° angle, framing an open access corridor under an optical sensor eye.",
        "palette": ["#00F2FE", "#0284C7", "#10B981", "#FFFFFF"],
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <linearGradient id="p1_bg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="512" y2="512">
      <stop offset="0%" stop-color="#0B0F19"/>
      <stop offset="100%" stop-color="#04070F"/>
    </linearGradient>
    <linearGradient id="p1_stem" gradientUnits="userSpaceOnUse" x1="150" y1="110" x2="200" y2="400">
      <stop offset="0%" stop-color="#38BDF8"/>
      <stop offset="50%" stop-color="#0284C7"/>
      <stop offset="100%" stop-color="#0F172A"/>
    </linearGradient>
    <linearGradient id="p1_loop" gradientUnits="userSpaceOnUse" x1="180" y1="110" x2="410" y2="280">
      <stop offset="0%" stop-color="#00F2FE"/>
      <stop offset="100%" stop-color="#0284C7"/>
    </linearGradient>
    <linearGradient id="p1_arm" gradientUnits="userSpaceOnUse" x1="180" y1="270" x2="400" y2="120">
      <stop offset="0%" stop-color="#10B981"/>
      <stop offset="50%" stop-color="#00F5A0"/>
      <stop offset="100%" stop-color="#38BDF8"/>
    </linearGradient>
    <filter id="p1_glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="10" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>
  
  <rect width="512" height="512" rx="112" fill="url(#p1_bg)"/>
  <rect width="508" height="508" x="2" y="2" rx="110" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="2"/>
  
  <!-- Optical Target Reticle & Ground Markings -->
  <circle cx="180" cy="270" r="160" fill="none" stroke="rgba(0,242,254,0.04)" stroke-width="1.5" stroke-dasharray="6 8"/>
  <line x1="110" y1="410" x2="400" y2="410" stroke="rgba(255,255,255,0.08)" stroke-width="3" stroke-linecap="round"/>
  
  <!-- Vertical Pedestal Stem of 'P' -->
  <rect x="150" y="110" width="50" height="290" rx="25" fill="url(#p1_stem)"/>
  <rect x="150" y="110" width="50" height="290" rx="25" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="1.5"/>
  
  <!-- Architectural Upper P Loop (Outer Framing) -->
  <path d="M180 110 L310 110 C375 110, 410 145, 410 200 C410 255, 375 275, 310 275 L180 275" 
        fill="none" stroke="url(#p1_loop)" stroke-width="32" stroke-linecap="round" stroke-linejoin="round"/>
  
  <!-- Resting Barrier Position (Subtle Ghost Guide) -->
  <line x1="180" y1="270" x2="350" y2="270" stroke="rgba(255,255,255,0.1)" stroke-width="14" stroke-dasharray="6 10" stroke-linecap="round"/>
  
  <!-- Kinetic Rising Barrier Arm (Pivoting 42 deg Upward) -->
  <g filter="url(#p1_glow)">
    <line x1="180" y1="270" x2="390" y2="120" stroke="url(#p1_arm)" stroke-width="26" stroke-linecap="round"/>
  </g>
  
  <!-- Mechanical Pivot Hub / Smart Optical Sensor -->
  <circle cx="180" cy="270" r="28" fill="#0B1120" stroke="#00F2FE" stroke-width="5"/>
  <circle cx="180" cy="270" r="14" fill="#10B981"/>
  <circle cx="180" cy="270" r="5" fill="#FFFFFF"/>
  
  <!-- Active Gate Tip Beacon -->
  <circle cx="390" cy="120" r="9" fill="#00F5A0" filter="url(#p1_glow)"/>
  <circle cx="390" cy="120" r="4" fill="#FFFFFF"/>
</svg>"""
    },
    {
        "id": "edition_2",
        "title": "Edition 2: The Continuous Ribbon",
        "subtitle": "Seamless Kinetic Monogram + Elevated Boom",
        "desc": "A continuous geometric ribbon flows up the vertical stem, wraps through the upper 'P' arch, and extends gracefully into the sky as an elevated barrier arm. Pure, frictionless mobility in continuous line form.",
        "palette": ["#00F2FE", "#38BDF8", "#10B981", "#00F5A0"],
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <linearGradient id="p2_bg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="512" y2="512">
      <stop offset="0%" stop-color="#090E17"/>
      <stop offset="100%" stop-color="#03060B"/>
    </linearGradient>
    <linearGradient id="p2_ribbon" gradientUnits="userSpaceOnUse" x1="140" y1="400" x2="420" y2="100">
      <stop offset="0%" stop-color="#0284C7"/>
      <stop offset="30%" stop-color="#00F2FE"/>
      <stop offset="70%" stop-color="#10B981"/>
      <stop offset="100%" stop-color="#00F5A0"/>
    </linearGradient>
    <filter id="p2_glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="9" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>
  
  <rect width="512" height="512" rx="112" fill="url(#p2_bg)"/>
  <rect width="508" height="508" x="2" y="2" rx="110" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="2"/>
  
  <!-- Perspective Lane Ground Markings -->
  <line x1="120" y1="410" x2="390" y2="410" stroke="rgba(255,255,255,0.08)" stroke-width="3" stroke-linecap="round"/>
  
  <g filter="url(#p2_glow)">
    <!-- Tall Vertical Stem of 'P' (Solid Pedestal) -->
    <rect x="145" y="110" width="44" height="290" rx="22" fill="url(#p2_ribbon)"/>
    
    <!-- Sweeping P Arch Loop -->
    <path d="M165 110 L310 110 C375 110, 415 145, 415 195 C415 245, 365 275, 290 275 L165 275" 
          fill="none" stroke="url(#p2_ribbon)" stroke-width="40" stroke-linecap="round" stroke-linejoin="round"/>
    
    <!-- Elevated Barrier Arm (Dynamic Extension lifting from the loop) -->
    <path d="M290 275 L420 160" stroke="#00F5A0" stroke-width="22" stroke-linecap="round"/>
  </g>
  
  <!-- Central AI Vision Aperture -->
  <circle cx="285" cy="192" r="24" fill="#090E17" stroke="#00F2FE" stroke-width="5"/>
  <circle cx="285" cy="192" r="10" fill="#00F5A0"/>
  <circle cx="285" cy="192" r="4" fill="#FFFFFF"/>
  
  <!-- Strobe Light at Boom Tip -->
  <circle cx="420" cy="160" r="8" fill="#00F5A0" filter="url(#p2_glow)"/>
  <circle cx="420" cy="160" r="4" fill="#FFFFFF"/>
</svg>"""
    },
    {
        "id": "edition_3",
        "title": "Edition 3: The Cyber Monolith",
        "subtitle": "Chamfered Pedestal + Laser Barrier Blade",
        "desc": "An authoritative, industrial barrier housing with 45° chamfers and optical camera slits. A high-intensity electric cyan barrier beam slices upward, embodying institutional security and instant ALPR clearance.",
        "palette": ["#1E293B", "#38BDF8", "#00F5A0", "#FFFFFF"],
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <linearGradient id="p3_bg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="512" y2="512">
      <stop offset="0%" stop-color="#080C14"/>
      <stop offset="100%" stop-color="#020408"/>
    </linearGradient>
    <linearGradient id="p3_monolith" gradientUnits="userSpaceOnUse" x1="140" y1="110" x2="210" y2="400">
      <stop offset="0%" stop-color="#1E293B"/>
      <stop offset="100%" stop-color="#0F172A"/>
    </linearGradient>
    <linearGradient id="p3_beam" gradientUnits="userSpaceOnUse" x1="185" y1="275" x2="400" y2="135">
      <stop offset="0%" stop-color="#0284C7"/>
      <stop offset="40%" stop-color="#00F2FE"/>
      <stop offset="100%" stop-color="#00F5A0"/>
    </linearGradient>
    <filter id="p3_glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="12" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>
  
  <rect width="512" height="512" rx="112" fill="url(#p3_bg)"/>
  <rect width="508" height="508" x="2" y="2" rx="110" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="2"/>
  
  <!-- Monolith Terminal Pillar (The Tall 'P' Upright) -->
  <path d="M140 150 L185 110 L210 110 L210 400 L140 400 Z" fill="url(#p3_monolith)" stroke="rgba(255,255,255,0.12)" stroke-width="2"/>
  
  <!-- Optical Camera Status Slits in Monolith -->
  <rect x="155" y="170" width="18" height="4" rx="2" fill="#00F2FE"/>
  <rect x="155" y="185" width="18" height="4" rx="2" fill="#00F2FE"/>
  <rect x="155" y="200" width="18" height="4" rx="2" fill="#00F5A0"/>
  
  <!-- Upper P Loop Geometry -->
  <path d="M185 110 L305 110 C365 110, 405 145, 405 195 C405 245, 365 275, 305 275 L185 275" 
        fill="none" stroke="#38BDF8" stroke-width="32" stroke-linecap="round" stroke-linejoin="round"/>
  
  <!-- Kinetic Laser Barrier Blade Slicing Upward -->
  <g filter="url(#p3_glow)">
    <line x1="185" y1="275" x2="395" y2="135" stroke="url(#p3_beam)" stroke-width="24" stroke-linecap="round"/>
  </g>
  
  <!-- High-Precision Dual Optical Sensors -->
  <circle cx="185" cy="275" r="22" fill="#080C14" stroke="#00F5A0" stroke-width="5"/>
  <circle cx="185" cy="275" r="9" fill="#FFFFFF"/>
  <circle cx="395" cy="135" r="9" fill="#00F5A0" filter="url(#p3_glow)"/>
  <circle cx="395" cy="135" r="4" fill="#FFFFFF"/>
</svg>"""
    },
    {
        "id": "edition_4",
        "title": "Edition 4: The HexaGate AI",
        "subtitle": "Isometric IoT Hexagon + Gull-Wing Access",
        "desc": "A crystalline hexagonal 'P' emblem framing an active computer vision sensor eye. The upper starboard barrier facet lifts open like a gull-wing gate, engineered for precision CAD analytics and smart city hubs.",
        "palette": ["#00F2FE", "#10B981", "#38BDF8", "#FFFFFF"],
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <linearGradient id="p4_bg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="512" y2="512">
      <stop offset="0%" stop-color="#090D1A"/>
      <stop offset="100%" stop-color="#03060C"/>
    </linearGradient>
    <linearGradient id="p4_stem" gradientUnits="userSpaceOnUse" x1="140" y1="120" x2="190" y2="400">
      <stop offset="0%" stop-color="#00F2FE"/>
      <stop offset="100%" stop-color="#0F172A"/>
    </linearGradient>
    <linearGradient id="p4_hexa" gradientUnits="userSpaceOnUse" x1="160" y1="120" x2="380" y2="280">
      <stop offset="0%" stop-color="#0284C7"/>
      <stop offset="50%" stop-color="#00F2FE"/>
      <stop offset="100%" stop-color="#10B981"/>
    </linearGradient>
    <filter id="p4_glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="10" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>
  
  <rect width="512" height="512" rx="112" fill="url(#p4_bg)"/>
  <rect width="508" height="508" x="2" y="2" rx="110" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="2"/>
  
  <!-- Tall Left Stem of 'P' (Solid Vertical Axis) -->
  <rect x="145" y="115" width="44" height="285" rx="22" fill="url(#p4_stem)"/>
  <rect x="145" y="115" width="44" height="285" rx="22" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="1.5"/>
  
  <!-- Hexagonal P Loop Structure -->
  <g filter="url(#p4_glow)">
    <path d="M165 125 L275 125 L355 190 L275 255 L165 255" 
          fill="none" stroke="url(#p4_hexa)" stroke-width="34" stroke-linecap="round" stroke-linejoin="round"/>
    
    <!-- Lifting Gull-Wing Barrier Arm -->
    <path d="M275 255 L395 155" stroke="#00F5A0" stroke-width="22" stroke-linecap="round"/>
  </g>
  
  <!-- Central AI Optical Eye & Radar Rings -->
  <circle cx="256" cy="190" r="26" fill="#090D1A" stroke="#00F2FE" stroke-width="4"/>
  <circle cx="256" cy="190" r="12" fill="#00F5A0"/>
  <circle cx="256" cy="190" r="5" fill="#FFFFFF"/>
  
  <!-- Active Barrier Tip Strobe -->
  <circle cx="395" cy="155" r="8" fill="#00F5A0" filter="url(#p4_glow)"/>
  <circle cx="395" cy="155" r="4" fill="#FFFFFF"/>
</svg>"""
    },
    {
        "id": "edition_5",
        "title": "Edition 5: The Dual-Track Velocity",
        "subtitle": "Twin Speed Blades + 45° Sweeping Boom",
        "desc": "Parallel twin-velocity tracks represent dual-camera perception and inductive ground loops. The inner track anchors the terminal while the outer track launches gracefully into a high-speed rising barrier arm with a forward tracking chevron.",
        "palette": ["#00F2FE", "#38BDF8", "#00F5A0", "#E2E8F0"],
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <linearGradient id="p5_bg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="512" y2="512">
      <stop offset="0%" stop-color="#0B0F19"/>
      <stop offset="100%" stop-color="#04060A"/>
    </linearGradient>
    <linearGradient id="p5_track1" gradientUnits="userSpaceOnUse" x1="150" y1="400" x2="340" y2="100">
      <stop offset="0%" stop-color="#0284C7"/>
      <stop offset="100%" stop-color="#00F2FE"/>
    </linearGradient>
    <linearGradient id="p5_track2" gradientUnits="userSpaceOnUse" x1="190" y1="400" x2="420" y2="100">
      <stop offset="0%" stop-color="#00F2FE"/>
      <stop offset="50%" stop-color="#10B981"/>
      <stop offset="100%" stop-color="#00F5A0"/>
    </linearGradient>
    <filter id="p5_glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>
  
  <rect width="512" height="512" rx="112" fill="url(#p5_bg)"/>
  <rect width="508" height="508" x="2" y="2" rx="110" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="2"/>
  
  <!-- Ground Induction Loop Grid Lines -->
  <line x1="120" y1="410" x2="390" y2="410" stroke="rgba(255,255,255,0.08)" stroke-width="3" stroke-linecap="round"/>
  
  <g filter="url(#p5_glow)">
    <!-- Inner Track (Pillar Anchor) -->
    <path d="M150 400 L150 150 C150 115, 185 100, 230 100 L260 100 C305 100, 335 125, 335 165 C335 205, 305 230, 260 230 L175 230" 
          fill="none" stroke="url(#p5_track1)" stroke-width="24" stroke-linecap="round" stroke-linejoin="round"/>
    
    <!-- Outer Track (Dynamic Rising Boom Blade) -->
    <path d="M190 400 L190 190 C190 150, 225 140, 270 140 C340 140, 395 175, 395 230 C395 260, 370 280, 310 280 L210 280" 
          fill="none" stroke="url(#p5_track2)" stroke-width="24" stroke-linecap="round" stroke-linejoin="round"/>
    
    <!-- Forward Velocity Boom Sweep (Launching 42 deg upward) -->
    <path d="M290 200 L420 105" stroke="#00F5A0" stroke-width="22" stroke-linecap="round"/>
  </g>
  
  <!-- Precision Tracking Chevron -->
  <path d="M235 190 L255 205 L235 220" fill="none" stroke="#FFFFFF" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
  
  <!-- Sensor Beacon -->
  <circle cx="420" cy="105" r="9" fill="#00F5A0" filter="url(#p5_glow)"/>
  <circle cx="420" cy="105" r="4" fill="#FFFFFF"/>
</svg>"""
    }
]

# Write SVGs
for ed in EDITIONS:
    p1 = f"public/assets/logos/editions/{ed['id']}.svg"
    p2 = f"static/assets/logos/editions/{ed['id']}.svg"
    with open(p1, "w", encoding="utf-8") as f:
        f.write(ed["svg"])
    with open(p2, "w", encoding="utf-8") as f:
        f.write(ed["svg"])
    print(f"Refined {ed['id']}.svg")

print("All 5 refined editions generated successfully.")
