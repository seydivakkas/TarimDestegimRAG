// Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
// ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/theme/app_theme.dart';
import 'presentation/providers/destek_provider.dart';
import 'presentation/screens/ask_rag_screen.dart';
import 'presentation/screens/input_screen.dart';
import 'presentation/screens/my_supports_screen.dart';

void main() {
  runApp(const TarimDestekApp());
}

class TarimDestekApp extends StatelessWidget {
  const TarimDestekApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => DestekProvider()..loadPrograms(),
      child: MaterialApp(
        title: 'TarımDestekRAG 2026',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.lightTheme,
        home: const MainNavigationScreen(),
      ),
    );
  }
}

class MainNavigationScreen extends StatefulWidget {
  const MainNavigationScreen({super.key});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    final screens = [
      InputScreen(
        onEvaluationSuccess: () {
          setState(() => _currentIndex = 1); // Desteklerim sekmesine geçiş
        },
      ),
      const MySupportsScreen(),
      const AskRagScreen(),
    ];

    return Scaffold(
      body: screens[_currentIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) => setState(() => _currentIndex = index),
        indicatorColor: const Color(0xFFC8E6C9),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.edit_note_rounded),
            selectedIcon: Icon(Icons.edit_note_rounded, color: AppTheme.primaryGreen),
            label: "Parsel Girişi",
          ),
          NavigationDestination(
            icon: Icon(Icons.format_list_bulleted_rounded),
            selectedIcon: Icon(Icons.format_list_bulleted_rounded, color: AppTheme.primaryGreen),
            label: "Desteklerim",
          ),
          NavigationDestination(
            icon: Icon(Icons.menu_book_rounded),
            selectedIcon: Icon(Icons.menu_book_rounded, color: AppTheme.primaryGreen),
            label: "Mevzuat Asistanı",
          ),
        ],
      ),
    );
  }
}
