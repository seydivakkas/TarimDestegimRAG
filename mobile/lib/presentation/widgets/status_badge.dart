// Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
// ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class StatusBadge extends StatelessWidget {
  final String status;
  final String? customLabel;

  const StatusBadge({super.key, required this.status, this.customLabel});

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color textColor;
    IconData icon;
    String label;

    switch (status.toUpperCase()) {
      case 'ELIGIBLE':
        bg = const Color(0xFFE8F5E9);
        textColor = AppTheme.statusEligible;
        icon = Icons.check_circle_rounded;
        label = customLabel ?? 'Uygun görünüyor';
        break;
      case 'NOT_ELIGIBLE':
        bg = const Color(0xFFFFEBEE);
        textColor = AppTheme.statusNotEligible;
        icon = Icons.cancel_rounded;
        label = customLabel ?? 'Uygun görünmüyor';
        break;
      case 'REVIEW':
      default:
        bg = const Color(0xFFFFF3E0);
        textColor = AppTheme.statusReview;
        icon = Icons.info_rounded;
        label = customLabel ?? 'Ek kontrol gerekiyor';
        break;
    }

    return Semantics(
      label: 'Uygunluk Durumu: $label',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: textColor.withOpacity(0.3), width: 1),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 16, color: textColor),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                color: textColor,
                fontSize: 13,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
