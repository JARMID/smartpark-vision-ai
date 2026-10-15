import 'package:flutter/material.dart';
import '../models/parking_slot.dart';
import '../state/parking_controller.dart';
import '../widgets/stall_grid_widget.dart';

class DeckMapScreen extends StatefulWidget {
  final ParkingController controller;

  const DeckMapScreen({super.key, required this.controller});

  @override
  State<DeckMapScreen> createState() => _DeckMapScreenState();
}

class _DeckMapScreenState extends State<DeckMapScreen> {
  String _selectedZoneFilter = 'ALL';

  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;
    final allSlots = controller.slots;

    final filteredSlots = _selectedZoneFilter == 'ALL'
        ? allSlots
        : allSlots.where((s) => s.zoneName.toUpperCase().contains(_selectedZoneFilter)).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Disponibilité du Parking',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            Text(
              'Niveau 0 - Alger Centre',
              style: TextStyle(fontSize: 11, color: Colors.grey),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => controller.loadSlots(),
            tooltip: 'Actualiser les places',
          ),
        ],
      ),
      body: controller.isLoading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                _buildZoneFilterBar(),
                const SizedBox(height: 8),
                Expanded(
                  child: StallGridWidget(
                    slots: filteredSlots,
                    selectedSlotNumber: controller.selectedSlot?.slotNumber,
                    onSlotSelected: (slot) => _onSlotTapped(context, slot),
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildZoneFilterBar() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          _filterChip('TOUTES', 'ALL'),
          const SizedBox(width: 8),
          _filterChip('Zone A (VIP)', 'ZONE A'),
          const SizedBox(width: 8),
          _filterChip('Zone B (Public)', 'ZONE B'),
          const SizedBox(width: 8),
          _filterChip('Zone C (Utilitaire)', 'ZONE C'),
          const SizedBox(width: 8),
          _filterChip('Zone D (PMR)', 'ZONE D'),
        ],
      ),
    );
  }

  Widget _filterChip(String label, String key) {
    final isSelected = _selectedZoneFilter == key;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (val) {
        if (val) {
          setState(() {
            _selectedZoneFilter = key;
          });
        }
      },
      selectedColor: const Color(0xFF0284C7).withValues(alpha: 0.2),
      labelStyle: TextStyle(
        fontSize: 12,
        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
        color: isSelected ? const Color(0xFF0284C7) : null,
      ),
    );
  }

  void _onSlotTapped(BuildContext context, ParkingSlot slot) {
    widget.controller.selectSlot(slot);

    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Emplacement ${slot.slotNumber}',
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: slot.isVacant
                          ? Colors.green.withValues(alpha: 0.15)
                          : Colors.red.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      slot.status.toUpperCase(),
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: slot.isVacant ? Colors.green : Colors.red,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text('Zone: ${slot.zoneName}', style: const TextStyle(fontSize: 14)),
              Text('Etage: ${slot.floorLevel}', style: const TextStyle(fontSize: 14)),
              if (slot.plate != null)
                Text('Véhicule: ${slot.plate}', style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
              const SizedBox(height: 16),
              const Divider(),
              const SizedBox(height: 8),
              if (slot.isVacant)
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF0284C7),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    icon: const Icon(Icons.bookmark_add),
                    label: const Text('Réserver cette place (Franchise 30 min)'),
                    onPressed: () async {
                      Navigator.pop(ctx);
                      final ok = await widget.controller.reserveSelectedSlot();
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(ok
                                ? 'Place ${slot.slotNumber} réservée pour 30 minutes.'
                                : 'Échec de réservation.'),
                            backgroundColor: ok ? Colors.green : Colors.red,
                          ),
                        );
                      }
                    },
                  ),
                )
              else
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(ctx),
                    child: const Text('Fermer'),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }
}
