// Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
// ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

import 'package:intl/intl.dart';

class CurrencyFormatter {
  static final NumberFormat _formatter = NumberFormat.currency(
    locale: 'tr_TR',
    symbol: 'TL',
    decimalDigits: 2,
  );

  static String format(num amount) {
    return _formatter.format(amount);
  }

  static String formatUnitAmount(num amount, [String unit = 'TL/da']) {
    return '${_formatter.format(amount)} / da';
  }
}
