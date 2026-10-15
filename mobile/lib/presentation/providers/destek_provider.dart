// Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
// ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../../data/models/farmer_parcel_models.dart';
import '../../data/models/support_models.dart';
import '../../data/models/canonical_evidence_models.dart';
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

  CanonicalEvidenceIndex? _evidenceIndex;
  CanonicalEvidenceIndex? get evidenceIndex => _evidenceIndex;
  ViewState _evidenceState = ViewState.initial;
  ViewState get evidenceState => _evidenceState;
  String? _evidenceError;
  String? get evidenceError => _evidenceError;

  bool _indexMatchesEvaluation(
      FullEvaluationResponse evaluation, CanonicalEvidenceIndex index) {
    if (index.productionYear != evaluation.parcel.productionYear) return false;
    final local = <String>[];
    for (final rule in evaluation.rules) {
      for (final text in rule.passedChecks) {
        local.add(jsonEncode([rule.ruleId, rule.supportId, 'passed_checks', text]));
      }
      for (final text in rule.failedChecks) {
        local.add(jsonEncode([rule.ruleId, rule.supportId, 'failed_checks', text]));
      }
      for (final text in rule.missingFields) {
        local.add(jsonEncode([rule.ruleId, rule.supportId, 'missing_fields', text]));
      }
    }
    if (index.claimCount != local.length ||
        index.claims.length != local.length ||
        local.toSet().length != local.length) {
      return false;
    }
    final received = index.claims.map((c) => jsonEncode([
      c.ruleId, c.supportId, c.claimField, c.claimText,
    ])).toSet();
    return received.length == local.length &&
        received.containsAll(local);
  }

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
    _evidenceState = ViewState.initial;
    _evidenceIndex = null;
    _evidenceError = null;
    _evaluationResult = null;
    _errorMessage = null;
    notifyListeners();

    try {
      _evaluationResult = await apiService.evaluateFull(farmer, parcel);
      _evalState = ViewState.success;
      _evidenceState = ViewState.loading;
      notifyListeners();
      try {
        final contract = await apiService.getEvaluationEvidence(farmer, parcel);
        if (!_indexMatchesEvaluation(_evaluationResult!, contract)) {
          throw StateError('Kanıt değerlendirmesi farklı; yeniden eşleşme gerekli');
        }
        _evidenceIndex = contract;
        _evidenceState = ViewState.success;
      } catch (e) {
        // A stale or unavailable evidence index never prevents a separate
        // preliminary calculation but all source citations remain HOLD.
        _evidenceIndex = null;
        _evidenceState = ViewState.error;
        _evidenceError = 'Kaynak zinciri: HOLD — $e';
      }
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
