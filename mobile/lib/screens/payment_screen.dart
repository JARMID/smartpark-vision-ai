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
            const Text('Choisir la méthode de paiement', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
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
                  backgroundColor: const Color(0xFF0284C7),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                onPressed: _isProcessing ? null : _handlePaymentSubmit,
                child: _isProcessing
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                      )
                    : Text(
                        _otpSent ? 'Confirmer le débit (${widget.amountDzd.toStringAsFixed(0)} DZD)' : 'Recevoir le code SMS OTP',
                        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _cardSelectorChip(String type, String title, IconData icon, Color color) {
    final isSelected = _cardType == type;
    return InkWell(
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
    );
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

    if (mounted) {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (ctx) => AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.check_circle, color: Color(0xFF10B981)),
              SizedBox(width: 8),
              Text('Paiement Validé'),
            ],
          ),
          content: Text(
            'Reçu: ${res['receipt_number'] ?? 'REC-2026'}\n'
            'Montant: ${widget.amountDzd.toStringAsFixed(0)} DZD\n'
            'Statut: Réglé avec succès.\n\n'
            'La barrière de sortie s\'ouvrira automatiquement à votre approche (délai de grâce sortie: 15 minutes).',
          ),
          actions: [
            TextButton(
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
