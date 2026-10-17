import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:smartpark_mobile/main.dart';
import 'package:smartpark_mobile/state/parking_controller.dart';
import 'package:smartpark_mobile/models/access_pass.dart';
import 'package:smartpark_mobile/models/vehicle_location.dart';
import 'package:smartpark_mobile/screens/car_finder_screen.dart';
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


