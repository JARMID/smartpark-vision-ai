import 'package:flutter/material.dart';
import '../state/parking_controller.dart';
import 'deck_map_screen.dart';
import 'access_pass_screen.dart';
import 'car_finder_screen.dart';
import 'patrol_scanner_screen.dart';

class HomeShell extends StatefulWidget {
  final ParkingController controller;

  const HomeShell({super.key, required this.controller});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;

    final screens = [
      DeckMapScreen(controller: controller),
      AccessPassScreen(controller: controller),
      CarFinderScreen(controller: controller),
      PatrolScannerScreen(controller: controller),
    ];

    return Scaffold(
      body: AnimatedBuilder(
        animation: controller,
        builder: (context, _) => screens[_currentIndex],
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
        type: BottomNavigationBarType.fixed,
        backgroundColor: const Color(0xFF0D131F),
        selectedItemColor: const Color(0xFF00F2FE),
        unselectedItemColor: const Color(0xFF64748B),
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.local_parking),
            label: 'Places',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.qr_code_2),
            label: 'Pass d\'Accès',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.directions_walk),
            label: 'Véhicule',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.security),
            label: 'Patrouille',
          ),
        ],
      ),
    );
  }
}
