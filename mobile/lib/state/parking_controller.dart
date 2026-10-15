import 'dart:async';
import 'package:flutter/material.dart';
import '../models/parking_slot.dart';
import '../models/access_pass.dart';
import '../models/vehicle_location.dart';
import '../services/api_service.dart';

class ParkingController extends ChangeNotifier {
  final SmartParkApiService apiService;

  List<ParkingSlot> _slots = [];
  bool _isLoading = false;
  ParkingSlot? _selectedSlot;

  AccessPass? _accessPass;
  Timer? _passTimer;

  VehicleLocation? _myVehicle;
  ThemeMode _themeMode = ThemeMode.dark;
  Locale _locale = const Locale('fr');

  // Patrol mode for security guards
  bool _isPatrolMode = false;
  String? _patrolLastScannedPlate;
  Map<String, dynamic>? _patrolPlateStatus;

  ParkingController({SmartParkApiService? service, bool autoStartTicker = true})
      : apiService = service ?? SmartParkApiService() {
    _initialize(autoStartTicker);
  }

  List<ParkingSlot> get slots => _slots;
  bool get isLoading => _isLoading;
  ParkingSlot? get selectedSlot => _selectedSlot;
  AccessPass? get accessPass => _accessPass;
  VehicleLocation? get myVehicle => _myVehicle;
  ThemeMode get themeMode => _themeMode;
  Locale get locale => _locale;
  bool get isPatrolMode => _isPatrolMode;
  String? get patrolLastScannedPlate => _patrolLastScannedPlate;
  Map<String, dynamic>? get patrolPlateStatus => _patrolPlateStatus;

  void _initialize(bool autoStartTicker) {
    loadSlots();
    _initDemoPass();
    _initDemoVehicle();
    if (autoStartTicker) {
      _startPassTokenTicker();
    }
  }

  void _initDemoPass() {
    final now = DateTime.now();
    const plate = '104822 119 16';
    final token = AccessPass.generateRotatingToken(plate, now.millisecondsSinceEpoch ~/ 1000);

    _accessPass = AccessPass(
      passId: 'PASS-ALG-9901',
      plateNumber: plate,
      driverName: 'Amine Hadj',
      zoneName: 'Zone A (VIP)',
      slotNumber: 'A01',
      issuedAt: now,
      validUntil: now.add(const Duration(hours: 4)),
      isVip: true,
      currentToken: token,
      secondsRemaining: 30,
    );
  }

  void _initDemoVehicle() {
    _myVehicle = VehicleLocation(
      slotNumber: 'A01',
      zoneName: 'Zone A (VIP)',
      floorLevel: 'Niveau 0 (Entree Principale)',
      parkedAt: DateTime.now().subtract(const Duration(minutes: 85)),
      latitude: 36.7538,
      longitude: 3.0588,
      sectionName: 'Allee Centrale Nord',
    );
  }

  void _startPassTokenTicker() {
    _passTimer?.cancel();
    _passTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_accessPass == null) return;
      final nowSec = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      final rem = 30 - (nowSec % 30);
      final token = AccessPass.generateRotatingToken(_accessPass!.plateNumber, nowSec);

      _accessPass = _accessPass!.copyWith(
        currentToken: token,
        secondsRemaining: rem,
      );
      notifyListeners();
    });
  }

  Future<void> loadSlots() async {
    _isLoading = true;
    notifyListeners();
    _slots = List<ParkingSlot>.from(await apiService.fetchSlots());
    _isLoading = false;
    notifyListeners();
  }

  void selectSlot(ParkingSlot slot) {
    _selectedSlot = slot;
    notifyListeners();
  }

  Future<bool> reserveSelectedSlot() async {
    if (_selectedSlot == null || !_selectedSlot!.isVacant) return false;
    final success = await apiService.toggleSlotReservation(_selectedSlot!.slotNumber, true);
    if (success) {
      final index = _slots.indexWhere((s) => s.slotNumber == _selectedSlot!.slotNumber);
      if (index != -1) {
        _slots[index] = _slots[index].copyWith(status: 'reserved');
        _selectedSlot = _slots[index];
        notifyListeners();
      }
    }
    return success;
  }

  Future<Map<String, dynamic>> payTicketWithChargily({
    required String plate,
    required double amountDzd,
    required String cardType,
    required String otp,
  }) async {
    final checkout = await apiService.createChargilyCheckout(
      plate: plate,
      amountDzd: amountDzd,
      cardType: cardType,
    );
    final checkoutId = checkout['checkout_id'] as String;
    final confirm = await apiService.confirmChargilyPayment(
      checkoutId: checkoutId,
      otpCode: otp,
    );
    return confirm;
  }

  // Security Patrol Mode functions
  void togglePatrolMode(bool enabled) {
    _isPatrolMode = enabled;
    notifyListeners();
  }

  void executePatrolScan(String plate) {
    _patrolLastScannedPlate = plate;
    // Query local list to verify authorization
    final matched = _slots.where((s) => s.plate != null && s.plate!.contains(plate)).toList();
    if (matched.isNotEmpty) {
      _patrolPlateStatus = {
        'status': 'AUTHORIZED',
        'slot': matched.first.slotNumber,
        'zone': matched.first.zoneName,
        'message': 'Vehicule stationne en regle',
        'is_alert': false,
      };
    } else if (plate.contains('00551')) {
      _patrolPlateStatus = {
        'status': 'BLACKLIST_ALERT',
        'slot': 'INCONNU',
        'zone': 'NON ENREGISTRE',
        'message': 'ALERTE: Fiche de recherche active. Bloquer vehicule.',
        'is_alert': true,
      };
    } else {
      _patrolPlateStatus = {
        'status': 'UNPAID_OVERSTAY',
        'slot': 'B04',
        'zone': 'Zone B',
        'message': 'Depassement de forfait non regle (+45 min)',
        'is_alert': true,
      };
    }
    notifyListeners();
  }

  Future<bool> patrolReleaseBarrier() async {
    return await apiService.remoteBarrierOverride(channel: 1);
  }

  void toggleTheme() {
    _themeMode = _themeMode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
    notifyListeners();
  }

  void setLocale(Locale loc) {
    _locale = loc;
    notifyListeners();
  }

  @override
  void dispose() {
    _passTimer?.cancel();
    super.dispose();
  }
}
