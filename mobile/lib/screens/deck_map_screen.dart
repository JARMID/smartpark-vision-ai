import 'package:flutter/material.dart';
import '../models/parking_slot.dart';
import '../state/parking_controller.dart';
import '../widgets/stall_grid_widget.dart';
import '../widgets/smart_park_logo.dart';

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
        : allSlots
              .where(
                (s) => s.zoneName.toUpperCase().contains(_selectedZoneFilter),
              )
              .toList();

    return Scaffold(
      appBar: AppBar(
        leading: const Padding(
          padding: EdgeInsets.all(10.0),
          child: SmartParkLogo(size: 28),
        ),
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
            icon: const Icon(Icons.settings_outlined),
            onPressed: () => _showGatewayConfigDialog(context),
            tooltip: 'Configuration Passerelle',
          ),
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
                if (controller.apiService.isOffline)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 8,
                    ),
                    color: const Color(0xFFF59E0B).withValues(alpha: 0.15),
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.cloud_off,
                          size: 14,
                          color: Color(0xFFF59E0B),
                        ),
                        SizedBox(width: 8),
                        Text(
                          'Mode hors ligne (données locales synchronisées)',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFFF59E0B),
                          ),
                        ),
                      ],
                    ),
                  ),
                _buildZoneFilterBar(),
                const SizedBox(height: 8),
                Expanded(
                  child: RefreshIndicator(
                    onRefresh: () => controller.loadSlots(),
                    color: const Color(0xFF00F2FE),
                    backgroundColor: const Color(0xFF0F172A),
                    child: filteredSlots.isEmpty
                        ? _buildEmptyState()
                        : StallGridWidget(
                            slots: filteredSlots,
                            selectedSlotNumber:
                                controller.selectedSlot?.slotNumber,
                            onSlotSelected: (slot) =>
                                _onSlotTapped(context, slot),
                          ),
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildEmptyState() {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 48),
      children: [
        Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.05),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.local_parking,
                  size: 48,
                  color: Colors.grey,
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'Aucun emplacement trouvé',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text(
                'Aucune place ne correspond au filtre de zone sélectionné.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13, color: Colors.grey),
              ),
            ],
          ),
        ),
      ],
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
      selectedColor: const Color(0xFF00F2FE).withValues(alpha: 0.2),
      labelStyle: TextStyle(
        fontSize: 12,
        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
        color: isSelected ? const Color(0xFF00F2FE) : null,
      ),
    );
  }

  void _onSlotTapped(BuildContext context, ParkingSlot slot) {
    widget.controller.selectSlot(slot);
    bool isActionInFlight = false;

    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (modalContext, setModalState) {
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
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 4,
                        ),
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
                  Text(
                    'Zone: ${slot.zoneName}',
                    style: const TextStyle(fontSize: 14),
                  ),
                  Text(
                    'Etage: ${slot.floorLevel}',
                    style: const TextStyle(fontSize: 14),
                  ),
                  if (slot.plate != null)
                    Text(
                      'Véhicule: ${slot.plate}',
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
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
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                        ),
                        icon: isActionInFlight
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Icon(Icons.bookmark_add),
                        label: Text(
                          isActionInFlight
                              ? 'Réservation en cours...'
                              : 'Réserver cette place (Franchise 30 min)',
                        ),
                        onPressed: isActionInFlight
                            ? null
                            : () async {
                                setModalState(() => isActionInFlight = true);
                                final ok = await widget.controller.reserveSelectedSlot();
                                if (ctx.mounted) {
                                  Navigator.pop(ctx);
                                }
                                if (context.mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text(
                                        ok
                                            ? 'Place ${slot.slotNumber} réservée pour 30 minutes.'
                                            : 'Échec de réservation.',
                                      ),
                                      backgroundColor: ok ? Colors.green : Colors.red,
                                    ),
                                  );
                                }
                              },
                      ),
                    )
                  else if (slot.isReserved)
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.amber.shade800,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                        ),
                        icon: isActionInFlight
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Icon(Icons.bookmark_remove),
                        label: Text(
                          isActionInFlight
                              ? 'Annulation en cours...'
                              : 'Libérer cette réservation',
                        ),
                        onPressed: isActionInFlight
                            ? null
                            : () async {
                                setModalState(() => isActionInFlight = true);
                                final ok = await widget.controller.releaseSelectedSlot();
                                if (ctx.mounted) {
                                  Navigator.pop(ctx);
                                }
                                if (context.mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text(
                                        ok
                                            ? 'Réservation de la place ${slot.slotNumber} annulée.'
                                            : 'Échec de l\'annulation.',
                                      ),
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
      },
    );
  }

  void _showGatewayConfigDialog(BuildContext context) {
    final textController = TextEditingController(
      text: widget.controller.currentServerUrl,
    );

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.router, color: Color(0xFF00F2FE)),
            SizedBox(width: 8),
            Text('Passerelle Edge Gateway', style: TextStyle(fontSize: 16)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Saisir l\'adresse IP ou l\'URL du serveur passerelle du parking :',
              style: TextStyle(fontSize: 12.5),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: textController,
              decoration: const InputDecoration(
                labelText: 'URL Serveur',
                hintText: 'http://192.168.1.100:8080',
                border: OutlineInputBorder(),
                isDense: true,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Statut actuel : ${widget.controller.apiService.isOffline ? "Hors-ligne (Cache local)" : "Connecté (En direct)"}',
              style: TextStyle(
                fontSize: 11.5,
                color: widget.controller.apiService.isOffline
                    ? Colors.amber
                    : Colors.green,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Annuler'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF0284C7),
              foregroundColor: Colors.white,
            ),
            onPressed: () {
              final newUrl = textController.text.trim();
              if (newUrl.isNotEmpty) {
                widget.controller.updateServerUrl(newUrl);
              }
              Navigator.pop(ctx);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Passerelle configurée : $newUrl'),
                  backgroundColor: Colors.green,
                ),
              );
            },
            child: const Text('Enregistrer'),
          ),
        ],
      ),
    );
  }
}
