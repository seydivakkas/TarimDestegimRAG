// Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
// ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../data/models/farmer_parcel_models.dart';
import '../providers/destek_provider.dart';

class InputScreen extends StatefulWidget {
  final VoidCallback onEvaluationSuccess;

  const InputScreen({super.key, required this.onEvaluationSuccess});

  @override
  State<InputScreen> createState() => _InputScreenState();
}

class _InputScreenState extends State<InputScreen> {
  final _formKey = GlobalKey<FormState>();

  String _selectedProvince = "KONYA";
  String _selectedDistrict = "KARATAY";
  bool? _cksStatus = true;

  String _selectedCrop = "BUĞDAY";
  final TextEditingController _areaController = TextEditingController(text: "10.0");
  bool _seedCert = false;
  bool _saplingCert = false;
  bool _isClosedOrchard = false;
  String _irrigation = "IRRIGATED";

  final Map<String, List<String>> _districtsByProvince = {
    "KONYA": ["KARATAY", "ÇUMRA", "SELÇUKLU", "MERAM"],
    "SAMSUN": ["ÇARŞAMBA", "BAFRA", "İLKADIM"],
    "ANKARA": ["POLATLI", "HAYMANA", "BALA"],
    "ORDU": ["ÜNYE", "FATSA", "ALTINORDU"],
    "GİRESUN": ["BULANCAK", "GÖRELE", "TİREBOLU"],
    "ADANA": ["SEYHAN", "YÜREĞİR", "CEYHAN"],
    "TEKİRDAĞ": ["SÜLEYMANPAŞA", "ÇORLU", "HAYRABOLU"],
  };

  final List<String> _crops = [
    "BUĞDAY",
    "ARPA",
    "MISIR",
    "FINDIK",
    "MERCİMEK",
    "PAMUK",
    "AYÇİÇEĞİ",
  ];

  @override
  void dispose() {
    _areaController.dispose();
    super.dispose();
  }

  void _submit() async {
    if (!_formKey.currentState!.validate()) return;

    final area = double.tryParse(_areaController.text) ?? 10.0;
    final farmer = FarmerProfile(
      province: _selectedProvince,
      district: _selectedDistrict,
      cksStatus: _cksStatus,
    );
    final parcel = Parcel(
      crop: _selectedCrop,
      areaDa: area,
      productionYear: 2026,
      seedCertificateAvailable: _seedCert,
      saplingCertificateAvailable: _saplingCert,
      isClosedOrchard: _isClosedOrchard,
      irrigation: _irrigation,
    );

    final provider = context.read<DestekProvider>();
    await provider.evaluate(farmer, parcel);

    if (provider.evalState == ViewState.success && mounted) {
      widget.onEvaluationSuccess();
    }
  }

