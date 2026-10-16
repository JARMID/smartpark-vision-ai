import 'package:flutter/material.dart';

/// Renders the official Smart Park Dynamic Lift vector logo.
/// Features the architectural 'P' monogram, electric cyan loop, and rising mint barrier arm.
class SmartParkLogo extends StatelessWidget {
  final double size;
  final bool showText;
  final Color textColor;

  const SmartParkLogo({
    super.key,
    this.size = 36.0,
    this.showText = false,
    this.textColor = const Color(0xFFF8FAFC),
  });

  @override
  Widget build(BuildContext context) {
    final iconWidget = SizedBox(
      width: size,
      height: size,
      child: CustomPaint(
        painter: _SmartParkLogoPainter(),
      ),
    );

    if (!showText) {
      return iconWidget;
    }

    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        iconWidget,
        const SizedBox(width: 8),
        Text(
          'SMART PARK',
          style: TextStyle(
            color: textColor,
            fontSize: size * 0.45,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.2,
          ),
        ),
      ],
    );
  }
}

class _SmartParkLogoPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final scale = size.width / 512.0;
    canvas.save();
    canvas.scale(scale);

    // 1. Background Rounded Tile
    final bgRect = RRect.fromRectAndRadius(
      const Rect.fromLTWH(0, 0, 512, 512),
      const Radius.circular(112),
    );
    final bgPaint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Color(0xFF0B0F19), Color(0xFF04070F)],
      ).createShader(const Rect.fromLTWH(0, 0, 512, 512));
    canvas.drawRRect(bgRect, bgPaint);

    // Subtle border stroke
    final borderPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0
      ..color = const Color(0x1AFFFFFF);
    canvas.drawRRect(bgRect, borderPaint);

    // 2. Optical Reticle Dashed Ring
    final reticlePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5
      ..color = const Color(0x0A00F2FE);
    canvas.drawCircle(const Offset(180, 270), 160, reticlePaint);

    // 3. Ground Track Marking
    final groundPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.0
      ..strokeCap = StrokeCap.round
      ..color = const Color(0x14FFFFFF);
    canvas.drawLine(const Offset(110, 410), const Offset(400, 410), groundPaint);

    // 4. Vertical Pedestal Stem of 'P'
    final stemRRect = RRect.fromRectAndRadius(
      const Rect.fromLTWH(150, 110, 50, 290),
      const Radius.circular(25),
    );
    final stemPaint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [Color(0xFF38BDF8), Color(0xFF0284C7), Color(0xFF0F172A)],
      ).createShader(const Rect.fromLTWH(150, 110, 50, 290));
    canvas.drawRRect(stemRRect, stemPaint);

    // 5. Architectural Upper P Loop (Outer Framing)
    final loopPath = Path()
      ..moveTo(180, 110)
      ..lineTo(310, 110)
      ..cubicTo(375, 110, 410, 145, 410, 200)
      ..cubicTo(410, 255, 375, 275, 310, 275)
      ..lineTo(180, 275);

    final loopPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 32.0
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..shader = const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Color(0xFF00F2FE), Color(0xFF0284C7)],
      ).createShader(const Rect.fromLTWH(180, 110, 230, 165));
    canvas.drawPath(loopPath, loopPaint);

    // 6. Kinetic Rising Barrier Arm (Pivoting 42 deg Upward)
    final armPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 26.0
      ..strokeCap = StrokeCap.round
      ..shader = const LinearGradient(
        begin: Alignment.bottomLeft,
        end: Alignment.topRight,
        colors: [Color(0xFF10B981), Color(0xFF00F5A0), Color(0xFF38BDF8)],
      ).createShader(const Rect.fromLTWH(180, 120, 210, 150));
    canvas.drawLine(const Offset(180, 270), const Offset(390, 120), armPaint);

    // 7. Mechanical Pivot Hub / Smart Optical Sensor
    final hubOuterPaint = Paint()
      ..color = const Color(0xFF0B1120)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(const Offset(180, 270), 28, hubOuterPaint);

    final hubRingPaint = Paint()
      ..color = const Color(0xFF00F2FE)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 5.0;
    canvas.drawCircle(const Offset(180, 270), 28, hubRingPaint);

    final hubInnerPaint = Paint()
      ..color = const Color(0xFF10B981)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(const Offset(180, 270), 14, hubInnerPaint);

    final hubCenterPaint = Paint()
      ..color = const Color(0xFFFFFFFF)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(const Offset(180, 270), 5, hubCenterPaint);

    // 8. Active Gate Tip Beacon
    final beaconPaint = Paint()
      ..color = const Color(0xFF00F5A0)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(const Offset(390, 120), 9, beaconPaint);

    final beaconCorePaint = Paint()
      ..color = const Color(0xFFFFFFFF)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(const Offset(390, 120), 4, beaconCorePaint);

    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
