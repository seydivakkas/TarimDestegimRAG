// Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
// ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../data/models/support_models.dart';

class WhyCitationsDialog extends StatelessWidget {
  final ExplanationResult explanation;

  const WhyCitationsDialog({super.key, required this.explanation});

  static void show(BuildContext context, ExplanationResult explanation) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => WhyCitationsDialog(explanation: explanation),
    );
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.7,
      maxChildSize: 0.9,
      minChildSize: 0.4,
      expand: false,
      builder: (context, scrollController) {
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          child: ListView(
            controller: scrollController,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  const Icon(Icons.menu_book_rounded, color: AppTheme.primaryGreen, size: 28),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      "Resmî Karar Gerekçesi & Atıf",
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.bold,
                            color: AppTheme.primaryGreen,
                          ),
                    ),
                  ),
                ],
              ),
              const Divider(height: 24),
              Text(
                explanation.supportName,
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.grey.shade200),
                ),
                child: Text(
                  explanation.detailedReasonTr,
                  style: const TextStyle(fontSize: 14, height: 1.5, color: Colors.black87),
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                "Doğrulanan Mevzuat Kaynakları (Citations):",
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              if (explanation.citations.isEmpty)
                const Text("Doğrulanmış atıf bulunamadı.", style: TextStyle(color: Colors.grey))
              else
                ...explanation.citations.map((c) => _buildCitationCard(c)),
              const SizedBox(height: 20),
            ],
          ),
        );
      },
    );
  }

  Widget _buildCitationCard(CitationDetail citation) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6),
      elevation: 0,
      color: const Color(0xFFF4F8F4),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: Color(0xFFC8E6C9)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.gavel_rounded, size: 16, color: AppTheme.primaryGreen),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    citation.title,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                      color: AppTheme.primaryGreen,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: Colors.grey.shade300),
                  ),
                  child: Text(
                    "${citation.year}",
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              "Bölüm/Madde: ${citation.section}",
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.grey.shade800),
            ),
            const SizedBox(height: 4),
            Text(
              '"${citation.snippet}"',
              style: const TextStyle(fontSize: 13, fontStyle: FontStyle.italic, color: Colors.black87),
            ),
            if (citation.url != null) ...[
              const SizedBox(height: 6),
              Text(
                "Resmî Gazete Linki: ${citation.url}",
                style: const TextStyle(fontSize: 11, color: Colors.blueAccent, decoration: TextDecoration.underline),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
