// Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
// ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

import 'farmer_parcel_models.dart';

class CitationDetail {
  final String sourceId;
  final String title;
  final String section;
  final int year;
  final String snippet;
  final String? url;
  final String verificationStatus;
  final String? highlightedPdfUrl;
  final String? documentSha256;
  final int? pageNumber;

  CitationDetail({
    required this.sourceId,
    required this.title,
    required this.section,
    required this.year,
    required this.snippet,
    this.url,
    this.verificationStatus = 'UNVERIFIED_EXPLANATION',
    this.highlightedPdfUrl,
    this.documentSha256,
    this.pageNumber,
  });

  /// UI route validation supplements server-side original-SHA verification.
  String? verifiedHighlightPath({String? supportId}) {
    final digest = documentSha256;
    final link = highlightedPdfUrl;
    if (digest == null ||
        !RegExp(r'^[a-f0-9]{64}$').hasMatch(digest) ||
        link == null ||
        !link.startsWith('/evidence/highlight/')) {
      return null;
    }
    final uri = Uri.tryParse(link);
    if (uri == null || uri.hasScheme || uri.hasAuthority ||
        uri.path.startsWith('//')) {
      return null;
    }
    final query = uri.queryParametersAll;
    if (query.values.any((values) => values.length != 1)) return null;
    final value = uri.queryParameters;
    if (verificationStatus == 'ORIGINAL_HTML_TEXT_LOCATED_PENDING_LEGAL_REVIEW') {
      if (uri.path != '/evidence/highlight/html/$digest' ||
          query.length != 1 || !query.containsKey('support_id') ||
          uri.fragment != 'tarim-evidence-highlight' ||
          (value['support_id'] ?? '').isEmpty ||
          (supportId != null && value['support_id'] != supportId)) {
        return null;
      }
    } else if (verificationStatus == 'VISUAL_SOURCE_LOCATED_PENDING_SECOND_REVIEW') {
      if (pageNumber == null || pageNumber! < 1 ||
          uri.path != '/evidence/highlight/visual/$digest' ||
          query.length != 1 || !query.containsKey('support_id') ||
          uri.fragment != 'page=$pageNumber' ||
          (value['support_id'] ?? '').isEmpty ||
          (supportId != null && value['support_id'] != supportId)) {
        return null;
      }
    } else if (verificationStatus == 'EXACT_PDF_MATCH_PENDING_LEGAL_REVIEW') {
      if (pageNumber == null || pageNumber! < 1 ||
          uri.path != '/evidence/highlight/$digest' ||
          query.length != 2 || !query.containsKey('page') ||
          !query.containsKey('quote') || uri.fragment.isNotEmpty ||
          value['page'] != pageNumber.toString() ||
          value['quote'] != snippet || snippet.isEmpty) {
        return null;
      }
    } else {
      return null;
    }
    return link;
  }

  factory CitationDetail.fromJson(Map<String, dynamic> json) => CitationDetail(
        sourceId: json['source_id'] ?? '',
        title: json['title'] ?? '',
        section: json['section'] ?? '',
        year: json['year'] ?? 2026,
        snippet: json['snippet'] ?? '',
        url: json['url'],
        verificationStatus: json['verification_status'] ?? 'UNVERIFIED_EXPLANATION',
        highlightedPdfUrl: json['highlighted_pdf_url'],
        documentSha256: json['document_sha256'],
        pageNumber: json['page_number'] is int ? json['page_number'] as int : null,
      );
}

class RuleResult {
  final String ruleId;
  final String supportId;
  final String supportName;
  final String status; // ELIGIBLE, NOT_ELIGIBLE, REVIEW
  final List<String> passedChecks;
  final List<String> failedChecks;
  final List<String> missingFields;
  final List<String> trace;

  RuleResult({
    required this.ruleId,
    required this.supportId,
    required this.supportName,
    required this.status,
    required this.passedChecks,
    required this.failedChecks,
    required this.missingFields,
    required this.trace,
  });

  factory RuleResult.fromJson(Map<String, dynamic> json) => RuleResult(
        ruleId: json['rule_id'] ?? '',
        supportId: json['support_id'] ?? '',
        supportName: json['support_name'] ?? '',
        status: json['status'] ?? 'REVIEW',
        passedChecks: List<String>.from(json['passed_checks'] ?? []),
        failedChecks: List<String>.from(json['failed_checks'] ?? []),
        missingFields: List<String>.from(json['missing_fields'] ?? []),
        trace: List<String>.from(json['trace'] ?? []),
      );
}

class CalculationResult {
  final String ruleId;
  final String supportId;
  final String supportName;
  final String status;
  final double? estimatedAmount;
  final double? unitAmount;
  final String formula;

  CalculationResult({
    required this.ruleId,
    required this.supportId,
    required this.supportName,
    required this.status,
    this.estimatedAmount,
    this.unitAmount,
    required this.formula,
  });

