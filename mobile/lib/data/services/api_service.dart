// Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
// ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../../core/constants/api_constants.dart';
import '../models/farmer_parcel_models.dart';
import '../models/support_models.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;

  ApiException(this.message, [this.statusCode]);

  @override
  String toString() => "ApiException: $message (Kod: $statusCode)";
}

class TarimDestekApiService {
  final http.Client _client;
  final Duration timeout;

  TarimDestekApiService({http.Client? client, this.timeout = const Duration(seconds: 10)})
      : _client = client ?? http.Client();

  Uri _uri(String endpoint, [Map<String, dynamic>? queryParameters]) {
    final base = ApiConstants.baseUrl;
    return Uri.parse('$base$endpoint').replace(queryParameters: queryParameters);
  }

  Future<bool> checkHealth() async {
    try {
      final response = await _client.get(_uri(ApiConstants.healthEndpoint)).timeout(timeout);
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<List<SupportProgramDTO>> getSupports({int year = 2026}) async {
    try {
      final response = await _client
          .get(_uri(ApiConstants.supportsEndpoint, {'year': year.toString()}))
          .timeout(timeout);

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
        return data.map((json) => SupportProgramDTO.fromJson(json)).toList();
      } else {
        throw ApiException("Destek programları listelenemedi", response.statusCode);
      }
    } on SocketException {
      throw ApiException("Sunucuya bağlanılamadı. Lütfen internetinizi ve sunucu adresini kontrol edin.");
    } on TimeoutException {
      throw ApiException("İstek zaman aşımına uğradı.");
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException("Beklenmeyen hata: $e");
    }
  }

  Future<FullEvaluationResponse> evaluateFull(FarmerProfile farmer, Parcel parcel) async {
    try {
      final body = jsonEncode({
        'farmer': farmer.toJson(),
        'parcel': parcel.toJson(),
      });

      final response = await _client
          .post(
            _uri(ApiConstants.evaluateFullEndpoint),
            headers: {'Content-Type': 'application/json'},
            body: body,
          )
          .timeout(timeout);

      if (response.statusCode == 200) {
        final Map<String, dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
        return FullEvaluationResponse.fromJson(data);
      } else {
        String msg = "Değerlendirme yapılamadı";
        try {
          final errJson = jsonDecode(utf8.decode(response.bodyBytes));
          if (errJson['message'] != null) msg = errJson['message'];
        } catch (_) {}
        throw ApiException(msg, response.statusCode);
      }
    } on SocketException {
      throw ApiException("Sunucu bağlantısı sağlanamadı. Backend servisinin açık olduğunu doğrulayın.");
    } on TimeoutException {
      throw ApiException("Değerlendirme isteği zaman aşımına uğradı.");
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException("Değerlendirme hatası: $e");
    }
  }

  Future<AskQuestionResponse> askQuestion(String question, {int topK = 3}) async {
    try {
      final body = jsonEncode({
        'question': question,
        'top_k': topK,
      });

      final response = await _client
          .post(
            _uri(ApiConstants.askEndpoint),
            headers: {'Content-Type': 'application/json'},
            body: body,
          )
          .timeout(timeout);

      if (response.statusCode == 200) {
        final Map<String, dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
        return AskQuestionResponse.fromJson(data);
      } else {
        throw ApiException("Mevzuat sorgulanamadı", response.statusCode);
      }
    } on SocketException {
      throw ApiException("Sunucu bağlantısı sağlanamadı.");
    } on TimeoutException {
      throw ApiException("Zaman aşımı oluştu.");
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException("Mevzuat arama hatası: $e");
    }
  }
}
