class VehicleLocation {
  final String slotNumber;
  final String zoneName;
  final String floorLevel;
  final DateTime parkedAt;
  final double latitude;
  final double longitude;
  final String sectionName;

  const VehicleLocation({
    required this.slotNumber,
    required this.zoneName,
    required this.floorLevel,
    required this.parkedAt,
    required this.latitude,
    required this.longitude,
    required this.sectionName,
  });

  Duration get elapsedDuration => DateTime.now().difference(parkedAt);

  double calculateAccruedTariff({double hourlyRateDzd = 100.0, int gracePeriodMin = 15}) {
    final minutes = elapsedDuration.inMinutes;
    if (minutes <= gracePeriodMin) {
      return 0.0;
    }
    final hours = (minutes / 60.0).ceil();
    return hours * hourlyRateDzd;
  }
}