  factory CalculationResult.fromJson(Map<String, dynamic> json) => CalculationResult(
        ruleId: json['rule_id'] ?? '',
        supportId: json['support_id'] ?? '',
        supportName: json['support_name'] ?? '',
        status: json['status'] ?? 'REVIEW',
        estimatedAmount: json['estimated_amount'] != null
            ? double.tryParse(json['estimated_amount'].toString())
            : null,
        unitAmount: json['unit_amount'] != null
            ? double.tryParse(json['unit_amount'].toString())
            : null,
        formula: json['formula'] ?? '',
      );
}

class ExplanationResult {
  final String supportId;
  final String supportName;
  final String status;
  final String statusLabelTr;
  final String summaryTr;
  final String detailedReasonTr;
  final List<String> missingRequirementsTr;
  final List<String> nextActionsTr;
  final List<CitationDetail> citations;

  ExplanationResult({
    required this.supportId,
    required this.supportName,
    required this.status,
    required this.statusLabelTr,
    required this.summaryTr,
    required this.detailedReasonTr,
    required this.missingRequirementsTr,
    required this.nextActionsTr,
    required this.citations,
  });

  factory ExplanationResult.fromJson(Map<String, dynamic> json) => ExplanationResult(
        supportId: json['support_id'] ?? '',
        supportName: json['support_name'] ?? '',
        status: json['status'] ?? 'REVIEW',
        statusLabelTr: json['status_label_tr'] ?? '',
        summaryTr: json['summary_tr'] ?? '',
        detailedReasonTr: json['detailed_reason_tr'] ?? '',
        missingRequirementsTr: List<String>.from(json['missing_requirements_tr'] ?? []),
        nextActionsTr: List<String>.from(json['next_actions_tr'] ?? []),
        citations: (json['citations'] as List<dynamic>? ?? [])
            .map((c) => CitationDetail.fromJson(c as Map<String, dynamic>))
            .toList(),
      );
}

class FullEvaluationResponse {
  final FarmerProfile farmer;
  final Parcel parcel;
  final List<RuleResult> rules;
  final List<CalculationResult> calculations;
  final List<ExplanationResult> explanations;
  final double totalEstimatedAmount;

  FullEvaluationResponse({
    required this.farmer,
    required this.parcel,
    required this.rules,
    required this.calculations,
    required this.explanations,
    required this.totalEstimatedAmount,
  });

  factory FullEvaluationResponse.fromJson(Map<String, dynamic> json) => FullEvaluationResponse(
        farmer: FarmerProfile.fromJson(json['farmer']),
        parcel: Parcel.fromJson(json['parcel']),
        rules: (json['rules'] as List<dynamic>? ?? [])
            .map((r) => RuleResult.fromJson(r as Map<String, dynamic>))
            .toList(),
        calculations: (json['calculations'] as List<dynamic>? ?? [])
            .map((c) => CalculationResult.fromJson(c as Map<String, dynamic>))
            .toList(),
        explanations: (json['explanations'] as List<dynamic>? ?? [])
            .map((e) => ExplanationResult.fromJson(e as Map<String, dynamic>))
            .toList(),
        totalEstimatedAmount:
            double.tryParse(json['total_estimated_amount']?.toString() ?? '0.0') ?? 0.0,
      );
}

class SupportProgramDTO {
  final String id;
  final String name;
  final int year;
  final bool active;
  final String description;
  final String? applicationStart;
  final String? applicationEnd;

  SupportProgramDTO({
    required this.id,
    required this.name,
    required this.year,
    required this.active,
    required this.description,
    this.applicationStart,
    this.applicationEnd,
  });

  factory SupportProgramDTO.fromJson(Map<String, dynamic> json) => SupportProgramDTO(
        id: json['id'] ?? '',
        name: json['name'] ?? '',
        year: json['year'] ?? 2026,
        active: json['active'] ?? true,
        description: json['description'] ?? '',
        applicationStart: json['application_start'],
        applicationEnd: json['application_end'],
      );
}

class AskQuestionResponse {
  final String question;
  final String summaryAnswerTr;
  final List<CitationDetail> matchedChunks;
  final List<String> sourceTitles;

  AskQuestionResponse({
    required this.question,
    required this.summaryAnswerTr,
    required this.matchedChunks,
    required this.sourceTitles,
  });

  factory AskQuestionResponse.fromJson(Map<String, dynamic> json) => AskQuestionResponse(
        question: json['question'] ?? '',
        summaryAnswerTr: json['summary_answer_tr'] ?? '',
        matchedChunks: (json['matched_chunks'] as List<dynamic>? ?? [])
            .map((c) => CitationDetail.fromJson(c as Map<String, dynamic>))
            .toList(),
        sourceTitles: List<String>.from(json['source_titles'] ?? []),
      );
}
