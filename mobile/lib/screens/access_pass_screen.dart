import 'package:flutter/material.dart';
import '../state/parking_controller.dart';
import '../widgets/dynamic_qr_widget.dart';

class AccessPassScreen extends StatelessWidget {
  final ParkingController controller;

  const AccessPassScreen({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    final pass = controller.accessPass;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Pass d\'Accès Sans Contact'),
        actions: [
          IconButton(
            icon: const Icon(Icons.nfc),
            tooltip: 'Simuler détection NFC Borne',
            onPressed: () => _triggerNfcSimulation(context),
          ),
        ],
      ),
      body: pass == null
          ? const Center(child: Text('Aucun pass actif'))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  // Digital Driver Card
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      gradient: pass.isVip
                          ? const LinearGradient(
                              colors: [Color(0xFF0D131F), Color(0xFF161F30)],
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                            )
                          : const LinearGradient(
                              colors: [Color(0xFF080C14), Color(0xFF0D131F)],
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                            ),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: pass.isVip ? const Color(0xFF10B981) : const Color(0xFF00F2FE).withValues(alpha: 0.5),
                        width: 1.5,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.2),
                          blurRadius: 10,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text(
                              'SMART PARK PASS',
                              style: TextStyle(
                                color: Colors.white70,
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 1.5,
                              ),
                            ),
                            if (pass.isVip)
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFF59E0B),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: const Text(
                                  'ABONNÉ VIP',
                                  style: TextStyle(
                                    color: Colors.black,
                                    fontSize: 10,
                                    fontWeight: FontWeight.w900,
                                  ),
                                ),
                              ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        Text(
                          pass.driverName,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          pass.plateNumber,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 18,
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.w700,
                            letterSpacing: 2,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Expanded(
                              child: Text(
                                'Zone: ${pass.zoneName} (${pass.slotNumber})',
                                style: const TextStyle(color: Colors.white70, fontSize: 12),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              pass.passId,
                              style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11, fontFamily: 'monospace'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 30),

                  // Dynamic Rotating QR Code
                  DynamicQrWidget(
                    payload: '${pass.passId}|${pass.plateNumber}|${pass.currentToken}',
                    secondsRemaining: pass.secondsRemaining,
                    size: 200,
                  ),

                  const SizedBox(height: 24),

                  // Security and Guidance info
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Theme.of(context).cardColor,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: Theme.of(context).dividerColor),
                    ),
                    child: const Row(
                      children: [
                        Icon(Icons.shield_outlined, color: Color(0xFF00F2FE), size: 20),
                        SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            'Code QR dynamique à jeton tournant anti-capture. Présentez l\'écran devant le lecteur optique de la borne.',
                            style: TextStyle(fontSize: 11.5, color: Colors.grey),
                          ),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 16),

                  // Simulated NFC button
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                      icon: const Icon(Icons.contactless_outlined),
                      label: const Text('Simuler Approche NFC Voie 1'),
                      onPressed: () => _triggerNfcSimulation(context),
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  void _triggerNfcSimulation(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.nfc, color: Color(0xFF00F2FE)),
            SizedBox(width: 8),
            Text('Contact NFC Détecté'),
          ],
        ),
        content: Text(
          'Pass [${controller.accessPass?.passId}] validé par la borne.\n'
          'Plaque: ${controller.accessPass?.plateNumber}\n'
          'Impulsion relais Modbus envoyée.\n'
          'La barrière d\'entrée est ouverte.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }
}
