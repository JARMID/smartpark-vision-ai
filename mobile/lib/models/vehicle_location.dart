class TariffBreakdown {
  final double totalDueDzd;
  final bool isGracePeriod;
  final int billableHours;
  final String breakdownDescription;

  const TariffBreakdown({
    required this.totalDueDzd,
    required this.isGracePeriod,
    required this.billableHours,
    required this.breakdownDescription,
  });
}

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

  TariffBreakdown calculateProgressiveTariff({
    int gracePeriodMin = 15,
    double firstHourDzd = 100.0,
    double tier2Dzd = 50.0,
    double tier3Dzd = 30.0,
    double dailyCapDzd = 800.0,
  }) {
    final minutes = elapsedDuration.inMinutes;
    if (minutes <= gracePeriodMin) {
      return const TariffBreakdown(
        totalDueDzd: 0.0,
        isGracePeriod: true,
        billableHours: 0,
        breakdownDescription: 'Franchise Gratuite (15 min)',
      );
    }

    final totalHours = (minutes / 60.0).ceil();
    final days = totalHours ~/ 24;
    final remainderHours = totalHours % 24;

    double baseDue = 0.0;
    if (remainderHours > 0) {
      double dayDue = firstHourDzd;
      final tier2Hours = (remainderHours - 1).clamp(0, 3);
      dayDue += tier2Hours * tier2Dzd;
      final tier3Hours = (remainderHours - 4).clamp(0, 24);
      dayDue += tier3Hours * tier3Dzd;
      baseDue += dayDue > dailyCapDzd ? dailyCapDzd : dayDue;
    }
    baseDue += days * dailyCapDzd;

    String desc = '$totalHours h en tarif progressif';
    if (days > 0) {
      desc = '$days jour(s) + $remainderHours h';
    }

    return TariffBreakdown(
      totalDueDzd: baseDue,
      isGracePeriod: false,
      billableHours: totalHours,
      breakdownDescription: desc,
    );
  }
}
