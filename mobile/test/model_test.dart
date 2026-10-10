// Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
// ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:tarim_destek_rag_mobile/data/models/farmer_parcel_models.dart';
import 'package:tarim_destek_rag_mobile/data/models/support_models.dart';

void main() {
  group('Farmer & Parcel Models', () {
    test('FarmerProfile serialization and deserialization', () {
      final farmer = FarmerProfile(
        province: 'KONYA',
        district: 'KARATAY',
        cksStatus: true,
      );

      final json = farmer.toJson();
      expect(json['province'], 'KONYA');
      expect(json['district'], 'KARATAY');
      expect(json['cks_status'], true);

      final fromJson = FarmerProfile.fromJson(json);
      expect(fromJson.province, 'KONYA');
      expect(fromJson.district, 'KARATAY');
      expect(fromJson.cksStatus, true);
    });

    test('Parcel serialization and decimal area parsing', () {
      final parcel = Parcel(
        crop: 'BUĞDAY',
        areaDa: 12.4,
        productionYear: 2026,
        seedCertificateAvailable: true,
      );

      final json = parcel.toJson();
      expect(json['crop'], 'BUĞDAY');
      expect(json['area_da'], '12.40');
      expect(json['seed_certificate_available'], true);

      final fromJson = Parcel.fromJson(json);
      expect(fromJson.crop, 'BUĞDAY');
      expect(fromJson.areaDa, 12.4);
      expect(fromJson.seedCertificateAvailable, true);
    });
  });

  group('FullEvaluationResponse JSON Parsing', () {
    test('parses realistic FastAPI evaluate response', () {
      const mockJsonStr = '''
      {
        "farmer": {
          "province": "KONYA",
          "district": "KARATAY",
          "cks_status": true
        },
        "parcel": {
          "crop": "BUĞDAY",
          "area_da": "10.00",
          "production_year": 2026,
          "seed_certificate_available": null,
          "sapling_certificate_available": null
        },
        "rules": [
          {
            "rule_id": "RULE_BASIC_SUPPORT_2026",
            "support_id": "BASIC_SUPPORT_2026",
            "support_name": "Temel Destek",
            "status": "ELIGIBLE",
            "passed_checks": ["ÇKS aktif"],
            "failed_checks": [],
            "missing_fields": [],
            "trace": ["Kural başarıyla çalıştı"]
          }
        ],
        "calculations": [
          {
            "rule_id": "RULE_BASIC_SUPPORT_2026",
            "support_id": "BASIC_SUPPORT_2026",
            "support_name": "Temel Destek",
            "status": "ELIGIBLE",
            "estimated_amount": "4650.00",
            "unit_amount": "465.00",
            "formula": "10.0 da x 465.00 TL/da"
          }
        ],
        "explanations": [
          {
            "support_id": "BASIC_SUPPORT_2026",
            "support_name": "Temel Destek",
            "status": "ELIGIBLE",
            "status_label_tr": "Uygun görünüyor",
            "summary_tr": "4,650.00 TL tahmini temel destek.",
            "detailed_reason_tr": "Şartlar sağlandı.",
            "missing_requirements_tr": [],
            "next_actions_tr": ["Başvuruyu tamamlayınız."],
            "citations": [
              {
                "source_id": "RG-2026-BITKISEL",
                "title": "2026 Kararı",
                "section": "Madde 1",
                "year": 2026,
                "snippet": "Metin"
              }
            ]
          }
        ],
        "total_estimated_amount": "4650.00"
      }
      ''';

      final Map<String, dynamic> data = jsonDecode(mockJsonStr);
      final response = FullEvaluationResponse.fromJson(data);

      expect(response.farmer.province, 'KONYA');
      expect(response.totalEstimatedAmount, 4650.00);
      expect(response.rules.length, 1);
      expect(response.rules[0].status, 'ELIGIBLE');
      expect(response.calculations.length, 1);
      expect(response.calculations[0].estimatedAmount, 4650.00);
      expect(response.explanations.length, 1);
      expect(response.explanations[0].citations.length, 1);
      expect(response.explanations[0].citations[0].sourceId, 'RG-2026-BITKISEL');
    });
  });
  test('mobile proof route requires exact hash, page and quote', () {
    const sha = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';
    final exact = CitationDetail(
      sourceId: 'RG_DECISION_8859', title: 'Özgün PDF', section: 'MADDE 2',
      year: 2026, snippet: 'Doğru birebir cümle',
      verificationStatus: 'EXACT_PDF_MATCH_PENDING_LEGAL_REVIEW',
      documentSha256: sha, pageNumber: 2,
      highlightedPdfUrl: '/evidence/highlight/$sha?page=2&quote=Do%C4%9Fru%20birebir%20c%C3%BCmle',
    );
    expect(exact.verifiedHighlightPath(), isNotNull);
    final forged = CitationDetail(
      sourceId: exact.sourceId, title: exact.title, section: exact.section,
      year: exact.year, snippet: exact.snippet,
      verificationStatus: exact.verificationStatus,
      documentSha256: sha, pageNumber: 2,
      highlightedPdfUrl: '/evidence/highlight/$sha?page=3&quote=wrong',
    );
    expect(forged.verifiedHighlightPath(), isNull);
    final unverified = CitationDetail(
      sourceId: exact.sourceId, title: exact.title,
      section: exact.section, year: exact.year, snippet: exact.snippet,
    );
    expect(unverified.verifiedHighlightPath(), isNull);
  });

}
