// Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
// ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

import '../../data/models/farmer_parcel_models.dart';
import '../../data/models/support_models.dart';
import '../../data/services/api_service.dart';

/// Clean Architecture Domain Katmanı: Çiftçi ve parsel değerlendirme UseCase'i.
class EvaluateSupportUseCase {
  final ApiService _apiService;

  EvaluateSupportUseCase([ApiService? apiService])
      : _apiService = apiService ?? ApiService();

  Future<FullEvaluationResponse> execute({
    required FarmerProfile farmer,
    required Parcel parcel,
  }) async {
    return await _apiService.evaluateFull(farmer: farmer, parcel: parcel);
  }
}
