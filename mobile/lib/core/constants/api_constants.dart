// Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
// ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

class ApiConstants {
  // Android emülatörü için varsayılan loopback 10.0.2.2, iOS ve Masaüstü için 127.0.0.1
  static const String defaultAndroidEmulatorUrl = "http://10.0.2.2:8000";
  static const String defaultLocalhostUrl = "http://127.0.0.1:8000";

  // Değiştirilebilir API taban adresi
  static String baseUrl = defaultLocalhostUrl;

  static const String healthEndpoint = "/health";
  static const String supportsEndpoint = "/supports";
  static const String sourcesEndpoint = "/sources";
  static const String eligibilityEndpoint = "/eligibility";
  static const String calculateEndpoint = "/calculate";
  static const String evaluateFullEndpoint = "/evaluate";
  static const String askEndpoint = "/ask";
}
