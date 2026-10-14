// F10 — exact claim evidence only; generic RAG citations are NOT official.
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../data/models/support_models.dart';
import '../../data/models/canonical_evidence_models.dart';

class WhyCitationsDialog extends StatelessWidget {
  final ExplanationResult explanation;
  final RuleResult? rule;
  final CanonicalEvidenceIndex? evidenceIndex;

  const WhyCitationsDialog({
    super.key,
    required this.explanation,
    this.rule,
    this.evidenceIndex,
  });

  static void show(
    BuildContext context,
    ExplanationResult explanation, {
    RuleResult? rule,
    CanonicalEvidenceIndex? evidenceIndex,
  }) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      builder: (ctx) => WhyCitationsDialog(
        explanation: explanation,
        rule: rule,
        evidenceIndex: evidenceIndex,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final scoped = evidenceIndex?.claims.where((c) =>
        rule != null &&
        c.ruleId == rule!.ruleId &&
        c.supportId == rule!.supportId).toList() ?? [];

    return DraggableScrollableSheet(
      initialChildSize: 0.74,
      minChildSize: 0.40,
      maxChildSize: 0.93,
      expand: false,
      builder: (context, controller) => ListView(
        controller: controller,
        padding: const EdgeInsets.all(18),
        children: [
          Text('Neden? — Tekil Gerekçe ve Kaynak Kanıtı',
              style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          Text(explanation.supportName,
              style: const TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text(explanation.detailedReasonTr),
          const SizedBox(height: 12),
          const Text(
            'YASAL UYARI: Kaynak pasajının bulunması, üretim yılının '
            'hukukî geçerliliği, çiftçi olguları veya ödeme onayı değildir. '
            'Bu alanlar HOLD.',
            style: TextStyle(color: Color(0xFF92400E)),
          ),
          const Divider(height: 25),
          const Text('Bu değerlendirmeye ait tekil gerekçeler',
              style: TextStyle(fontWeight: FontWeight.bold)),
          if (scoped.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 12),
              child: Text(
                'HOLD — Aynı değerlendirmeye bağlı kaynak sözleşmesi '
                'bulunamadı. Genel arama linki resmî kanıt gibi açılmaz.',
              ),
            )
          else
            ...scoped.map((proof) => _proofCard(proof)),
          if (explanation.citations.isNotEmpty) ...[
            const Divider(height: 26),
            const Text(
              'Genel arama parçaları — kaynak konumu doğrulanmadı',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            ...explanation.citations.take(5).map((citation) => Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(citation.title,
                        style: const TextStyle(fontWeight: FontWeight.bold)),
                    Text(citation.section),
                    const Text(
                      'HOLD — Birebir SHA/madde/pasaj denetimi yok. '
                      'Bu arama sonucu tıklanabilir resmî kanıt değildir.',
                    ),
                  ],
                ),
              ),
            )),
          ],
        ],
      ),
    );
  }

  Widget _proofCard(CanonicalClaimEvidence proof) {
    final source = proof.source;
    final located = proof.hasVerifiableSourceLocation && source != null;
    final uri = proof.originalSourceUri;
    final isPdf = located && source['format'] == 'pdf';
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(proof.claimText ?? 'Şart metni bulunamadı',
                style: const TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            SelectableText('claim_id: ' + (proof.claimId ?? 'HOLD')),
            if (located) ...[
              SelectableText('evidence_id: ' + (proof.evidenceId ?? 'HOLD')),
              Text(source['document_id'].toString() + ' • ' +
                  source['article'].toString() + ' • ' +
                  source['target_provision'].toString()),
              SelectableText('SHA-256: ' + source['source_sha256'].toString()),
              const SizedBox(height: 7),
              Container(
                // Yellow remains for verified exact HTML passage preview;
                // PDF native-text geometry is only a source-location
                // candidate, not dual-reviewed visual proof.
                color: isPdf
                    ? const Color(0xFFFFEDD5)
                    : const Color(0xFFFFED52),
                padding: const EdgeInsets.all(10),
                child: SelectableText(
                  source['exact_quote'].toString(),
                  style: const TextStyle(color: Colors.black87),
                ),
              ),
              if (isPdf)
                Text(
                  'Özgün PDF sayfa ' + source['pdf_page'].toString() +
                  ' — native metin ve gerçek piksel koordinatı konumu '
                  'sunucuda denetlendi. Turuncu metin önizlemesidir; '
                  'çift incelemeci görsel onayı/yürürlük/ödeme HOLD.',
                )
              else
                const Text(
                  'Birebir HTML pasajı özgün kaynakta konumlandırıldı. '
                  'Sarı metin uygulama önizlemesidir; yürürlük/ödeme HOLD.',
                ),
              if (uri != null)
                TextButton.icon(
                  onPressed: () async {
                    await launchUrl(uri, mode: LaunchMode.externalApplication);
                  },
                  icon: const Icon(Icons.open_in_new),
                  label: const Text('Doğrulanmış özgün kaynak belgesini aç'),
                ),
            ] else
              const Text(
                'HOLD — Tekil gerekçenin kaynak konumu doğrulanmadı. '
                'Sarı pasaj veya kaynak bağlantısı üretilmez.',
                style: TextStyle(color: Color(0xFF92400E)),
              ),
            const Text(
              'Mevzuat değişiklik zinciri: HOLD • Yıl geçerliliği: HOLD • '
              'Çiftçi koşulu: doğrulanmadı • Ödeme: HOLD',
              style: TextStyle(color: Color(0xFF92400E)),
            ),
          ],
        ),
      ),
    );
  }
}
