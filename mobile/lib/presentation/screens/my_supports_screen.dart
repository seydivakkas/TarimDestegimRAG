// Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
// ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../data/models/support_models.dart';
import '../providers/destek_provider.dart';
import '../widgets/state_views.dart';
import '../widgets/status_badge.dart';
import 'support_detail_screen.dart';

class MySupportsScreen extends StatelessWidget {
  const MySupportsScreen({super.key});

  String _formatCurrency(double amount) {
    final fmt = NumberFormat("#,##0.00", "tr_TR");
    return "${fmt.format(amount)} TL";
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<DestekProvider>();

    if (provider.evalState == ViewState.loading) {
      return const LoadingView();
    }

    if (provider.evalState == ViewState.error) {
      return ErrorView(
        message: provider.errorMessage ?? "Bilinmeyen bir hata oluştu.",
        onRetry: () {},
      );
    }

    final res = provider.evaluationResult;
    if (res == null || res.rules.isEmpty) {
      return const EmptyView(
        message: "Henüz bir hesaplama yapılmadı.\n'Parsel Girişi' sekmesinden bilgilerinizi giriniz.",
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text("Tarımsal Desteklerim (2026)"),
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(vertical: 12),
        children: [
          // Toplam Tahmini Destek Özeti Bannerı
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [AppTheme.primaryGreen, AppTheme.secondaryGreen],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: AppTheme.primaryGreen.withOpacity(0.3),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.monetization_on_rounded, color: AppTheme.accentAmber, size: 24),
                    SizedBox(width: 8),
                    Text(
                      "TOPLAM TAHMİNİ DESTEK",
                      style: TextStyle(
                        color: Colors.white70,
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1.1,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  _formatCurrency(res.totalEstimatedAmount),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 28,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  "Ürün: ${res.parcel.crop} | Alan: ${res.parcel.areaDa} dekar | Konum: ${res.farmer.province}/${res.farmer.district}",
                  style: const TextStyle(color: Colors.white70, fontSize: 13),
                ),
              ],
            ),
          ),

          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 18, vertical: 8),
            child: Text(
              "Değerlendirilen Programlar",
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
          ),

          // 5 Destek Programı Kartları Listesi
          ...res.rules.map((rule) {
            final calc = res.calculations.firstWhere(
              (c) => c.supportId == rule.supportId,
              orElse: () => CalculationResult(
                ruleId: rule.ruleId,
                supportId: rule.supportId,
                supportName: rule.supportName,
                status: rule.status,
                formula: '',
              ),
            );
            final exp = res.explanations.firstWhere(
              (e) => e.supportId == rule.supportId,
              orElse: () => ExplanationResult(
                supportId: rule.supportId,
                supportName: rule.supportName,
                status: rule.status,
                statusLabelTr: '',
                summaryTr: '',
                detailedReasonTr: '',
                missingRequirementsTr: [],
                nextActionsTr: [],
                citations: [],
              ),
            );

            return Card(
              child: InkWell(
                borderRadius: BorderRadius.circular(14),
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => SupportDetailScreen(
                        rule: rule,
                        calculation: calc,
                        explanation: exp,
                      ),
                    ),
                  );
                },
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
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                          StatusBadge(status: rule.status),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        exp.summaryTr.isNotEmpty
                            ? exp.summaryTr
                            : "Detayları görüntülemek için tıklayınız.",
                        style: TextStyle(fontSize: 13, color: Colors.grey.shade700),
                      ),
                      const SizedBox(height: 10),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            calc.estimatedAmount != null
                                ? _formatCurrency(calc.estimatedAmount!)
                                : "0.00 TL",
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: calc.estimatedAmount != null
                                  ? AppTheme.primaryGreen
                                  : Colors.grey,
                            ),
                          ),
                          const Row(
                            children: [
                              Text(
                                "İncele",
                                style: TextStyle(
                                  color: AppTheme.primaryGreen,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 13,
                                ),
                              ),
                              Icon(Icons.chevron_right_rounded, color: AppTheme.primaryGreen, size: 20),
                            ],
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}
