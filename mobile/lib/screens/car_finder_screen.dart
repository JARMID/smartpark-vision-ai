import 'package:flutter/material.dart';
import '../state/parking_controller.dart';
import 'payment_screen.dart';

class CarFinderScreen extends StatelessWidget {
  final ParkingController controller;

  const CarFinderScreen({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    final vehicle = controller.myVehicle;

    if (vehicle == null) {
      return const Scaffold(
        body: Center(child: Text('Aucun véhicule stationné actuellement.')),
      );
    }

    final duration = vehicle.elapsedDuration;
    final tariff = vehicle.calculateAccruedTariff();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Retrouver mon Véhicule'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            // Vehicle Location Info Card
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Theme.of(context).cardColor,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Theme.of(context).dividerColor),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.05),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'EMPLACEMENT ACTUEL',
                            style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.grey),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            vehicle.slotNumber,
                            style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w900, color: Color(0xFF0284C7)),
                          ),
                        ],
                      ),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0284C7).withValues(alpha: 0.15),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.directions_car, color: Color(0xFF0284C7), size: 30),
                      ),
                    ],
                  ),
                  const Divider(height: 24),
                  _infoRow('Zone & Niveau', '${vehicle.zoneName} - ${vehicle.floorLevel}'),
                  const SizedBox(height: 8),
                  _infoRow('Allée d\'Accès', vehicle.sectionName),
                  const SizedBox(height: 8),
                  _infoRow('Stationné Depuis', '${duration.inHours}h ${duration.inMinutes % 60}m'),
                  const SizedBox(height: 8),
                  _infoRow('Tarif Estimé', '${tariff.toStringAsFixed(0)} DZD', isHighlight: true),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // Visual Walking Guidance Canvas / Map Compass
            Container(
              height: 220,
              width: double.infinity,
              decoration: BoxDecoration(
                color: const Color(0xFF0F172A),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: Stack(
                alignment: Alignment.center,
                children: [
                  // Compass Ring
                  Container(
                    width: 160,
                    height: 160,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: const Color(0xFF38BDF8).withValues(alpha: 0.3), width: 1.5),
                    ),
                  ),
                  Container(
                    width: 100,
                    height: 100,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: const Color(0xFF38BDF8).withValues(alpha: 0.6), width: 1),
                    ),
                  ),
                  // Compass Arrow pointing to vehicle
                  Transform.rotate(
                    angle: -0.45,
                    child: const Icon(Icons.navigation, size: 48, color: Color(0xFF38BDF8)),
                  ),
                  const Positioned(
                    bottom: 16,
                    child: Column(
                      children: [
                        Text(
                          'A 45 mètres - Prendre Ascenseur A vers Niveau 0',
                          style: TextStyle(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.bold),
                        ),
                        Text(
                          'Guidage piéton direct dans le parking',
                          style: TextStyle(color: Colors.white38, fontSize: 10.5),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // Settle Parking Button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF10B981),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                icon: const Icon(Icons.payment),
                label: Text(
                  'Régler mon stationnement (${tariff.toStringAsFixed(0)} DZD)',
                  style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                ),
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => PaymentScreen(
                        controller: controller,
                        amountDzd: tariff > 0 ? tariff : 100.0,
                        plateNumber: controller.accessPass?.plateNumber ?? '104822 119 16',
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _infoRow(String label, String value, {bool isHighlight = false}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(fontSize: 13, color: Colors.grey)),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            value,
            textAlign: TextAlign.end,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 13,
              fontWeight: isHighlight ? FontWeight.w900 : FontWeight.bold,
              color: isHighlight ? const Color(0xFF10B981) : null,
            ),
          ),
        ),
      ],
    );
  }
}
