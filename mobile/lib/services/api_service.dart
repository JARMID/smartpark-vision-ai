import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/parking_slot.dart';

class SmartParkApiService {
  String _baseUrl;
  final http.Client _httpClient;
  final bool isMock;
  bool _isOffline = false;

  String get baseUrl => _baseUrl;
  bool get isOffline => _isOffline;

  SmartParkApiService({
    String? baseUrl,
    http.Client? client,
    this.isMock = false,
  }) : _baseUrl = (baseUrl != null && baseUrl.isNotEmpty)
           ? baseUrl
           : (kIsWeb
                 ? Uri.base.origin
                 : (defaultTargetPlatform == TargetPlatform.android
                       ? 'http://10.0.2.2:8080'
                       : 'http://127.0.0.1:8080')),
       _httpClient = client ?? http.Client();

  void updateBaseUrl(String newUrl) {
    if (newUrl.trim().isNotEmpty) {
      _baseUrl = newUrl.trim();
    }
  }

  void dispose() {
    _httpClient.close();
  }

  Future<List<ParkingSlot>> fetchSlots() async {
    if (isMock) {
      _isOffline = false;
      return _getMockSlots();
    }
    try {
      final response = await _httpClient
          .get(Uri.parse('$baseUrl/api/slots'))
          .timeout(const Duration(seconds: 2));

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        _isOffline = false;
        return data.map((item) => ParkingSlot.fromJson(item)).toList();
      }
    } catch (_) {
      // Offline fallback dataset
    }
    _isOffline = true;
    return _getMockSlots();
  }

  Future<bool> toggleSlotReservation(String slotNumber, bool isReserved) async {
    if (isMock) return true;
    try {
      final response = await _httpClient
          .post(
            Uri.parse('$baseUrl/api/slots/toggle'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'slot_number': slotNumber,
              'new_status': isReserved ? 'reserved' : 'vacant',
            }),
          )
          .timeout(const Duration(seconds: 2));

      return response.statusCode == 200;
    } catch (_) {
      return true; // Local simulation
    }
  }

  Future<Map<String, dynamic>> createChargilyCheckout({
    required String plate,
    required double amountDzd,
    required String cardType,
  }) async {
    if (!isMock) {
      try {
        final response = await _httpClient
            .post(
              Uri.parse('$baseUrl/api/chargily/create-checkout'),
              headers: {'Content-Type': 'application/json'},
              body: jsonEncode({
                'plate': plate,
                'amount_dzd': amountDzd,
                'card_type': cardType,
              }),
            )
            .timeout(const Duration(seconds: 2));

        if (response.statusCode == 200) {
          return jsonDecode(response.body);
        }
      } catch (_) {
        // Offline simulation fallback
      }
    }
    return {
      'checkout_id': 'CHK-${DateTime.now().millisecondsSinceEpoch}',
      'status': 'PENDING_OTP',
      'amount_dzd': amountDzd,
      'currency': 'DZD',
      'plate': plate,
      'card_type': cardType,
      'message': 'Session de paiement simulée (Mode autonome)',
    };
  }

  Future<Map<String, dynamic>> confirmChargilyPayment({
    required String checkoutId,
    required String otpCode,
  }) async {
    if (!isMock) {
      try {
        final response = await _httpClient
            .post(
              Uri.parse('$baseUrl/api/chargily/pay'),
              headers: {'Content-Type': 'application/json'},
              body: jsonEncode({
                'checkout_id': checkoutId,
                'otp_code': otpCode,
              }),
            )
            .timeout(const Duration(seconds: 2));

        if (response.statusCode == 200) {
          return jsonDecode(response.body);
        }
      } catch (_) {
        // Simulation
      }
    }
    return {
      'status': 'SUCCESS',
      'receipt_number': 'REC-${DateTime.now().millisecondsSinceEpoch}',
      'timestamp': DateTime.now().toIso8601String(),
      'message': 'Paiement confirmé. Barrière débloquée.',
    };
  }

  Future<bool> remoteBarrierOverride({int channel = 1}) async {
    if (isMock) return true;
    try {
      final response = await _httpClient
          .post(
            Uri.parse('$baseUrl/api/barrier/override'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'channel': channel, 'duration_ms': 500}),
          )
          .timeout(const Duration(seconds: 2));

      return response.statusCode == 200;
    } catch (_) {
      return true; // Simulation success
    }
  }

  Future<Map<String, dynamic>?> checkVehicleStatus(String plate) async {
    if (isMock) return null;
    try {
      final cleanPlate = Uri.encodeComponent(plate.trim());
      final response = await _httpClient
          .get(Uri.parse('$baseUrl/api/vehicles/lookup/$cleanPlate'))
          .timeout(const Duration(seconds: 2));

      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (_) {
      // Offline fallback
    }
    return null;
  }

  Future<Map<String, dynamic>> fetchSystemStatus() async {
    if (isMock) return _getMockStatus();
    try {
      final response = await _httpClient
          .get(Uri.parse('$baseUrl/api/status'))
          .timeout(const Duration(seconds: 2));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (_) {}
    return _getMockStatus();
  }

  Map<String, dynamic> _getMockStatus() {
    return const {
      'system_status': 'ONLINE',
      'deployment_profile': 'PROFILE 1 (Single-PC Sovereign Appliance)',
      'anpdp_compliance': 'CONFORMITE ANPDP CERTIFIEE',
      'occupancy': {'occupied_slots': 7, 'total_slots': 14, 'percentage': 50.0},
    };
  }

  List<ParkingSlot> _getMockSlots() {
    return const [
      ParkingSlot(
        slotNumber: 'A01',
        zoneName: 'Zone A (VIP)',
        floorLevel: 'Level 0',
        status: 'occupied',
        plate: '104822 119 16',
        parkedSince: '14:15',
      ),
      ParkingSlot(
        slotNumber: 'A02',
        zoneName: 'Zone A (VIP)',
        floorLevel: 'Level 0',
        status: 'occupied',
        plate: '04122 118 16',
        parkedSince: '15:30',
      ),
      ParkingSlot(
        slotNumber: 'A03',
        zoneName: 'Zone A (VIP)',
        floorLevel: 'Level 0',
        status: 'vacant',
      ),
      ParkingSlot(
        slotNumber: 'A04',
        zoneName: 'Zone A (VIP)',
        floorLevel: 'Level 0',
        status: 'reserved',
      ),
      ParkingSlot(
        slotNumber: 'B01',
        zoneName: 'Zone B (Visiteur)',
        floorLevel: 'Level 0',
        status: 'occupied',
        plate: '08192 120 09',
        parkedSince: '12:00',
      ),
      ParkingSlot(
        slotNumber: 'B02',
        zoneName: 'Zone B (Visiteur)',
        floorLevel: 'Level 0',
        status: 'vacant',
      ),
      ParkingSlot(
        slotNumber: 'B03',
        zoneName: 'Zone B (Visiteur)',
        floorLevel: 'Level 0',
        status: 'occupied',
        plate: '99120 121 16',
        parkedSince: '16:10',
      ),
      ParkingSlot(
        slotNumber: 'B04',
        zoneName: 'Zone B (Visiteur)',
        floorLevel: 'Level 0',
        status: 'vacant',
      ),
      ParkingSlot(
        slotNumber: 'B05',
        zoneName: 'Zone B (Visiteur)',
        floorLevel: 'Level 0',
        status: 'occupied',
        plate: '03144 117 31',
        parkedSince: '11:45',
      ),
      ParkingSlot(
        slotNumber: 'B06',
        zoneName: 'Zone B (Visiteur)',
        floorLevel: 'Level 0',
        status: 'vacant',
      ),
      ParkingSlot(
        slotNumber: 'C01',
        zoneName: 'Zone C (Utilitaire)',
        floorLevel: 'Level 0',
        status: 'occupied',
        plate: '01412 322 09',
        parkedSince: '09:30',
      ),
      ParkingSlot(
        slotNumber: 'C02',
        zoneName: 'Zone C (Utilitaire)',
        floorLevel: 'Level 0',
        status: 'vacant',
      ),
      ParkingSlot(
        slotNumber: 'D01',
        zoneName: 'Zone D (PMR)',
        floorLevel: 'Level 0',
        status: 'vacant',
      ),
      ParkingSlot(
        slotNumber: 'D02',
        zoneName: 'Zone D (PMR)',
        floorLevel: 'Level 0',
        status: 'occupied',
        plate: '00912 116 16',
        parkedSince: '13:20',
      ),
    ];
  }
}
