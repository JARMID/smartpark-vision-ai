import 'package:flutter/material.dart';
import '../state/parking_controller.dart';

class PaymentScreen extends StatefulWidget {
  final ParkingController controller;
  final double amountDzd;
  final String plateNumber;

  const PaymentScreen({
    super.key,
    required this.controller,
    required this.amountDzd,
    required this.plateNumber,
  });

  @override
  State<PaymentScreen> createState() => _PaymentScreenState();
}

class _PaymentScreenState extends State<PaymentScreen> {
  String _cardType = 'EDAHABIA';
  final _cardNumberController = TextEditingController(text: '6038 9200 1234 5678');
  final _expiryController = TextEditingController(text: '09/28');
  final _cvvController = TextEditingController(text: '842');
  final _otpController = TextEditingController(text: '481902');
  bool _isProcessing = false;
  bool _otpSent = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Règlement Sécurisé Chargily V2'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Amount Summary Card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Theme.of(context).cardColor,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Theme.of(context).dividerColor),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Total à régler', style: TextStyle(color: Colors.grey, fontSize: 12)),
                      Text(
                        '${widget.amountDzd.toStringAsFixed(0)} DZD',
                        style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Color(0xFF10B981)),
                      ),
                    ],
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      const Text('Plaque Véhicule', style: TextStyle(color: Colors.grey, fontSize: 12)),
                      Text(
                        widget.plateNumber,
                        style: const TextStyle(fontWeight: FontWeight.bold, fontFamily: 'monospace'),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            if (widget.amountDzd <= 0) ...[
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFF10B981).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFF10B981)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: const [
                        Icon(Icons.verified, color: Color(0xFF10B981), size: 24),
                        SizedBox(width: 8),
                        Text(
                          'Franchise Gratuite de 15 Minutes',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 15,
                            color: Color(0xFF10B981),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Votre durée de stationnement est inférieure à la franchise de 15 minutes. Aucun règlement n\'est requis. La barrière s\'ouvrira automatiquement.',
                      style: TextStyle(fontSize: 13, height: 1.4),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 30),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF10B981),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                  icon: _isProcessing
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                            color: Colors.white,
                            strokeWidth: 2,
                          ),
                        )
                      : const Icon(Icons.check_circle_outline),
                  label: Text(
                    _isProcessing
                        ? 'Validation en cours...'
                        : 'Valider la Franchise de Sortie',
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  onPressed: _isProcessing ? null : _handleGraceDeparture,
                ),
              ),
            ] else ...[
              const Text(
                'Choisir la méthode de paiement',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
              ),
              const SizedBox(height: 10),

              // Card Type Toggle
              Row(
                children: [
                  Expanded(
                    child: _cardSelectorChip(
                      'EDAHABIA',
                      'Algérie Poste (Edahabia)',
                      Icons.credit_card,
                      const Color(0xFFD97706),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _cardSelectorChip(
                      'CIB',
                      'Carte Interbancaire (CIB)',
                      Icons.account_balance,
                      const Color(0xFF0284C7),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 20),

              // Card Details Form
              TextField(
                controller: _cardNumberController,
                decoration: const InputDecoration(
                  labelText: 'Numéro de Carte',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.payment),
                ),
                keyboardType: TextInputType.number,
              ),
              const SizedBox(height: 12),

              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _expiryController,
                      decoration: const InputDecoration(
                        labelText: 'Expiration (MM/AA)',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextField(
                      controller: _cvvController,
                      decoration: const InputDecoration(
                        labelText: 'Code CVV',
                        border: OutlineInputBorder(),
                      ),
                      obscureText: true,
                    ),
                  ),
                ],
              ),

              if (_otpSent) ...[
                const SizedBox(height: 16),
                TextField(
                  controller: _otpController,
                  decoration: const InputDecoration(
                    labelText: 'Code de confirmation SMS (OTP)',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.sms_outlined),
                    helperText: 'Code reçu par SMS sur votre mobile lié à la carte',
                  ),
                  keyboardType: TextInputType.number,
                ),
              ],

              const SizedBox(height: 30),

              // Action Button
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF10B981),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                  onPressed: _isProcessing ? null : _handlePaymentSubmit,
                  child: _isProcessing
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                            color: Colors.white,
                            strokeWidth: 2,
                          ),
                        )
                      : Text(
                          _otpSent
                              ? 'Confirmer le débit (${widget.amountDzd.toStringAsFixed(0)} DZD)'
                              : 'Recevoir le code SMS OTP',
                          style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _cardSelectorChip(
    String type,
    String title,
    IconData icon,
    Color color,
  ) {
    final isSelected = _cardType == type;
    return Semantics(
      button: true,
      selected: isSelected,
      label: '$title, ${isSelected ? "sélectionné" : "non sélectionné"}',
      child: InkWell(
        onTap: () => setState(() => _cardType = type),
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
          decoration: BoxDecoration(
            color: isSelected ? color.withValues(alpha: 0.15) : Theme.of(context).cardColor,
            border: Border.all(
              color: isSelected ? color : Theme.of(context).dividerColor,
              width: isSelected ? 2 : 1,
            ),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Column(
            children: [
              Icon(icon, color: color, size: 28),
              const SizedBox(height: 6),
              Text(
                title,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _handleGraceDeparture() async {
    setState(() => _isProcessing = true);
    await Future.delayed(const Duration(milliseconds: 600));
    setState(() => _isProcessing = false);

    final graceReceipt = {
      'receipt_number': 'REC-GRACE-${DateTime.now().millisecondsSinceEpoch % 100000}',
      'method': 'FRANCHISE GRATUITE',
      'amount': 0.0,
      'status': 'Franchise Validée',
    };

    if (mounted) {
      _showReceiptDialog(graceReceipt);
    }
  }

  Future<void> _handlePaymentSubmit() async {
    if (!_otpSent) {
      setState(() => _otpSent = true);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Code OTP envoyé par SMS (Simulé: 481902)')),
      );
      return;
    }

    setState(() => _isProcessing = true);
    final res = await widget.controller.payTicketWithChargily(
      plate: widget.plateNumber,
      amountDzd: widget.amountDzd,
      cardType: _cardType,
      otp: _otpController.text,
    );
    setState(() => _isProcessing = false);

    final paymentReceipt = {
      'receipt_number': res['receipt_number'] ?? 'REC-DZ-${DateTime.now().millisecondsSinceEpoch % 100000}',
      'method': _cardType == 'EDAHABIA' ? 'Carte EDAHABIA' : 'Carte CIB',
      'amount': widget.amountDzd,
      'status': 'Paiement Réglé avec Succès',
    };

    if (mounted) {
      _showReceiptDialog(paymentReceipt);
    }
  }

  void _showReceiptDialog(Map<String, dynamic> receipt) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: const [
            Icon(Icons.check_circle, color: Color(0xFF10B981), size: 28),
            SizedBox(width: 8),
            Text('Reçu de Sortie', style: TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
        content: Container(
          width: double.maxFinite,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Theme.of(context).cardColor,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: Theme.of(context).dividerColor),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Center(
                child: Text(
                  'SMART PARK ALGER',
                  style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 1),
                ),
              ),
              const Center(
                child: Text(
                  'JUSTIFICATIF DE STATIONNEMENT',
                  style: TextStyle(fontSize: 10, color: Colors.grey),
                ),
              ),
              const Divider(height: 20),
              _receiptRow('Reçu N°:', receipt['receipt_number'].toString()),
              _receiptRow('Immatriculation:', widget.plateNumber),
              _receiptRow('Mode Règlement:', receipt['method'].toString()),
              _receiptRow(
                'Montant Réglé:',
                '${(receipt['amount'] as double).toStringAsFixed(0)} DZD',
                isBold: true,
              ),
              _receiptRow('Délai de Grâce Sortie:', '15 minutes'),
              const Divider(height: 20),
              const Text(
                'Protection des Données ANPDP - Loi 18-07',
                style: TextStyle(fontSize: 9.5, color: Colors.grey),
              ),
            ],
          ),
        ),
        actions: [
          TextButton.icon(
            icon: const Icon(Icons.share, size: 16),
            label: const Text('Partager Reçu'),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Reçu copié dans le presse-papier.')),
              );
            },
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF0284C7),
              foregroundColor: Colors.white,
            ),
            onPressed: () {
              Navigator.pop(ctx);
              Navigator.pop(context);
            },
            child: const Text('Retour à l\'accueil'),
          ),
        ],
      ),
    );
  }

  Widget _receiptRow(String label, String value, {bool isBold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey)),
          Text(
            value,
            style: TextStyle(
              fontSize: 12,
              fontWeight: isBold ? FontWeight.bold : FontWeight.w600,
              fontFamily: 'monospace',
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _cardNumberController.dispose();
    _expiryController.dispose();
    _cvvController.dispose();
    _otpController.dispose();
    super.dispose();
  }
}
