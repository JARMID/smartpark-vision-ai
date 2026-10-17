import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:smartpark_mobile/main.dart';
import 'package:smartpark_mobile/state/parking_controller.dart';
import 'package:smartpark_mobile/models/access_pass.dart';
import 'package:smartpark_mobile/models/vehicle_location.dart';
import 'package:smartpark_mobile/screens/car_finder_screen.dart';
import 'package:smartpark_mobile/screens/access_pass_screen.dart';
import 'package:smartpark_mobile/screens/payment_screen.dart';
import 'package:smartpark_mobile/screens/patrol_scanner_screen.dart';
import 'package:smartpark_mobile/screens/deck_map_screen.dart';
import 'package:smartpark_mobile/widgets/stall_grid_widget.dart';
import 'package:smartpark_mobile/services/api_service.dart';

void main() {
  testWidgets('SmartPark Mobile App smoke test and navigation tabs', (WidgetTester tester) async {
    final mockService = SmartParkApiService(isMock: true);
    final controller = ParkingController(service: mockService, autoStartTicker: false);

    await tester.pumpWidget(SmartParkMobileApp(controller: controller));
    await tester.pumpAndSettle();

    // Verify initial Deck Map tab
    expect(find.text('Disponibilité du Parking'), findsOneWidget);
    expect(find.byType(BottomNavigationBar), findsOneWidget);

    // Switch to Access Pass tab
    await tester.tap(find.text("Pass d'Accès"));
    await tester.pumpAndSettle();

    expect(find.text("Pass d'Accès Sans Contact"), findsOneWidget);
    expect(find.text('SMART PARK PASS'), findsOneWidget);
    expect(find.text('Amine Hadj'), findsOneWidget);

    // Switch to Car Finder tab
    await tester.tap(find.text('Véhicule'));
    await tester.pumpAndSettle();

    expect(find.text('Retrouver mon Véhicule'), findsOneWidget);
    expect(find.text('A01'), findsOneWidget);

    // Switch to Patrol Scanner tab
    await tester.tap(find.text('Patrouille'));
    await tester.pumpAndSettle();

    expect(find.text('Patrouille & Contrôle ALPR'), findsOneWidget);
    expect(find.text('104822 119 16 (VIP)'), findsOneWidget);

    controller.dispose();
  });

  test('ParkingController TOTP rotating token calculation test', () {
    final token1 = AccessPass.generateRotatingToken('104822 119 16', 1000);
    final token2 = AccessPass.generateRotatingToken('104822 119 16', 1010);
    final token3 = AccessPass.generateRotatingToken('104822 119 16', 1040); // Next 30s step

    // Within same 30s window (1000 // 30 == 33 and 1010 // 30 == 33)
    expect(token1, equals(token2));

    // Next 30s window (1040 // 30 == 34)
    expect(token1, isNot(equals(token3)));
  });

  test('ParkingController slot reservation flow', () async {
    final mockService = SmartParkApiService(isMock: true);
    final controller = ParkingController(service: mockService, autoStartTicker: false);
    await controller.loadSlots();

    final vacantSlots = controller.slots.where((s) => s.isVacant).toList();
    expect(vacantSlots, isNotEmpty);

    controller.selectSlot(vacantSlots.first);
    expect(controller.selectedSlot, isNotNull);

    final success = await controller.reserveSelectedSlot();
    expect(success, isTrue);
    expect(controller.selectedSlot!.isReserved, isTrue);

    // Test releasing reservation
    final released = await controller.releaseSelectedSlot();
    expect(released, isTrue);
    expect(controller.selectedSlot!.isVacant, isTrue);

    // Test updating server URL
    expect(controller.currentServerUrl, isNotEmpty);
    await controller.updateServerUrl('http://192.168.1.120:8080');
    expect(controller.currentServerUrl, equals('http://192.168.1.120:8080'));

    controller.dispose();
  });

  test('VehicleLocation progressive tariff tiered calculation test', () {
    final now = DateTime.now();

    // 1. Grace period: 10 min -> 0 DZD
    final locGrace = VehicleLocation(
      slotNumber: 'B01',
      zoneName: 'Zone B',
      floorLevel: 'Niveau 0',
      parkedAt: now.subtract(const Duration(minutes: 10)),
      latitude: 36.75,
      longitude: 3.05,
      sectionName: 'Allee Nord',
    );
    final breakGrace = locGrace.calculateProgressiveTariff();
    expect(breakGrace.isGracePeriod, isTrue);
    expect(breakGrace.totalDueDzd, equals(0.0));

    // 2. 2-hour duration (75 min) -> 100 + 50 = 150 DZD
    final loc2h = VehicleLocation(
      slotNumber: 'B01',
      zoneName: 'Zone B',
      floorLevel: 'Niveau 0',
      parkedAt: now.subtract(const Duration(minutes: 75)),
      latitude: 36.75,
      longitude: 3.05,
      sectionName: 'Allee Nord',
    );
    final break2h = loc2h.calculateProgressiveTariff();
    expect(break2h.isGracePeriod, isFalse);
    expect(break2h.totalDueDzd, equals(150.0));
    expect(break2h.billableHours, equals(2));

    // 3. 5-hour duration (280 min) -> 100 + 3*50 + 1*30 = 280 DZD
    final loc5h = VehicleLocation(
      slotNumber: 'B01',
      zoneName: 'Zone B',
      floorLevel: 'Niveau 0',
      parkedAt: now.subtract(const Duration(minutes: 280)),
      latitude: 36.75,
      longitude: 3.05,
      sectionName: 'Allee Nord',
    );
    final break5h = loc5h.calculateProgressiveTariff();
    expect(break5h.totalDueDzd, equals(280.0));
    expect(break5h.billableHours, equals(5));

    // 4. 20-hour duration -> 100 + 3*50 + 16*30 = 730 DZD
    final loc20h = VehicleLocation(
      slotNumber: 'B01',
      zoneName: 'Zone B',
      floorLevel: 'Niveau 0',
      parkedAt: now.subtract(const Duration(hours: 20)),
      latitude: 36.75,
      longitude: 3.05,
      sectionName: 'Allee Nord',
    );
    final break20h = loc20h.calculateProgressiveTariff();
    expect(break20h.totalDueDzd, equals(730.0));

    // 5. Daily cap test: 23 hours -> 100 + 150 + 19*30 = 820 capped at 800 DZD
    final locCap = VehicleLocation(
      slotNumber: 'B01',
      zoneName: 'Zone B',
      floorLevel: 'Niveau 0',
      parkedAt: now.subtract(const Duration(hours: 23)),
      latitude: 36.75,
      longitude: 3.05,
      sectionName: 'Allee Nord',
    );
    final breakCap = locCap.calculateProgressiveTariff();
    expect(breakCap.totalDueDzd, equals(800.0));
  });

  testWidgets('DeckMapScreen and StallGridWidget empty category state', (WidgetTester tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: StallGridWidget(
          slots: const [],
          onSlotSelected: (_) {},
        ),
      ),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Aucune place disponible dans cette catégorie.'), findsOneWidget);
    expect(find.byIcon(Icons.local_parking_outlined), findsOneWidget);
  });

  testWidgets('DeckMapScreen Gateway Config modal opens and displays current URL', (WidgetTester tester) async {
    final mockService = SmartParkApiService(isMock: true);
    final controller = ParkingController(service: mockService, autoStartTicker: false);

    await tester.pumpWidget(MaterialApp(
      home: DeckMapScreen(controller: controller),
    ));
    await tester.pumpAndSettle();

    // Tap settings icon in AppBar
    await tester.tap(find.byIcon(Icons.settings_outlined));
    await tester.pumpAndSettle();

    expect(find.text('Passerelle Edge Gateway'), findsOneWidget);
    expect(find.text('URL Serveur'), findsOneWidget);
    expect(find.text('Enregistrer'), findsOneWidget);

    // Tap Annuler
    await tester.tap(find.text('Annuler'));
    await tester.pumpAndSettle();

    expect(find.text('Passerelle Edge Gateway'), findsNothing);

    controller.dispose();
  });

  testWidgets('CarFinderScreen grace period vs paid tariff', (WidgetTester tester) async {
    final mockService = SmartParkApiService(isMock: true);
    final controller = ParkingController(service: mockService, autoStartTicker: false);

    // Initial vehicle is parked for 85 minutes -> Tariff > 0 DZD
    await tester.pumpWidget(MaterialApp(
      home: CarFinderScreen(controller: controller),
    ));
    await tester.pumpAndSettle();

    expect(find.text('EMPLACEMENT ACTUEL'), findsOneWidget);
    expect(find.textContaining('Régler mon stationnement'), findsOneWidget);

    controller.dispose();
  });

  testWidgets('CarFinderScreen null vehicle shows friendly empty state', (WidgetTester tester) async {
    final mockService = SmartParkApiService(isMock: true);
    final controller = ParkingController(service: mockService, autoStartTicker: false);

    // In a new widget with a controller that has no vehicle
    await tester.pumpWidget(MaterialApp(
      home: CarFinderScreen(
        controller: _NullVehicleMockController(),
      ),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Aucun véhicule stationné'), findsOneWidget);
    expect(find.text('Aucun véhicule actif n\'est associé à votre compte actuellement.'), findsOneWidget);
    controller.dispose();
  });

  testWidgets('CarFinderScreen grace period shows free exit authorized', (WidgetTester tester) async {
    final controller = _GracePeriodMockController();

    await tester.pumpWidget(MaterialApp(
      home: CarFinderScreen(controller: controller),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Sortie Gratuite Autorisée'), findsOneWidget);
    expect(find.text('0 DZD (Franchise 15 min)'), findsOneWidget);
    expect(find.byIcon(Icons.check_circle), findsOneWidget);

    controller.dispose();
  });

  testWidgets('AccessPassScreen NFC simulation triggers barrier pulse dialog', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final mockService = SmartParkApiService(isMock: true);
    final controller = ParkingController(service: mockService, autoStartTicker: false);

    await tester.pumpWidget(MaterialApp(
      home: AccessPassScreen(controller: controller),
    ));
    await tester.pumpAndSettle();

    expect(find.text("Pass d'Accès Sans Contact"), findsOneWidget);
    expect(find.text('Simuler Approche NFC Voie 1'), findsOneWidget);

    await tester.tap(find.text('Simuler Approche NFC Voie 1'));
    await tester.pumpAndSettle();

    expect(find.text('Contact NFC Détecté'), findsOneWidget);
    expect(find.textContaining('La barrière d\'entrée est ouverte'), findsOneWidget);

    controller.dispose();
  });

  testWidgets('PaymentScreen card selection and confirmation flow', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final mockService = SmartParkApiService(isMock: true);
    final controller = ParkingController(service: mockService, autoStartTicker: false);

    await tester.pumpWidget(MaterialApp(
      home: PaymentScreen(
        controller: controller,
        amountDzd: 200.0,
        plateNumber: '104822 119 16',
      ),
    ));
    await tester.pumpAndSettle();

    expect(find.text('200 DZD'), findsOneWidget);
    expect(find.text('104822 119 16'), findsOneWidget);
    expect(find.text('Recevoir le code SMS OTP'), findsOneWidget);

    // Tap CIB card selection
    await tester.tap(find.text('Carte Interbancaire (CIB)'));
    await tester.pumpAndSettle();

    // Tap OTP request
    await tester.tap(find.text('Recevoir le code SMS OTP'));
    await tester.pumpAndSettle();

    expect(find.text('Confirmer le débit (200 DZD)'), findsOneWidget);

    // Tap Confirm payment
    await tester.tap(find.text('Confirmer le débit (200 DZD)'));
    await tester.pumpAndSettle();

    expect(find.text('Paiement Validé'), findsOneWidget);

    controller.dispose();
  });

  testWidgets('PatrolScannerScreen ALPR plate checks and barrier override', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final mockService = SmartParkApiService(isMock: true);
    final controller = ParkingController(service: mockService, autoStartTicker: false);

    await tester.pumpWidget(MaterialApp(
      home: PatrolScannerScreen(controller: controller),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Patrouille & Contrôle ALPR'), findsOneWidget);

    // Tap stolen vehicle chip
    await tester.tap(find.text('00551 218 16 (Volé)'));
    await tester.pumpAndSettle();

    expect(find.text('BLACKLIST_ALERT'), findsOneWidget);
    expect(find.textContaining('Fiche de recherche active'), findsOneWidget);

    // Test barrier override button
    await tester.tap(find.byIcon(Icons.lock_open));
    await tester.pumpAndSettle();

    expect(find.textContaining('Impulsion barrière envoyée avec succès'), findsOneWidget);

    controller.dispose();
  });

  testWidgets('PatrolScannerScreen live gateway lookup updates status card', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final mockService = _LivePatrolMockService();
    final controller = ParkingController(service: mockService, autoStartTicker: false);

    await tester.pumpWidget(MaterialApp(
      home: PatrolScannerScreen(controller: controller),
    ));
    await tester.pumpAndSettle();

    // Tap VIP chip
    await tester.tap(find.text('104822 119 16 (VIP)'));
    await tester.pumpAndSettle();

    expect(find.text('AUTHORIZED'), findsOneWidget);
    expect(find.textContaining('Vehicule verifie sur la passerelle'), findsOneWidget);

    controller.dispose();
  });
}

class _LivePatrolMockService extends SmartParkApiService {
  _LivePatrolMockService() : super(isMock: false);

  @override
  Future<Map<String, dynamic>?> checkVehicleStatus(String plate) async {
    if (plate.contains('104822')) {
      return {
        'found': true,
        'status': 'INSIDE_PARKED',
        'plate': '104822 119 16',
        'slot_number': 'A01',
        'driver_name': 'Amine Hadj',
        'is_vip': true,
        'entry_time': '14:15',
        'is_alert': false,
        'message': 'Vehicule verifie sur la passerelle.',
      };
    }
    return null;
  }
}

class _NullVehicleMockController extends ParkingController {
  _NullVehicleMockController() : super(service: SmartParkApiService(isMock: true), autoStartTicker: false);

  @override
  VehicleLocation? get myVehicle => null;
}

class _GracePeriodMockController extends ParkingController {
  _GracePeriodMockController() : super(service: SmartParkApiService(isMock: true), autoStartTicker: false);

  @override
  VehicleLocation? get myVehicle => VehicleLocation(
        slotNumber: 'B04',
        zoneName: 'Zone B (Public)',
        floorLevel: 'Niveau 0',
        parkedAt: DateTime.now().subtract(const Duration(minutes: 8)), // 8 min < 15 min grace
        latitude: 36.7538,
        longitude: 3.0588,
        sectionName: 'Allee Sud',
      );
}


