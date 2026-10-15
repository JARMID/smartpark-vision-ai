import 'dart:math';

class AccessPass {
  final String passId;
  final String plateNumber;
  final String driverName;
  final String zoneName;
  final String slotNumber;
  final DateTime issuedAt;
  final DateTime validUntil;
  final bool isVip;
  final String currentToken;
  final int secondsRemaining;

  const AccessPass({
    required this.passId,
    required this.plateNumber,
    required this.driverName,
    required this.zoneName,
    required this.slotNumber,
    required this.issuedAt,
    required this.validUntil,
    required this.isVip,
    required this.currentToken,
    required this.secondsRemaining,
  });

  static String generateRotatingToken(String plate, int timestampSec) {
    // 30-second time-step TOTP token simulation
    final timeStep = timestampSec ~/ 30;
    final seed = (plate.hashCode ^ timeStep).abs();
    final random = Random(seed);
    final tokenNum = 100000 + random.nextInt(900000);
    return tokenNum.toString();
  }

  AccessPass copyWith({
    String? currentToken,
    int? secondsRemaining,
  }) {
    return AccessPass(
      passId: passId,
      plateNumber: plateNumber,
      driverName: driverName,
      zoneName: zoneName,
      slotNumber: slotNumber,
      issuedAt: issuedAt,
      validUntil: validUntil,
      isVip: isVip,
      currentToken: currentToken ?? this.currentToken,
      secondsRemaining: secondsRemaining ?? this.secondsRemaining,
    );
  }
}
