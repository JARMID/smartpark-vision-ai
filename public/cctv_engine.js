/**
 * SmartPark Vision AI - High-Fidelity CCTV Rendering Engine (V3.2 Sovereign DZ)
 * Real-Time Canvas Pipeline with Complete Day/Night & Trilingual Support
 * 
 * CAM-01: Voie 1 Entry ALPR (High-Angle Architectural Perspective)
 * CAM-02: Biometric Access Kiosk (100% Spatially Consistent Driver Close-Up)
 * CAM-03: Voie 2 Exit ALPR & Toll Barrier (Perspective Exit Lane)
 * CAM-04: Zone A & B Deck Overview (Tactical Overhead CCTV)
 */

(function (window) {
  'use strict';

  // Global Vehicle Engine State (Running vs Off)
  window.isVehicleEngineRunning = true;

  window.setVehicleEngineState = function (state) {
    window.isVehicleEngineRunning = Boolean(state);
    const btn = document.getElementById('engine-toggle-btn');
    const dot = document.getElementById('engine-status-dot');
    const txt = document.getElementById('engine-status-text');
    const lang = window.currentLang || 'fr';
    const I18N = window.I18N || {};
    if (btn && dot && txt) {
      if (window.isVehicleEngineRunning) {
        dot.className = 'w-2 h-2 rounded-full bg-emerald-400 animate-pulse';
        btn.className = 'flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-xs font-mono border border-emerald-500/40 bg-emerald-950/40 text-emerald-400 hover:bg-emerald-900/50 transition';
        txt.innerText = (I18N[lang] && I18N[lang].engine_running) || "Moteur : EN MARCHE (820 RPM)";
      } else {
        dot.className = 'w-2 h-2 rounded-full bg-amber-400';
        btn.className = 'flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-xs font-mono border border-amber-500/40 bg-amber-950/40 text-amber-400 hover:bg-amber-900/50 transition';
        txt.innerText = (I18N[lang] && I18N[lang].engine_off) || "Moteur : ÉTEINT (0 RPM)";
      }
    }
  };

  window.toggleVehicleEngine = function () {
    window.setVehicleEngineState(!window.isVehicleEngineRunning);
  };

  // =========================================================================
  // COMMON CCTV OVERLAYS, OSD, CRT SCANLINES & SENSOR NOISE
  // =========================================================================
  function drawCCTVEffects(ctx, w, h, camCode, camTitle, fps = 25.0, nowStr = '', isRec = true) {
    const isLight = document.documentElement.classList.contains('light');
    const lang = window.currentLang || 'fr';

    // 1. Horizontal Micro-Scanlines
    ctx.fillStyle = isLight ? 'rgba(15, 23, 42, 0.025)' : 'rgba(0, 0, 0, 0.16)';
    for (let y = 0; y < h; y += 3) {
      ctx.fillRect(0, y, w, 1);
    }

    // 2. Optical Security Lens Barrel Vignette
    const vig = ctx.createRadialGradient(w / 2, h / 2, h * 0.45, w / 2, h / 2, w * 0.75);
    if (isLight) {
      vig.addColorStop(0, 'rgba(0, 0, 0, 0)');
      vig.addColorStop(1, 'rgba(15, 23, 42, 0.14)');
    } else {
      vig.addColorStop(0, 'rgba(0, 0, 0, 0)');
      vig.addColorStop(1, 'rgba(2, 6, 18, 0.68)');
    }
    ctx.fillStyle = vig;
    ctx.fillRect(0, 0, w, h);

    // 3. Dynamic Low-Light Sensor Grain / Noise
    ctx.fillStyle = isLight ? 'rgba(0, 0, 0, 0.02)' : 'rgba(255, 255, 255, 0.035)';
    const seed = (Date.now() % 1000) * 0.01;
    for (let i = 0; i < 50; i++) {
      const rx = Math.abs((Math.sin(seed + i * 1.7) * 43758.5453) % w);
      const ry = Math.abs((Math.cos(seed + i * 2.3) * 43758.5453) % h);
      ctx.fillRect(rx, ry, 1, 1);
    }

    // 4. CCTV Top Header Bar
    ctx.fillStyle = isLight ? 'rgba(248, 250, 252, 0.95)' : 'rgba(4, 8, 20, 0.90)';
    ctx.fillRect(0, 0, w, 22);
    ctx.strokeStyle = isLight ? 'rgba(203, 213, 225, 0.9)' : 'rgba(30, 41, 59, 0.85)';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, 22); ctx.lineTo(w, 22); ctx.stroke();

    // Blinking REC Status Indicator
    const blink = Math.floor(Date.now() / 600) % 2 === 0;
    if (isRec && blink) {
      ctx.fillStyle = '#EF4444';
      ctx.beginPath(); ctx.arc(12, 11, 3.5, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = isLight ? '#DC2626' : '#FCA5A5';
      ctx.font = 'bold 8px "JetBrains Mono", monospace';
      ctx.fillText('REC', 20, 14);
    } else {
      ctx.fillStyle = isLight ? '#64748B' : '#94A3B8';
      ctx.font = 'bold 8px "JetBrains Mono", monospace';
      ctx.fillText('STBY', 14, 14);
    }

    ctx.fillStyle = isLight ? '#0F172A' : '#F1F5F9';
    ctx.font = 'bold 9px "JetBrains Mono", monospace';
    ctx.fillText(`${camCode} [${camTitle}]`, 48, 14);

    // Real-Time Timecode
    ctx.fillStyle = isLight ? '#0284C7' : '#38BDF8';
    ctx.textAlign = 'right';
    const timeText = nowStr || new Date().toISOString().replace('T', ' ').substring(0, 19);
    ctx.fillText(`${timeText} UTC+1`, w - 10, 14);
    ctx.textAlign = 'left';

    // 5. CCTV Bottom Telemetry Footer
    ctx.fillStyle = isLight ? 'rgba(248, 250, 252, 0.95)' : 'rgba(4, 8, 20, 0.90)';
    ctx.fillRect(0, h - 20, w, 20);
    ctx.strokeStyle = isLight ? 'rgba(203, 213, 225, 0.9)' : 'rgba(30, 41, 59, 0.85)';
    ctx.beginPath(); ctx.moveTo(0, h - 20); ctx.lineTo(w, h - 20); ctx.stroke();

    ctx.fillStyle = isLight ? '#334155' : '#94A3B8';
    ctx.font = '8px "JetBrains Mono", monospace';
    const lawText = lang === 'ar' ? 'القانون 25-11 لحماية المعطيات الشخصية | NVDEC 4.8 Mb/s' : (lang === 'en' ? 'LAW 25-11 PRIVACY COMPLIANT | NVDEC 4.8 Mb/s' : 'LOI 25-11 PROTECTION DES DONNEES | NVDEC 4.8 Mb/s');
    ctx.fillText(`1080p50 H.265 | ${lawText}`, 10, h - 7);

    ctx.textAlign = 'right';
    ctx.fillStyle = isLight ? '#059669' : '#10B981';
    ctx.fillText(`${fps.toFixed(1)} FPS | AXIS-DZ SECURE`, w - 10, h - 7);
    ctx.textAlign = 'left';
  }

  // =========================================================================
  // CAM 1 : VOIE 1 ENTREE (ALPR PERSPECTIVE & ARCHITECTURAL GUARD POST)
  // =========================================================================
  function setupCam1() {
    const cvs = document.getElementById('cam1-canvas');
    if (!cvs) return;
    const ctx = cvs.getContext('2d');
    cvs.width = 480; cvs.height = 270;

    let carY = 88; // Waiting position strictly behind stop line & barrier arm
    let carSpeed = 0;
    let carDeparting = false;
    let plateText = "104822 119 16";
    let armAngle = 0;
    let targetArmAngle = 0;
    let frameCount = 0;

    function render() {
      frameCount++;
      const isLight = document.documentElement.classList.contains('light');
      const lang = window.currentLang || 'fr';
      const I18N = window.I18N || {};

      // Barrier Arm Physics Animation
      armAngle += (targetArmAngle - armAngle) * 0.12;

      // Vehicle Progression
      if (carDeparting) {
        carY -= 2.8;
        if (carY < -120) {
          carDeparting = false;
          targetArmAngle = 0;
          setTimeout(() => {
            carY = 15;
            plateText = "08412 119 16";
          }, 1200);
        }
      } else if (carY < 88) {
        carY += 1.8;
      }

      // 1. Sky & Horizon
      const skyGrad = ctx.createLinearGradient(0, 0, 0, 85);
      if (isLight) {
        skyGrad.addColorStop(0, '#BAE6FD');
        skyGrad.addColorStop(1, '#E0F2FE');
      } else {
        skyGrad.addColorStop(0, '#030712');
        skyGrad.addColorStop(1, '#0F172A');
      }
      ctx.fillStyle = skyGrad;
      ctx.fillRect(0, 0, cvs.width, 85);

      // Background Horizon Architectural Line (Algiers Central Commercial District)
      ctx.fillStyle = isLight ? '#94A3B8' : '#1E293B';
      const bldgPoints = [
        [0, 65, 35, 20], [38, 55, 42, 30], [84, 60, 30, 25], [118, 50, 48, 35],
        [320, 52, 45, 33], [370, 58, 38, 27], [412, 48, 40, 37], [455, 62, 25, 23]
      ];
      bldgPoints.forEach(([bx, by, bw, bh]) => {
        ctx.fillRect(bx, by, bw, bh);
        ctx.strokeStyle = isLight ? '#CBD5E1' : '#334155';
        ctx.lineWidth = 0.8;
        ctx.strokeRect(bx, by, bw, bh);
      });

      // 2. Asphalt Roadway with Perspective Convergence
      const roadGrad = ctx.createLinearGradient(240, 75, 240, cvs.height);
      if (isLight) {
        roadGrad.addColorStop(0, '#64748B');
        roadGrad.addColorStop(0.4, '#475569');
        roadGrad.addColorStop(1, '#334155');
      } else {
        roadGrad.addColorStop(0, '#0F172A');
        roadGrad.addColorStop(0.4, '#1E293B');
        roadGrad.addColorStop(1, '#090D16');
      }
      ctx.fillStyle = roadGrad;
      ctx.beginPath();
      ctx.moveTo(180, 75); ctx.lineTo(300, 75);
      ctx.lineTo(460, cvs.height); ctx.lineTo(60, cvs.height);
      ctx.closePath(); ctx.fill();

      // Road Surface Aggregate Texture
      ctx.fillStyle = isLight ? 'rgba(0, 0, 0, 0.04)' : 'rgba(255, 255, 255, 0.03)';
      for (let i = 0; i < 50; i++) {
        const tx = (i * 37) % cvs.width;
        const ty = 80 + (i * 19) % (cvs.height - 80);
        ctx.fillRect(tx, ty, 2, 1);
      }

      // Yellow Centerline Dashes (Perspective)
      ctx.strokeStyle = '#F59E0B';
      ctx.lineWidth = 3;
      ctx.setLineDash([16, 14]);
      ctx.beginPath();
      ctx.moveTo(240, 75); ctx.lineTo(260, cvs.height);
      ctx.stroke();
      ctx.setLineDash([]);

      // 3. Embedded Inductive Loop Sensor in Lane 1 (Loop A)
      const isLoopOccupied = carY >= 40 && carY <= 120;
      ctx.strokeStyle = isLoopOccupied ? '#06B6D4' : (isLight ? '#94A3B8' : '#475569');
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(150, 110); ctx.lineTo(330, 110);
      ctx.lineTo(355, 165); ctx.lineTo(125, 165);
      ctx.closePath();
      ctx.stroke();

      ctx.fillStyle = isLoopOccupied ? 'rgba(6, 182, 212, 0.18)' : 'rgba(0, 0, 0, 0)';
      ctx.fill();

      // Inductive Loop Chamfered Corner Cuts
      ctx.strokeStyle = isLoopOccupied ? '#06B6D4' : (isLight ? '#CBD5E1' : '#334155');
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(150, 116); ctx.lineTo(156, 110);
      ctx.moveTo(324, 110); ctx.lineTo(330, 116);
      ctx.moveTo(125, 159); ctx.lineTo(131, 165);
      ctx.moveTo(349, 165); ctx.lineTo(355, 159);
      ctx.stroke();

      // 4. White Stop Bar at Barrier (Ahead of car at Y = 176)
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(120, 176); ctx.lineTo(370, 176);
      ctx.stroke();

      // Stop Bar Stencil Text ("ARRÊT / STOP / قف")
      ctx.fillStyle = isLight ? '#FFFFFF' : 'rgba(255, 255, 255, 0.85)';
      ctx.font = 'bold 8.5px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      const stopText = lang === 'ar' ? 'قـــــف' : (lang === 'en' ? 'STOP' : 'ARRET');
      ctx.fillText(stopText, 245, 173);
      ctx.textAlign = 'left';

      // 5. Concrete Curb Island with Yellow & Black Safety Stripes (Left Side)
      const curbStartX = 28, curbStartY = 95;
      const curbW = 92;
      for (let s = 0; s < 9; s++) {
        const segY = curbStartY + s * 16;
        ctx.fillStyle = (s % 2 === 0) ? '#F59E0B' : (isLight ? '#334155' : '#0F172A');
        ctx.beginPath();
        ctx.moveTo(curbStartX + s * 3.5, segY);
        ctx.lineTo(curbStartX + curbW + s * 3.5, segY);
        ctx.lineTo(curbStartX + curbW + (s + 1) * 3.5, segY + 16);
        ctx.lineTo(curbStartX + (s + 1) * 3.5, segY + 16);
        ctx.closePath();
        ctx.fill();
        ctx.strokeStyle = isLight ? '#64748B' : '#1E293B';
        ctx.lineWidth = 0.8;
        ctx.stroke();
      }

      // 6. Architectural Security Guard Post (Cabine de Garde)
      const gbX = 35, gbY = 60, gbW = 80, gbH = 98;
      ctx.fillStyle = isLight ? '#E2E8F0' : '#1E293B';
      ctx.fillRect(gbX, gbY, gbW, gbH);
      ctx.strokeStyle = isLight ? '#94A3B8' : '#475569';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(gbX, gbY, gbW, gbH);

      // Booth Projecting Roof Canopy
      ctx.fillStyle = isLight ? '#334155' : '#0F172A';
      ctx.fillRect(gbX - 4, gbY - 5, gbW + 8, 8);
      ctx.strokeStyle = isLight ? '#475569' : '#1E293B';
      ctx.strokeRect(gbX - 4, gbY - 5, gbW + 8, 8);

      // Security Observation Window
      const winX = gbX + 6, winY = gbY + 12, winW = gbW - 12, winH = 46;
      if (isLight) {
        const winGrad = ctx.createLinearGradient(winX, winY, winX + winW, winY + winH);
        winGrad.addColorStop(0, '#93C5FD');
        winGrad.addColorStop(0.5, '#BAE6FD');
        winGrad.addColorStop(1, '#60A5FA');
        ctx.fillStyle = winGrad;
        ctx.fillRect(winX, winY, winW, winH);
        ctx.strokeStyle = '#3B82F6';
        ctx.strokeRect(winX, winY, winW, winH);
      } else {
        const winGrad = ctx.createLinearGradient(winX, winY, winX + winW, winY + winH);
        winGrad.addColorStop(0, 'rgba(251, 191, 36, 0.7)');
        winGrad.addColorStop(1, 'rgba(217, 119, 6, 0.35)');
        ctx.fillStyle = winGrad;
        ctx.fillRect(winX, winY, winW, winH);
        ctx.strokeStyle = '#D97706';
        ctx.strokeRect(winX, winY, winW, winH);
      }

      // Security Officer in Uniform (Looking out at approaching lane)
      const offX = winX + winW * 0.38, offY = winY + 14;
      // Dark Navy Officer Shoulders with Epaulets
      ctx.fillStyle = '#0F172A';
      ctx.beginPath();
      ctx.moveTo(offX - 16, offY + 28);
      ctx.lineTo(offX + 16, offY + 28);
      ctx.lineTo(offX + 12, offY + 12);
      ctx.lineTo(offX - 12, offY + 12);
      ctx.closePath();
      ctx.fill();
      // Gold Epaulets on Shoulders
      ctx.fillStyle = '#F59E0B';
      ctx.fillRect(offX - 14, offY + 13, 5, 2);
      ctx.fillRect(offX + 9, offY + 13, 5, 2);
      // Head with Official Peaked Officer Cap
      ctx.fillStyle = '#C68B59'; // Neck/Face
      ctx.beginPath();
      ctx.arc(offX, offY + 6, 5.5, 0, Math.PI * 2);
      ctx.fill();
      // Navy Peak Cap with Gold Visor Crest
      ctx.fillStyle = '#0F172A';
      ctx.beginPath();
      ctx.arc(offX, offY + 2, 7, Math.PI, Math.PI * 2);
      ctx.lineTo(offX + 8, offY + 4);
      ctx.lineTo(offX - 8, offY + 4);
      ctx.closePath();
      ctx.fill();
      // Cap Visor Peak
      ctx.fillStyle = '#020617';
      ctx.beginPath();
      ctx.ellipse(offX + 3, offY + 4.5, 6, 2, 0.15, 0, Math.PI * 2);
      ctx.fill();
      // Gold Police/Security Badge
      ctx.fillStyle = '#F59E0B';
      ctx.fillRect(offX - 1, offY - 1, 2.5, 2.5);

      // Desk Control Screen Glow (Angled Multi-Monitor Array)
      ctx.fillStyle = '#064E3B';
      ctx.fillRect(winX + winW * 0.60, winY + 22, 13, 10);
      ctx.fillStyle = '#10B981';
      ctx.fillRect(winX + winW * 0.61, winY + 23, 11, 8);
      ctx.fillStyle = '#083344';
      ctx.fillRect(winX + winW * 0.77, winY + 20, 11, 12);
      ctx.fillStyle = '#06B6D4';
      ctx.fillRect(winX + winW * 0.78, winY + 21, 9, 10);
      // Desk Base & Gooseneck Mic
      ctx.fillStyle = '#1E293B';
      ctx.fillRect(winX + 2, winY + 36, winW - 4, 8);
      ctx.strokeStyle = '#64748B';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(winX + winW * 0.54, winY + 36);
      ctx.quadraticCurveTo(winX + winW * 0.50, winY + 28, winX + winW * 0.44, winY + 26);
      ctx.stroke();

      // Window Glass Specular Highlights (Diagonal Reflection Streaks)
      ctx.strokeStyle = isLight ? 'rgba(255, 255, 255, 0.65)' : 'rgba(255, 255, 255, 0.18)';
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(winX + 4, winY + winH - 4); ctx.lineTo(winX + 22, winY + 4);
      ctx.moveTo(winX + 16, winY + winH - 4); ctx.lineTo(winX + 34, winY + 4);
      ctx.stroke();

      // 7. Driver Access Kiosk Totem (CAM 2 Physical Enclosure)
      const kioskX = gbX + gbW + 6, kioskY = 168, kioskW = 14, kioskH = 40;
      ctx.fillStyle = isLight ? '#1E293B' : '#0F172A';
      ctx.fillRect(kioskX, kioskY, kioskW, kioskH);
      ctx.strokeStyle = '#0284C7';
      ctx.lineWidth = 1;
      ctx.strokeRect(kioskX, kioskY, kioskW, kioskH);

      // Kiosk Optical Camera Aperture Ring (CAM 2 lens)
      ctx.fillStyle = '#000000';
      ctx.beginPath(); ctx.arc(kioskX + kioskW / 2, kioskY + 9, 4, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#06B6D4';
      ctx.beginPath(); ctx.arc(kioskX + kioskW / 2, kioskY + 9, 2, 0, Math.PI * 2); ctx.fill();

      // Kiosk Card/Ticket Slot
      ctx.fillStyle = '#F59E0B';
      ctx.fillRect(kioskX + 3, kioskY + 22, 8, 2);

      // 8. Approaching / Stationed Sedan (Rendered strictly BEHIND the barrier arm)
      const isEngineRunning = window.isVehicleEngineRunning !== false;
      const engineVibe = isEngineRunning ? Math.sin(frameCount * 0.45) * 0.08 : 0;
      const scale = 0.84;
      const w = 152;
      const h = 82;
      const cx = 240;
      const x = cx - w / 2;
      const y = carY + engineVibe;

      // Chassis Ground Drop Shadow
      ctx.fillStyle = isLight ? 'rgba(15, 23, 42, 0.45)' : 'rgba(0, 0, 0, 0.8)';
      ctx.beginPath();
      ctx.ellipse(cx, y + h + 2, w * 0.50, 9, 0, 0, Math.PI * 2);
      ctx.fill();

      // Main Sedan Body (Metallic Charcoal Finish)
      const bodyGrad = ctx.createLinearGradient(cx, y, cx, y + h);
      if (isLight) {
        bodyGrad.addColorStop(0, '#334155');
        bodyGrad.addColorStop(0.35, '#475569');
        bodyGrad.addColorStop(0.7, '#334155');
        bodyGrad.addColorStop(1, '#1E293B');
      } else {
        bodyGrad.addColorStop(0, '#1E293B');
        bodyGrad.addColorStop(0.35, '#334155');
        bodyGrad.addColorStop(0.7, '#1E293B');
        bodyGrad.addColorStop(1, '#0F172A');
      }
      ctx.fillStyle = bodyGrad;
      ctx.beginPath();
      ctx.roundRect(x, y + h * 0.32, w, h * 0.68, 7);
      ctx.fill();
      ctx.strokeStyle = isLight ? '#64748B' : '#475569';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Sculpted Hood Creases & Specular Highlights
      ctx.strokeStyle = isLight ? 'rgba(255, 255, 255, 0.4)' : 'rgba(255, 255, 255, 0.18)';
      ctx.lineWidth = 1.1;
      ctx.beginPath();
      ctx.moveTo(cx - w * 0.28, y + h * 0.32); ctx.lineTo(cx - w * 0.18, y + h * 0.65);
      ctx.moveTo(cx + w * 0.28, y + h * 0.32); ctx.lineTo(cx + w * 0.18, y + h * 0.65);
      ctx.stroke();

      // Curved Aerodynamic Windshield
      const wsGrad = ctx.createLinearGradient(cx, y, cx, y + h * 0.35);
      if (isLight) {
        wsGrad.addColorStop(0, '#38BDF8');
        wsGrad.addColorStop(0.5, '#7DD3FC');
        wsGrad.addColorStop(1, '#0284C7');
      } else {
        wsGrad.addColorStop(0, '#0F172A');
        wsGrad.addColorStop(0.5, '#0284C7');
        wsGrad.addColorStop(1, '#0C4A6E');
      }
      ctx.fillStyle = wsGrad;
      ctx.beginPath();
      ctx.moveTo(cx - w * 0.36, y + h * 0.32);
      ctx.lineTo(cx - w * 0.28, y + h * 0.05);
      ctx.lineTo(cx + w * 0.28, y + h * 0.05);
      ctx.lineTo(cx + w * 0.36, y + h * 0.32);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = '#1E293B';
      ctx.stroke();

      // Driver Silhouette Behind Windshield (Left Side Seat)
      ctx.fillStyle = 'rgba(15, 23, 42, 0.88)';
      ctx.beginPath();
      ctx.arc(cx - w * 0.14, y + h * 0.18, 10, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.ellipse(cx - w * 0.14, y + h * 0.36, 16, 9, 0, 0, Math.PI);
      ctx.fill();

      // Steering Wheel Rim
      ctx.strokeStyle = 'rgba(51, 65, 85, 0.9)';
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.arc(cx - w * 0.14, y + h * 0.34, 11, Math.PI * 0.8, Math.PI * 1.8);
      ctx.stroke();

      // Rearview Mirror
      ctx.fillStyle = '#0F172A';
      ctx.fillRect(cx - 7, y + h * 0.06, 14, 4.5);

      // Front Radiator Grille
      const gw = w * 0.52, gh = h * 0.24, gx = cx - gw / 2, gy = y + h * 0.45;
      ctx.fillStyle = '#090D16';
      ctx.beginPath(); ctx.roundRect(gx, gy, gw, gh, 4); ctx.fill();
      ctx.strokeStyle = '#64748B'; ctx.lineWidth = 1; ctx.stroke();

      // Chrome Grille Slats
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.35)';
      ctx.lineWidth = 0.8;
      for (let row = 1; row < 4; row++) {
        const ry = gy + (gh / 4) * row;
        ctx.beginPath(); ctx.moveTo(gx + 5, ry); ctx.lineTo(gx + gw - 5, ry); ctx.stroke();
      }

      // Projector Headlights
      const hw = w * 0.18, hh = h * 0.15;
      const leftHX = x + w * 0.05, rightHX = x + w * 0.77, hy = y + h * 0.42;

      [leftHX, rightHX].forEach((hlx, idx) => {
        ctx.fillStyle = '#020617';
        ctx.beginPath(); ctx.roundRect(hlx, hy, hw, hh, 4); ctx.fill();
        ctx.strokeStyle = '#38BDF8'; ctx.lineWidth = 1; ctx.stroke();

        // Projector Core Lens
        ctx.fillStyle = isEngineRunning ? (isLight ? '#BAE6FD' : '#FEF08A') : '#334155';
        ctx.beginPath(); ctx.arc(hlx + hw * 0.5, hy + hh * 0.5, 4.5, 0, Math.PI * 2); ctx.fill();

        // Volumetric Forward Light Cone
        if (isEngineRunning) {
          const dirX = idx === 0 ? -w * 0.20 : w * 0.20;
          const beamGrad = ctx.createRadialGradient(hlx + hw * 0.5, hy + hh, 2, hlx + dirX, hy + 80, 75);
          beamGrad.addColorStop(0, isLight ? 'rgba(254, 240, 138, 0.35)' : 'rgba(254, 240, 138, 0.45)');
          beamGrad.addColorStop(1, 'rgba(254, 240, 138, 0)');
          ctx.fillStyle = beamGrad;
          ctx.beginPath();
          ctx.moveTo(hlx + hw * 0.2, hy + hh);
          ctx.lineTo(hlx + dirX - 30, hy + 80);
          ctx.lineTo(hlx + dirX + 40, hy + 80);
          ctx.closePath(); ctx.fill();
        }
      });

      // Front Algerian License Plate
      const pw = w * 0.44, ph = 14, px = cx - pw / 2, py = gy + gh * 0.88;
      ctx.fillStyle = '#000000';
      ctx.fillRect(px - 1, py - 1, pw + 2, ph + 2);
      ctx.fillStyle = '#FDE047'; // Algerian Front Plate Yellow
      ctx.fillRect(px, py, pw, ph);

      // Plate Text (Serif Numerals)
      ctx.fillStyle = '#000000';
      ctx.font = 'bold 8px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(plateText, cx, py + ph * 0.72);
      ctx.textAlign = 'left';

      // 9. Automatic Barrier Gate Pedestal & Boom Arm (Positioned in FRONT of vehicle)
      const bPedX = 132, bPedY = 168;
      const bPedW = 18, bPedH = 48;
      ctx.fillStyle = '#EA580C'; // RAL 2004 Pure Orange
      ctx.fillRect(bPedX, bPedY, bPedW, bPedH);
      ctx.strokeStyle = '#9A3412'; ctx.lineWidth = 1.2;
      ctx.strokeRect(bPedX, bPedY, bPedW, bPedH);

      // Strobe Dome on Cabinet Top
      const strobeActive = Math.abs(armAngle) > 5 && Math.abs(armAngle) < 75;
      const strobeColor = strobeActive ? (Math.floor(frameCount / 4) % 2 === 0 ? '#F59E0B' : '#EF4444') : (armAngle < -50 ? '#10B981' : '#EF4444');
      ctx.fillStyle = strobeColor;
      ctx.beginPath(); ctx.arc(bPedX + 9, bPedY - 3, 4, Math.PI, 0); ctx.fill();

      // Articulated Boom Arm Across Lane (Foreground In Front of Car at Y = 182)
      ctx.save();
      ctx.translate(bPedX + 9, bPedY + 14);
      ctx.rotate((armAngle * Math.PI) / 180);

      ctx.fillStyle = '#F8FAFC';
      ctx.fillRect(0, -4.5, 180, 9);
      // Red Reflective Diagonal Chevrons
      ctx.fillStyle = '#EF4444';
      for (let s = 10; s < 175; s += 20) {
        ctx.beginPath();
        ctx.moveTo(s, -4.5); ctx.lineTo(s + 10, -4.5);
        ctx.lineTo(s + 4, 4.5); ctx.lineTo(s - 6, 4.5);
        ctx.closePath(); ctx.fill();
      }
      // Active Continuous LED Neon Strip
      ctx.strokeStyle = armAngle < -40 ? '#10B981' : '#EF4444';
      ctx.lineWidth = 2.2;
      ctx.beginPath(); ctx.moveTo(2, -4.5); ctx.lineTo(178, -4.5); ctx.stroke();
      ctx.restore();

      // 10. Overhead Security Portal Structure & Localized Signage
      const portalY = 24, portalH = 22;
      ctx.fillStyle = isLight ? '#1E293B' : '#0B1329';
      ctx.fillRect(40, portalY, 400, portalH);
      ctx.strokeStyle = isLight ? '#475569' : '#1E3A8A';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(40, portalY, 400, portalH);

      // Steel Truss Internal Lattice Struts
      ctx.strokeStyle = isLight ? '#94A3B8' : '#334155';
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let tx = 45; tx < 435; tx += 22) {
        ctx.moveTo(tx, portalY); ctx.lineTo(tx + 11, portalY + portalH);
        ctx.moveTo(tx + 11, portalY + portalH); ctx.lineTo(tx + 22, portalY);
      }
      ctx.stroke();

      // Signage Backplate
      const isGateOpen = armAngle < -45;
      ctx.fillStyle = '#020617';
      ctx.fillRect(90, portalY + 3, 300, portalH - 6);
      ctx.strokeStyle = isGateOpen ? '#10B981' : '#0284C7';
      ctx.lineWidth = 1;
      ctx.strokeRect(90, portalY + 3, 300, portalH - 6);

      // Signage Text (Trilingual)
      const signText = isGateOpen
        ? (lang === 'ar' ? '● تم السماح بالدخول | مرحباً بكم' : (lang === 'en' ? '● ACCESS GRANTED | WELCOME' : '● ACCÈS AUTORISÉ | BIENVENUE'))
        : (lang === 'ar' ? '● سمارت بارك • الجزائر الوسطى | الدخول' : (lang === 'en' ? '● SMART PARK • ALGIERS CENTRAL | ENTRANCE' : '● SMART PARK • ALGER-CENTRE | ENTRÉE'));
      ctx.fillStyle = isGateOpen ? '#10B981' : '#F59E0B';
      ctx.font = 'bold 8px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(signText, 240, portalY + 14);
      ctx.textAlign = 'left';

      // Overhead Lane Indicator Lamp
      ctx.fillStyle = isGateOpen ? '#10B981' : '#EF4444';
      ctx.beginPath(); ctx.arc(410, portalY + portalH / 2, 6, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#FFFFFF';
      ctx.font = 'bold 7px "JetBrains Mono", monospace';
      ctx.fillText(isGateOpen ? '↓' : '✕', 408, portalY + portalH / 2 + 2.5);

      // 11. Real-Time YOLOv11 Vehicle Bounding Box (Surrounding ONLY the vehicle)
      ctx.strokeStyle = '#06B6D4';
      ctx.lineWidth = 1.6;
      ctx.strokeRect(x - 4, y - 4, w + 8, h + 6);
      ctx.fillStyle = 'rgba(6, 182, 212, 0.9)';
      ctx.fillRect(x - 4, y - 16, 150, 13);
      ctx.fillStyle = '#000000';
      ctx.font = 'bold 7.5px "JetBrains Mono", monospace';
      const vehLabel = lang === 'ar'
        ? `YOLOv11: مركبة (0.98) | ${isEngineRunning ? 'يعمل' : 'متوقف'}`
        : (lang === 'en'
            ? `YOLOv11: VEHICLE (0.98) | ${isEngineRunning ? 'RUN' : 'OFF'}`
            : `YOLOv11: VEHICULE (0.98) | ${isEngineRunning ? 'MARCHE' : 'ARRET'}`);
      ctx.fillText(vehLabel, x - 1, y - 6.5);

      // Optical Engine Status & Vibration Telemetry Pill (On vehicle hood)
      const engColor = isEngineRunning ? '#10B981' : '#F59E0B';
      const engText = isEngineRunning
        ? (lang === 'ar' ? '● رصد المحرك: يعمل (820 د/د | 13.8 هرتز)' : (lang === 'en' ? '● ENGINE: RUNNING (820 RPM | 13.8Hz VIB)' : '● MOTEUR: EN MARCHE (820 RPM | 13.8Hz VIB)'))
        : (lang === 'ar' ? '■ رصد المحرك: متوقف (0 د/د | سكون)' : (lang === 'en' ? '■ ENGINE: STOPPED (0 RPM | STATIC)' : '■ MOTEUR: ÉTEINT (0 RPM | VIB NULLE)'));
      ctx.fillStyle = 'rgba(2, 6, 23, 0.90)';
      ctx.fillRect(x - 4, y + h - 16, 180, 12);
      ctx.strokeStyle = engColor; ctx.lineWidth = 0.8;
      ctx.strokeRect(x - 4, y + h - 16, 180, 12);
      ctx.fillStyle = engColor;
      ctx.font = 'bold 6.8px "JetBrains Mono", monospace';
      ctx.fillText(engText, x - 1, y + h - 7.5);

      // Plate OCR Reticle
      ctx.strokeStyle = '#10B981';
      ctx.lineWidth = 1.2;
      ctx.strokeRect(px - 4, py - 4, pw + 8, ph + 8);
      ctx.fillStyle = 'rgba(16, 185, 129, 0.9)';
      ctx.fillRect(px - 4, py - 13, 115, 10);
      ctx.fillStyle = '#000000';
      ctx.font = 'bold 6.8px "JetBrains Mono", monospace';
      ctx.fillText(`OCR: ${plateText} (99.4%)`, px - 2, py - 5.5);

      // Apply Common CCTV Security OSD & Grain
      const now = new Date().toLocaleTimeString(lang === 'ar' ? 'ar-DZ' : (lang === 'en' ? 'en-US' : 'fr-DZ'));
      const camTitle = (I18N[lang] && I18N[lang].cam1_name) || 'CAM-01 : VOIE 1 ENTREE';
      drawCCTVEffects(ctx, cvs.width, cvs.height, 'CAM-01', camTitle, 25.0, now, true);

      requestAnimationFrame(render);
    }
    render();

    return {
      triggerVehicle: (plate) => {
        plateText = plate;
        targetArmAngle = -80;
        setTimeout(() => {
          carDeparting = true;
        }, 1500);
      }
    };
  }
  // =========================================================================
  function setupCam2() {
    const cvs = document.getElementById('cam2-canvas');
    if (!cvs) return;
    const ctx = cvs.getContext('2d');
    cvs.width = 480; cvs.height = 270;

    let spoofMode = false;
    let frameCount = 0;
    let rppgHistory = [];
    for (let i = 0; i < 44; i++) rppgHistory.push(0);

    // InsightFace / MediaPipe 68-Point Facial Landmark Offsets
    const baseLandmarks = [
      // Jawline (0-14)
      [-42, -10], [-41, 8], [-38, 24], [-32, 38], [-24, 50], [-14, 58], [-4, 63], [0, 64], [4, 63], [14, 58], [24, 50], [32, 38], [38, 24], [41, 8], [42, -10],
      // Eyebrows (15-24)
      [-30, -23], [-23, -26], [-14, -26], [-6, -23], [6, -23], [14, -26], [23, -26], [30, -23],
      // Nose Bridge and Tip (25-33)
      [0, -18], [0, -10], [0, -2], [0, 6], [-6, 11], [-3, 12], [0, 13], [3, 12], [6, 11],
      // Eyes (34-45)
      [-24, -14], [-20, -17], [-14, -17], [-10, -14], [-14, -12], [-20, -12],
      [10, -14], [14, -17], [20, -17], [24, -14], [20, -12], [14, -12],
      // Lips Outer (46-57)
      [-16, 25], [-10, 22], [-4, 21], [0, 22], [4, 21], [10, 22], [16, 25],
      [10, 31], [4, 33], [0, 33], [-4, 33], [-10, 31]
    ];

    function render() {
      frameCount++;
      const isLight = document.documentElement.classList.contains('light');
      const lang = window.currentLang || 'fr';
      const I18N = window.I18N || {};

      // 1. Vehicle Cabin Background
      const bgGrad = ctx.createLinearGradient(0, 0, cvs.width, cvs.height);
      if (isLight) {
        bgGrad.addColorStop(0, '#94A3B8');
        bgGrad.addColorStop(0.4, '#64748B');
        bgGrad.addColorStop(1, '#475569');
      } else {
        bgGrad.addColorStop(0, '#0F172A');
        bgGrad.addColorStop(0.4, '#1E293B');
        bgGrad.addColorStop(1, '#0B1120');
      }
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, cvs.width, cvs.height);

      // Car Door Window Frame & A-Pillar (Left)
      ctx.fillStyle = isLight ? '#334155' : '#090D16';
      ctx.beginPath();
      ctx.moveTo(0, 0); ctx.lineTo(60, 0); ctx.lineTo(85, cvs.height); ctx.lineTo(0, cvs.height);
      ctx.closePath(); ctx.fill();
      ctx.strokeStyle = isLight ? '#475569' : '#1E293B'; ctx.lineWidth = 1.5; ctx.stroke();

      // Outdoor Sunlight / Lane Reflection Glint through Window
      const winGrad = ctx.createLinearGradient(0, 40, 70, 180);
      winGrad.addColorStop(0, 'rgba(56, 189, 248, 0.35)');
      winGrad.addColorStop(0.5, 'rgba(255, 255, 255, 0.15)');
      winGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = winGrad;
      ctx.fillRect(0, 0, 75, cvs.height);

      // 2. Access Kiosk Totem Structure (Right)
      const kW = 75, kX = cvs.width - kW;
      const kGrad = ctx.createLinearGradient(kX, 0, cvs.width, 0);
      kGrad.addColorStop(0, '#1E293B');
      kGrad.addColorStop(0.3, '#334155');
      kGrad.addColorStop(0.7, '#475569');
      kGrad.addColorStop(1, '#0F172A');
      ctx.fillStyle = kGrad;
      ctx.fillRect(kX, 0, kW, cvs.height);
      ctx.strokeStyle = '#0284C7'; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(kX, 0); ctx.lineTo(kX, cvs.height); ctx.stroke();

      // Kiosk Optical Lens Aperture Ring
      ctx.fillStyle = '#020617';
      ctx.beginPath(); ctx.arc(kX + 22, 115, 16, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#06B6D4'; ctx.lineWidth = 2; ctx.stroke();
      ctx.fillStyle = '#38BDF8';
      ctx.beginPath(); ctx.arc(kX + 22, 115, 7, 0, Math.PI * 2); ctx.fill();

      // Dual 850nm NIR Illuminators
      [100, 130].forEach(ledY => {
        ctx.fillStyle = '#06B6D4';
        ctx.beginPath(); ctx.arc(kX + 22, ledY, 3, 0, Math.PI * 2); ctx.fill();
      });

      // RFID Target Symbol
      ctx.fillStyle = isLight ? '#CBD5E1' : '#64748B';
      ctx.font = 'bold 7px "JetBrains Mono", monospace';
      ctx.fillText('RFID/CIB', kX + 6, 210);

      // 3. Realistic Driver Portrait inside Vehicle Cabin
      const breath = Math.sin(frameCount * 0.05) * 0.7;
      const faceCenterX = 230;
      const faceCenterY = 114 + breath;

      if (!spoofMode) {
        // Padded Car Seat Headrest behind Driver Head
        ctx.fillStyle = '#111827';
        ctx.beginPath();
        ctx.roundRect(faceCenterX - 36, faceCenterY - 65, 72, 65, 14);
        ctx.fill();
        ctx.strokeStyle = '#374151'; ctx.lineWidth = 1.5; ctx.stroke();
        // Headrest Steel Twin Posts
        ctx.fillStyle = '#9CA3AF';
        ctx.fillRect(faceCenterX - 20, faceCenterY - 6, 5, 20);
        ctx.fillRect(faceCenterX + 15, faceCenterY - 6, 5, 20);

        // Driver Torso & Navy Polo Shirt
        ctx.fillStyle = isLight ? '#1E293B' : '#0A1326';
        ctx.beginPath();
        ctx.ellipse(faceCenterX, faceCenterY + 115, 105, 52, 0, 0, Math.PI);
        ctx.fill();

        // 3-Point Diagonal Seatbelt Strap
        ctx.strokeStyle = '#020617';
        ctx.lineWidth = 14;
        ctx.beginPath();
        ctx.moveTo(faceCenterX - 65, faceCenterY + 60);
        ctx.lineTo(faceCenterX + 60, faceCenterY + 140);
        ctx.stroke();

        // Polo Collar
        ctx.fillStyle = isLight ? '#334155' : '#1E293B';
        ctx.beginPath();
        ctx.moveTo(faceCenterX - 28, faceCenterY + 68);
        ctx.lineTo(faceCenterX, faceCenterY + 98);
        ctx.lineTo(faceCenterX + 28, faceCenterY + 68);
        ctx.lineTo(faceCenterX + 16, faceCenterY + 64);
        ctx.lineTo(faceCenterX, faceCenterY + 82);
        ctx.lineTo(faceCenterX - 16, faceCenterY + 64);
        ctx.closePath(); ctx.fill();

        // Anatomical Neck
        const neckGrad = ctx.createLinearGradient(faceCenterX - 20, faceCenterY + 45, faceCenterX + 20, faceCenterY + 75);
        neckGrad.addColorStop(0, '#9A6B48');
        neckGrad.addColorStop(0.5, '#B5835C');
        neckGrad.addColorStop(1, '#8A5D3B');
        ctx.fillStyle = neckGrad;
        ctx.beginPath();
        ctx.moveTo(faceCenterX - 22, faceCenterY + 42);
        ctx.lineTo(faceCenterX + 22, faceCenterY + 42);
        ctx.lineTo(faceCenterX + 26, faceCenterY + 74);
        ctx.lineTo(faceCenterX - 26, faceCenterY + 74);
        ctx.closePath(); ctx.fill();

        // Realistic Anatomical Head Contour (Jawline & Chin)
        const skinGrad = ctx.createRadialGradient(faceCenterX - 6, faceCenterY - 8, 10, faceCenterX, faceCenterY + 5, 56);
        skinGrad.addColorStop(0, '#DFB088');
        skinGrad.addColorStop(0.55, '#C68B59');
        skinGrad.addColorStop(0.85, '#AD7243');
        skinGrad.addColorStop(1, '#7C4B27');
        ctx.fillStyle = skinGrad;

        ctx.beginPath();
        ctx.moveTo(faceCenterX - 42, faceCenterY - 14);
        ctx.quadraticCurveTo(faceCenterX - 42, faceCenterY + 20, faceCenterX - 32, faceCenterY + 40);
        ctx.quadraticCurveTo(faceCenterX - 20, faceCenterY + 60, faceCenterX, faceCenterY + 63);
        ctx.quadraticCurveTo(faceCenterX + 20, faceCenterY + 60, faceCenterX + 32, faceCenterY + 40);
        ctx.quadraticCurveTo(faceCenterX + 42, faceCenterY + 20, faceCenterX + 42, faceCenterY - 14);
        ctx.quadraticCurveTo(faceCenterX + 44, faceCenterY - 45, faceCenterX, faceCenterY - 52);
        ctx.quadraticCurveTo(faceCenterX - 44, faceCenterY - 45, faceCenterX - 42, faceCenterY - 14);
        ctx.closePath();
        ctx.fill();

        // Realistic Ears with Cartilage Depth
        [-43, 43].forEach(earX => {
          ctx.fillStyle = '#BA8153';
          ctx.beginPath();
          ctx.ellipse(faceCenterX + earX, faceCenterY + 4, 5.5, 11, 0, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = '#8B542E';
          ctx.beginPath();
          ctx.ellipse(faceCenterX + earX + (earX < 0 ? 1.5 : -1.5), faceCenterY + 4, 2.5, 6, 0, 0, Math.PI * 2);
          ctx.fill();
        });

        // Subtle 5 o'clock Shadow / Stubble along Jawline & Chin
        ctx.fillStyle = 'rgba(40, 25, 20, 0.35)';
        ctx.beginPath();
        ctx.moveTo(faceCenterX - 32, faceCenterY + 28);
        ctx.quadraticCurveTo(faceCenterX - 20, faceCenterY + 58, faceCenterX, faceCenterY + 61);
        ctx.quadraticCurveTo(faceCenterX + 20, faceCenterY + 58, faceCenterX + 32, faceCenterY + 28);
        ctx.quadraticCurveTo(faceCenterX, faceCenterY + 42, faceCenterX - 32, faceCenterY + 28);
        ctx.closePath(); ctx.fill();

        // Realistic Hair (Natural Crop with Temple Fade & Texture)
        ctx.fillStyle = '#171412';
        ctx.beginPath();
        ctx.moveTo(faceCenterX - 44, faceCenterY - 16);
        ctx.quadraticCurveTo(faceCenterX - 45, faceCenterY - 56, faceCenterX, faceCenterY - 60);
        ctx.quadraticCurveTo(faceCenterX + 45, faceCenterY - 56, faceCenterX + 44, faceCenterY - 16);
        ctx.lineTo(faceCenterX + 40, faceCenterY - 18);
        ctx.quadraticCurveTo(faceCenterX + 24, faceCenterY - 36, faceCenterX, faceCenterY - 34);
        ctx.quadraticCurveTo(faceCenterX - 24, faceCenterY - 36, faceCenterX - 40, faceCenterY - 18);
        ctx.closePath();
        ctx.fill();

        // Sideburns
        ctx.fillStyle = '#171412';
        ctx.fillRect(faceCenterX - 43, faceCenterY - 18, 3.5, 14);
        ctx.fillRect(faceCenterX + 39.5, faceCenterY - 18, 3.5, 14);

        // Natural Eyebrows
        ctx.strokeStyle = '#231B15';
        ctx.lineWidth = 2.8;
        ctx.beginPath();
        ctx.moveTo(faceCenterX - 28, faceCenterY - 24); ctx.lineTo(faceCenterX - 8, faceCenterY - 25);
        ctx.moveTo(faceCenterX + 8, faceCenterY - 25); ctx.lineTo(faceCenterX + 28, faceCenterY - 24);
        ctx.stroke();

        // Realistic Eyes (Almond contours with Iris striations & corneal glint)
        const isBlinking = (frameCount % 110 >= 105);
        if (isBlinking) {
          ctx.strokeStyle = '#3E2723';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(faceCenterX - 26, faceCenterY - 14); ctx.quadraticCurveTo(faceCenterX - 18, faceCenterY - 12, faceCenterX - 10, faceCenterY - 14);
          ctx.moveTo(faceCenterX + 10, faceCenterY - 14); ctx.quadraticCurveTo(faceCenterX + 18, faceCenterY - 12, faceCenterX + 26, faceCenterY - 14);
          ctx.stroke();
        } else {
          [-17, 17].forEach(eyeOffsetX => {
            const eyeX = faceCenterX + eyeOffsetX;
            const eyeY = faceCenterY - 14;
            // Sclera with soft ambient shading
            ctx.fillStyle = '#F5F5F7';
            ctx.beginPath();
            ctx.ellipse(eyeX, eyeY, 8.5, 4.8, 0, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = '#6D4C41'; ctx.lineWidth = 0.8; ctx.stroke();

            // Iris with Limbal Ring
            const irisGrad = ctx.createRadialGradient(eyeX, eyeY, 1, eyeX, eyeY, 4.2);
            irisGrad.addColorStop(0, '#5D4037');
            irisGrad.addColorStop(0.7, '#3E2723');
            irisGrad.addColorStop(1, '#1A0E0A');
            ctx.fillStyle = irisGrad;
            ctx.beginPath();
            ctx.arc(eyeX, eyeY, 4.2, 0, Math.PI * 2);
            ctx.fill();

            // Pupil
            ctx.fillStyle = '#000000';
            ctx.beginPath();
            ctx.arc(eyeX, eyeY, 2.0, 0, Math.PI * 2);
            ctx.fill();

            // Specular Corneal Glint (Reflecting Kiosk Ring Light)
            ctx.fillStyle = '#FFFFFF';
            ctx.beginPath();
            ctx.arc(eyeX - 1.2, eyeY - 1.2, 1.2, 0, Math.PI * 2);
            ctx.fill();
          });
        }

        // Realistic Nose (Bridge Shadow, Highlight & Nostrils)
        ctx.strokeStyle = '#9A6B48';
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        ctx.moveTo(faceCenterX, faceCenterY - 18);
        ctx.lineTo(faceCenterX - 1.5, faceCenterY + 6);
        ctx.lineTo(faceCenterX + 4.0, faceCenterY + 10);
        ctx.stroke();

        ctx.fillStyle = 'rgba(70, 35, 15, 0.45)';
        ctx.beginPath();
        ctx.ellipse(faceCenterX - 3.8, faceCenterY + 10.5, 2.2, 1.4, 0, 0, Math.PI * 2);
        ctx.ellipse(faceCenterX + 3.8, faceCenterY + 10.5, 2.2, 1.4, 0, 0, Math.PI * 2);
        ctx.fill();

        // Realistic Lips (Cupid's bow & vermilion border)
        ctx.fillStyle = '#9C584B';
        ctx.beginPath();
        ctx.ellipse(faceCenterX, faceCenterY + 26, 12, 4.2, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = 'rgba(255, 255, 255, 0.15)';
        ctx.fillRect(faceCenterX - 4, faceCenterY + 26, 8, 1.5);

        // Biometric FaceMesh 68-Point Landmark Constellation
        ctx.fillStyle = 'rgba(6, 182, 212, 0.85)';
        baseLandmarks.forEach(([lx, ly]) => {
          ctx.beginPath();
          ctx.arc(faceCenterX + lx, faceCenterY + ly, 1.3, 0, Math.PI * 2);
          ctx.fill();
        });

        // 3D Bounding Box with Corner Reticles
        const bbX = faceCenterX - 52, bbY = faceCenterY - 68, bbW = 104, bbH = 138;
        ctx.strokeStyle = '#06B6D4';
        ctx.lineWidth = 1.6;
        ctx.setLineDash([6, 3]);
        ctx.strokeRect(bbX, bbY, bbW, bbH);
        ctx.setLineDash([]);

        // Top ID Pill
        ctx.fillStyle = 'rgba(6, 182, 212, 0.95)';
        ctx.fillRect(bbX, bbY - 16, bbW, 16);
        ctx.fillStyle = '#000000';
        ctx.font = 'bold 7.5px "JetBrains Mono", monospace';
        const driverTitle = lang === 'ar' ? 'أمين حاج (VIP) | 99.4%' : 'AMINE HADJ (VIP) | 99.4%';
        ctx.fillText(driverTitle, bbX + 4, bbY - 4);

        // Real-Time Arterial Pulse Waveform (rPPG 72 BPM)
        rppgHistory.shift();
        const pulseVal = Math.sin(frameCount * 0.18) * 12 + Math.sin(frameCount * 0.36) * 4;
        rppgHistory.push(pulseVal);

        ctx.fillStyle = 'rgba(6, 20, 36, 0.90)';
        ctx.fillRect(285, 178, 125, 52);
        ctx.strokeStyle = '#06B6D4'; ctx.lineWidth = 1; ctx.strokeRect(285, 178, 125, 52);

        ctx.fillStyle = '#38BDF8';
        ctx.font = '7.5px "JetBrains Mono", monospace';
        const rppgTitle = lang === 'ar' ? 'النبض rPPG: 72 ن/د' : (lang === 'en' ? 'PULSE rPPG: 72 BPM' : 'POULS rPPG : 72 BPM');
        ctx.fillText(rppgTitle, 290, 190);
        ctx.fillStyle = '#10B981';
        const livenessOk = lang === 'ar' ? 'حيوي' : (lang === 'en' ? 'LIVE OK' : 'VIVACITE OK');
        ctx.fillText(livenessOk, 372, 190);

        ctx.strokeStyle = '#10B981';
        ctx.lineWidth = 1.6;
        ctx.beginPath();
        for (let p = 0; p < rppgHistory.length; p++) {
          const px = 289 + p * 2.6;
          const py = 212 - rppgHistory[p];
          if (p === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        }
        ctx.stroke();

        // ArcFace 512-D Embedding Vector Spectrum
        ctx.fillStyle = 'rgba(6, 20, 36, 0.90)';
        ctx.fillRect(65, 178, 125, 52);
        ctx.strokeStyle = '#06B6D4'; ctx.lineWidth = 1; ctx.strokeRect(65, 178, 125, 52);
        ctx.fillStyle = '#38BDF8';
        ctx.font = '7.5px "JetBrains Mono", monospace';
        const embedTitle = lang === 'ar' ? 'المتجه 512-D' : 'EMBEDDING 512-D';
        ctx.fillText(embedTitle, 70, 190);
        ctx.fillStyle = '#10B981';
        ctx.fillText('DIST: 0.42', 145, 190);

        for (let b = 0; b < 10; b++) {
          const bh = 5 + Math.abs(Math.sin(frameCount * 0.08 + b * 0.6)) * 22;
          ctx.fillStyle = '#06B6D4';
          ctx.fillRect(70 + b * 11.5, 224 - bh, 8.5, bh);
        }

      } else {
        // PHOTO SPOOF ATTACK (PAPER / SCREEN REPLAY)
        ctx.fillStyle = '#EF4444';
        ctx.font = 'bold 12px "JetBrains Mono", monospace';
        const spoofWarn = lang === 'ar' ? '⚠️ احتيال بصري: إعادة تشغيل شاشة' : (lang === 'en' ? '⚠️ SPOOF ATTACK: SCREEN REPLAY' : '⚠️ ATTAQUE PHOTO : ECRAN REPLAY');
        ctx.fillText(spoofWarn, 75, 100);

        // Tablet / Paper Border
        ctx.strokeStyle = '#EF4444';
        ctx.lineWidth = 3;
        ctx.strokeRect(155, 45, 150, 140);
        ctx.fillStyle = '#1E293B';
        ctx.fillRect(160, 50, 140, 130);

        // Fourier Moire High Frequency Analysis
        ctx.fillStyle = 'rgba(239, 68, 68, 0.9)';
        ctx.fillRect(65, 178, 125, 52);
        ctx.fillStyle = '#FFFFFF';
        ctx.font = '7.5px "JetBrains Mono", monospace';
        ctx.fillText('MOIRE SPECTRUM 88.4%', 70, 190);
        for (let b = 0; b < 10; b++) {
          const bh = b > 5 ? (22 + (b % 3) * 5) : (3 + (b % 2) * 2);
          ctx.fillStyle = '#FFFFFF';
          ctx.fillRect(70 + b * 11.5, 224 - bh, 8.5, bh);
        }
      }

      // 4. PIP VIEWPORT (TOP RIGHT): 850nm NIR CHANNEL
      const pipX = 310, pipY = 24, pipW = 98, pipH = 68;
      ctx.fillStyle = '#020617';
      ctx.fillRect(pipX, pipY, pipW, pipH);
      ctx.strokeStyle = spoofMode ? '#EF4444' : '#06B6D4';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(pipX, pipY, pipW, pipH);

      ctx.fillStyle = spoofMode ? 'rgba(239, 68, 68, 0.2)' : 'rgba(6, 182, 212, 0.2)';
      ctx.fillRect(pipX, pipY, pipW, 13);
      ctx.fillStyle = spoofMode ? '#EF4444' : '#06B6D4';
      ctx.font = 'bold 7px "JetBrains Mono", monospace';
      ctx.fillText('CANAL NIR 850nm', pipX + 4, pipY + 9);

      if (!spoofMode) {
        const nirGrad = ctx.createRadialGradient(pipX + pipW / 2, pipY + 40, 4, pipX + pipW / 2, pipY + 40, 20);
        nirGrad.addColorStop(0, '#CBD5E1');
        nirGrad.addColorStop(0.7, '#64748B');
        nirGrad.addColorStop(1, '#1E293B');
        ctx.fillStyle = nirGrad;
        ctx.beginPath(); ctx.arc(pipX + pipW / 2, pipY + 40, 18, 0, Math.PI * 2); ctx.fill();

        // Bright Corneal Retro-Reflection Glints
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(pipX + pipW / 2 - 7, pipY + 36, 2, 2);
        ctx.fillRect(pipX + pipW / 2 + 5, pipY + 36, 2, 2);

        ctx.fillStyle = '#10B981';
        ctx.font = 'bold 6.5px "JetBrains Mono", monospace';
        const perfText = lang === 'ar' ? 'الانتشار الجلدي: سليم' : (lang === 'en' ? 'DERMAL PERFUSION OK' : 'DIFFUSION DERMIQUE OK');
        ctx.fillText(perfText, pipX + 4, pipY + pipH - 4);
      } else {
        ctx.fillStyle = '#F8FAFC';
        ctx.fillRect(pipX + 16, pipY + 18, 66, 38);
        ctx.fillStyle = '#EF4444';
        ctx.font = 'bold 6.5px "JetBrains Mono", monospace';
        const reflText = lang === 'ar' ? 'انعكاس زجاجي صلب' : (lang === 'en' ? 'GLASS REFLECTION' : 'REFLET VERRE COMPACT');
        ctx.fillText(reflText, pipX + 4, pipY + pipH - 4);
      }

      // Apply CCTV Security OSD
      const now = new Date().toLocaleTimeString(lang === 'ar' ? 'ar-DZ' : (lang === 'en' ? 'en-US' : 'fr-DZ'));
      const camTitle = (I18N[lang] && I18N[lang].cam2_name) || 'CAM-02 : BORNE BIOMETRIQUE';
      drawCCTVEffects(ctx, cvs.width, cvs.height, 'CAM-02', camTitle, 25.0, now, true);

      requestAnimationFrame(render);
    }
    render();

    return {
      triggerVehicle: (isSpoof = false) => {
        spoofMode = isSpoof;
        setTimeout(() => { spoofMode = false; }, 20000);
      }
    };
  }
  // =========================================================================
  // CAM 3 : VOIE 2 SORTIE (ALPR PERSPECTIVE & DYNAMIC TOLL BARRIER)
  // =========================================================================
  function setupCam3() {
    const cvs = document.getElementById('cam3-canvas');
    if (!cvs) return;
    const ctx = cvs.getContext('2d');
    cvs.width = 480; cvs.height = 270;

    let armAngle = 0; // 0 = straight up across lane (closed), 82 = rotated clockwise along curb (open)
    let targetAngle = 0;

    // Physical State Machine:
    // 'APPROACHING' -> 'STOPPED' -> 'OPENING' -> 'DEPARTING' -> 'LANE_CLEAR'
    let carState = 'STOPPED';
    let carX = 60; // Stop position at X=60 (bumper X=178, stop line X=205, barrier X=220)
    let carSpeed = 0.0;
    let wheelAngle = 0.0;
    let stopDwellFrames = 0;
    let clearDwellFrames = 0;
    let brakeDip = 0.0;
    let frameCount = 0;
    let plateText = "08192 120 09";
    const availablePlates = [
      "08192 120 09",
      "104822 119 16",
      "04122 118 16",
      "08412 00 16",
      "03144 117 31"
    ];

    function render() {
      frameCount++;
      const isLight = document.documentElement.classList.contains('light');
      const lang = window.currentLang || 'fr';
      const I18N = window.I18N || {};
      const isEngineOn = window.isVehicleEngineRunning !== false;

      // Barrier Arm Interpolation
      armAngle += (targetAngle - armAngle) * 0.09;

      // Card Header Arm Status Indicator Sync
      const armEl = document.getElementById('cam3-arm-text');
      if (armEl) {
        if (armAngle > 15) {
          armEl.innerText = lang === 'ar' ? 'مفتوح' : (lang === 'en' ? 'OPEN' : 'LEVÉE (OUVERT)');
          armEl.className = 'text-emeraldAccent font-semibold';
        } else {
          armEl.innerText = lang === 'ar' ? 'مغلق' : (lang === 'en' ? 'CLOSED' : 'BAISSÉE');
          armEl.className = 'text-red-400 font-semibold';
        }
      }

      // -------------------------------------------------------------
      // Physical Vehicle Motion & Detection State Machine
      // -------------------------------------------------------------
      if (carState === 'APPROACHING') {
        targetAngle = 0; // Barrier strictly lowered
        const dist = 60 - carX;
        if (dist > 0.8) {
          // Smooth deceleration curve towards stop line
          carSpeed = Math.min(2.8, Math.max(0.35, dist * 0.04));
          carX += carSpeed;
          wheelAngle += (carSpeed / 12.5) * Math.PI * 2;
          brakeDip = Math.min(1.6, carSpeed * 0.45); // Forward braking pitch
        } else {
          // Complete full stop
          carX = 60;
          carSpeed = 0.0;
          brakeDip = 0.0;
          carState = 'STOPPED';
          stopDwellFrames = 0;
        }
      } else if (carState === 'STOPPED') {
        carSpeed = 0.0;
        brakeDip = 0.0;
        // Wheels do NOT spin when car is stopped!
        stopDwellFrames++;
        // Dwell at barrier for ~300 frames (5-6 seconds) before auto-departing
        if (stopDwellFrames > 320) {
          targetAngle = 82;
          carState = 'OPENING';
        }
      } else if (carState === 'OPENING') {
        carSpeed = 0.0;
        targetAngle = 82;
        // Wait for barrier arm to clear past 38 degrees before car rolls
        if (armAngle > 38) {
          carState = 'DEPARTING';
          carSpeed = 0.6;
        }
      } else if (carState === 'DEPARTING') {
        targetAngle = 82;
        // Accelerate forward across departure loop
        if (carSpeed < 3.6) carSpeed += 0.055;
        carX += carSpeed;
        wheelAngle += (carSpeed / 12.5) * Math.PI * 2;
        brakeDip = -0.5; // Slight rear acceleration squat

        if (carX > cvs.width + 120) {
          carState = 'LANE_CLEAR';
          clearDwellFrames = 0;
          targetAngle = 0; // Smoothly lower barrier
        }
      } else if (carState === 'LANE_CLEAR') {
        targetAngle = 0;
        carSpeed = 0.0;
        clearDwellFrames++;
        if (clearDwellFrames > 90) { // 1.5 seconds clear
          // Spawn next vehicle approach from offscreen left
          carX = -130;
          carSpeed = 2.8;
          carState = 'APPROACHING';
          const nextIdx = Math.floor(Math.random() * availablePlates.length);
          plateText = availablePlates[nextIdx];
        }
      }

      // 1. Horizon & Industrial Building Facade (Exit Gate Enclosure)
      const skyGrad = ctx.createLinearGradient(0, 0, 0, 95);
      if (isLight) {
        skyGrad.addColorStop(0, '#BAE6FD');
        skyGrad.addColorStop(1, '#E2E8F0');
      } else {
        skyGrad.addColorStop(0, '#020617');
        skyGrad.addColorStop(1, '#0F172A');
      }
      ctx.fillStyle = skyGrad;
      ctx.fillRect(0, 0, cvs.width, 95);

      // Distant Industrial Facade
      ctx.fillStyle = isLight ? '#94A3B8' : '#1E293B';
      ctx.fillRect(0, 60, cvs.width, 35);
      ctx.strokeStyle = isLight ? '#CBD5E1' : '#334155'; ctx.lineWidth = 1;
      for (let w = 20; w < cvs.width; w += 40) {
        ctx.strokeRect(w, 68, 20, 18);
      }

      // 2. Asphalt Roadway (Spanning Y=95 to Y=244)
      const roadGrad = ctx.createLinearGradient(0, 95, 0, 244);
      if (isLight) {
        roadGrad.addColorStop(0, '#64748B');
        roadGrad.addColorStop(0.5, '#475569');
        roadGrad.addColorStop(1, '#334155');
      } else {
        roadGrad.addColorStop(0, '#1E293B');
        roadGrad.addColorStop(0.5, '#0F172A');
        roadGrad.addColorStop(1, '#020617');
      }
      ctx.fillStyle = roadGrad;
      ctx.fillRect(0, 95, cvs.width, 149);

      // Road Surface Asphalt Aggregate Texture
      ctx.fillStyle = isLight ? 'rgba(0, 0, 0, 0.04)' : 'rgba(255, 255, 255, 0.025)';
      for (let i = 0; i < 40; i++) {
        const tx = (i * 47) % cvs.width;
        const ty = 100 + (i * 13) % 135;
        ctx.fillRect(tx, ty, 3, 1);
      }

      // Centerline White Dashed Markings
      ctx.strokeStyle = isLight ? '#FFFFFF' : 'rgba(226, 232, 240, 0.8)';
      ctx.lineWidth = 3;
      ctx.setLineDash([18, 16]);
      ctx.beginPath();
      ctx.moveTo(0, 172); ctx.lineTo(cvs.width, 172);
      ctx.stroke();
      ctx.setLineDash([]);

      // White Stop Line in front of barrier (at X = 205, spanning lane from Y=96 to 244)
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(205, 96); ctx.lineTo(205, 244);
      ctx.stroke();

      // Stop Line Transverse Text "STOP"
      ctx.save();
      ctx.translate(196, 175);
      ctx.rotate(-Math.PI / 2);
      ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
      ctx.font = 'bold 8.5px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText('ARRÊT / STOP', 0, 0);
      ctx.restore();

      // Safety Curbs with Yellow & Black Segments (Top and Bottom)
      for (let x = 0; x < cvs.width; x += 32) {
        const isYellow = Math.floor(x / 32) % 2 === 0;
        ctx.fillStyle = isYellow ? '#F59E0B' : (isLight ? '#334155' : '#0F172A');
        ctx.fillRect(x, 244, 32, 8);
        ctx.fillRect(x, 88, 32, 8);
        ctx.strokeStyle = isLight ? '#64748B' : '#334155'; ctx.lineWidth = 0.8;
        ctx.strokeRect(x, 244, 32, 8);
        ctx.strokeRect(x, 88, 32, 8);
      }

      // 3. Embedded Inductive Ground Loops in Roadway
      // Loop A: Approach Loop (at X=70..166)
      const isLoopAOccupied = carState !== 'LANE_CLEAR' && carX >= -20 && carX <= 180;
      ctx.strokeStyle = isLoopAOccupied ? '#06B6D4' : (isLight ? '#64748B' : '#475569');
      ctx.lineWidth = 2;
      ctx.strokeRect(70, 118, 96, 96);
      ctx.fillStyle = isLoopAOccupied ? 'rgba(6, 182, 212, 0.22)' : (isLight ? 'rgba(255, 255, 255, 0.15)' : 'rgba(30, 41, 59, 0.25)');
      ctx.fillRect(70, 118, 96, 96);

      ctx.fillStyle = isLoopAOccupied ? '#06B6D4' : (isLight ? '#1E293B' : '#64748B');
      ctx.font = 'bold 7.5px "JetBrains Mono", monospace';
      const loopALabel = lang === 'ar' ? (isLoopAOccupied ? 'المستشعر أ: رصد المركبة' : 'المستشعر أ (انتظار)') : (lang === 'en' ? (isLoopAOccupied ? 'LOOP A: ACTIVE' : 'LOOP A (STANDBY)') : (isLoopAOccupied ? 'BOUCLE A : ACTIF' : 'BOUCLE A (ATTENTE)'));
      ctx.fillText(loopALabel, 75, 130);

      // Loop B: Departure Loop (at X=260..356)
      const isLoopBOccupied = carState !== 'LANE_CLEAR' && carX >= 210 && carX <= 420;
      ctx.strokeStyle = isLoopBOccupied ? '#10B981' : (isLight ? '#64748B' : '#475569');
      ctx.lineWidth = 2;
      ctx.strokeRect(260, 118, 96, 96);
      ctx.fillStyle = isLoopBOccupied ? 'rgba(16, 185, 129, 0.22)' : (isLight ? 'rgba(255, 255, 255, 0.15)' : 'rgba(30, 41, 59, 0.25)');
      ctx.fillRect(260, 118, 96, 96);
      ctx.fillStyle = isLoopBOccupied ? '#10B981' : (isLight ? '#1E293B' : '#64748B');
      const loopBLabel = lang === 'ar' ? (isLoopBOccupied ? 'المستشعر ب: إخلاء المسلك' : 'المستشعر ب (مغادرة)') : (lang === 'en' ? (isLoopBOccupied ? 'LOOP B: CLEARED' : 'LOOP B (DEPARTURE)') : (isLoopBOccupied ? 'BOUCLE B : PASSAGE OK' : 'BOUCLE B (DEGAGEMENT)'));
      ctx.fillText(loopBLabel, 265, 130);

      // 4. Optical Safety Photocell Beam (at X = 215)
      const isBeamBroken = carState !== 'LANE_CLEAR' && carX >= 165 && carX <= 285;
      ctx.fillStyle = '#F59E0B';
      ctx.fillRect(212, 88, 7, 12);
      ctx.fillRect(212, 244, 7, 12);
      ctx.fillStyle = '#020617';
      ctx.fillRect(213, 92, 5, 5);
      ctx.fillRect(213, 247, 5, 5);

      // Infrared Safety Beam
      ctx.strokeStyle = isBeamBroken ? '#EF4444' : 'rgba(6, 182, 212, 0.55)';
      ctx.lineWidth = isBeamBroken ? 2 : 1;
      ctx.setLineDash(isBeamBroken ? [4, 4] : [2, 6]);
      ctx.beginPath();
      ctx.moveTo(215, 98); ctx.lineTo(215, 244);
      ctx.stroke();
      ctx.setLineDash([]);

      // 5. Heavy Structural Toll Gantry & VMS Display (Unobstructed at top)
      [15, 450].forEach(colX => {
        ctx.fillStyle = isLight ? '#475569' : '#1E293B';
        ctx.fillRect(colX, 15, 15, 235);
        ctx.strokeStyle = isLight ? '#64748B' : '#334155'; ctx.lineWidth = 1; ctx.strokeRect(colX, 15, 15, 235);
      });

      const girderGrad = ctx.createLinearGradient(15, 15, 15, 38);
      if (isLight) {
        girderGrad.addColorStop(0, '#334155');
        girderGrad.addColorStop(0.5, '#475569');
        girderGrad.addColorStop(1, '#1E293B');
      } else {
        girderGrad.addColorStop(0, '#1E293B');
        girderGrad.addColorStop(0.5, '#334155');
        girderGrad.addColorStop(1, '#0F172A');
      }
      ctx.fillStyle = girderGrad;
      ctx.fillRect(15, 15, 451, 24);
      ctx.strokeStyle = isLight ? '#64748B' : '#475569'; ctx.lineWidth = 1.5; ctx.strokeRect(15, 15, 451, 24);

      // Steel Truss Internal Lattice Struts
      ctx.strokeStyle = isLight ? 'rgba(255, 255, 255, 0.35)' : 'rgba(148, 163, 184, 0.4)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let t = 20; t < 460; t += 22) {
        ctx.moveTo(t, 16); ctx.lineTo(t + 11, 38);
        ctx.moveTo(t + 11, 38); ctx.lineTo(t + 22, 16);
      }
      ctx.stroke();

      // VMS LED Matrix Board (Trilingual)
      ctx.fillStyle = '#020617';
      ctx.fillRect(95, 19, 290, 26);
      ctx.strokeStyle = '#64748B'; ctx.lineWidth = 1.2;
      ctx.strokeRect(95, 19, 290, 26);

      const isOpen = armAngle > 35;
      ctx.textAlign = 'center';
      if (isOpen) {
        ctx.fillStyle = '#10B981';
        ctx.font = 'bold 8px "JetBrains Mono", monospace';
        const vmsHeader = (I18N[lang] && I18N[lang].gantry_sign_open) || "● VOIE 2 : SORTIE ACCORDEE | BONNE ROUTE";
        ctx.fillText(vmsHeader, 240, 31);
        ctx.fillStyle = '#34D399';
        ctx.font = '7px "JetBrains Mono", monospace';
        const vmsSub = lang === 'ar' ? 'الدفع الإلكتروني CIB/SATIM مؤكد | رافقتكم السلامة' : (lang === 'en' ? 'SATIM PAYMENT CONFIRMED | SAFE TRAVELS' : 'PAIEMENT SATIM CONFIRMÉ | BONNE ROUTE');
        ctx.fillText(vmsSub, 240, 41);
      } else {
        ctx.fillStyle = '#F59E0B';
        ctx.font = 'bold 8px "JetBrains Mono", monospace';
        const vmsHeader = (I18N[lang] && I18N[lang].gantry_sign_closed) || "■ VOIE 2 : PEAGE AUTOMATIQUE";
        ctx.fillText(vmsHeader, 240, 31);
        ctx.fillStyle = '#FCD34D';
        ctx.font = '7px "JetBrains Mono", monospace';
        const vmsSub = lang === 'ar' ? 'يرجى التوقف أمام الحاجز الآلي' : (lang === 'en' ? 'STOP IN FRONT OF AUTOMATIC BARRIER' : "MARQUEZ L'ARRET DEVANT LA BARRIERE");
        ctx.fillText(vmsSub, 240, 41);
      }
      ctx.textAlign = 'left';

      // Overhead Lane Signals
      // Red Cross
      ctx.fillStyle = !isOpen ? '#EF4444' : '#450A0A';
      ctx.beginPath(); ctx.arc(68, 29, 6.5, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#FFFFFF';
      ctx.font = 'bold 7.5px "JetBrains Mono", monospace';
      ctx.fillText('✕', 65.5, 31.5);

      // Green Down Arrow
      ctx.fillStyle = isOpen ? '#10B981' : '#064E3B';
      ctx.beginPath(); ctx.arc(412, 29, 6.5, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#FFFFFF';
      ctx.fillText('↓', 409.5, 31.5);

      // 6. Photorealistic Moving Sedan (Exiting)
      const vy = 138;
      // Idle chassis vibration ONLY when stopped or rolling with engine on
      const chassisVib = (isEngineOn && carState === 'STOPPED') ? (Math.sin(frameCount * 0.45) * 0.08) : 0.0;

      if (carState !== 'LANE_CLEAR') {
        // Chassis Drop Shadow
        ctx.fillStyle = isLight ? 'rgba(15, 23, 42, 0.45)' : 'rgba(0, 0, 0, 0.75)';
        ctx.beginPath();
        ctx.ellipse(carX + 59, vy + 46, 64, 11, 0, 0, Math.PI * 2);
        ctx.fill();

        // Exhaust Heat Drift (Only when engine is running)
        if (isEngineOn) {
          ctx.fillStyle = isLight ? 'rgba(100, 116, 139, 0.25)' : 'rgba(203, 213, 225, 0.20)';
          for (let p = 0; p < 4; p++) {
            const px = carX - 6 - ((frameCount * 1.5 + p * 12) % 36);
            const py = vy + 38 + chassisVib + brakeDip - ((frameCount * 0.6 + p * 8) % 18);
            const pr = 2 + (p * 1.2);
            ctx.beginPath(); ctx.arc(px, py, pr, 0, Math.PI * 2); ctx.fill();
          }
        }

        // Sedan Lower Body
        const carGrad = ctx.createLinearGradient(carX, vy + chassisVib + brakeDip, carX, vy + 44 + chassisVib + brakeDip);
        if (isLight) {
          carGrad.addColorStop(0, '#64748B');
          carGrad.addColorStop(0.35, '#475569');
          carGrad.addColorStop(0.7, '#334155');
          carGrad.addColorStop(1, '#1E293B');
        } else {
          carGrad.addColorStop(0, '#475569');
          carGrad.addColorStop(0.35, '#334155');
          carGrad.addColorStop(0.7, '#1E293B');
          carGrad.addColorStop(1, '#0F172A');
        }
        ctx.fillStyle = carGrad;
        ctx.beginPath();
        ctx.roundRect(carX, vy + 12 + chassisVib + brakeDip, 118, 32, 6);
        ctx.fill();
        ctx.strokeStyle = isLight ? '#94A3B8' : '#64748B'; ctx.lineWidth = 1; ctx.stroke();

        // Cabin Glasshouse
        const glassGrad = ctx.createLinearGradient(carX + 20, vy + chassisVib + brakeDip, carX + 90, vy + 14 + chassisVib + brakeDip);
        if (isLight) {
          glassGrad.addColorStop(0, '#38BDF8');
          glassGrad.addColorStop(0.5, '#7DD3FC');
          glassGrad.addColorStop(1, '#0284C7');
        } else {
          glassGrad.addColorStop(0, '#0369A1');
          glassGrad.addColorStop(0.5, '#0284C7');
          glassGrad.addColorStop(1, '#0F172A');
        }
        ctx.fillStyle = glassGrad;
        ctx.beginPath();
        ctx.moveTo(carX + 18, vy + 12 + chassisVib + brakeDip);
        ctx.lineTo(carX + 38, vy - 2 + chassisVib + brakeDip);
        ctx.lineTo(carX + 78, vy - 2 + chassisVib + brakeDip);
        ctx.lineTo(carX + 98, vy + 12 + chassisVib + brakeDip);
        ctx.closePath();
        ctx.fill();
        ctx.strokeStyle = '#1E293B'; ctx.lineWidth = 1.5; ctx.stroke();

        // B-Pillar Divider
        ctx.fillStyle = '#0F172A';
        ctx.fillRect(carX + 58, vy - 1 + chassisVib + brakeDip, 4, 13);

        // Driver Silhouette Inside Cabin
        ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
        ctx.beginPath(); ctx.arc(carX + 48, vy + 4 + chassisVib + brakeDip, 6.5, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.ellipse(carX + 48, vy + 12 + chassisVib + brakeDip, 9, 5, 0, 0, Math.PI); ctx.fill();

        // Door Handles
        ctx.fillStyle = '#CBD5E1';
        ctx.fillRect(carX + 42, vy + 16 + chassisVib + brakeDip, 7, 2);
        ctx.fillRect(carX + 68, vy + 16 + chassisVib + brakeDip, 7, 2);

        // Rotating Alloy Wheels (Accurately tied to linear vehicle motion)
        [carX + 26, carX + 94].forEach(wx => {
          const wy = vy + 42 + chassisVib + brakeDip;
          ctx.fillStyle = '#020617';
          ctx.beginPath(); ctx.arc(wx, wy, 12.5, 0, Math.PI * 2); ctx.fill();
          ctx.strokeStyle = '#1E293B'; ctx.lineWidth = 1.5; ctx.stroke();

          ctx.strokeStyle = '#CBD5E1'; ctx.lineWidth = 1.2;
          ctx.beginPath();
          // Spokes rotate strictly with linear translation; stationary when stopped!
          for (let s = 0; s < 5; s++) {
            const a = wheelAngle + (s * Math.PI * 2) / 5;
            ctx.moveTo(wx, wy); ctx.lineTo(wx + Math.cos(a) * 9, wy + Math.sin(a) * 9);
          }
          ctx.stroke();
        });

        // Front Headlights & Volumetric Cone
        if (isEngineOn) {
          ctx.fillStyle = '#F8FAFC';
          ctx.beginPath(); ctx.roundRect(carX + 114, vy + 16 + chassisVib + brakeDip, 4, 8, 2); ctx.fill();
          ctx.strokeStyle = '#38BDF8'; ctx.lineWidth = 1; ctx.stroke();

          const beamLimit = isOpen ? (carX + 190) : Math.min(carX + 190, 204);
          if (beamLimit > carX + 118) {
            const lightBeam = ctx.createLinearGradient(carX + 118, vy + 20, beamLimit, vy + 20);
            lightBeam.addColorStop(0, 'rgba(240, 249, 255, 0.45)');
            lightBeam.addColorStop(0.4, 'rgba(56, 189, 248, 0.22)');
            lightBeam.addColorStop(1, 'rgba(56, 189, 248, 0)');
            ctx.fillStyle = lightBeam;
            ctx.beginPath();
            ctx.moveTo(carX + 118, vy + 16 + chassisVib + brakeDip);
            ctx.lineTo(beamLimit, vy + 6);
            ctx.lineTo(beamLimit, vy + 34);
            ctx.lineTo(carX + 118, vy + 24 + chassisVib + brakeDip);
            ctx.closePath();
            ctx.fill();
          }
        } else {
          ctx.fillStyle = '#475569';
          ctx.beginPath(); ctx.roundRect(carX + 114, vy + 16 + chassisVib + brakeDip, 4, 8, 2); ctx.fill();
        }

        // Rear Taillights
        ctx.fillStyle = isEngineOn ? '#EF4444' : '#7F1D1D';
        ctx.beginPath(); ctx.roundRect(carX, vy + 16 + chassisVib + brakeDip, 4, 8, 2); ctx.fill();

        // Front License Plate
        ctx.fillStyle = '#000000';
        ctx.fillRect(carX + 114, vy + 26 + chassisVib + brakeDip, 4, 10);
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(carX + 115, vy + 27 + chassisVib + brakeDip, 3, 8);

        // -------------------------------------------------------------
        // Complete AI Detection Overlay (Bounding Box, Speed, Status)
        // -------------------------------------------------------------
        const speedKmH = (carSpeed * 7.2).toFixed(1);
        let tagColor = '#06B6D4';
        let statusText = '';
        let subText = '';

        if (carState === 'APPROACHING') {
          tagColor = '#06B6D4';
          statusText = lang === 'ar' ? `رصد: يقترب (${speedKmH} كم/سا)` : (lang === 'en' ? `[AI] APPROACHING: ${speedKmH} km/h` : `[IA] EN APPROCHE : ${speedKmH} km/h`);
          subText = lang === 'ar' ? 'حاجز مسلك 2: مغلق (مغلق)' : (lang === 'en' ? 'BARRIER: INTERLOCKED (LOWERED)' : 'BARRIÈRE : VERROUILLÉE (BAISSÉE)');
        } else if (carState === 'STOPPED') {
          tagColor = isEngineOn ? '#10B981' : '#F59E0B';
          statusText = lang === 'ar' ? `رصد: متوقف (0.0 كم/سا) | ${plateText}` : (lang === 'en' ? `[AI] STOPPED: 0.0 km/h | ${plateText}` : `[IA] ARRÊTÉ : 0.0 km/h | ${plateText}`);
          subText = lang === 'ar' ? (isEngineOn ? 'المحرك: يعمل (820 د/د) | بانتظار الفتح' : 'المحرك: متوقف (0 د/د)') : (lang === 'en' ? (isEngineOn ? 'ENGINE: IDLE (820 RPM) | CLEAR TO LIFT' : 'ENGINE: OFF (0 RPM)') : (isEngineOn ? 'MOTEUR : AU RALENTI (820 RPM)' : 'MOTEUR : ÉTEINT (0 RPM)'));
        } else if (carState === 'OPENING') {
          tagColor = '#34D399';
          statusText = lang === 'ar' ? 'الحاجز يفتح | الاستعداد للانطلاق' : (lang === 'en' ? '[AI] BARRIER CLEARING | PREPARING' : '[IA] LEVÉE BARRIÈRE | DÉPART IMMINENT');
          subText = lang === 'ar' ? 'المسلك مأمون | تصريح الخروج نشط' : (lang === 'en' ? 'LANE 2 CLEAR | TICKET VALIDATED' : 'VOIE 2 SÉCURISÉE | VALIDATION OK');
        } else if (carState === 'DEPARTING') {
          tagColor = '#10B981';
          statusText = lang === 'ar' ? `مغادرة: انطلاق (${speedKmH} كم/سا)` : (lang === 'en' ? `[AI] DEPARTING: ${speedKmH} km/h` : `[IA] EN DÉPART : ${speedKmH} km/h`);
          subText = lang === 'ar' ? 'إخلاء المسلك | رافقتكم السلامة' : (lang === 'en' ? 'LANE EVACUATION | SAFE TRAVELS' : 'ÉVACUATION SAS | BONNE ROUTE');
        }

        // AI Bounding Box
        ctx.strokeStyle = tagColor;
        ctx.lineWidth = 1.6;
        ctx.strokeRect(carX - 4, vy - 6 + chassisVib + brakeDip, 126, 56);

        // Motion & Status Header Badge
        ctx.fillStyle = tagColor;
        ctx.fillRect(carX - 4, vy - 20 + chassisVib + brakeDip, 126, 14);
        ctx.fillStyle = '#020617';
        ctx.font = 'bold 7px "JetBrains Mono", monospace';
        ctx.fillText(statusText, carX - 1, vy - 10 + chassisVib + brakeDip);

        // Sub-Telemetry Pill Below
        ctx.fillStyle = 'rgba(15, 23, 42, 0.94)';
        ctx.fillRect(carX - 4, vy + 52 + chassisVib + brakeDip, 126, 12);
        ctx.strokeStyle = tagColor;
        ctx.lineWidth = 0.8;
        ctx.strokeRect(carX - 4, vy + 52 + chassisVib + brakeDip, 126, 12);
        ctx.fillStyle = tagColor;
        ctx.font = 'bold 6.8px "JetBrains Mono", monospace';
        ctx.fillText(subText, carX - 1, vy + 61 + chassisVib + brakeDip);
      } else {
        // Lane is Clear Notice
        ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
        ctx.fillRect(130, 150, 220, 24);
        ctx.strokeStyle = '#10B981'; ctx.lineWidth = 1.2;
        ctx.strokeRect(130, 150, 220, 24);
        ctx.fillStyle = '#10B981';
        ctx.font = 'bold 8px "JetBrains Mono", monospace';
        ctx.textAlign = 'center';
        const clearMsg = lang === 'ar' ? 'مسلك 2: شاغر | جاهز للمركبة القادمة' : (lang === 'en' ? 'LANE 2: CLEAR | READY FOR NEXT VEHICLE' : 'VOIE 2 : LIBRE | EN ATTENTE VÉHICULE');
        ctx.fillText(clearMsg, 240, 165);
        ctx.textAlign = 'left';
      }

      // 7. Automatic Barrier Gate Cabinet & Articulated Boom Arm
      const barrierX = 220, barrierY = 196;
      const pivotX = barrierX + 9, pivotY = barrierY + 12;

      // Heavy Duty Steel Pedestal Cabinet
      ctx.fillStyle = '#EA580C'; // RAL 2004 Safety Orange
      ctx.beginPath();
      ctx.roundRect(barrierX, barrierY, 18, 48, 4);
      ctx.fill();
      ctx.strokeStyle = '#9A3412'; ctx.lineWidth = 1.5;
      ctx.strokeRect(barrierX, barrierY, 18, 48);

      // Flashing Strobe Beacon on Barrier Top
      const isMovingArm = Math.abs(armAngle) > 4 && Math.abs(armAngle) < 78;
      const beaconColor = isMovingArm ? (Math.floor(frameCount / 4) % 2 === 0 ? '#F59E0B' : '#EF4444') : (isOpen ? '#10B981' : '#EF4444');
      ctx.fillStyle = beaconColor;
      ctx.beginPath(); ctx.arc(pivotX, barrierY - 3, 4, Math.PI, 0); ctx.fill();

      // Articulated Boom Arm
      ctx.save();
      ctx.translate(pivotX, pivotY);
      ctx.rotate((armAngle * Math.PI) / 180);

      // Mechanical Hub
      ctx.fillStyle = '#0F172A';
      ctx.beginPath(); ctx.arc(0, 0, 6.5, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#94A3B8'; ctx.lineWidth = 1.2; ctx.stroke();

      // Boom Arm Tube (extends -108px along -Y when armAngle = 0)
      ctx.fillStyle = '#F8FAFC';
      ctx.fillRect(-3, -108, 6, 108);
      ctx.strokeStyle = '#64748B'; ctx.lineWidth = 0.8;
      ctx.strokeRect(-3, -108, 6, 108);

      // Red Reflective Diagonal Safety Bands
      ctx.fillStyle = '#EF4444';
      for (let s = -100; s < -10; s += 20) {
        ctx.beginPath();
        ctx.moveTo(-3, s);
        ctx.lineTo(3, s + 6);
        ctx.lineTo(3, s + 13);
        ctx.lineTo(-3, s + 7);
        ctx.closePath();
        ctx.fill();
      }

      // Tip Red LED Warning Light
      ctx.fillStyle = isOpen ? '#10B981' : '#EF4444';
      ctx.beginPath(); ctx.arc(0, -106, 3, 0, Math.PI * 2); ctx.fill();

      // Under-Arm Red/Green Integrated Safety Strip
      ctx.strokeStyle = isOpen ? '#10B981' : '#EF4444';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(0, -106); ctx.lineTo(0, -6);
      ctx.stroke();

      ctx.restore();

      // Apply CCTV Effects
      const now = new Date().toLocaleTimeString(lang === 'ar' ? 'ar-DZ' : (lang === 'en' ? 'en-US' : 'fr-DZ'));
      const camTitle = (I18N[lang] && I18N[lang].cam3_name) || 'CAM-03 : SORTIE VOIE 2';
      drawCCTVEffects(ctx, cvs.width, cvs.height, 'CAM-03', camTitle, 25.0, now, true);

      requestAnimationFrame(render);
    }
    render();

    return {
      openBarrier: () => {
        targetAngle = 82;
        if (carState === 'STOPPED' || carState === 'APPROACHING') {
          carState = 'OPENING';
        }
        const armEl = document.getElementById('cam3-arm-text');
        if (armEl) {
          const lang = window.currentLang || 'fr';
          armEl.innerText = lang === 'ar' ? 'مفتوح' : (lang === 'en' ? 'OPEN' : 'LEVÉE (OUVERT)');
          armEl.className = 'text-emeraldAccent font-semibold';
        }
      }
    };
  }
  // =========================================================================
  // CAM 4 : ZONE A & B (TACTICAL OVERHEAD PARKING DECK CCTV)
  // =========================================================================
  function setupCam4() {
    const cvs = document.getElementById('cam4-canvas');
    if (!cvs) return;
    const ctx = cvs.getContext('2d');
    cvs.width = 480; cvs.height = 270;
    let frameCount = 0;

    function render() {
      frameCount++;
      const isLight = document.documentElement.classList.contains('light');
      const lang = window.currentLang || 'fr';
      const I18N = window.I18N || {};
      const stalls = window.currentStalls || [];

      // 1. Industrial Epoxy Parking Deck Floor
      if (isLight) {
        ctx.fillStyle = '#E2E8F0';
        ctx.fillRect(0, 0, cvs.width, cvs.height);
      } else {
        ctx.fillStyle = '#060B18';
        ctx.fillRect(0, 0, cvs.width, cvs.height);
      }

      // Driving Aisle (Center)
      ctx.fillStyle = isLight ? '#CBD5E1' : '#0B132B';
      ctx.fillRect(0, 105, cvs.width, 60);
      ctx.strokeStyle = isLight ? '#94A3B8' : '#1E293B';
      ctx.lineWidth = 1;
      ctx.strokeRect(0, 105, cvs.width, 60);

      // Guidance Direction Arrows
      ctx.fillStyle = isLight ? 'rgba(255, 255, 255, 0.9)' : 'rgba(148, 163, 184, 0.45)';
      [110, 240, 370].forEach((ax, idx) => {
        const dir = idx === 1 ? -1 : 1;
        ctx.save();
        ctx.translate(ax, 135);
        ctx.scale(dir, 1);
        ctx.beginPath();
        ctx.moveTo(-12, -3); ctx.lineTo(4, -3); ctx.lineTo(4, -7); ctx.lineTo(14, 0); ctx.lineTo(4, 7); ctx.lineTo(4, 3); ctx.lineTo(-12, 3);
        ctx.closePath();
        ctx.fill();
        ctx.restore();
      });

      // Pedestrian Safety Green Walkway (Right Edge)
      ctx.fillStyle = isLight ? '#A7F3D0' : 'rgba(16, 185, 129, 0.2)';
      ctx.fillRect(425, 0, 55, cvs.height);
      ctx.strokeStyle = '#10B981'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(425, 0); ctx.lineTo(425, cvs.height); ctx.stroke();

      ctx.fillStyle = '#10B981';
      ctx.font = 'bold 7px "JetBrains Mono", monospace';
      ctx.save();
      ctx.translate(450, 135);
      ctx.rotate(Math.PI / 2);
      const pedText = lang === 'ar' ? 'مشاة' : (lang === 'en' ? 'PEDESTRIANS' : 'PIÉTONS');
      ctx.fillText(pedText, -15, 4);
      ctx.restore();

      // 2. Render Top Row (Zone A: A01 to A07)
      for (let i = 0; i < 7; i++) {
        const stallId = `A0${i + 1}`;
        const stallData = stalls.find(s => s.slot_number === stallId) || { status: 'vacant', plate: null };
        const sx = 20 + i * 56;
        const sy = 24;
        renderSingleStall(ctx, sx, sy, 46, 75, stallId, stallData, true, isLight, frameCount);
      }

      // 3. Render Bottom Row (Zone B: B01 to B07)
      for (let i = 0; i < 7; i++) {
        const stallId = `B0${i + 1}`;
        const stallData = stalls.find(s => s.slot_number === stallId) || { status: 'vacant', plate: null };
        const sx = 20 + i * 56;
        const sy = 171;
        renderSingleStall(ctx, sx, sy, 46, 75, stallId, stallData, false, isLight, frameCount);
      }

      // Apply CCTV OSD
      const now = new Date().toLocaleTimeString(lang === 'ar' ? 'ar-DZ' : (lang === 'en' ? 'en-US' : 'fr-DZ'));
      const camTitle = (I18N[lang] && I18N[lang].cam4_name) || 'CAM-04 : ZONE A & B (DECK)';
      drawCCTVEffects(ctx, cvs.width, cvs.height, 'CAM-04', camTitle, 25.0, now, true);

      requestAnimationFrame(render);
    }
    render();
  }

  function renderSingleStall(ctx, x, y, w, h, id, data, isTopRow, isLight, frameCount) {
    const isOccupied = data.status === 'occupied' || data.status === 'vip_occupied';
    const isVip = data.status === 'reserved' || data.status === 'vip';
    const lang = window.currentLang || 'fr';

    // Stall Floor Demarcation Lines
    ctx.strokeStyle = isLight ? '#94A3B8' : '#334155';
    ctx.lineWidth = 1.2;
    ctx.setLineDash([4, 2]);
    ctx.strokeRect(x, y, w, h);
    ctx.setLineDash([]);

    // Ultrasonic Sensor Indicator Light (Ceiling Puck)
    const puckY = isTopRow ? y + h - 5 : y + 5;
    const puckColor = isOccupied ? '#EF4444' : (isVip ? '#A855F7' : '#10B981');

    ctx.fillStyle = puckColor;
    ctx.beginPath(); ctx.arc(x + w / 2, puckY, 3.5, 0, Math.PI * 2); ctx.fill();

    // Soft Light Pool on Floor
    const puckGrad = ctx.createRadialGradient(x + w / 2, puckY, 1, x + w / 2, puckY, 14);
    puckGrad.addColorStop(0, puckColor + (isLight ? '40' : '60'));
    puckGrad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = puckGrad;
    ctx.beginPath(); ctx.arc(x + w / 2, puckY, 14, 0, Math.PI * 2); ctx.fill();

    // Stall Identifier
    ctx.fillStyle = isLight ? '#475569' : '#64748B';
    ctx.font = 'bold 7px "JetBrains Mono", monospace';
    ctx.fillText(id, x + 3, isTopRow ? y + 10 : y + h - 4);

    if (isOccupied) {
      // Top-Down Vehicle Render
      const carW = w - 10;
      const carH = h - 14;
      const cx = x + 5;
      const cy = y + 7;

      ctx.fillStyle = isLight ? 'rgba(15, 23, 42, 0.4)' : 'rgba(0, 0, 0, 0.7)';
      ctx.beginPath(); ctx.roundRect(cx + 1, cy + 1, carW, carH, 6); ctx.fill();

      // Car Body
      const carGrad = ctx.createLinearGradient(cx, cy, cx + carW, cy);
      carGrad.addColorStop(0, '#1E293B');
      carGrad.addColorStop(0.5, '#334155');
      carGrad.addColorStop(1, '#1E293B');
      ctx.fillStyle = carGrad;
      ctx.beginPath(); ctx.roundRect(cx, cy, carW, carH, 6); ctx.fill();
      ctx.strokeStyle = isLight ? '#64748B' : '#475569'; ctx.lineWidth = 1; ctx.stroke();

      // Windshield & Rear Window
      ctx.fillStyle = isLight ? '#38BDF8' : '#0284C7';
      const wsY = isTopRow ? cy + carH * 0.22 : cy + carH * 0.65;
      const rwY = isTopRow ? cy + carH * 0.72 : cy + carH * 0.15;
      ctx.fillRect(cx + 3, wsY, carW - 6, 6);
      ctx.fillRect(cx + 4, rwY, carW - 8, 5);

      // Roof Surface
      ctx.fillStyle = isLight ? '#475569' : '#1E293B';
      const roofY = isTopRow ? cy + carH * 0.34 : cy + carH * 0.28;
      ctx.fillRect(cx + 4, roofY, carW - 8, carH * 0.35);

    } else {
      ctx.fillStyle = isLight ? '#059669' : '#10B981';
      ctx.font = 'bold 7px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      const freeLabel = isVip ? (lang === 'ar' ? 'محجوز' : (lang === 'en' ? 'RESERVED' : 'RÉSERVÉ')) : (lang === 'ar' ? 'شاغرة' : (lang === 'en' ? 'FREE' : 'LIBRE'));
      ctx.fillText(freeLabel, x + w / 2, y + h / 2 + 3);
      ctx.textAlign = 'left';
    }
  }

  // =========================================================================
  // BOOTSTRAP CCTV ENGINE
  // =========================================================================
  window.initCCTVEngine = function () {
    const cam1 = setupCam1();
    const cam2 = setupCam2();
    const cam3 = setupCam3();
    setupCam4();

    window.cctvEngine = {
      triggerCam1: (plate) => { if (cam1) cam1.triggerVehicle(plate); },
      triggerCam2: (isSpoof) => { if (cam2) cam2.triggerVehicle(isSpoof); },
      triggerCam3: () => { if (cam3) cam3.openBarrier(); },
      setEngineRunning: (state) => window.setVehicleEngineState(state),
      toggleEngine: () => window.toggleVehicleEngine(),
      isEngineRunning: () => window.isVehicleEngineRunning
    };
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', window.initCCTVEngine);
  } else {
    window.initCCTVEngine();
  }

})(window);