  @override
  Widget build(BuildContext context) {
    final districts = _districtsByProvince[_selectedProvince] ?? ["MERKEZ"];
    final provider = context.watch<DestekProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text("Çiftçi & Parsel Bilgileri"),
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Bölüm 1: Çiftçi Profili (P16.2)
            const Row(
              children: [
                Icon(Icons.person_pin_rounded, color: AppTheme.primaryGreen),
                SizedBox(width: 8),
                Text("Çiftçi Profili", style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 12),
            Card(
              margin: EdgeInsets.zero,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    DropdownButtonFormField<String>(
                      value: _selectedProvince,
                      decoration: const InputDecoration(labelText: "İl"),
                      items: _districtsByProvince.keys.map((p) {
                        return DropdownMenuItem(value: p, child: Text(p));
                      }).toList(),
                      onChanged: (val) {
                        if (val != null) {
                          setState(() {
                            _selectedProvince = val;
                            _selectedDistrict = _districtsByProvince[val]!.first;
                          });
                        }
                      },
                    ),
                    const SizedBox(height: 14),
                    DropdownButtonFormField<String>(
                      value: _selectedDistrict,
                      decoration: const InputDecoration(labelText: "İlçe"),
                      items: districts.map((d) {
                        return DropdownMenuItem(value: d, child: Text(d));
                      }).toList>,
                      onChanged: (val) {
                        if (val != null) setState(() => _selectedDistrict = val);
                      },
                    ),
                    const SizedBox(height: 14),
                    DropdownButtonFormField<bool?>(
                      value: _cksStatus,
                      decoration: const InputDecoration(labelText: "Çiftçi Kayıt Sistemi (ÇKS)"),
                      items: const [
                        DropdownMenuItem(value: true, child: Text("✅ ÇKS Kaydı Aktif (2026)")),
                        DropdownMenuItem(value: false, child: Text("❌ ÇKS Kaydı Yok")),
                        DropdownMenuItem(value: null, child: Text("⚠️ Bilinmiyor / Eksik Beyan")),
                      ],
                      onChanged: (val) => setState(() => _cksStatus = val),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),

            // Bölüm 2: Parsel Bilgisi (P16.3)
            const Row(
              children: [
                Icon(Icons.landscape_rounded, color: AppTheme.primaryGreen),
                SizedBox(width: 8),
                Text("Parsel & Ürün Bilgisi", style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 12),
            Card(
              margin: EdgeInsets.zero,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    DropdownButtonFormField<String>(
                      value: _selectedCrop,
                      decoration: const InputDecoration(labelText: "Ekilmesi Planlanan Ürün"),
                      items: _crops.map((c) {
                        return DropdownMenuItem(value: c, child: Text(c));
                      }).toList(),
                      onChanged: (val) {
                        if (val != null) setState(() => _selectedCrop = val);
                      },
                    ),
                    const SizedBox(height: 14),
                    TextFormField(
                      controller: _areaController,
                      decoration: const InputDecoration(
                        labelText: "Parsel Büyüklüğü (Dekar)",
                        suffixText: "da",
                      ),
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      validator: (val) {
                        if (val == null || val.trim().isEmpty) return "Alan giriniz";
                        final d = double.tryParse(val);
                        if (d == null || d <= 0) return "Geçerli pozitif bir alan giriniz";
                        return null;
                      },
                    ),
                    const SizedBox(height: 14),
                    DropdownButtonFormField<String>(
                      value: _irrigation,
                      decoration: const InputDecoration(labelText: "Sulama Durumu"),
                      items: const [
                        DropdownMenuItem(value: "IRRIGATED", child: Text("💧 Sulu Tarım")),
                        DropdownMenuItem(value: "DRY", child: Text("☀️ Kuru Tarım")),
                        DropdownMenuItem(value: "UNKNOWN", child: Text("❓ Bilmiyorum / Belirsiz")),
                      ],
                      onChanged: (val) {
                        if (val != null) setState(() => _irrigation = val);
                      },
                    ),
                    const SizedBox(height: 14),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text("Sertifikalı Tohum Kullanımı", style: TextStyle(fontSize: 14)),
                      subtitle: const Text("Yetkili bayiden faturalı tohum temini", style: TextStyle(fontSize: 12)),
                      value: _seedCert,
                      activeColor: AppTheme.primaryGreen,
                      onChanged: (val) => setState(() => _seedCert = val),
                    ),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text("Sertifikalı Fidan Kullanımı", style: TextStyle(fontSize: 14)),
                      subtitle: const Text("Fidan sertifikası temini", style: TextStyle(fontSize: 12)),
                      value: _saplingCert,
                      activeColor: AppTheme.primaryGreen,
                      onChanged: (val) => setState(() => _saplingCert = val),
                    ),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text("Kapama Meyve Bahçesi Tesisi", style: TextStyle(fontSize: 14)),
                      subtitle: const Text("En az 5 da büyüklüğünde tek tür kapama bahçe", style: TextStyle(fontSize: 12)),
                      value: _isClosedOrchard,
                      activeColor: AppTheme.primaryGreen,
                      onChanged: (val) => setState(() => _isClosedOrchard = val),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Sorgulama Butonu
            ElevatedButton.icon(
              onPressed: provider.evalState == ViewState.loading ? null : _submit,
              icon: provider.evalState == ViewState.loading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                    )
                  : const Icon(Icons.calculate_rounded),
              label: Text(
                provider.evalState == ViewState.loading
                    ? "Hesaplanıyor..."
                    : "Desteklerimi Değerlendir & Hesapla",
              ),
            ),
            const SizedBox(height: 30),
          ],
        ),
      ),
    );
  }
}
