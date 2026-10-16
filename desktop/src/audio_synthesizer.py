"""
Smart Park - Audio Threat Synthesizer and Notification Chimes.
Provides non-blocking audible alarms for blacklisted plates, anti-spoof detections,
plate cloning conflicts, cashier settlements, and barrier releases.
"""

import math
import struct
import threading
import time
from typing import Optional


class AudioThreatSynthesizer:
    """
    Synthesizes acoustic warning alarms and tactile feedback chimes.
    Executes in background worker threads to keep UI event loops responsive.
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._is_playing = False
        self._lock = threading.Lock()

    def play_siren_threat(self, cycles: int = 3):
        """Play high-urgency dual-tone siren for stolen or blacklisted vehicle detection."""
        if not self.enabled:
            return
        threading.Thread(target=self._run_siren, args=(cycles,), daemon=True).start()

    def play_warning_beep(self, count: int = 2):
        """Play short warning beep for verification mismatch or manual review."""
        if not self.enabled:
            return
        threading.Thread(target=self._run_warning, args=(count,), daemon=True).start()

    def play_success_chime(self):
        """Play ascending three-tone chime for clearance or payment confirmation."""
        if not self.enabled:
            return
        threading.Thread(target=self._run_success, daemon=True).start()

    def _run_siren(self, cycles: int):
        with self._lock:
            try:
                import winsound
                for _ in range(cycles):
                    winsound.Beep(880, 200)   # Note A5
                    winsound.Beep(1175, 200)  # Note D6
            except (ImportError, RuntimeError):
                # Fallback on platforms without winsound or when audio output is disabled
                time.sleep(0.4 * cycles)

    def _run_warning(self, count: int):
        with self._lock:
            try:
                import winsound
                for _ in range(count):
                    winsound.Beep(600, 150)
                    time.sleep(0.05)
            except (ImportError, RuntimeError):
                time.sleep(0.2 * count)

    def _run_success(self):
        with self._lock:
            try:
                import winsound
                # Ascending triad: C5 (523Hz), E5 (659Hz), G5 (784Hz)
                winsound.Beep(523, 100)
                winsound.Beep(659, 100)
                winsound.Beep(784, 180)
            except (ImportError, RuntimeError):
                time.sleep(0.38)

    @staticmethod
    def synthesize_wav_buffer(frequencies: list, duration_s: float = 0.2, sample_rate: int = 44100) -> bytes:
        """
        Synthesize raw uncompressed 16-bit PCM WAV audio buffer.
        Useful for web audio streaming or external sound devices.
        """
        num_samples = int(sample_rate * duration_s)
        raw_samples = []

        for i in range(num_samples):
            t = float(i) / sample_rate
            value = 0.0
            for freq in frequencies:
                value += math.sin(2.0 * math.pi * freq * t)
            value /= max(1, len(frequencies))
            int_val = int(value * 32767.0 * 0.8)
            raw_samples.append(max(-32768, min(32767, int_val)))

        pcm_data = struct.pack(f"<{len(raw_samples)}h", *raw_samples)
        wav_header = bytearray(b"RIFF")
        wav_header.extend(struct.pack("<I", 36 + len(pcm_data)))
        wav_header.extend(b"WAVEfmt ")
        wav_header.extend(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
        wav_header.extend(b"data")
        wav_header.extend(struct.pack("<I", len(pcm_data)))
        return bytes(wav_header + pcm_data)
