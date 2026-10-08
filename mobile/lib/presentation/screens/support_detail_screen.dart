// Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
// ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/theme/app_theme.dart';
import '../../data/models/support_models.dart';
import '../widgets/status_badge.dart';
import 'why_citations_dialog.dart';

class SupportDetailScreen extends StatelessWidget {
  final RuleResult rule;
  final CalculationResult? calculation;
  final ExplanationResult? explanation;

  const SupportDetailScreen({
    super.key,
    required this.rule,
    this.calculation,
    this.explanation,
  });

  String _formatCurrency(double? amount) {
    if (amount == null) return "0.00 TL";
    final fmt = NumberFormat("#,##0.00", "tr_TR");
    return "${fmt.format(amount)} TL";
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(rule.supportName),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Başlık ve Durum Kartı
          Card(
            margin: EdgeInsets.zero,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text(
                          rule.supportName,
                          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                        ),
                      ),
                      StatusBadge(status: rule.status),
                    ],
                  ),
                  const Divider(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text("Tahmini Destek:", style: TextStyle(fontSize: 15, color: Colors.black54)),
                      Text(
                        _formatCurrency(calculation?.estimatedAmount),
                        style: const TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                          color: AppTheme.primaryGreen,
                        ),
                      ),
                    ],
                  ),
                  if (calculation?.formula.isNotEmpty ?? false) ...[
                    const SizedBox(height: 6),
                    Text(
                      "Hesaplama Formülü: ${calculation!.formula}",
                      style: TextStyle(fontSize: 13, color: Colors.grey.shade600, fontStyle: FontStyle.italic),
                    ),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Şartlar ve Kontroller
          Card(
            margin: EdgeInsets.zero,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Uygunluk Kontrolleri", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 12),
                  if (rule.passedChecks.isNotEmpty) ...[
                    ...rule.passedChecks.map(
                      (c) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.check_circle_outline, color: AppTheme.statusEligible, size: 20),
                            const SizedBox(width: 8),
                            Expanded(child: Text(c, style: const TextStyle(fontSize: 14))),
                          ],
                        ),
                      ),
                    ),
                  ],
                  if (rule.failedChecks.isNotEmpty) ...[
                    ...rule.failedChecks.map(
                      (c) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.highlight_off_rounded, color: AppTheme.statusNotEligible, size: 20),
                            const SizedBox(width: 8),
                            Expanded(child: Text(c, style: const TextStyle(fontSize: 14))),
                          ],
                        ),
                      ),
                    ),
                  ],
                  if (rule.missingFields.isNotEmpty) ...[
                    ...rule.missingFields.map(
                      (m) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.help_outline_rounded, color: AppTheme.statusReview, size: 20),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                "Eksik Bilgi/Belge: $m",
                                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Sonraki Adımlar & Başvuru Süreci
          if (explanation?.nextActionsTr.isNotEmpty ?? false) ...[
            Card(
              margin: EdgeInsets.zero,
              color: const Color(0xFFF1F8E9),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.assignment_turned_in_rounded, color: AppTheme.primaryGreen, size: 20),
                        SizedBox(width: 8),
                        Text(
                          "Başvuru İçin Yapılması Gerekenler",
                          style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    ...explanation!.nextActionsTr.map(
                      (a) => Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Text("• $a", style: const TextStyle(fontSize: 13, height: 1.4)),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],

          // Neden? (Resmî Gerekçe ve Atıflar) Butonu
          if (explanation != null)
            ElevatedButton.icon(
              onPressed: () => WhyCitationsDialog.show(context, explanation!),
              icon: const Icon(Icons.help_center_rounded),
              label: const Text("Neden Bu Karar Verildi? (Resmî Atıflar)"),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.accentAmber,
                foregroundColor: Colors.black,
              ),
            ),
        ],
      ),
    );
  }
}
