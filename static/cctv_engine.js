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

    let carY = 158;
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

      // Physics: Barrier Arm Easing
      armAngle += (targetArmAngle - armAngle) * 0.08;

      // Physics: Car Departure Animation
      if (carDeparting) {
        carY += carSpeed;
        carSpeed += 0.28;
        if (carY > 320) {
          carDeparting = false;
          carSpeed = 0;
          targetArmAngle = 0;
          setTimeout(() => {
            carY = 48;
            plateText = "08412 119 16";
          }, 1200);
        }
      } else if (carY < 158) {
        carY += 1.8;
      }

      // 1. Sky & Background Lighting
      if (isLight) {
        const skyGrad = ctx.createLinearGradient(0, 0, 0, 95);
        skyGrad.addColorStop(0, '#93C5FD');
        skyGrad.addColorStop(0.6, '#BAE6FD');
        skyGrad.addColorStop(1, '#E0F2FE');
        ctx.fillStyle = skyGrad;
        ctx.fillRect(0, 0, cvs.width, cvs.height);

        // Distant Algiers Urban Backdrop
        ctx.fillStyle = '#CBD5E1';
        ctx.fillRect(50, 48, 65, 30);
        ctx.fillRect(125, 42, 50, 36);
        ctx.fillRect(320, 50, 80, 28);
      } else {
        const skyGrad = ctx.createLinearGradient(0, 0, 0, 95);
        skyGrad.addColorStop(0, '#020617');
        skyGrad.addColorStop(0.6, '#0B132B');
        skyGrad.addColorStop(1, '#111C3A');
        ctx.fillStyle = skyGrad;
        ctx.fillRect(0, 0, cvs.width, cvs.height);

        // Night Skyline Silhouette
        ctx.fillStyle = '#0F172A';
        ctx.fillRect(50, 52, 65, 26);
        ctx.fillRect(125, 46, 50, 32);
        ctx.fillRect(320, 54, 80, 24);
      }

      // 2. Roadway Perspective (Lane 1 Asphalt)
      const roadGrad = ctx.createLinearGradient(0, 75, 0, cvs.height);
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

      // Road Surface Asphalt Aggregate Texture
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

      // White Stop Bar at Barrier
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(115, 215); ctx.lineTo(395, 215);
      ctx.stroke();

      // Stop Bar Stencil Text ("ARRÊT / STOP / قف")
      ctx.fillStyle = isLight ? '#FFFFFF' : 'rgba(255, 255, 255, 0.85)';
      ctx.font = 'bold 9px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      const stopText = lang === 'ar' ? 'قـــــف' : (lang === 'en' ? 'STOP' : 'ARRET');
      ctx.fillText(stopText, 255, 212);
      ctx.textAlign = 'left';

      // 3. Embedded Inductive Loop Sensor in Lane 1
      const isLoopOccupied = carY >= 110 && carY <= 240;
      ctx.strokeStyle = isLoopOccupied ? '#06B6D4' : (isLight ? '#94A3B8' : '#475569');
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(135, 175); ctx.lineTo(345, 175);
      ctx.lineTo(375, 228); ctx.lineTo(105, 228);
      ctx.closePath();
      ctx.stroke();

      ctx.fillStyle = isLoopOccupied ? 'rgba(6, 182, 212, 0.22)' : 'rgba(0, 0, 0, 0)';
      ctx.fill();

      // Inductive Loop Sealed Corner Cuts
      ctx.strokeStyle = isLoopOccupied ? '#06B6D4' : (isLight ? '#CBD5E1' : '#334155');
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(135, 183); ctx.lineTo(145, 175);
      ctx.moveTo(335, 175); ctx.lineTo(345, 183);
      ctx.moveTo(105, 220); ctx.lineTo(115, 228);
      ctx.moveTo(365, 228); ctx.lineTo(375, 220);
      ctx.stroke();

      // 4. Concrete Curb Island with Yellow & Black Safety Stripes (Left Side)
      const curbStartX = 28, curbStartY = 110;
      const curbW = 95;
      for (let s = 0; s < 8; s++) {
        const segY = curbStartY + s * 18;
        ctx.fillStyle = (s % 2 === 0) ? '#F59E0B' : (isLight ? '#334155' : '#0F172A');
        ctx.beginPath();
        ctx.moveTo(curbStartX + s * 4, segY);
        ctx.lineTo(curbStartX + curbW + s * 4, segY);
        ctx.lineTo(curbStartX + curbW + (s + 1) * 4, segY + 18);
        ctx.lineTo(curbStartX + (s + 1) * 4, segY + 18);
        ctx.closePath();
        ctx.fill();
        ctx.strokeStyle = isLight ? '#64748B' : '#1E293B';
        ctx.lineWidth = 0.8;
        ctx.stroke();
      }

      // 5. Architectural Security Guard Post (Cabine de Garde)
      const gbX = 38, gbY = 62, gbW = 82, gbH = 100;
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

      // Observation Window
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

      // Officer Silhouette & Desk Monitors Inside Booth
      ctx.fillStyle = isLight ? 'rgba(30, 41, 59, 0.9)' : 'rgba(15, 23, 42, 0.95)';
      ctx.beginPath();
      ctx.arc(winX + winW * 0.42, winY + 16, 8, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath();
      ctx.ellipse(winX + winW * 0.42, winY + 36, 14, 10, 0, 0, Math.PI); ctx.fill();

      // Desk Control Screen Glow (Green/Cyan monitors)
      ctx.fillStyle = '#10B981';
      ctx.fillRect(winX + winW * 0.62, winY + 24, 11, 8);
      ctx.fillStyle = '#06B6D4';
      ctx.fillRect(winX + winW * 0.78, winY + 24, 8, 8);

      // 6. Driver Access Kiosk Totem (CAM 2 Physical Enclosure)
      const kioskX = gbX + gbW + 8, kioskY = 175, kioskW = 15, kioskH = 42;
      ctx.fillStyle = isLight ? '#1E293B' : '#0F172A';
      ctx.fillRect(kioskX, kioskY, kioskW, kioskH);
      ctx.strokeStyle = '#0284C7';
      ctx.lineWidth = 1;
      ctx.strokeRect(kioskX, kioskY, kioskW, kioskH);

      // Kiosk Optical Camera Aperture Ring (CAM 2 lens)
      ctx.fillStyle = '#000000';
      ctx.beginPath(); ctx.arc(kioskX + kioskW / 2, kioskY + 10, 4.5, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#06B6D4';
      ctx.beginPath(); ctx.arc(kioskX + kioskW / 2, kioskY + 10, 2, 0, Math.PI * 2); ctx.fill();

      // Kiosk Card/Ticket Slot
      ctx.fillStyle = '#F59E0B';
      ctx.fillRect(kioskX + 3, kioskY + 24, 9, 2);

      // 7. Automatic Barrier Gate Pedestal & Boom Arm
      const bPedX = gbX + gbW + 28, bPedY = 178;
      const bPedW = 20, bPedH = 55;
      ctx.fillStyle = '#EA580C'; // RAL 2004 Pure Orange
      ctx.fillRect(bPedX, bPedY, bPedW, bPedH);
      ctx.strokeStyle = '#9A3412'; ctx.lineWidth = 1.2;
      ctx.strokeRect(bPedX, bPedY, bPedW, bPedH);

      // Strobe Dome on Cabinet Top
      const strobeActive = Math.abs(armAngle) > 5 && Math.abs(armAngle) < 75;
      const strobeColor = strobeActive ? (Math.floor(frameCount / 4) % 2 === 0 ? '#F59E0B' : '#EF4444') : (armAngle < -50 ? '#10B981' : '#EF4444');
      ctx.fillStyle = strobeColor;
      ctx.beginPath(); ctx.arc(bPedX + 10, bPedY - 3, 4.5, Math.PI, 0); ctx.fill();

      // Articulated Boom Arm Across Lane
      ctx.save();
      ctx.translate(bPedX + 10, bPedY + 16);
      ctx.rotate((armAngle * Math.PI) / 180);

      ctx.fillStyle = '#F8FAFC';
      ctx.fillRect(0, -5, 175, 9);
      // Red Reflective Diagonal Chevrons
      ctx.fillStyle = '#EF4444';
      for (let s = 10; s < 170; s += 22) {
        ctx.beginPath();
        ctx.moveTo(s, -5); ctx.lineTo(s + 11, -5);
        ctx.lineTo(s + 4, 4); ctx.lineTo(s - 7, 4);
        ctx.closePath(); ctx.fill();
      }
      // Active Continuous LED Neon Strip
      ctx.strokeStyle = armAngle < -40 ? '#10B981' : '#EF4444';
      ctx.lineWidth = 2.4;
      ctx.beginPath(); ctx.moveTo(2, -5); ctx.lineTo(172, -5); ctx.stroke();
      ctx.restore();

      // 8. Overhead Security Portal Structure & Localized Signage
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
      for (let x = 45; x < 435; x += 22) {
        ctx.moveTo(x, portalY); ctx.lineTo(x + 11, portalY + portalH);
        ctx.moveTo(x + 11, portalY + portalH); ctx.lineTo(x + 22, portalY);
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
        : ((I18N[lang] && I18N[lang].portal_sign) || "PARKING ALGER-CENTRE | ENTRÉE");
      ctx.fillStyle = isGateOpen ? '#10B981' : '#F59E0B';
      ctx.font = 'bold 8.5px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(signText, 240, portalY + 14);
      ctx.textAlign = 'left';

      // Overhead Lane Indicator Lamp (Left = Arrow, Right = Cross)
      ctx.fillStyle = isGateOpen ? '#10B981' : '#EF4444';
      ctx.beginPath(); ctx.arc(410, portalY + portalH / 2, 6, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#FFFFFF';
      ctx.font = 'bold 7px "JetBrains Mono", monospace';
      ctx.fillText(isGateOpen ? '↓' : '✕', 408, portalY + portalH / 2 + 2.5);

      // 9. Photorealistic Approaching / Stationed Sedan
      const idleVibe = Math.sin(frameCount * 0.15) * 0.35;
      const scale = 0.88;
      const w = 180 * scale;
      const h = 105 * scale;
      const cx = 240;
      const x = cx - w / 2;
      const y = carY + idleVibe;

      // Chassis Ground Drop Shadow
      ctx.fillStyle = isLight ? 'rgba(15, 23, 42, 0.45)' : 'rgba(0, 0, 0, 0.8)';
      ctx.beginPath();
      ctx.ellipse(cx, y + h + 2, w * 0.52, 10 * scale, 0, 0, Math.PI * 2);
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
      ctx.roundRect(x, y + h * 0.32, w, h * 0.68, 8 * scale);
      ctx.fill();
      ctx.strokeStyle = isLight ? '#64748B' : '#475569';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Sculpted Hood Creases & Specular Highlights
      ctx.strokeStyle = isLight ? 'rgba(255, 255, 255, 0.4)' : 'rgba(255, 255, 255, 0.18)';
      ctx.lineWidth = 1.2 * scale;
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
      ctx.arc(cx - w * 0.14, y + h * 0.18, 11 * scale, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.ellipse(cx - w * 0.14, y + h * 0.36, 18 * scale, 10 * scale, 0, 0, Math.PI);
      ctx.fill();

      // Steering Wheel Rim
      ctx.strokeStyle = 'rgba(51, 65, 85, 0.9)';
      ctx.lineWidth = 3 * scale;
      ctx.beginPath();
      ctx.arc(cx - w * 0.14, y + h * 0.34, 12 * scale, Math.PI * 0.8, Math.PI * 1.8);
      ctx.stroke();

      // Rearview Mirror
      ctx.fillStyle = '#0F172A';
      ctx.fillRect(cx - 8 * scale, y + h * 0.06, 16 * scale, 5 * scale);

      // Front Radiator Grille
      const gw = w * 0.52, gh = h * 0.24, gx = cx - gw / 2, gy = y + h * 0.45;
      ctx.fillStyle = '#090D16';
      ctx.beginPath(); ctx.roundRect(gx, gy, gw, gh, 4 * scale); ctx.fill();
      ctx.strokeStyle = '#64748B'; ctx.lineWidth = 1.2 * scale; ctx.stroke();

      // Chrome Grille Slats
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.35)';
      ctx.lineWidth = 0.8 * scale;
      for (let row = 1; row < 4; row++) {
        const ry = gy + (gh / 4) * row;
        ctx.beginPath(); ctx.moveTo(gx + 6 * scale, ry); ctx.lineTo(gx + gw - 6 * scale, ry); ctx.stroke();
      }

      // Projector Headlights
      const hw = w * 0.18, hh = h * 0.15;
      const leftHX = x + w * 0.05, rightHX = x + w * 0.77, hy = y + h * 0.42;

      [leftHX, rightHX].forEach((hlx, idx) => {
        ctx.fillStyle = '#020617';
        ctx.beginPath(); ctx.roundRect(hlx, hy, hw, hh, 4 * scale); ctx.fill();
        ctx.strokeStyle = '#38BDF8'; ctx.lineWidth = 1 * scale; ctx.stroke();

        // Projector Core Lens
        ctx.fillStyle = isLight ? '#BAE6FD' : '#FEF08A';
        ctx.beginPath(); ctx.arc(hlx + hw * 0.5, hy + hh * 0.5, 5 * scale, 0, Math.PI * 2); ctx.fill();

        // Volumetric Forward Light Fan (Night Only)
        if (!isLight) {
          const dirX = idx === 0 ? -w * 0.25 : w * 0.25;
          const beamGrad = ctx.createRadialGradient(hlx + hw * 0.5, hy + hh, 2, hlx + dirX, hy + 90 * scale, 85 * scale);
          beamGrad.addColorStop(0, 'rgba(254, 240, 138, 0.45)');
          beamGrad.addColorStop(1, 'rgba(254, 240, 138, 0)');
          ctx.fillStyle = beamGrad;
          ctx.beginPath();
          ctx.moveTo(hlx + hw * 0.2, hy + hh);
          ctx.lineTo(hlx + dirX - 35 * scale, hy + 95 * scale);
          ctx.lineTo(hlx + dirX + 45 * scale, hy + 95 * scale);
          ctx.closePath(); ctx.fill();
        }
      });

      // Front Algerian License Plate
      const pw = w * 0.44, ph = 16 * scale, px = cx - pw / 2, py = gy + gh * 0.88;
      ctx.fillStyle = '#000000';
      ctx.fillRect(px - 1, py - 1, pw + 2, ph + 2);
      ctx.fillStyle = '#FDE047'; // Algerian Front Plate Yellow
      ctx.fillRect(px, py, pw, ph);

      // Plate Text (Serif Numerals)
      ctx.fillStyle = '#000000';
      ctx.font = `bold ${9 * scale}px "JetBrains Mono", monospace`;
      ctx.textAlign = 'center';
      ctx.fillText(plateText, cx, py + ph * 0.72);
      ctx.textAlign = 'left';

      // 10. Real-Time YOLOv11 Vehicle Bounding Box
      ctx.strokeStyle = '#06B6D4';
      ctx.lineWidth = 1.8;
      ctx.strokeRect(x - 6, y - 4, w + 12, h + 12);
      ctx.fillStyle = 'rgba(6, 182, 212, 0.9)';
      ctx.fillRect(x - 6, y - 18, 140, 14);
      ctx.fillStyle = '#000000';
      ctx.font = 'bold 8px "JetBrains Mono", monospace';
      const vehLabel = lang === 'ar' ? 'YOLOv11: مركبة (0.98)' : (lang === 'en' ? 'YOLOv11: VEHICLE (0.98)' : 'YOLOv11: VEHICULE (0.98)');
      ctx.fillText(vehLabel, x - 2, y - 7);

      // PaddleOCR v4 License Plate Bounding Box
      ctx.strokeStyle = '#10B981';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(px - 4, py - 3, pw + 8, ph + 6);
      ctx.fillStyle = 'rgba(16, 185, 129, 0.9)';
      ctx.fillRect(px - 4, py - 14, 125, 11);
      ctx.fillStyle = '#000000';
      ctx.font = 'bold 7px "JetBrains Mono", monospace';
      ctx.fillText(`OCR: ${plateText} (99.4%)`, px - 2, py - 5);

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
  // CAM 2 : BORNE BIOMETRIQUE (RGB + 850nm NIR DRIVER CLOSE-UP)
  // 100% SPATIALLY AND ARCHITECTURALLY CONSISTENT WITH CAM 1
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
      [-46, -14], [-45, 6], [-42, 24], [-36, 40], [-26, 54], [-15, 64], [-5, 70], [0, 72], [5, 70], [15, 64], [26, 54], [36, 40], [42, 24], [45, 6], [46, -14],
      // Eyebrows (15-24)
      [-36, -26], [-28, -32], [-18, -33], [-8, -30], [-2, -24],
      [2, -24], [8, -30], [18, -33], [28, -32], [36, -26],
      // Nose Bridge & Base (25-33)
      [0, -22], [0, -12], [0, -3], [0, 8], [-9, 14], [-4, 16], [0, 17], [4, 16], [9, 14],
      // Left Eye Contour (34-39)
      [-26, -16], [-20, -20], [-12, -19], [-7, -15], [-13, -13], [-21, -14],
      // Right Eye Contour (40-45)
      [7, -15], [12, -19], [20, -20], [26, -16], [21, -14], [13, -13],
      // Lips (46-57)
      [-20, 32], [-12, 27], [-5, 26], [0, 27], [5, 26], [12, 27], [20, 32], [12, 42], [5, 45], [0, 46], [-5, 45], [-12, 42]
    ];

    function render() {
      frameCount++;
      const isLight = document.documentElement.classList.contains('light');
      const lang = window.currentLang || 'fr';
      const I18N = window.I18N || {};

      // ========================================================
      // 1. EXTERIOR BACKGROUND SEEN FROM KIOSK (MATCHING CAM 1)
      // ========================================================
      if (isLight) {
        const skyGrad = ctx.createLinearGradient(0, 0, 0, 110);
        skyGrad.addColorStop(0, '#93C5FD');
        skyGrad.addColorStop(0.6, '#BAE6FD');
        skyGrad.addColorStop(1, '#E0F2FE');
        ctx.fillStyle = skyGrad;
        ctx.fillRect(0, 0, cvs.width, cvs.height);
      } else {
        const skyGrad = ctx.createLinearGradient(0, 0, 0, 110);
        skyGrad.addColorStop(0, '#020617');
        skyGrad.addColorStop(0.6, '#0B132B');
        skyGrad.addColorStop(1, '#111C3A');
        ctx.fillStyle = skyGrad;
        ctx.fillRect(0, 0, cvs.width, cvs.height);
      }

      // Background Voie 1 Pavement Outside Car
      const bgRoadGrad = ctx.createLinearGradient(0, 50, 0, cvs.height);
      if (isLight) {
        bgRoadGrad.addColorStop(0, '#64748B');
        bgRoadGrad.addColorStop(1, '#475569');
      } else {
        bgRoadGrad.addColorStop(0, '#0F172A');
        bgRoadGrad.addColorStop(1, '#020617');
      }
      ctx.fillStyle = bgRoadGrad;
      ctx.fillRect(0, 50, cvs.width, cvs.height - 50);

      // Overhead Steel Portal Truss Canopy (Matching CAM 1)
      const pY = 0, pH = 26;
      ctx.fillStyle = isLight ? '#1E293B' : '#0B1329';
      ctx.fillRect(0, pY, cvs.width, pH);
      ctx.strokeStyle = isLight ? '#475569' : '#1E3A8A';
      ctx.lineWidth = 1.2;
      ctx.strokeRect(0, pY, cvs.width, pH);

      // Internal Lattice Struts
      ctx.strokeStyle = isLight ? '#94A3B8' : '#334155';
      ctx.lineWidth = 0.8;
      ctx.beginPath();
      for (let tx = 0; tx < cvs.width; tx += 24) {
        ctx.moveTo(tx, pY); ctx.lineTo(tx + 12, pY + pH);
        ctx.moveTo(tx + 12, pY + pH); ctx.lineTo(tx + 24, pY);
      }
      ctx.stroke();

      // Signage Backplate
      ctx.fillStyle = '#020617';
      ctx.fillRect(50, pY + 4, 320, pH - 8);
      ctx.strokeStyle = '#0284C7'; ctx.lineWidth = 1;
      ctx.strokeRect(50, pY + 4, 320, pH - 8);
      ctx.fillStyle = '#F59E0B';
      ctx.font = 'bold 8px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      const portalText = (I18N[lang] && I18N[lang].portal_sign) || "PARKING ALGER-CENTRE | ENTRÉE";
      ctx.fillText(portalText, 210, pY + 16);
      ctx.textAlign = 'left';

      // Security Guard Cabin on Left Curb (Matching CAM 1)
      const gBoothX = 12, gBoothY = 28, gBoothW = 95, gBoothH = 150;
      ctx.fillStyle = isLight ? '#E2E8F0' : '#1E293B';
      ctx.fillRect(gBoothX, gBoothY, gBoothW, gBoothH);
      ctx.strokeStyle = isLight ? '#94A3B8' : '#475569';
      ctx.lineWidth = 1.2;
      ctx.strokeRect(gBoothX, gBoothY, gBoothW, gBoothH);

      // Booth Overhang Fascia
      ctx.fillStyle = isLight ? '#334155' : '#0F172A';
      ctx.fillRect(gBoothX - 3, gBoothY - 3, gBoothW + 6, 8);

      // Booth Observation Window (Matching CAM 1)
      const gWinX = gBoothX + 8, gWinY = gBoothY + 14, gWinW = gBoothW - 16, gWinH = 65;
      if (isLight) {
        const gWinGrad = ctx.createLinearGradient(gWinX, gWinY, gWinX + gWinW, gWinY + gWinH);
        gWinGrad.addColorStop(0, '#93C5FD');
        gWinGrad.addColorStop(0.5, '#BAE6FD');
        gWinGrad.addColorStop(1, '#60A5FA');
        ctx.fillStyle = gWinGrad;
        ctx.fillRect(gWinX, gWinY, gWinW, gWinH);
        ctx.strokeStyle = '#3B82F6';
        ctx.strokeRect(gWinX, gWinY, gWinW, gWinH);
      } else {
        const gWinGrad = ctx.createLinearGradient(gWinX, gWinY, gWinX + gWinW, gWinY + gWinH);
        gWinGrad.addColorStop(0, 'rgba(251, 191, 36, 0.6)');
        gWinGrad.addColorStop(1, 'rgba(217, 119, 6, 0.25)');
        ctx.fillStyle = gWinGrad;
        ctx.fillRect(gWinX, gWinY, gWinW, gWinH);
        ctx.strokeStyle = '#D97706';
        ctx.strokeRect(gWinX, gWinY, gWinW, gWinH);
      }

      // Security Guard Silhouette in Booth Window
      ctx.fillStyle = isLight ? 'rgba(30, 41, 59, 0.88)' : 'rgba(15, 23, 42, 0.94)';
      ctx.beginPath();
      ctx.arc(gWinX + gWinW * 0.45, gWinY + 22, 11, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.ellipse(gWinX + gWinW * 0.45, gWinY + 52, 18, 14, 0, 0, Math.PI);
      ctx.fill();

      // Concrete Curb with Yellow/Black Safety Stripes (Matching CAM 1)
      const curbBaseY = 175;
      for (let c = 0; c < 7; c++) {
        const cx1 = gBoothX + c * 20;
        ctx.fillStyle = (c % 2 === 0) ? '#F59E0B' : (isLight ? '#334155' : '#0F172A');
        ctx.fillRect(cx1, curbBaseY, 20, 10);
        ctx.strokeStyle = isLight ? '#64748B' : '#1E293B';
        ctx.lineWidth = 0.8;
        ctx.strokeRect(cx1, curbBaseY, 20, 10);
      }

      // Orange Barrier Pedestal (Matching CAM 1)
      const pedX = 112, pedY = 135, pedW = 20, pedH = 50;
      ctx.fillStyle = '#EA580C';
      ctx.fillRect(pedX, pedY, pedW, pedH);
      ctx.strokeStyle = '#9A3412'; ctx.lineWidth = 1;
      ctx.strokeRect(pedX, pedY, pedW, pedH);
      ctx.fillStyle = '#10B981';
      ctx.beginPath(); ctx.arc(pedX + 10, pedY + 12, 3, 0, Math.PI * 2); ctx.fill();

      // ========================================================
      // 2. VEHICLE DOOR & CABIN (LOOKING THROUGH OPEN DRIVER WINDOW)
      // ========================================================
      const carBodyGrad = ctx.createLinearGradient(0, 170, 0, cvs.height);
      if (isLight) {
        carBodyGrad.addColorStop(0, '#334155');
        carBodyGrad.addColorStop(0.5, '#475569');
        carBodyGrad.addColorStop(1, '#1E293B');
      } else {
        carBodyGrad.addColorStop(0, '#1E293B');
        carBodyGrad.addColorStop(0.5, '#0F172A');
        carBodyGrad.addColorStop(1, '#020617');
      }
      ctx.fillStyle = carBodyGrad;

      // Vehicle Exterior Door Shell
      ctx.beginPath();
      ctx.moveTo(0, 185);
      ctx.lineTo(395, 185);
      ctx.lineTo(410, cvs.height);
      ctx.lineTo(0, cvs.height);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = isLight ? '#64748B' : '#334155';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Rubber Window Weatherstrip / Chrome Beltline Trim
      ctx.fillStyle = isLight ? '#CBD5E1' : '#475569';
      ctx.fillRect(0, 182, 396, 3.5);

      // Driver A-Pillar (Structural Beam on Left)
      ctx.fillStyle = isLight ? '#1E293B' : '#0F172A';
      ctx.beginPath();
      ctx.moveTo(0, 0); ctx.lineTo(55, 0); ctx.lineTo(85, 185); ctx.lineTo(0, 185);
      ctx.closePath(); ctx.fill();
      ctx.strokeStyle = isLight ? '#475569' : '#1E293B'; ctx.lineWidth = 1.5; ctx.stroke();

      // Vehicle Roof Edge (Top)
      ctx.fillStyle = isLight ? '#1E293B' : '#0F172A';
      ctx.fillRect(0, 26, 390, 16);

      // Driver Side Mirror Housing
      ctx.fillStyle = isLight ? '#334155' : '#1E293B';
      ctx.beginPath();
      ctx.ellipse(75, 178, 16, 9, -0.2, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = isLight ? '#64748B' : '#0F172A'; ctx.lineWidth = 1; ctx.stroke();

      // Interior Driver Seat Headrest
      ctx.fillStyle = isLight ? '#334155' : '#0B132B';
      ctx.beginPath();
      ctx.roundRect(190, 48, 80, 75, 18);
      ctx.fill();
      ctx.strokeStyle = isLight ? '#475569' : '#1E293B'; ctx.lineWidth = 2; ctx.stroke();

      // Steering Wheel Rim (Lower Left)
      ctx.strokeStyle = isLight ? '#334155' : '#1E293B';
      ctx.lineWidth = 8;
      ctx.beginPath();
      ctx.arc(118, 225, 46, Math.PI * 1.05, Math.PI * 1.95);
      ctx.stroke();

      // ========================================================
      // 3. BIOMETRIC KIOSK SCANNER FRAME (FOREGROUND RIGHT)
      // ========================================================
      const kX = 415, kW = 65;
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

      // ========================================================
      // 4. DRIVER BIOMETRIC PROCESSING & FACIAL RECOGNITION
      // ========================================================
      const breath = Math.sin(frameCount * 0.05) * 0.8;
      const faceCenterX = 230;
      const faceCenterY = 112 + breath;

      if (!spoofMode) {
        // LIVING DRIVER PORTRAIT
        // Torso & Navy Polo Collar
        ctx.fillStyle = isLight ? '#1E293B' : '#0A1326';
        ctx.beginPath();
        ctx.ellipse(faceCenterX, faceCenterY + 115, 105, 50, 0, 0, Math.PI);
        ctx.fill();

        // 3-Point Diagonal Seatbelt Strap
        ctx.strokeStyle = '#020617';
        ctx.lineWidth = 14;
        ctx.beginPath();
        ctx.moveTo(faceCenterX - 65, faceCenterY + 60);
        ctx.lineTo(faceCenterX + 60, faceCenterY + 140);
        ctx.stroke();

        // Collar
        ctx.fillStyle = isLight ? '#334155' : '#1E293B';
        ctx.beginPath();
        ctx.moveTo(faceCenterX - 28, faceCenterY + 68);
        ctx.lineTo(faceCenterX, faceCenterY + 98);
        ctx.lineTo(faceCenterX + 28, faceCenterY + 68);
        ctx.lineTo(faceCenterX + 16, faceCenterY + 64);
        ctx.lineTo(faceCenterX, faceCenterY + 82);
        ctx.lineTo(faceCenterX - 16, faceCenterY + 64);
        ctx.closePath(); ctx.fill();

        // Neck
        const neckGrad = ctx.createLinearGradient(faceCenterX - 20, faceCenterY + 45, faceCenterX + 20, faceCenterY + 75);
        neckGrad.addColorStop(0, '#9A6B48');
        neckGrad.addColorStop(0.5, '#B5835C');
        neckGrad.addColorStop(1, '#8A5D3B');
        ctx.fillStyle = neckGrad;
        ctx.beginPath();
        ctx.moveTo(faceCenterX - 24, faceCenterY + 40);
        ctx.lineTo(faceCenterX + 24, faceCenterY + 40);
        ctx.lineTo(faceCenterX + 28, faceCenterY + 74);
        ctx.lineTo(faceCenterX - 28, faceCenterY + 74);
        ctx.closePath(); ctx.fill();

        // Head & Face Oval (Warm Natural Skin Tone)
        const skinGrad = ctx.createRadialGradient(faceCenterX - 8, faceCenterY - 10, 8, faceCenterX, faceCenterY + 5, 58);
        skinGrad.addColorStop(0, '#D4A373');
        skinGrad.addColorStop(0.65, '#C68B59');
        skinGrad.addColorStop(0.92, '#A66E43');
        skinGrad.addColorStop(1, '#7A4D2B');
        ctx.fillStyle = skinGrad;
        ctx.beginPath();
        ctx.ellipse(faceCenterX, faceCenterY, 47, 62, 0, 0, Math.PI * 2);
        ctx.fill();

        // Ears
        ctx.fillStyle = '#C68B59';
        ctx.beginPath();
        ctx.ellipse(faceCenterX - 48, faceCenterY, 6, 12, 0, 0, Math.PI * 2);
        ctx.ellipse(faceCenterX + 48, faceCenterY, 6, 12, 0, 0, Math.PI * 2);
        ctx.fill();

        // Natural Hair (Properly Shaped Above Forehead - No Chord Bug!)
        ctx.fillStyle = '#1C1917';
        ctx.beginPath();
        ctx.arc(faceCenterX, faceCenterY - 16, 48, Math.PI, Math.PI * 2);
        ctx.lineTo(faceCenterX + 48, faceCenterY - 2);
        ctx.lineTo(faceCenterX + 43, faceCenterY - 14);
        ctx.quadraticCurveTo(faceCenterX + 25, faceCenterY - 32, faceCenterX, faceCenterY - 30);
        ctx.quadraticCurveTo(faceCenterX - 25, faceCenterY - 32, faceCenterX - 43, faceCenterY - 14);
        ctx.lineTo(faceCenterX - 48, faceCenterY - 2);
        ctx.closePath();
        ctx.fill();

        // Natural Eyebrows
        ctx.strokeStyle = '#292524';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(faceCenterX - 28, faceCenterY - 24); ctx.lineTo(faceCenterX - 8, faceCenterY - 26);
        ctx.moveTo(faceCenterX + 8, faceCenterY - 26); ctx.lineTo(faceCenterX + 28, faceCenterY - 24);
        ctx.stroke();

        // Natural Eyes (White Sclera, Dark Iris, Pupil, Corneal Glint)
        const isBlinking = (frameCount % 110 >= 105);
        if (isBlinking) {
          ctx.strokeStyle = '#3E2723';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(faceCenterX - 26, faceCenterY - 14); ctx.quadraticCurveTo(faceCenterX - 18, faceCenterY - 12, faceCenterX - 10, faceCenterY - 14);
          ctx.moveTo(faceCenterX + 10, faceCenterY - 14); ctx.quadraticCurveTo(faceCenterX + 18, faceCenterY - 12, faceCenterX + 26, faceCenterY - 14);
          ctx.stroke();
        } else {
          [-18, 18].forEach(eyeOffsetX => {
            const eyeX = faceCenterX + eyeOffsetX;
            const eyeY = faceCenterY - 14;
            // Sclera
            ctx.fillStyle = '#F8FAFC';
            ctx.beginPath();
            ctx.ellipse(eyeX, eyeY, 8.5, 5, 0, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = '#4A2E18'; ctx.lineWidth = 0.8; ctx.stroke();

            // Iris
            ctx.fillStyle = '#2D1E12';
            ctx.beginPath();
            ctx.arc(eyeX, eyeY, 4.2, 0, Math.PI * 2);
            ctx.fill();

            // Pupil
            ctx.fillStyle = '#000000';
            ctx.beginPath();
            ctx.arc(eyeX, eyeY, 2.2, 0, Math.PI * 2);
            ctx.fill();

            // Specular Corneal Glint
            ctx.fillStyle = '#FFFFFF';
            ctx.beginPath();
            ctx.arc(eyeX - 1.2, eyeY - 1.2, 1.2, 0, Math.PI * 2);
            ctx.fill();
          });
        }

        // Nose Bridge & Contoured Nostrils
        ctx.strokeStyle = '#9A6B48';
        ctx.lineWidth = 1.6;
        ctx.beginPath();
        ctx.moveTo(faceCenterX, faceCenterY - 18);
        ctx.lineTo(faceCenterX - 1.5, faceCenterY + 6);
        ctx.lineTo(faceCenterX + 4.5, faceCenterY + 11);
        ctx.stroke();

        ctx.fillStyle = 'rgba(100, 50, 20, 0.4)';
        ctx.beginPath();
        ctx.ellipse(faceCenterX - 4, faceCenterY + 11, 2.5, 1.5, 0, 0, Math.PI * 2);
        ctx.ellipse(faceCenterX + 4, faceCenterY + 11, 2.5, 1.5, 0, 0, Math.PI * 2);
        ctx.fill();

        // Natural Lips
        ctx.fillStyle = '#A05240';
        ctx.beginPath();
        ctx.ellipse(faceCenterX, faceCenterY + 28, 13, 4.5, 0, 0, Math.PI * 2);
        ctx.fill();

        // Biometric FaceMesh 68-Point Landmark Constellation
        ctx.fillStyle = 'rgba(6, 182, 212, 0.85)';
        baseLandmarks.forEach(([lx, ly]) => {
          ctx.beginPath();
          ctx.arc(faceCenterX + lx, faceCenterY + ly, 1.4, 0, Math.PI * 2);
          ctx.fill();
        });

        // 3D Bounding Box with Corner Reticles
        const bbX = faceCenterX - 55, bbY = faceCenterY - 72, bbW = 110, bbH = 144;
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
        const driverTitle = lang === 'ar' ? 'أمين حاج (VIP) | 99.4%' : (lang === 'en' ? 'AMINE HADJ (VIP) | 99.4%' : 'AMINE HADJ (VIP) | 99.4%');
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

      // ========================================================
      // 5. PIP VIEWPORT (TOP RIGHT): 850nm NIR CHANNEL
      // ========================================================
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
  // CAM 3 : VOIE 2 SORTIE (ALPR PERSPECTIVE & AUTOMATED TOLL BARRIER)
  // =========================================================================
  function setupCam3() {
    const cvs = document.getElementById('cam3-canvas');
    if (!cvs) return;
    const ctx = cvs.getContext('2d');
    cvs.width = 480; cvs.height = 270;

    let armAngle = 0;
    let targetAngle = 0;
    let carX = 140; // Ambient waiting position at exit barrier
    let carRolling = false;
    let frameCount = 0;
    let plateText = "08192 120 09";

    function render() {
      frameCount++;
      const isLight = document.documentElement.classList.contains('light');
      const lang = window.currentLang || 'fr';
      const I18N = window.I18N || {};

      // Barrier Arm Physics Easing
      armAngle += (targetAngle - armAngle) * 0.08;

      // Car Roll Out Physics
      if (carRolling) {
        carX += 3.2;
        if (carX > cvs.width + 120) {
          carRolling = false;
          targetAngle = 0;
          setTimeout(() => {
            carX = 140;
            const armEl = document.getElementById('cam3-arm-text');
            if (armEl) {
              armEl.innerText = lang === 'ar' ? 'مغلق' : (lang === 'en' ? 'CLOSED' : 'BAISSÉE');
              armEl.className = 'text-red-400 font-semibold';
            }
          }, 2000);
        }
      }

      // 1. Sky & Horizon Gradient
      if (isLight) {
        const skyGrad = ctx.createLinearGradient(0, 0, 0, 95);
        skyGrad.addColorStop(0, '#93C5FD');
        skyGrad.addColorStop(0.6, '#BAE6FD');
        skyGrad.addColorStop(1, '#E0F2FE');
        ctx.fillStyle = skyGrad;
        ctx.fillRect(0, 0, cvs.width, cvs.height);
      } else {
        const skyGrad = ctx.createLinearGradient(0, 0, 0, 95);
        skyGrad.addColorStop(0, '#020617');
        skyGrad.addColorStop(0.6, '#0B132B');
        skyGrad.addColorStop(1, '#111C3A');
        ctx.fillStyle = skyGrad;
        ctx.fillRect(0, 0, cvs.width, cvs.height);
      }

      // 2. Perspective Roadway & Asphalt Pavement (Exit Voie 2)
      const roadGrad = ctx.createLinearGradient(0, 85, 0, 246);
      if (isLight) {
        roadGrad.addColorStop(0, '#64748B');
        roadGrad.addColorStop(0.4, '#475569');
        roadGrad.addColorStop(1, '#334155');
      } else {
        roadGrad.addColorStop(0, '#0F172A');
        roadGrad.addColorStop(0.4, '#1E293B');
        roadGrad.addColorStop(1, '#0B111E');
      }
      ctx.fillStyle = roadGrad;
      ctx.beginPath();
      ctx.moveTo(0, 95); ctx.lineTo(cvs.width, 95);
      ctx.lineTo(cvs.width, 248); ctx.lineTo(0, 248);
      ctx.closePath(); ctx.fill();

      // Asphalt Micro-Texture
      ctx.fillStyle = isLight ? 'rgba(0, 0, 0, 0.03)' : 'rgba(255, 255, 255, 0.025)';
      for (let i = 0; i < 40; i++) {
        const sx = (i * 37) % cvs.width;
        const sy = 98 + (i * 19) % 145;
        ctx.fillRect(sx, sy, 2.5, 1.5);
      }

      // White Roadway Centerline Dashes
      ctx.strokeStyle = isLight ? '#FFFFFF' : 'rgba(226, 232, 240, 0.8)';
      ctx.lineWidth = 3;
      ctx.setLineDash([18, 16]);
      ctx.beginPath();
      ctx.moveTo(0, 172); ctx.lineTo(cvs.width, 172);
      ctx.stroke();
      ctx.setLineDash([]);

      // White Stop Line in front of barrier
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(252, 96); ctx.lineTo(252, 246);
      ctx.stroke();

      // Safety Curb with Yellow & Black Beveled Segments
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
      const isLoopAOccupied = carX >= 80 && carX <= 260;
      ctx.strokeStyle = isLoopAOccupied ? '#06B6D4' : (isLight ? '#64748B' : '#475569');
      ctx.lineWidth = 2;
      ctx.strokeRect(135, 118, 88, 96);
      ctx.fillStyle = isLoopAOccupied ? 'rgba(6, 182, 212, 0.22)' : (isLight ? 'rgba(255, 255, 255, 0.15)' : 'rgba(30, 41, 59, 0.25)');
      ctx.fillRect(135, 118, 88, 96);

      // Loop Chamfered Corner Cuts
      ctx.strokeStyle = isLoopAOccupied ? '#06B6D4' : (isLight ? '#94A3B8' : '#334155');
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(135, 128); ctx.lineTo(145, 118);
      ctx.moveTo(213, 118); ctx.lineTo(223, 128);
      ctx.moveTo(135, 204); ctx.lineTo(145, 214);
      ctx.moveTo(213, 214); ctx.lineTo(223, 204);
      ctx.stroke();

      ctx.fillStyle = isLoopAOccupied ? '#06B6D4' : (isLight ? '#1E293B' : '#64748B');
      ctx.font = 'bold 8px "JetBrains Mono", monospace';
      const loopALabel = lang === 'ar' ? (isLoopAOccupied ? 'المستشعر أ: رصد المركبة' : 'المستشعر أ (انتظار)') : (lang === 'en' ? (isLoopAOccupied ? 'LOOP A: ACTIVE' : 'LOOP A (STANDBY)') : (isLoopAOccupied ? 'BOUCLE A : ACTIF (-3.4%)' : 'BOUCLE A (ATTENTE)'));
      ctx.fillText(loopALabel, 140, 130);

      const isLoopBOccupied = carX >= 270 && carX <= 430;
      ctx.strokeStyle = isLoopBOccupied ? '#10B981' : (isLight ? '#64748B' : '#475569');
      ctx.lineWidth = 2;
      ctx.strokeRect(285, 118, 88, 96);
      ctx.fillStyle = isLoopBOccupied ? 'rgba(16, 185, 129, 0.22)' : (isLight ? 'rgba(255, 255, 255, 0.15)' : 'rgba(30, 41, 59, 0.25)');
      ctx.fillRect(285, 118, 88, 96);
      ctx.fillStyle = isLoopBOccupied ? '#10B981' : (isLight ? '#1E293B' : '#64748B');
      ctx.font = 'bold 8px "JetBrains Mono", monospace';
      const loopBLabel = lang === 'ar' ? (isLoopBOccupied ? 'المستشعر ب: إخلاء المسلك' : 'المستشعر ب (مغادرة)') : (lang === 'en' ? (isLoopBOccupied ? 'LOOP B: CLEARED' : 'LOOP B (DEPARTURE)') : (isLoopBOccupied ? 'BOUCLE B : PASSAGE OK' : 'BOUCLE B (DEGAGEMENT)'));
      ctx.fillText(loopBLabel, 290, 130);

      // 4. Optical Safety Photocell Beam
      const isBeamBroken = carX >= 185 && carX <= 315;
      ctx.fillStyle = '#F59E0B';
      ctx.fillRect(250, 88, 7, 14);
      ctx.fillRect(250, 243, 7, 14);
      ctx.fillStyle = '#020617';
      ctx.fillRect(251, 93, 5, 5);
      ctx.fillRect(251, 246, 5, 5);

      // Infrared Safety Beam
      ctx.strokeStyle = isBeamBroken ? '#EF4444' : 'rgba(6, 182, 212, 0.55)';
      ctx.lineWidth = isBeamBroken ? 2 : 1;
      ctx.setLineDash(isBeamBroken ? [4, 4] : [2, 6]);
      ctx.beginPath();
      ctx.moveTo(253, 98); ctx.lineTo(253, 246);
      ctx.stroke();
      ctx.setLineDash([]);
      if (isBeamBroken) {
        ctx.fillStyle = '#EF4444';
        ctx.font = 'bold 7.5px "JetBrains Mono", monospace';
        const beamAlert = lang === 'ar' ? 'انقطاع الحزمة: نظام منع الاصطدام' : (lang === 'en' ? 'BEAM INTERRUPTED: ANTI-CRUSH' : 'FAISCEAU COUPE : ANTI-ECRASEMENT');
        ctx.fillText(beamAlert, 160, 240);
      }

      // 5. Heavy Structural Toll Gantry & VMS Display
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
      ctx.fillRect(95, 19, 290, 28);
      ctx.strokeStyle = '#64748B'; ctx.lineWidth = 1.2;
      ctx.strokeRect(95, 19, 290, 28);

      const isOpen = armAngle < -40;
      ctx.textAlign = 'center';
      if (isOpen) {
        ctx.fillStyle = '#10B981';
        ctx.font = 'bold 8.5px "JetBrains Mono", monospace';
        const vmsHeader = (I18N[lang] && I18N[lang].gantry_sign_open) || "● VOIE 02 : SORTIE ACCORDEE | BONNE ROUTE";
        ctx.fillText(vmsHeader, 240, 31);
        ctx.fillStyle = '#34D399';
        ctx.font = '7.5px "JetBrains Mono", monospace';
        const vmsSub = lang === 'ar' ? 'الدفع الإلكتروني CIB/SATIM مؤكد | رافقتكم السلامة' : (lang === 'en' ? 'SATIM 100 DZD PAYMENT CONFIRMED | SAFE TRAVELS' : 'PAIEMENT SATIM 100 DZD CONFIRME | BONNE ROUTE');
        ctx.fillText(vmsSub, 240, 42);
      } else {
        ctx.fillStyle = '#F59E0B';
        ctx.font = 'bold 8.5px "JetBrains Mono", monospace';
        const vmsHeader = (I18N[lang] && I18N[lang].gantry_sign_closed) || "■ VOIE 02 : PEAGE AUTOMATIQUE | 100 DZD";
        ctx.fillText(vmsHeader, 240, 31);
        ctx.fillStyle = '#FCD34D';
        ctx.font = '7.5px "JetBrains Mono", monospace';
        const vmsSub = lang === 'ar' ? 'يرجى التوقف أمام الحاجز الآلي' : (lang === 'en' ? 'STOP IN FRONT OF AUTOMATIC BARRIER' : "MARQUEZ L'ARRET DEVANT LA BARRIERE");
        ctx.fillText(vmsSub, 240, 42);
      }
      ctx.textAlign = 'left';

      // Overhead Lane Signals
      // Red Cross
      ctx.fillStyle = !isOpen ? '#EF4444' : '#450A0A';
      ctx.beginPath(); ctx.arc(68, 30, 7, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = !isOpen ? '#FCA5A5' : '#7F1D1D'; ctx.lineWidth = 1.2; ctx.stroke();
      ctx.fillStyle = '#FFFFFF';
      ctx.font = 'bold 8px "JetBrains Mono", monospace';
      ctx.fillText('✕', 65, 33);

      // Green Down Arrow
      ctx.fillStyle = isOpen ? '#10B981' : '#064E3B';
      ctx.beginPath(); ctx.arc(412, 30, 7, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = isOpen ? '#6EE7B7' : '#065F46'; ctx.lineWidth = 1.2; ctx.stroke();
      ctx.fillStyle = '#FFFFFF';
      ctx.fillText('↓', 409, 33);

      // Gantry ALPR Camera
      ctx.fillStyle = '#0284C7';
      ctx.fillRect(40, 40, 22, 14);
      ctx.fillStyle = '#E2E8F0';
      ctx.beginPath(); ctx.arc(40, 47, 4.5, 0, Math.PI * 2); ctx.fill();
      const irAlpha = (Math.sin(frameCount * 0.2) + 1) / 2;
      ctx.strokeStyle = `rgba(6, 182, 212, ${0.3 + irAlpha * 0.7})`;
      ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(40, 47, 9, 0, Math.PI * 2); ctx.stroke();

      // 6. Photorealistic Moving Sedan (Exiting)
      const vy = 138;
      // Chassis Drop Shadow
      ctx.fillStyle = isLight ? 'rgba(15, 23, 42, 0.45)' : 'rgba(0, 0, 0, 0.75)';
      ctx.beginPath();
      ctx.ellipse(carX + 58, vy + 46, 68, 11, 0, 0, Math.PI * 2);
      ctx.fill();

      // Sedan Lower Body
      const carGrad = ctx.createLinearGradient(carX, vy, carX, vy + 44);
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
      ctx.roundRect(carX, vy + 12, 118, 32, 6);
      ctx.fill();
      ctx.strokeStyle = isLight ? '#94A3B8' : '#64748B'; ctx.lineWidth = 1; ctx.stroke();

      // Cabin Glasshouse
      const glassGrad = ctx.createLinearGradient(carX + 20, vy, carX + 90, vy + 14);
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
      ctx.moveTo(carX + 22, vy + 12);
      ctx.lineTo(carX + 44, vy - 2);
      ctx.lineTo(carX + 88, vy - 2);
      ctx.lineTo(carX + 104, vy + 12);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = '#1E293B'; ctx.lineWidth = 1.5; ctx.stroke();

      // B-Pillar Divider
      ctx.fillStyle = '#0F172A';
      ctx.fillRect(carX + 64, vy - 1, 4, 13);

      // Driver Silhouette Inside Cabin
      ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
      ctx.beginPath(); ctx.arc(carX + 54, vy + 4, 6.5, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.ellipse(carX + 54, vy + 12, 9, 5, 0, 0, Math.PI); ctx.fill();

      // Door Handles
      ctx.fillStyle = '#CBD5E1';
      ctx.fillRect(carX + 48, vy + 16, 7, 2);
      ctx.fillRect(carX + 72, vy + 16, 7, 2);

      // Rotating Alloy Wheels
      [carX + 28, carX + 92].forEach(wx => {
        const wy = vy + 42;
        ctx.fillStyle = '#020617';
        ctx.beginPath(); ctx.arc(wx, wy, 12.5, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = '#1E293B'; ctx.lineWidth = 1.5; ctx.stroke();

        // 5-Spoke Wheel Rim
        ctx.strokeStyle = '#CBD5E1'; ctx.lineWidth = 1.2;
        ctx.beginPath();
        for (let s = 0; s < 5; s++) {
          const a = (frameCount * 0.15) + (s * Math.PI * 2) / 5;
          ctx.moveTo(wx, wy); ctx.lineTo(wx + Math.cos(a) * 9, wy + Math.sin(a) * 9);
        }
        ctx.stroke();
      });

      // Rear Taillights (Glowing Red)
      ctx.fillStyle = '#EF4444';
      ctx.beginPath(); ctx.roundRect(carX + 114, vy + 16, 4, 10, 2); ctx.fill();
      if (!isLight) {
        const redBloom = ctx.createRadialGradient(carX + 118, vy + 21, 2, carX + 128, vy + 21, 26);
        redBloom.addColorStop(0, 'rgba(239, 68, 68, 0.45)');
        redBloom.addColorStop(1, 'rgba(239, 68, 68, 0)');
        ctx.fillStyle = redBloom;
        ctx.beginPath(); ctx.arc(carX + 118, vy + 21, 26, 0, Math.PI * 2); ctx.fill();
      }

      // License Plate on Bumper
      ctx.fillStyle = '#000000';
      ctx.fillRect(carX + 112, vy + 28, 6, 8);
      ctx.fillStyle = '#FDE047'; // Rear yellow plate
      ctx.fillRect(carX + 113, vy + 29, 4, 6);

      // YOLOv11 & OCR Bounding Box
      ctx.strokeStyle = '#06B6D4';
      ctx.lineWidth = 1.8;
      ctx.strokeRect(carX - 4, vy - 6, 126, 56);
      ctx.fillStyle = 'rgba(6, 182, 212, 0.9)';
      ctx.fillRect(carX - 4, vy - 18, 120, 12);
      ctx.fillStyle = '#000000';
      ctx.font = 'bold 7px "JetBrains Mono", monospace';
      const exitTag = lang === 'ar' ? 'خروج' : (lang === 'en' ? 'EXIT' : 'SORTIE');
      ctx.fillText(`${exitTag} : ${plateText}`, carX - 1, vy - 9);

      // 7. Automatic Barrier Gate Cabinet & Boom Arm
      const barrierX = 248, barrierY = 155;
      ctx.fillStyle = '#EA580C'; // RAL 2004 Safety Orange
      ctx.beginPath();
      ctx.roundRect(barrierX - 15, barrierY, 30, 85, 4);
      ctx.fill();
      ctx.strokeStyle = '#9A3412'; ctx.lineWidth = 1.5;
      ctx.strokeRect(barrierX - 15, barrierY, 30, 85);

      // Flashing Strobe Beacon on Barrier
      const isMoving = Math.abs(armAngle) > 5 && Math.abs(armAngle) < 75;
      const beaconColor = isMoving ? (Math.floor(frameCount / 4) % 2 === 0 ? '#F59E0B' : '#EF4444') : (isOpen ? '#10B981' : '#EF4444');
      ctx.fillStyle = beaconColor;
      ctx.beginPath(); ctx.arc(barrierX, barrierY - 4, 5, Math.PI, 0); ctx.fill();

      // Articulated Boom Arm
      ctx.save();
      ctx.translate(barrierX, barrierY + 20);
      ctx.rotate((armAngle * Math.PI) / 180);

      ctx.fillStyle = '#F8FAFC';
      ctx.fillRect(-210, -5, 210, 10);
      // Red Reflective Chevrons
      ctx.fillStyle = '#EF4444';
      for (let s = -200; s < -10; s += 24) {
        ctx.beginPath();
        ctx.moveTo(s, -5); ctx.lineTo(s + 12, -5);
        ctx.lineTo(s + 4, 5); ctx.lineTo(s - 8, 5);
        ctx.closePath(); ctx.fill();
      }
      // Running LED Strip
      ctx.strokeStyle = isOpen ? '#10B981' : '#EF4444';
      ctx.lineWidth = 2.5;
      ctx.beginPath(); ctx.moveTo(-208, -5); ctx.lineTo(-2, -5); ctx.stroke();
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
        targetAngle = -85;
        carRolling = true;
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
      triggerCam3: () => { if (cam3) cam3.openBarrier(); }
    };
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', window.initCCTVEngine);
  } else {
    window.initCCTVEngine();
  }

})(window);
