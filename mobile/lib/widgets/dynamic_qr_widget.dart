import 'dart:math';
import 'package:flutter/material.dart';

class DynamicQrWidget extends StatelessWidget {
  final String payload;
  final int secondsRemaining;
  final double size;
  final Color primaryColor;

  const DynamicQrWidget({
    super.key,
    required this.payload,
    required this.secondsRemaining,
    this.size = 220,
    this.primaryColor = const Color(0xFF00F2FE),
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Semantics(
          image: true,
          label: 'Pass d\'accès QR dynamique sécurisé.',
          child: Stack(
            alignment: Alignment.center,
            children: [
              // Outer circular countdown indicator
              SizedBox(
                width: size + 40,
                height: size + 40,
                child: CircularProgressIndicator(
                  value: secondsRemaining / 30.0,
                  strokeWidth: 4,
                  backgroundColor: primaryColor.withValues(alpha: 0.15),
                  valueColor: AlwaysStoppedAnimation<Color>(
                    secondsRemaining > 5 ? primaryColor : Colors.red,
                  ),
                ),
              ),
              // Custom QR Matrix Card
              Container(
                width: size,
                height: size,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.1),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: CustomPaint(
                  size: Size(size - 24, size - 24),
                  painter: _MatrixQrPainter(
                    seedString: payload,
                    moduleColor: const Color(0xFF0F172A),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            ExcludeSemantics(
              child: Icon(Icons.refresh, size: 16, color: primaryColor),
            ),
            const SizedBox(width: 6),
            Text(
              'Renouvellement dans ${secondsRemaining}s',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: primaryColor,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _MatrixQrPainter extends CustomPainter {
  final String seedString;
  final Color moduleColor;

  _MatrixQrPainter({
    required this.seedString,
    required this.moduleColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = moduleColor
      ..style = PaintingStyle.fill;

    const int gridSize = 17; // 17x17 matrix
    final double cellSize = size.width / gridSize;

    // Draw standard 3 Corner Position Markers (7x7 blocks)
    _drawFinderPattern(canvas, 0, 0, cellSize, paint);
    _drawFinderPattern(canvas, (gridSize - 7) * cellSize, 0, cellSize, paint);
    _drawFinderPattern(canvas, 0, (gridSize - 7) * cellSize, cellSize, paint);

    // Draw Deterministic Data Cells derived from seedString
    final seed = seedString.hashCode.abs();
    final rng = Random(seed);

    for (int r = 0; r < gridSize; r++) {
      for (int c = 0; c < gridSize; c++) {
        // Skip corner markers
        if ((r < 7 && c < 7) ||
            (r < 7 && c >= gridSize - 7) ||
            (r >= gridSize - 7 && c < 7)) {
          continue;
        }

        // Timing lines
        if (r == 6 || c == 6) {
          if ((r + c) % 2 == 0) {
            canvas.drawRRect(
              RRect.fromRectAndRadius(
                Rect.fromLTWH(c * cellSize + 0.5, r * cellSize + 0.5, cellSize - 1, cellSize - 1),
                const Radius.circular(1.5),
              ),
              paint,
            );
          }
          continue;
        }

        // Data bits
        if (rng.nextBool()) {
          canvas.drawRRect(
            RRect.fromRectAndRadius(
              Rect.fromLTWH(c * cellSize + 0.5, r * cellSize + 0.5, cellSize - 1, cellSize - 1),
              const Radius.circular(1.5),
            ),
            paint,
          );
        }
      }
    }
  }

  void _drawFinderPattern(Canvas canvas, double x, double y, double cellSize, Paint paint) {
    // 7x7 outer square
    canvas.drawRect(Rect.fromLTWH(x, y, 7 * cellSize, 7 * cellSize), paint);
    // 5x5 inner white
    final whitePaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.fill;
    canvas.drawRect(Rect.fromLTWH(x + cellSize, y + cellSize, 5 * cellSize, 5 * cellSize), whitePaint);
    // 3x3 center solid
    canvas.drawRect(Rect.fromLTWH(x + 2 * cellSize, y + 2 * cellSize, 3 * cellSize, 3 * cellSize), paint);
  }

  @override
  bool shouldRepaint(covariant _MatrixQrPainter oldDelegate) {
    return oldDelegate.seedString != seedString;
  }
}
