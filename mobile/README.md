# TarımDestekRAG — Mobil İstemci (Flutter)

Türkiye 2026 Bitkisel Üretim Destekleri için Çiftçi ve Parsel Ön Değerlendirme Mobil Uygulaması.

---

## 📱 Özellikler

1. **Çiftçi & Parsel Girişi:**
   - 81 il ve ilçe seçimi, ÇKS aktif/pasif/bilinmiyor tri-state desteği.
   - 2026 üretim yılı, parsel alanı (da), sulama türü (`IRRIGATED`, `DRY`, `UNKNOWN`).
   - Sertifikalı tohum/fidan fatura ve kapama bahçe beyanları.

2. **Destek Değerlendirme & Hak Ediş:**
   - FastAPI `/evaluate` uç noktası ile uçtan uca deterministik kural motoru entegrasyonu.
   - Ön değerlendirme kartları (`ELIGIBLE`, `REVIEW`, `NOT_ELIGIBLE`), hesaplanamayan tutar (`Hesaplanmadı`) ve detay formül dökümü.
   - Resmî Gazete ve BÜGEM dayanak atıfları ile modal diyalog gösterimi.

3. **Mevzuat Asistanı (Sıfır LLM):**
   - Doğal dil ile mevzuat sorgulama (`/ask`).
   - Yasal madde alıntıları ve kanıt zinciri.

---

## 🛠️ Windows Kurulum ve Çalıştırma

### Gereksinimler
- [Flutter SDK](https://flutter.dev) (v3.2.0 veya üzeri)
- Dart SDK (v3.2.0 veya üzeri)
- Android Studio / Android Emulator veya fiziksel cihaz

### 1. Bağımlılıkları Yükleme
```powershell
cd mobile
flutter pub get
```

### 2. Statik Analiz ve Testleri Çalıştırma
```powershell
flutter analyze
flutter test
```

### 3. Arka Uç Bağlantısı
Mobil istemci varsayılan olarak `http://127.0.0.1:8000` (yerel masaüstü) veya `http://10.0.2.2:8000` (Android emülatörü) adresine bağlanır.
Bağlantı adresi `lib/core/constants/api_constants.dart` içerisinden yapılandırılabilir:

```dart
// Android Emülatörü için:
ApiConstants.baseUrl = ApiConstants.defaultAndroidEmulatorUrl; // http://10.0.2.2:8000

// Fiziksel Cihaz veya Masaüstü için:
ApiConstants.baseUrl = "http://192.168.1.XXX:8000";
```

### 4. Uygulamayı Başlatma
```powershell
# Android Emülatöründe çalıştırma:
flutter run
```

---

## 📄 Lisans
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR  
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
