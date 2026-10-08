// Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
// ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:tarim_destek_rag_mobile/data/models/farmer_parcel_models.dart';
import 'package:tarim_destek_rag_mobile/data/services/api_service.dart';

// Basit test HTTP Client Mock'u
class MockHttpClient extends http.BaseClient {
  final int statusCode;
  final String responseBody;

  MockHttpClient({required this.statusCode, required this.responseBody});

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final bytes = utf8.encode(responseBody);
    return http.StreamedResponse(
      Stream.value(bytes),
      statusCode,
      headers: {'content-type': 'application/json'},
    );
  }
}

void main() {
  group('TarimDestekApiService Tests', () {
    test('checkHealth returns true on 200', () async {
      final mock = MockHttpClient(
        statusCode: 200,
        responseBody: '{"status": "ok", "version": "1.0.0"}',
      );
      final service = TarimDestekApiService(client: mock);
      final isHealthy = await service.checkHealth();
      expect(isHealthy, true);
    });

    test('getSupports parses list successfully', () async {
      final mock = MockHttpClient(
        statusCode: 200,
        responseBody: '[{"id": "BASIC_2026", "name": "Temel Destek", "year": 2026, "active": true, "description": "Mazot"}]',
      );
      final service = TarimDestekApiService(client: mock);
      final list = await service.getSupports();
      expect(list.length, 1);
      expect(list[0].id, 'BASIC_2026');
      expect(list[0].name, 'Temel Destek');
    });

    test('evaluateFull throws ApiException on 400 error', () async {
      final mock = MockHttpClient(
        statusCode: 400,
        responseBody: '{"code": "VAL_ERROR", "message": "Geçersiz parsel verisi"}',
      );
      final service = TarimDestekApiService(client: mock);
      final farmer = FarmerProfile(province: "KONYA", district: "KARATAY");
      final parcel = Parcel(crop: "BUĞDAY", areaDa: 10.0);

      expect(
        () => service.evaluateFull(farmer, parcel),
        throwsA(isA<ApiException>()),
      );
    });
  });
}
