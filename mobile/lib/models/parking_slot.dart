class ParkingSlot {
  final String slotNumber;
  final String zoneName;
  final String floorLevel;
  final String status; // 'vacant', 'occupied', 'reserved'
  final String? plate;
  final String? parkedSince;

  const ParkingSlot({
    required this.slotNumber,
    required this.zoneName,
    required this.floorLevel,
    required this.status,
    this.plate,
    this.parkedSince,
  });

  bool get isVacant => status == 'vacant';
  bool get isOccupied => status == 'occupied';
  bool get isReserved => status == 'reserved';
  bool get isVip => zoneName.contains('VIP') || slotNumber.startsWith('A');

  factory ParkingSlot.fromJson(Map<String, dynamic> json) {
    return ParkingSlot(
      slotNumber: json['slot_number'] as String,
      zoneName: json['zone_name'] as String,
      floorLevel: json['floor_level'] as String? ?? 'Level 0',
      status: json['status'] as String? ?? 'vacant',
      plate: json['plate'] as String?,
      parkedSince: json['parked_since'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'slot_number': slotNumber,
      'zone_name': zoneName,
      'floor_level': floorLevel,
      'status': status,
      'plate': plate,
      'parked_since': parkedSince,
    };
  }

  ParkingSlot copyWith({
    String? slotNumber,
    String? zoneName,
    String? floorLevel,
    String? status,
    String? plate,
    String? parkedSince,
  }) {
    return ParkingSlot(
      slotNumber: slotNumber ?? this.slotNumber,
      zoneName: zoneName ?? this.zoneName,
      floorLevel: floorLevel ?? this.floorLevel,
      status: status ?? this.status,
      plate: plate ?? this.plate,
      parkedSince: parkedSince ?? this.parkedSince,
    );
  }
}
