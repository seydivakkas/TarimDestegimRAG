// Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
// ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/constants/api_constants.dart';
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
                      "Ön Değerlendirme Gerekçesi & Kanıt Durumu",
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
                "Mevzuat Kaynakları ve Kanıt Durumları:",
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              if (explanation.citations.isEmpty)
                const Text("Doğrulanmış atıf bulunamadı.", style: TextStyle(color: Colors.grey))
              else
                ...explanation.citations.map((c) => _buildCitationCard(context, c)),
              const SizedBox(height: 20),
            ],
          ),
        );
      },
    );
  }

  Widget _buildCitationCard(BuildContext context, CitationDetail citation) {
    final proofPath = citation.verifiedHighlightPath(supportId: explanation.supportId);
    final hasEvidence = proofPath != null;
    final exactText = citation.verificationStatus ==
            'EXACT_PDF_MATCH_PENDING_LEGAL_REVIEW' ||
        citation.verificationStatus ==
            'ORIGINAL_HTML_TEXT_LOCATED_PENDING_LEGAL_REVIEW';
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6),
      elevation: 0,
      color: hasEvidence ? const Color(0xFFF4F8F4) : Colors.grey.shade50,
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
                Icon(hasEvidence ? Icons.gavel_rounded : Icons.info_outline,
                    size: 16, color: hasEvidence ? AppTheme.primaryGreen : Colors.grey),
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
              hasEvidence ? "Eşleşen bölüm: ${citation.section}" :
                  "Konu etiketi (doğrulanmadı): ${citation.section}",
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.grey.shade800),
            ),
            const SizedBox(height: 4),
            Text(
              hasEvidence
                  ? (exactText
                      ? 'Özgün metnin konumu bulundu — hukukî onay bekliyor.'
                      : 'PDF görüntüsü işaretlendi — bağımsız metin incelemesi bekliyor.')
                  : 'Ön değerlendirme açıklaması — resmî alıntı değildir.',
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 4),
            Text(
              hasEvidence && exactText ? '“${citation.snippet}”' : citation.snippet,
              style: const TextStyle(fontSize: 13, height: 1.4, color: Colors.black87),
            ),
            if (hasEvidence) ...[
              const SizedBox(height: 8),
              TextButton.icon(
                icon: const Icon(Icons.open_in_new),
                label: const Text('Sarı işaretli özgün belgeyi aç'),
                onPressed: () async {
                  final target = Uri.tryParse('${ApiConstants.baseUrl}$proofPath');
                  if (target == null ||
                      !['http', 'https'].contains(target.scheme)) return;
                  final opened = await launchUrl(
                    target, mode: LaunchMode.externalApplication,
                  );
                  if (!opened && context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('İşaretli belge açılmadı. API adresini kontrol edin.')),
                    );
                  }
                },
              ),
            ],
            if (citation.url != null) ...[
              const SizedBox(height: 6),
              Text(
                "Genel kaynak adresi (tek başına madde kanıtı değildir): ${citation.url}",
                style: const TextStyle(fontSize: 11, color: Colors.black54),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
