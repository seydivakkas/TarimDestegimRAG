// Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
// ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../providers/destek_provider.dart';
import '../widgets/state_views.dart';

class AskRagScreen extends StatefulWidget {
  const AskRagScreen({super.key});

  @override
  State<AskRagScreen> createState() => _AskRagScreenState();
}

class _AskRagScreenState extends State<AskRagScreen> {
  final TextEditingController _queryController = TextEditingController();

  final List<String> _sampleQueries = [
    "2026 yılı buğday temel desteği dekar başına ne kadardır?",
    "Planlı üretim desteğinden kimler faydalanabilir?",
    "Yeraltı su kısıtı desteği hangi havzalarda uygulanır?",
    "Sertifikalı tohum desteğinde fatura zorunlu mu?",
  ];

  @override
  void dispose() {
    _queryController.dispose();
    super.dispose();
  }

  void _search(String query) {
    if (query.trim().isEmpty) return;
    _queryController.text = query;
    context.read<DestekProvider>().askRagQuestion(query);
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<DestekProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text("Mevzuat Asistanı & Soru-Cevap"),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Arama Girişi
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _queryController,
                  decoration: const InputDecoration(
                    hintText: "Tarımsal destek sorunuzu yazınız...",
                    prefixIcon: Icon(Icons.search_rounded, color: AppTheme.primaryGreen),
                  ),
                  onSubmitted: _search,
                ),
              ),
              const SizedBox(width: 8),
              IconButton.filled(
                icon: const Icon(Icons.arrow_forward_rounded),
                style: IconButton.styleFrom(backgroundColor: AppTheme.primaryGreen),
                onPressed: () => _search(_queryController.text),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Hızlı Örnek Sorular
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: _sampleQueries.map((q) {
              return ActionChip(
                label: Text(q, style: const TextStyle(fontSize: 12)),
                backgroundColor: const Color(0xFFF1F8E9),
                onPressed: () => _search(q),
              );
            }).toList(),
          ),
          const Divider(height: 28),

          // Sonuç Alanı
          if (provider.askState == ViewState.loading)
            const LoadingView(message: "Mevzuat taranıyor ve Resmî Gazete maddesi getiriliyor...")
          else if (provider.askState == ViewState.error)
            ErrorView(message: provider.askError ?? "Sorgulama hatası.")
          else if (provider.askState == ViewState.success && provider.askResult != null)
            _buildResultView(provider.askResult!)
          else
            const EmptyView(message: "Yukarıdaki kutucuğa bir soru yazıp arayabilirsiniz."),
        ],
      ),
    );
  }

  Widget _buildResultView(dynamic result) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Card(
          margin: EdgeInsets.zero,
          color: const Color(0xFFF9FBF9),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.verified_rounded, color: AppTheme.primaryGreen, size: 20),
                    SizedBox(width: 8),
                    Text(
                      "Mevzuat Ön Bilgisi (Bağımsız Kaynak İncelemesi Gerekir)",
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.primaryGreen,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  result.summaryAnswerTr,
                  style: const TextStyle(fontSize: 14, height: 1.5, color: Colors.black87),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        if (result.matchedChunks.isNotEmpty) ...[
          const Text(
            "Aday Kaynak Parçaları (Doğrulanmış Alıntı Değildir)",
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          ...result.matchedChunks.map((c) => Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "${c.title} — ${c.section}",
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                          color: AppTheme.primaryGreen,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        c.snippet,
                        style: const TextStyle(fontSize: 13, height: 1.4),
                      ),
                    ],
                  ),
                ),
              )),
        ],
      ],
    );
  }
}
