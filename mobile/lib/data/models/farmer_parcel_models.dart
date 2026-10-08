// Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
// ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

class FarmerProfile {
  final String province;
  final String district;
  final bool? cksStatus;

  FarmerProfile({
    required this.province,
    required this.district,
    this.cksStatus,
  });

  Map<String, dynamic> toJson() => {
        'province': province,
        'district': district,
        'cks_status': cksStatus,
      };

  factory FarmerProfile.fromJson(Map<String, dynamic> json) => FarmerProfile(
        province: json['province'] ?? '',
        district: json['district'] ?? '',
        cksStatus: json['cks_status'],
      );
}

class Parcel {
  final String crop;
  final double areaDa;
  final int productionYear;
  final bool? seedCertificateAvailable;
  final bool? saplingCertificateAvailable;
  final bool? isClosedOrchard;
  final String? irrigation;

  Parcel({
    required this.crop,
    required this.areaDa,
    this.productionYear = 2026,
    this.seedCertificateAvailable,
    this.saplingCertificateAvailable,
    this.isClosedOrchard,
    this.irrigation,
  });

  Map<String, dynamic> toJson() => {
        'crop': crop,
        'area_da': areaDa.toStringAsFixed(2),
        'production_year': productionYear,
        'seed_certificate_available': seedCertificateAvailable,
        'sapling_certificate_available': saplingCertificateAvailable,
        if (isClosedOrchard != null) 'is_closed_orchard': isClosedOrchard,
        if (irrigation != null) 'irrigation': irrigation,
      };

  factory Parcel.fromJson(Map<String, dynamic> json) => Parcel(
        crop: json['crop'] ?? '',
        areaDa: double.tryParse(json['area_da']?.toString() ?? '0.0') ?? 0.0,
        productionYear: json['production_year'] ?? 2026,
        seedCertificateAvailable: json['seed_certificate_available'],
        saplingCertificateAvailable: json['sapling_certificate_available'],
        isClosedOrchard: json['is_closed_orchard'],
        irrigation: json['irrigation'],
      );
}
