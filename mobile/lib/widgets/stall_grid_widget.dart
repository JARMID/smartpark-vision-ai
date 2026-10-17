import 'package:flutter/material.dart';
import '../models/parking_slot.dart';

class StallGridWidget extends StatelessWidget {
  final List<ParkingSlot> slots;
  final Function(ParkingSlot) onSlotSelected;
  final String? selectedSlotNumber;

  const StallGridWidget({
    super.key,
    required this.slots,
    required this.onSlotSelected,
    this.selectedSlotNumber,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildLegend(context),
        const SizedBox(height: 12),
        Expanded(
          child: GridView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            physics: const AlwaysScrollableScrollPhysics(),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              childAspectRatio: 1.6,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
            ),
            itemCount: slots.length,
            itemBuilder: (context, index) {
              final slot = slots[index];
              final isSelected = slot.slotNumber == selectedSlotNumber;
              return _buildStallCard(context, slot, isSelected);
            },
          ),
        ),
      ],
    );
  }

  Widget _buildLegend(BuildContext context) {
    final vacantCount = slots.where((s) => s.isVacant).length;
    final occupiedCount = slots.where((s) => s.isOccupied).length;
    final reservedCount = slots.where((s) => s.isReserved).length;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Wrap(
        spacing: 12,
        runSpacing: 6,
        children: [
          _legendChip(Icons.check_circle_outline, Colors.green, 'Libres: $vacantCount'),
          _legendChip(Icons.directions_car, Colors.red, 'Occupées: $occupiedCount'),
          _legendChip(Icons.bookmark_outline, Colors.amber, 'Réservées: $reservedCount'),
        ],
      ),
    );
  }

  Widget _legendChip(IconData icon, Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: color),
        const SizedBox(width: 4),
        Text(
          label,
          style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: color),
        ),
      ],
    );
  }

  Widget _buildStallCard(BuildContext context, ParkingSlot slot, bool isSelected) {
    Color statusColor;
    Color statusBg;
    String statusLabel;

    if (slot.isVacant) {
      statusColor = const Color(0xFF10B981);
      statusBg = const Color(0xFF10B981).withValues(alpha: 0.12);
      statusLabel = 'DISPONIBLE';
    } else if (slot.isOccupied) {
      statusColor = const Color(0xFFEF4444);
      statusBg = const Color(0xFFEF4444).withValues(alpha: 0.12);
      statusLabel = 'OCCUPÉE';
    } else {
      statusColor = const Color(0xFFF59E0B);
      statusBg = const Color(0xFFF59E0B).withValues(alpha: 0.12);
      statusLabel = 'RÉSERVÉE';
    }

    final isVip = slot.isVip;
    final semanticStatus = slot.isVacant ? "Libre" : (slot.isOccupied ? "Occupée" : "Réservée");

    return Semantics(
      button: true,
      selected: isSelected,
      label: 'Place ${slot.slotNumber}, ${slot.zoneName}, statut $semanticStatus${slot.plate != null ? ", immatriculation ${slot.plate}" : ""}',
      child: InkWell(
        onTap: () => onSlotSelected(slot),
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Theme.of(context).cardColor,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isSelected
                  ? const Color(0xFF00F2FE)
                  : (isVip ? const Color(0xFFA78BFA) : Theme.of(context).dividerColor),
              width: isSelected ? 2.5 : 1.2,
            ),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: const Color(0xFF00F2FE).withValues(alpha: 0.25),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ]
                : null,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    slot.slotNumber,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0.5,
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: statusBg,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      statusLabel,
                      style: TextStyle(
                        fontSize: 9.5,
                        fontWeight: FontWeight.w800,
                        color: statusColor,
                      ),
                    ),
                  ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    slot.zoneName,
                    style: TextStyle(
                      fontSize: 11,
                      color: isVip ? const Color(0xFFA78BFA) : const Color(0xFF94A3B8),
                      fontWeight: isVip ? FontWeight.w700 : FontWeight.w500,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (slot.plate != null)
                    Text(
                      slot.plate!,
                      style: const TextStyle(
                        fontSize: 10.5,
                        fontWeight: FontWeight.bold,
                        fontFamily: 'monospace',
                      ),
                    )
                  else if (slot.isVacant)
                    const Text(
                      'Toucher pour reserver',
                      style: TextStyle(fontSize: 10, color: Color(0xFF10B981)),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
