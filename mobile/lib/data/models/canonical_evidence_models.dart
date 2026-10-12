// F10 — canonical claim/source evidence DTO.
// Source location does NOT mean year validity, farmer eligibility or payment.
// No fuzzy FAQ/RAG citation can be promoted to an original-source link.

class CanonicalClaimEvidence {
  final String? claimId;
  final String? evidenceId;
  final String? ruleId;
  final String? supportId;
  final int? productionYear;
  final String? claimText;
  final String? claimField;
  final String sourceLocationStatus;
  final String temporalLegalStatus;
  final String paymentStatus;
  final String finalAcceptance;
  final Map<String, dynamic>? source;
  final Map<String, dynamic> amendmentChain;

  const CanonicalClaimEvidence({
    this.claimId,
    this.evidenceId,
    this.ruleId,
    this.supportId,
    this.productionYear,
    this.claimText,
    this.claimField,
    this.source,
    this.amendmentChain = const {},
    required this.sourceLocationStatus,
    required this.temporalLegalStatus,
    required this.paymentStatus,
    required this.finalAcceptance,
  });

  static final RegExp _claimPattern = RegExp(r'^[a-f0-9]{24}$');
  static final RegExp _proofPattern = RegExp(r'^TRAG-EV1-[a-f0-9]{32}$');
  static final RegExp _shaPattern = RegExp(r'^[a-f0-9]{64}$');
  static const _trustedHosts = {
    'resmigazete.gov.tr',
    'www.resmigazete.gov.tr',
    'tarimorman.gov.tr',
    'www.tarimorman.gov.tr',
  };

  factory CanonicalClaimEvidence.fromJson(Map<String, dynamic> json) {
    if (json['schema_version'] != 1 ||
        json['contract_type'] != 'SINGLE_CLAIM_EVIDENCE') {
      throw const FormatException('Unsupported canonical evidence schema');
    }
    final claimId = json['claim_id'];
    final proofId = json['evidence_id'];
    final rawSource = json['source'];
    final validClaim = claimId is String && _claimPattern.hasMatch(claimId);
    final validId = proofId is String && _proofPattern.hasMatch(proofId);
    final located =
        json['source_location_status'] == 'ORIGINAL_HTML_SPAN_LOCATED_NORMATIVE_ONLY';
    Map<String, dynamic>? exactSource;
    if (validClaim && validId && located &&
        rawSource is Map<String, dynamic> &&
        rawSource['format'] == 'html' &&
        rawSource['source_sha256'] is String &&
        _shaPattern.hasMatch(rawSource['source_sha256']) &&
        rawSource['span_id'] is String &&
        (rawSource['span_id'] as String).isNotEmpty &&
        rawSource['exact_quote'] is String &&
        (rawSource['exact_quote'] as String).isNotEmpty) {
      final url = Uri.tryParse(rawSource['original_url']?.toString() ?? '');
      if (url != null && url.scheme == 'https' &&
          _trustedHosts.contains(url.host) && url.userInfo.isEmpty) {
        exactSource = Map<String, dynamic>.unmodifiable(rawSource);
      }
    }
    return CanonicalClaimEvidence(
      claimId: validClaim ? claimId : null,
      evidenceId: exactSource == null ? null : proofId,
      ruleId: json['rule_id'] is String ? json['rule_id'] : null,
      supportId: json['support_id'] is String ? json['support_id'] : null,
      productionYear: json['production_year'] is int
          ? json['production_year'] : null,
      claimText: json['claim_text'] is String ? json['claim_text'] : null,
      claimField: json['claim_field'] is String ? json['claim_field'] : null,
      source: exactSource,
      amendmentChain: json['amendment_chain'] is Map<String, dynamic>
          ? Map<String, dynamic>.unmodifiable(json['amendment_chain'])
          : const {},
      sourceLocationStatus: exactSource != null
          ? 'ORIGINAL_HTML_SPAN_LOCATED_NORMATIVE_ONLY' : 'HOLD',
      temporalLegalStatus: 'HOLD',
      paymentStatus: 'HOLD',
      finalAcceptance: 'HOLD',
    );
  }

  bool get hasVerifiableSourceLocation => source != null;
  Uri? get originalSourceUri => hasVerifiableSourceLocation
      ? Uri.tryParse(source!['original_url'] as String) : null;
  bool get paymentApproved => false; // separate signed legal gate, not supplied
}

class CanonicalEvidenceIndex {
  final int? productionYear;
  final List<CanonicalClaimEvidence> claims;
  final int claimCount;
  final bool legalApproval;
  final bool paymentApproval;
  final String acceptance;

  const CanonicalEvidenceIndex({
    this.productionYear,
    required this.claims,
    required this.claimCount,
    this.legalApproval = false,
    this.paymentApproval = false,
    this.acceptance = 'HOLD',
  });

  factory CanonicalEvidenceIndex.fromJson(Map<String, dynamic> json) {
    if (json['schema_version'] != 1 ||
        json['contract_type'] != 'EVALUATION_EVIDENCE_INDEX') {
      throw const FormatException('Unknown or incompatible evidence index');
    }
    final raw = json['claims'];
    if (raw is! List || raw.length > 2000) {
      throw const FormatException('Invalid evidence claim collection');
    }
    return CanonicalEvidenceIndex(
      productionYear: json['production_year'] is int
          ? json['production_year'] : null,
      claimCount: json['claim_count'] is int ? json['claim_count'] : -1,
      claims: List.unmodifiable(raw.map((item) {
        if (item is! Map<String, dynamic>) {
          throw const FormatException('Invalid single claim evidence');
        }
        return CanonicalClaimEvidence.fromJson(item);
      })),
      // No remote "true" flags may promote this feature to legal or payment PASS.
      legalApproval: false,
      paymentApproval: false,
      acceptance: 'HOLD',
    );
  }
}
