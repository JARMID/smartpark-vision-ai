import 'package:flutter/material.dart';
import 'state/parking_controller.dart';
import 'screens/home_shell.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final controller = ParkingController();
  runApp(SmartParkMobileApp(controller: controller));
}

class SmartParkMobileApp extends StatelessWidget {
  final ParkingController controller;

  const SmartParkMobileApp({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        return MaterialApp(
          title: 'Smart Park',
          debugShowCheckedModeBanner: false,
          themeMode: controller.themeMode,
          locale: controller.locale,
          theme: ThemeData(
            useMaterial3: true,
            brightness: Brightness.dark,
            colorScheme: ColorScheme.fromSeed(
              seedColor: const Color(0xFF00F2FE),
              brightness: Brightness.dark,
            ),
            scaffoldBackgroundColor: const Color(0xFF080C14),
            cardColor: const Color(0xFF0D131F),
            appBarTheme: const AppBarTheme(
              backgroundColor: Color(0xFF0D131F),
              elevation: 0,
              centerTitle: false,
              titleTextStyle: TextStyle(
                color: Color(0xFFF8FAFC),
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
              iconTheme: IconThemeData(color: Color(0xFF00F2FE)),
            ),
          ),
          darkTheme: ThemeData(
            useMaterial3: true,
            brightness: Brightness.dark,
            colorScheme: ColorScheme.fromSeed(
              seedColor: const Color(0xFF00F2FE),
              brightness: Brightness.dark,
            ),
            scaffoldBackgroundColor: const Color(0xFF080C14),
            cardColor: const Color(0xFF0D131F),
            appBarTheme: const AppBarTheme(
              backgroundColor: Color(0xFF0D131F),
              elevation: 0,
              centerTitle: false,
              titleTextStyle: TextStyle(
                color: Color(0xFFF8FAFC),
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
              iconTheme: IconThemeData(color: Color(0xFF00F2FE)),
            ),
          ),
          home: HomeShell(controller: controller),
        );
      },
    );
  }
}
