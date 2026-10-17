import 'package:flutter/material.dart';
import '../state/parking_controller.dart';

class PatrolScannerScreen extends StatefulWidget {
  final ParkingController controller;

  const PatrolScannerScreen({super.key, required this.controller});

  @override
  State<PatrolScannerScreen> createState() => _PatrolScannerScreenState();
}

class _PatrolScannerScreenState extends State<PatrolScannerScreen> {
  final _manualPlateInput = TextEditingController(text: '104822 119 16');

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (context, _) {
        final controller = widget.controller;
        final status = controller.patrolPlateStatus;

        return Scaffold(
          appBar: AppBar(
            title: const Text('Patrouille & Contrôle ALPR'),
            backgroundColor: const Color(0xFF0F172A),
            actions: [
              IconButton(
                icon: const Icon(Icons.lock_open, color: Colors.amber),
                tooltip: 'Déclencheur d\'ouverture manuelle barrière',
                onPressed: () => _triggerBarrierOverride(context),
              ),
            ],
          ),
          body: SingleChildScrollView(
            child: Column(
              children: [
                // Optical Viewfinder Simulation
                Container(
                  height: 260,
                  width: double.infinity,
                  color: Colors.black,
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      // Camera grid line simulation
                      Column(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [
                          Container(height: 1, color: Colors.white12),
                          Container(height: 1, color: Colors.white12),
                        ],
                      ),
                      // ALPR Target Bounding Box
                      Container(
                        width: 280,
                        height: 110,
                        decoration: BoxDecoration(
                          border: Border.all(
                            color:
                                (status != null && status['is_alert'] == true)
                                ? Colors.red
                                : const Color(0xFF10B981),
                            width: 2,
                          ),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Stack(
                          children: [
                            Positioned(
                              top: 4,
                              left: 6,
                              child: Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 4,
                                  vertical: 2,
                                ),
                                color: Colors.black87,
                                child: Text(
                                  'OCR YOLOv11 // CONF: 97.8%',
                                  style: TextStyle(
                                    fontSize: 9.5,
                                    fontWeight: FontWeight.bold,
                                    color:
                                        (status != null &&
                                            status['is_alert'] == true)
                                        ? Colors.red
                                        : const Color(0xFF10B981),
                                  ),
                                ),
                              ),
                            ),
                            Center(
                              child: Text(
                                controller.patrolLastScannedPlate ??
                                    'CADRER PLAQUE',
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 22,
                                  fontWeight: FontWeight.bold,
                                  fontFamily: 'monospace',
                                  letterSpacing: 2,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      Positioned(
                        bottom: 10,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.black54,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Row(
                            children: [
                              Icon(
                                Icons.camera_alt,
                                color: Colors.white70,
                                size: 14,
                              ),
                              SizedBox(width: 6),
                              Text(
                                'Scan Optique Continu Actif (30 FPS)',
                                style: TextStyle(
                                  color: Colors.white70,
                                  fontSize: 11,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

                Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Simuler la Détection d\'une Plaque :',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          ActionChip(
                            avatar: const Icon(
                              Icons.check,
                              size: 16,
                              color: Colors.green,
                            ),
                            label: const Text('104822 119 16 (VIP)'),
                            onPressed: () =>
                                controller.executePatrolScan('104822 119 16'),
                          ),
                          ActionChip(
                            avatar: const Icon(
                              Icons.warning,
                              size: 16,
                              color: Colors.red,
                            ),
                            label: const Text('00551 218 16 (Volé)'),
                            onPressed: () =>
                                controller.executePatrolScan('00551 218 16'),
                          ),
                          ActionChip(
                            avatar: const Icon(
                              Icons.access_time,
                              size: 16,
                              color: Colors.amber,
                            ),
                            label: const Text('99120 121 16 (Impayé)'),
                            onPressed: () =>
                                controller.executePatrolScan('99120 121 16'),
                          ),
                        ],
                      ),

                      const SizedBox(height: 16),

                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _manualPlateInput,
                              decoration: const InputDecoration(
                                labelText: 'Saisir Plaque Manuelle',
                                border: OutlineInputBorder(),
                                isDense: true,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          ElevatedButton(
                            onPressed: () => controller.executePatrolScan(
                              _manualPlateInput.text.trim(),
                            ),
                            child: const Text('Vérifier'),
                          ),
                        ],
                      ),

                      const SizedBox(height: 20),

                      // Status Card with LiveRegion Accessibility
                      if (status != null) ...[
                        Semantics(
                          liveRegion: true,
                          label:
                              "Résultat du contrôle: ${status['status']}, place ${status['slot']}. ${status['message']}",
                          child: Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color: status['is_alert'] == true
                                  ? Colors.red.withValues(alpha: 0.12)
                                  : Colors.green.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                color: status['is_alert'] == true
                                    ? Colors.red
                                    : Colors.green,
                              ),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  mainAxisAlignment:
                                      MainAxisAlignment.spaceBetween,
                                  children: [
                                    Text(
                                      status['status'] as String,
                                      style: TextStyle(
                                        fontWeight: FontWeight.bold,
                                        fontSize: 15,
                                        color: status['is_alert'] == true
                                            ? Colors.red
                                            : Colors.green,
                                      ),
                                    ),
                                    Text('Place: ${status['slot']}'),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  status['message'] as String,
                                  style: const TextStyle(fontSize: 13),
                                ),
                                if (status['is_alert'] == true) ...[
                                  const SizedBox(height: 12),
                                  ElevatedButton.icon(
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: Colors.red,
                                      foregroundColor: Colors.white,
                                    ),
                                    icon: const Icon(Icons.receipt_long),
                                    label: const Text(
                                      'Émettre Avis de Verbalisation / Fourrière',
                                    ),
                                    onPressed: () {
                                      ScaffoldMessenger.of(
                                        context,
                                      ).showSnackBar(
                                        const SnackBar(
                                          content: Text(
                                            'Avis d\'infraction transmis à la régie.',
                                          ),
                                        ),
                                      );
                                    },
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  void _triggerBarrierOverride(BuildContext context) async {
    final ok = await widget.controller.patrolReleaseBarrier();
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            ok
                ? 'Impulsion barrière envoyée avec succès (Voie 1).'
                : 'Échec de commande barrière.',
          ),
          backgroundColor: ok ? Colors.green : Colors.red,
        ),
      );
    }
  }

  @override
  void dispose() {
    _manualPlateInput.dispose();
    super.dispose();
  }
}
