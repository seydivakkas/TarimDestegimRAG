// Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
// ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

import 'package:flutter/foundation.dart';

import '../../data/models/farmer_parcel_models.dart';
import '../../data/models/support_models.dart';
import '../../data/services/api_service.dart';

enum ViewState { initial, loading, success, error }

class DestekProvider extends ChangeNotifier {
  final TarimDestekApiService apiService;

  DestekProvider({TarimDestekApiService? service})
      : apiService = service ?? TarimDestekApiService();

  ViewState _evalState = ViewState.initial;
  ViewState get evalState => _evalState;

  FullEvaluationResponse? _evaluationResult;
  FullEvaluationResponse? get evaluationResult => _evaluationResult;

  String? _errorMessage;
  String? get errorMessage => _errorMessage;

  // Ask RAG State
  ViewState _askState = ViewState.initial;
  ViewState get askState => _askState;

  AskQuestionResponse? _askResult;
  AskQuestionResponse? get askResult => _askResult;

  String? _askError;
  String? get askError => _askError;

  // Destek Programları
  List<SupportProgramDTO> _programs = [];
  List<SupportProgramDTO> get programs => _programs;

  Future<void> evaluate(FarmerProfile farmer, Parcel parcel) async {
    _evalState = ViewState.loading;
    _errorMessage = null;
    notifyListeners();

    try {
      _evaluationResult = await apiService.evaluateFull(farmer, parcel);
      _evalState = ViewState.success;
    } catch (e) {
      _errorMessage = e.toString();
      _evalState = ViewState.error;
    } finally {
      notifyListeners();
    }
  }

  Future<void> askRagQuestion(String query) async {
    if (query.trim().isEmpty) return;

    _askState = ViewState.loading;
    _askError = null;
    notifyListeners();

    try {
      _askResult = await apiService.askQuestion(query);
      _askState = ViewState.success;
    } catch (e) {
      _askError = e.toString();
      _askState = ViewState.error;
    } finally {
      notifyListeners();
    }
  }

  Future<void> loadPrograms() async {
    try {
      _programs = await apiService.getSupports();
      notifyListeners();
    } catch (_) {}
  }
}
