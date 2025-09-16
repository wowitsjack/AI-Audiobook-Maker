"""
Audio Quality Detection Module for TTS Corruption Detection
===========================================================

This module provides comprehensive audio quality analysis to detect corruption
and failures in TTS-generated audio from APIs like Gemini TTS.

Common corruption patterns detected:
- Sudden audio cutoffs and excessive silence
- Static, noise, and high-frequency artifacts
- Volume spikes and clipping (999db static)
- Digital artifacts and distortion
- Frequency anomalies and spectral corruption
- Incomplete or truncated audio generation
- Speed distortion (chipmunk/slowdown effects)
- Reverse speech corruption
- Gibberish and severe artifacting

Author: wowitsjack's Audio Quality Detection System
"""

import os
import wave
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum
import warnings

# Audio processing imports with fallbacks
try:
    import librosa
    import librosa.display
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    librosa = None
    
try:
    import scipy.stats as stats
    from scipy import signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    stats = None
    signal = None

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    sf = None

try:
    import matplotlib.pyplot as plt
    import matplotlib.mlab as mlab
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    mlab = None

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CorruptionType(Enum):
    """Types of audio corruption that can be detected"""
    NONE = "no_corruption"
    SUDDEN_CUTOFF = "sudden_cutoff"
    EXCESSIVE_SILENCE = "excessive_silence"
    STATIC_NOISE = "static_noise"
    VOLUME_SPIKE = "volume_spike"
    CLIPPING = "clipping"
    FREQUENCY_ANOMALY = "frequency_anomaly"
    DIGITAL_ARTIFACTS = "digital_artifacts"
    LOW_QUALITY = "low_quality"
    INCOMPLETE_GENERATION = "incomplete_generation"
    SPEED_DISTORTION = "speed_distortion"  # Time compression/expansion (same pitch, different speed)
    REVERSE_SPEECH = "reverse_speech"      # Audio played backwards
    GIBBERISH_ARTIFACTS = "gibberish_artifacts"  # Unintelligible speech with severe artifacts


@dataclass
class QualityMetrics:
    """Container for audio quality metrics"""
    duration: float
    sample_rate: int
    rms_energy: float
    peak_amplitude: float
    dynamic_range: float
    silence_percentage: float
    high_freq_energy: float
    spectral_centroid: float
    spectral_rolloff: float
    zero_crossing_rate: float
    clipping_percentage: float
    snr_estimate: float
    spectral_flatness: float
    harmonic_noise_ratio: float


@dataclass
class CorruptionReport:
    """Report containing corruption detection results"""
    is_corrupted: bool
    corruption_types: List[CorruptionType]
    confidence_score: float
    quality_metrics: QualityMetrics
    issues_found: List[str]
    recommendations: List[str]
    corruption_timestamps: List[Tuple[float, float]]  # Start, end times of corruption


class AudioQualityDetector:
    """
    Advanced audio quality detector for TTS corruption detection
    """
    
    def __init__(self, 
                 silence_threshold: float = -40.0,  # dB
                 static_threshold: float = -20.0,   # dB
                 spike_threshold: float = -6.0,     # dB
                 max_silence_duration: float = 3.0, # seconds
                 min_speech_duration: float = 1.0,  # seconds
                 corruption_confidence_threshold: float = 0.7):
        """
        Initialize the audio quality detector
        
        Args:
            silence_threshold: Threshold in dB below which audio is considered silence
            static_threshold: Threshold for detecting static/noise
            spike_threshold: Threshold for detecting volume spikes
            max_silence_duration: Maximum acceptable silence duration in seconds
            min_speech_duration: Minimum expected speech duration
            corruption_confidence_threshold: Confidence threshold for corruption detection
        """
        self.silence_threshold = silence_threshold
        self.static_threshold = static_threshold
        self.spike_threshold = spike_threshold
        self.max_silence_duration = max_silence_duration
        self.min_speech_duration = min_speech_duration
        self.corruption_confidence_threshold = corruption_confidence_threshold
        
        # Check library availability
        self._check_dependencies()
        
    def _check_dependencies(self):
        """Check which audio processing libraries are available"""
        missing_libs = []
        
        if not LIBROSA_AVAILABLE:
            missing_libs.append("librosa")
        if not SCIPY_AVAILABLE:
            missing_libs.append("scipy")
        if not SOUNDFILE_AVAILABLE:
            missing_libs.append("soundfile")
            
        if missing_libs:
            logger.warning(f"🚨 Missing audio libraries: {missing_libs}")
            logger.warning("📦 Install with: pip install " + " ".join(missing_libs))
            logger.warning("🔍 Detection capabilities will be limited!")
            
    def load_audio(self, file_path: str) -> Tuple[np.ndarray, int]:
        """
        Load audio file using the best available method
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Tuple of (audio_data, sample_rate)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"🚨 Audio file not found: {file_path}")
            
        # Try librosa first (most robust)
        if LIBROSA_AVAILABLE:
            try:
                audio, sr = librosa.load(file_path, sr=None, mono=False)
                # Convert stereo to mono if needed
                if len(audio.shape) > 1:
                    audio = np.mean(audio, axis=0)
                return audio, sr
            except Exception as e:
                logger.warning(f"⚠️ Librosa failed: {e}")
                
        # Try soundfile
        if SOUNDFILE_AVAILABLE:
            try:
                audio, sr = sf.read(file_path)
                # Convert stereo to mono if needed
                if len(audio.shape) > 1:
                    audio = np.mean(audio, axis=1)
                return audio, sr
            except Exception as e:
                logger.warning(f"⚠️ Soundfile failed: {e}")
                
        # Fallback to wave module (basic support)
        try:
            with wave.open(file_path, 'rb') as wav_file:
                frames = wav_file.readframes(-1)
                sound_info = wav_file.getparams()
                audio = np.frombuffer(frames, dtype=np.int16)
                # Convert to float and normalize
                audio = audio.astype(np.float32) / 32767.0
                return audio, sound_info.framerate
        except Exception as e:
            raise RuntimeError(f"🚨 Failed to load audio with all methods: {e}")
            
    def _compute_rms_energy(self, audio: np.ndarray) -> float:
        """Compute RMS energy of audio signal"""
        return float(np.sqrt(np.mean(audio**2)))
        
    def _compute_db(self, value: float, reference: float = 1.0) -> float:
        """Convert amplitude to decibels"""
        if value <= 0:
            return -np.inf
        return 20 * np.log10(value / reference)
        
    def _detect_silence_segments(self, audio: np.ndarray, sr: int) -> List[Tuple[float, float]]:
        """
        Detect segments of silence in audio
        
        Returns:
            List of (start_time, end_time) tuples for silence segments
        """
        # Compute frame-wise energy
        frame_length = int(0.025 * sr)  # 25ms frames
        hop_length = int(0.010 * sr)    # 10ms hop
        
        frames = []
        for i in range(0, len(audio) - frame_length, hop_length):
            frame = audio[i:i + frame_length]
            energy = self._compute_rms_energy(frame)
            energy_db = self._compute_db(energy)
            frames.append(energy_db)
            
        frames = np.array(frames)
        
        # Detect silence frames
        silence_mask = frames < self.silence_threshold
        
        # Find continuous silence segments
        silence_segments = []
        in_silence = False
        start_time = 0
        
        for i, is_silent in enumerate(silence_mask):
            time = i * hop_length / sr
            
            if is_silent and not in_silence:
                # Start of silence
                start_time = time
                in_silence = True
            elif not is_silent and in_silence:
                # End of silence
                silence_segments.append((start_time, time))
                in_silence = False
                
        # Handle case where audio ends in silence
        if in_silence:
            silence_segments.append((start_time, len(audio) / sr))
            
        return silence_segments
        
    def _detect_volume_spikes(self, audio: np.ndarray, sr: int) -> List[Tuple[float, float]]:
        """
        Detect sudden volume spikes that might indicate corruption
        
        Returns:
            List of (start_time, end_time) tuples for spike segments
        """
        # Compute short-term energy
        frame_length = int(0.010 * sr)  # 10ms frames
        hop_length = int(0.005 * sr)    # 5ms hop
        
        energies = []
        for i in range(0, len(audio) - frame_length, hop_length):
            frame = audio[i:i + frame_length]
            energy = self._compute_rms_energy(frame)
            energies.append(energy)
            
        energies = np.array(energies)
        
        # Detect spikes using statistical outlier detection
        if len(energies) < 10:
            return []
            
        # Use rolling median to detect sudden changes
        window_size = min(50, len(energies) // 4)
        if window_size < 3:
            return []
            
        # Compute rolling statistics
        rolling_median = np.convolve(energies, np.ones(window_size)/window_size, mode='same')
        rolling_std = np.array([np.std(energies[max(0, i-window_size//2):i+window_size//2+1]) 
                               for i in range(len(energies))])
        
        # Detect outliers
        spike_threshold_linear = 10**(self.spike_threshold / 20)  # Convert dB to linear
        spike_mask = energies > (rolling_median + 3 * rolling_std)
        spike_mask = spike_mask & (energies > spike_threshold_linear)
        
        # Convert to time segments
        spikes = []
        in_spike = False
        start_time = 0
        
        for i, is_spike in enumerate(spike_mask):
            time = i * hop_length / sr
            
            if is_spike and not in_spike:
                start_time = time
                in_spike = True
            elif not is_spike and in_spike:
                spikes.append((start_time, time))
                in_spike = False
                
        if in_spike:
            spikes.append((start_time, len(audio) / sr))
            
        return spikes
        
    def _detect_speed_distortion(self, audio: np.ndarray, sr: int) -> Tuple[bool, float]:
        """
        Detect if audio has been time-compressed/expanded (speed distortion)
        
        Returns:
            Tuple of (is_distorted, confidence_score)
        """
        try:
            # Analyze temporal characteristics
            duration = len(audio) / sr
            
            # Basic rhythm/tempo analysis using energy envelope
            frame_length = int(0.025 * sr)  # 25ms frames
            hop_length = int(0.010 * sr)    # 10ms hop
            
            # Compute energy envelope
            energies = []
            for i in range(0, len(audio) - frame_length, hop_length):
                frame = audio[i:i + frame_length]
                energy = self._compute_rms_energy(frame)
                energies.append(energy)
                
            if len(energies) < 10:
                return False, 0.0
                
            energies = np.array(energies)
            
            # Detect rapid energy changes (indicator of speed distortion)
            energy_diff = np.diff(energies)
            rapid_changes = np.sum(np.abs(energy_diff) > np.std(energy_diff) * 2)
            rapid_change_rate = rapid_changes / len(energy_diff)
            
            # Speech rate estimation (very basic)
            # Normal speech: ~4-6 syllables per second
            # Look for energy peaks that might indicate syllables
            from scipy.signal import find_peaks
            if SCIPY_AVAILABLE:
                peaks, _ = find_peaks(energies, height=np.mean(energies), distance=5)
                syllable_rate = len(peaks) / duration
                
                # Check for abnormally high syllable rate (indicates speed up)
                if syllable_rate > 10:  # Way too fast for normal speech
                    return True, min(0.9, (syllable_rate - 10) / 10)
                elif syllable_rate < 1:  # Too slow (might be slowed down)
                    return True, min(0.7, (1 - syllable_rate))
                    
            # Check for temporal irregularities
            if rapid_change_rate > 0.3:  # More than 30% of frames have rapid changes
                return True, min(0.8, rapid_change_rate)
                
            # Zero crossing rate analysis (sped up speech has higher ZCR)
            zcr = np.sum(np.diff(np.sign(audio)) != 0) / len(audio)
            if zcr > 0.5:  # Abnormally high zero crossing rate
                return True, min(0.7, zcr)
                
            return False, 0.0
            
        except Exception as e:
            logger.warning(f"⚠️ Speed distortion detection failed: {e}")
            return False, 0.0
            
    def _detect_reverse_speech(self, audio: np.ndarray, sr: int) -> Tuple[bool, float]:
        """
        Detect if audio is played in reverse
        
        Returns:
            Tuple of (is_reversed, confidence_score)
        """
        try:
            # Reverse speech has characteristic energy patterns
            # Normal speech typically has sharp onset, gradual decay
            # Reversed speech has gradual onset, sharp offset
            
            if len(audio) < sr:  # Need at least 1 second
                return False, 0.0
                
            # Analyze energy envelope directionality
            frame_length = int(0.050 * sr)  # 50ms frames
            hop_length = int(0.025 * sr)    # 25ms hop
            
            energies = []
            for i in range(0, len(audio) - frame_length, hop_length):
                frame = audio[i:i + frame_length]
                energy = self._compute_rms_energy(frame)
                energies.append(energy)
                
            if len(energies) < 20:
                return False, 0.0
                
            energies = np.array(energies)
            
            # Find energy peaks and analyze their shape
            if SCIPY_AVAILABLE:
                from scipy.signal import find_peaks
                peaks, properties = find_peaks(energies, height=np.mean(energies) * 1.5, distance=10)
                
                if len(peaks) < 3:
                    return False, 0.0
                    
                # Analyze asymmetry around peaks
                reverse_indicators = 0
                total_peaks = 0
                
                for peak_idx in peaks:
                    # Look at 10 frames before and after peak
                    start_idx = max(0, peak_idx - 10)
                    end_idx = min(len(energies), peak_idx + 10)
                    
                    if end_idx - start_idx < 15:  # Need enough context
                        continue
                        
                    before_peak = energies[start_idx:peak_idx]
                    after_peak = energies[peak_idx:end_idx]
                    
                    if len(before_peak) > 2 and len(after_peak) > 2:
                        # Calculate rise and fall rates
                        rise_rate = np.mean(np.diff(before_peak))
                        fall_rate = np.mean(np.diff(after_peak))
                        
                        # In normal speech: quick rise, slower fall (rise_rate > -fall_rate)
                        # In reverse speech: slow rise, quick fall (rise_rate < -fall_rate)
                        if rise_rate < -fall_rate * 0.5:  # Indicates reverse pattern
                            reverse_indicators += 1
                        total_peaks += 1
                        
                if total_peaks > 0:
                    reverse_ratio = reverse_indicators / total_peaks
                    if reverse_ratio > 0.6:  # More than 60% of peaks show reverse pattern
                        return True, min(0.9, reverse_ratio)
                        
            # Additional check: spectral flux directionality
            # (This would require more advanced analysis)
            
            return False, 0.0
            
        except Exception as e:
            logger.warning(f"⚠️ Reverse speech detection failed: {e}")
            return False, 0.0
            
    def _detect_gibberish_artifacts(self, audio: np.ndarray, sr: int) -> Tuple[bool, float]:
        """
        Detect gibberish speech with severe artifacts
        
        Returns:
            Tuple of (is_gibberish, confidence_score)
        """
        try:
            # Gibberish often has:
            # 1. Irregular spectral patterns
            # 2. Unusual formant structures
            # 3. High frequency artifacts
            # 4. Inconsistent temporal patterns
            
            # Spectral irregularity analysis
            if len(audio) < sr * 0.5:  # Need at least 0.5 seconds
                return False, 0.0
                
            # Compute spectrogram
            window_size = int(0.025 * sr)  # 25ms window
            hop_size = int(0.010 * sr)     # 10ms hop
            
            # Basic STFT for spectral analysis
            num_frames = (len(audio) - window_size) // hop_size + 1
            num_freqs = window_size // 2 + 1
            spectrogram = np.zeros((num_freqs, num_frames))
            
            for i in range(num_frames):
                start = i * hop_size
                end = start + window_size
                if end <= len(audio):
                    frame = audio[start:end]
                    # Apply window
                    frame = frame * np.hanning(len(frame))
                    # FFT
                    fft = np.fft.rfft(frame)
                    spectrogram[:, i] = np.abs(fft)
                    
            # Analyze spectral characteristics
            artifacts_detected = 0
            confidence_factors = []
            
            # 1. Check for excessive high-frequency content
            freqs = np.fft.rfftfreq(window_size, 1/sr)
            high_freq_mask = freqs > 4000
            if np.any(high_freq_mask):
                high_freq_energy = np.mean(spectrogram[high_freq_mask, :])
                total_energy = np.mean(spectrogram)
                high_freq_ratio = high_freq_energy / (total_energy + 1e-10)
                
                if high_freq_ratio > 0.4:  # More than 40% high frequency
                    artifacts_detected += 1
                    confidence_factors.append(min(0.8, high_freq_ratio))
                    
            # 2. Check for spectral discontinuities
            spectral_flux = np.mean(np.diff(spectrogram, axis=1)**2, axis=0)
            flux_variance = np.var(spectral_flux)
            flux_mean = np.mean(spectral_flux)
            
            if flux_variance > flux_mean * 2:  # High variance indicates artifacts
                artifacts_detected += 1
                confidence_factors.append(min(0.7, flux_variance / flux_mean / 2))
                
            # 3. Check for unnatural formant patterns (simplified)
            # Look for regular speech formant frequencies (300-3000 Hz)
            speech_freq_mask = (freqs >= 300) & (freqs <= 3000)
            if np.any(speech_freq_mask):
                speech_energy = np.mean(spectrogram[speech_freq_mask, :])
                noise_freq_mask = freqs > 6000
                if np.any(noise_freq_mask):
                    noise_energy = np.mean(spectrogram[noise_freq_mask, :])
                    speech_to_noise = speech_energy / (noise_energy + 1e-10)
                    
                    if speech_to_noise < 2:  # Poor speech-to-noise ratio
                        artifacts_detected += 1
                        confidence_factors.append(0.6)
                        
            # 4. Check for temporal inconsistencies
            frame_energies = np.mean(spectrogram, axis=0)
            energy_changes = np.abs(np.diff(frame_energies))
            abrupt_changes = np.sum(energy_changes > np.std(energy_changes) * 3)
            change_ratio = abrupt_changes / len(energy_changes)
            
            if change_ratio > 0.2:  # More than 20% abrupt changes
                artifacts_detected += 1
                confidence_factors.append(min(0.8, change_ratio * 2))
                
            # Determine if gibberish
            if artifacts_detected >= 2 and confidence_factors:
                overall_confidence = np.mean(confidence_factors)
                return True, min(0.9, overall_confidence)
                
            return False, 0.0
            
        except Exception as e:
            logger.warning(f"⚠️ Gibberish detection failed: {e}")
            return False, 0.0
        
    def _analyze_spectral_features(self, audio: np.ndarray, sr: int) -> Dict[str, float]:
        """
        Analyze spectral features of the audio
        
        Returns:
            Dictionary of spectral features
        """
        features = {}
        
        if not LIBROSA_AVAILABLE:
            # Basic frequency analysis without librosa
            try:
                # Compute FFT
                fft = np.fft.rfft(audio)
                magnitude = np.abs(fft)
                frequencies = np.fft.rfftfreq(len(audio), 1/sr)
                
                # Spectral centroid (center of mass of spectrum)
                spectral_centroid = np.sum(frequencies * magnitude) / np.sum(magnitude)
                features['spectral_centroid'] = float(spectral_centroid)
                
                # Spectral rolloff (frequency below which 85% of energy is contained)
                cumulative_energy = np.cumsum(magnitude**2)
                total_energy = cumulative_energy[-1]
                rolloff_idx = np.where(cumulative_energy >= 0.85 * total_energy)[0]
                if len(rolloff_idx) > 0:
                    features['spectral_rolloff'] = float(frequencies[rolloff_idx[0]])
                else:
                    features['spectral_rolloff'] = float(frequencies[-1])
                    
                # High frequency energy ratio
                high_freq_mask = frequencies > 4000  # Above 4kHz
                if np.any(high_freq_mask):
                    high_freq_energy = np.sum(magnitude[high_freq_mask]**2)
                    total_spec_energy = np.sum(magnitude**2)
                    features['high_freq_energy'] = float(high_freq_energy / total_spec_energy)
                else:
                    features['high_freq_energy'] = 0.0
                    
                # Spectral flatness (measure of noise vs tonal content)
                # Geometric mean / arithmetic mean of power spectrum
                power_spectrum = magnitude**2
                # Avoid log of zero
                power_spectrum_safe = np.maximum(power_spectrum, 1e-10)
                geometric_mean = np.exp(np.mean(np.log(power_spectrum_safe)))
                arithmetic_mean = np.mean(power_spectrum)
                features['spectral_flatness'] = float(geometric_mean / arithmetic_mean)
                
            except Exception as e:
                logger.warning(f"⚠️ Basic spectral analysis failed: {e}")
                features.update({
                    'spectral_centroid': 0.0,
                    'spectral_rolloff': 0.0,
                    'high_freq_energy': 0.0,
                    'spectral_flatness': 0.0
                })
        else:
            # Advanced analysis with librosa
            try:
                # Spectral centroid
                spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
                features['spectral_centroid'] = float(np.mean(spectral_centroid))
                
                # Spectral rolloff
                spectral_rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)[0]
                features['spectral_rolloff'] = float(np.mean(spectral_rolloff))
                
                # Zero crossing rate
                zcr = librosa.feature.zero_crossing_rate(audio)[0]
                features['zero_crossing_rate'] = float(np.mean(zcr))
                
                # MFCC for more advanced analysis
                mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
                features['mfcc_variance'] = float(np.var(mfccs))
                
                # Spectral contrast
                spectral_contrast = librosa.feature.spectral_contrast(y=audio, sr=sr)
                features['spectral_contrast'] = float(np.mean(spectral_contrast))
                
                # Chroma features (for pitch analysis)
                chroma = librosa.feature.chroma_stft(y=audio, sr=sr)
                features['chroma_variance'] = float(np.var(chroma))
                
                # High frequency energy
                stft = librosa.stft(audio)
                magnitude = np.abs(stft)
                freq_bins = librosa.fft_frequencies(sr=sr)
                high_freq_mask = freq_bins > 4000
                if np.any(high_freq_mask):
                    high_freq_energy = np.sum(magnitude[high_freq_mask]**2)
                    total_energy = np.sum(magnitude**2)
                    features['high_freq_energy'] = float(high_freq_energy / total_energy)
                else:
                    features['high_freq_energy'] = 0.0
                    
                # Spectral flatness
                spectral_flatness = librosa.feature.spectral_flatness(y=audio)[0]
                features['spectral_flatness'] = float(np.mean(spectral_flatness))
                
            except Exception as e:
                logger.warning(f"⚠️ Advanced spectral analysis failed: {e}")
                # Fallback to basic analysis
                return self._analyze_spectral_features(audio, sr)
                
        return features
        
    def _compute_quality_metrics(self, audio: np.ndarray, sr: int) -> QualityMetrics:
        """
        Compute comprehensive quality metrics for the audio
        
        Args:
            audio: Audio signal
            sr: Sample rate
            
        Returns:
            QualityMetrics object
        """
        duration = len(audio) / sr
        
        # Basic amplitude metrics
        rms_energy = self._compute_rms_energy(audio)
        peak_amplitude = float(np.max(np.abs(audio)))
        dynamic_range = float(peak_amplitude / (rms_energy + 1e-10))
        
        # Clipping detection
        clipping_threshold = 0.95  # 95% of full scale
        clipped_samples = np.sum(np.abs(audio) > clipping_threshold)
        clipping_percentage = float(clipped_samples / len(audio) * 100)
        
        # Silence analysis
        silence_segments = self._detect_silence_segments(audio, sr)
        total_silence_duration = sum(end - start for start, end in silence_segments)
        silence_percentage = float(total_silence_duration / duration * 100)
        
        # Spectral features
        spectral_features = self._analyze_spectral_features(audio, sr)
        
        # Estimate SNR (Signal-to-Noise Ratio)
        # Use spectral subtraction method
        if len(audio) > sr:  # At least 1 second of audio
            # Assume first 0.1 seconds might be noise
            noise_samples = int(0.1 * sr)
            if noise_samples < len(audio):
                noise_segment = audio[:noise_samples]
                signal_segment = audio[noise_samples:]
                noise_power = np.mean(noise_segment**2)
                signal_power = np.mean(signal_segment**2)
                if noise_power > 0:
                    snr_estimate = float(10 * np.log10(signal_power / noise_power))
                else:
                    snr_estimate = 60.0  # Very high SNR
            else:
                snr_estimate = 30.0  # Default reasonable SNR
        else:
            snr_estimate = 30.0
            
        # Harmonic-to-noise ratio estimation
        try:
            if LIBROSA_AVAILABLE:
                # Use harmonic separation
                harmonic, percussive = librosa.effects.hpss(audio)
                harmonic_power = np.mean(harmonic**2)
                noise_power = np.mean((audio - harmonic)**2)
                if noise_power > 0:
                    hnr = float(10 * np.log10(harmonic_power / noise_power))
                else:
                    hnr = 40.0
            else:
                # Simple estimation
                hnr = snr_estimate * 0.8  # Rough approximation
        except:
            hnr = snr_estimate * 0.8
            
        return QualityMetrics(
            duration=duration,
            sample_rate=sr,
            rms_energy=rms_energy,
            peak_amplitude=peak_amplitude,
            dynamic_range=dynamic_range,
            silence_percentage=silence_percentage,
            high_freq_energy=spectral_features.get('high_freq_energy', 0.0),
            spectral_centroid=spectral_features.get('spectral_centroid', 1000.0),
            spectral_rolloff=spectral_features.get('spectral_rolloff', 4000.0),
            zero_crossing_rate=spectral_features.get('zero_crossing_rate', 0.1),
            clipping_percentage=clipping_percentage,
            snr_estimate=snr_estimate,
            spectral_flatness=spectral_features.get('spectral_flatness', 0.1),
            harmonic_noise_ratio=hnr
        )
        
    def _analyze_corruption_patterns(self, audio: np.ndarray, sr: int, 
                                   metrics: QualityMetrics) -> Tuple[List[CorruptionType], List[str], float]:
        """
        Analyze audio for corruption patterns
        
        Returns:
            Tuple of (corruption_types, issues_found, confidence_score)
        """
        corruption_types = []
        issues = []
        confidence_scores = []
        
        # 1. Check for sudden cutoff / incomplete generation
        if metrics.duration < self.min_speech_duration:
            corruption_types.append(CorruptionType.INCOMPLETE_GENERATION)
            issues.append(f"🚨 Audio too short: {metrics.duration:.2f}s (minimum: {self.min_speech_duration}s)")
            confidence_scores.append(0.9)
            
        # 2. Check for excessive silence
        if metrics.silence_percentage > 50:
            corruption_types.append(CorruptionType.EXCESSIVE_SILENCE)
            issues.append(f"🔇 Excessive silence: {metrics.silence_percentage:.1f}% of audio")
            confidence_scores.append(0.8)
            
        # Detect silence at the end (sudden cutoff)
        silence_segments = self._detect_silence_segments(audio, sr)
        if silence_segments:
            last_silence = silence_segments[-1]
            if last_silence[1] >= metrics.duration - 0.1:  # Ends with silence
                silence_duration = last_silence[1] - last_silence[0]
                if silence_duration > self.max_silence_duration:
                    corruption_types.append(CorruptionType.SUDDEN_CUTOFF)
                    issues.append(f"✂️ Sudden cutoff detected: {silence_duration:.2f}s of silence at end")
                    confidence_scores.append(0.9)
                    
        # 3. Check for clipping
        if metrics.clipping_percentage > 1.0:  # More than 1% clipped
            corruption_types.append(CorruptionType.CLIPPING)
            issues.append(f"📈 Audio clipping detected: {metrics.clipping_percentage:.2f}% of samples")
            confidence_scores.append(0.8)
            
        # 4. Check for volume spikes (999db static)
        if metrics.peak_amplitude > 0.9 and metrics.dynamic_range > 50:
            spikes = self._detect_volume_spikes(audio, sr)
            if spikes:
                corruption_types.append(CorruptionType.VOLUME_SPIKE)
                issues.append(f"🔊 Volume spikes detected: {len(spikes)} spike(s)")
                confidence_scores.append(0.85)
                
        # 5. Check for static/noise corruption
        if metrics.high_freq_energy > 0.3:  # More than 30% high frequency energy
            corruption_types.append(CorruptionType.STATIC_NOISE)
            issues.append(f"📡 High frequency noise detected: {metrics.high_freq_energy*100:.1f}%")
            confidence_scores.append(0.7)
            
        # 6. Check spectral anomalies
        if metrics.spectral_flatness > 0.8:  # Very flat spectrum indicates noise
            corruption_types.append(CorruptionType.FREQUENCY_ANOMALY)
            issues.append(f"🌊 Spectral anomaly detected: flatness = {metrics.spectral_flatness:.3f}")
            confidence_scores.append(0.6)
            
        # 7. Check for very low SNR
        if metrics.snr_estimate < 10:  # Less than 10dB SNR
            corruption_types.append(CorruptionType.LOW_QUALITY)
            issues.append(f"📉 Low signal-to-noise ratio: {metrics.snr_estimate:.1f} dB")
            confidence_scores.append(0.7)
            
        # 8. Check for digital artifacts using zero crossing rate
        if metrics.zero_crossing_rate > 0.5:  # Unusually high ZCR
            corruption_types.append(CorruptionType.DIGITAL_ARTIFACTS)
            issues.append(f"💾 Digital artifacts detected: ZCR = {metrics.zero_crossing_rate:.3f}")
            confidence_scores.append(0.6)
            
        # 9. Check harmonic content
        if metrics.harmonic_noise_ratio < 5:  # Very low harmonic content
            if CorruptionType.LOW_QUALITY not in corruption_types:
                corruption_types.append(CorruptionType.LOW_QUALITY)
                issues.append(f"🎵 Low harmonic content: HNR = {metrics.harmonic_noise_ratio:.1f} dB")
                confidence_scores.append(0.6)
                
        # 10. Check for speed distortion (time compression/expansion)
        is_speed_distorted, speed_confidence = self._detect_speed_distortion(audio, sr)
        if is_speed_distorted and speed_confidence > 0.5:
            corruption_types.append(CorruptionType.SPEED_DISTORTION)
            issues.append(f"⚡ Speed distortion detected: confidence = {speed_confidence:.2f}")
            confidence_scores.append(speed_confidence)
            
        # 11. Check for reverse speech
        is_reversed, reverse_confidence = self._detect_reverse_speech(audio, sr)
        if is_reversed and reverse_confidence > 0.5:
            corruption_types.append(CorruptionType.REVERSE_SPEECH)
            issues.append(f"🔄 Reverse speech detected: confidence = {reverse_confidence:.2f}")
            confidence_scores.append(reverse_confidence)
            
        # 12. Check for gibberish artifacts
        is_gibberish, gibberish_confidence = self._detect_gibberish_artifacts(audio, sr)
        if is_gibberish and gibberish_confidence > 0.5:
            corruption_types.append(CorruptionType.GIBBERISH_ARTIFACTS)
            issues.append(f"🗣️ Gibberish/artifacts detected: confidence = {gibberish_confidence:.2f}")
            confidence_scores.append(gibberish_confidence)
        
        # Calculate overall confidence
        if confidence_scores:
            overall_confidence = float(np.mean(confidence_scores))
        else:
            overall_confidence = 0.0
            
        return corruption_types, issues, overall_confidence
        
    def detect_corruption(self, file_path: str, 
                         generate_report: bool = True,
                         save_plots: bool = False) -> CorruptionReport:
        """
        Main method to detect corruption in an audio file
        
        Args:
            file_path: Path to audio file to analyze
            generate_report: Whether to generate detailed recommendations
            save_plots: Whether to save visualization plots
            
        Returns:
            CorruptionReport object with detailed analysis results
        """
        logger.info(f"🔍 Analyzing audio quality: {os.path.basename(file_path)}")
        
        try:
            # Load audio
            audio, sr = self.load_audio(file_path)
            
            # Compute quality metrics
            metrics = self._compute_quality_metrics(audio, sr)
            
            # Analyze corruption patterns
            corruption_types, issues, confidence = self._analyze_corruption_patterns(audio, sr, metrics)
            
            # Determine if corrupted
            is_corrupted = len(corruption_types) > 0 and confidence >= self.corruption_confidence_threshold
            
            # Generate recommendations
            recommendations = []
            if generate_report:
                recommendations = self._generate_recommendations(corruption_types, metrics)
                
            # Find corruption timestamps
            corruption_timestamps = []
            if is_corrupted:
                corruption_timestamps = self._find_corruption_timestamps(audio, sr, corruption_types)
                
            # Save plots if requested
            if save_plots and MATPLOTLIB_AVAILABLE:
                self._save_analysis_plots(audio, sr, file_path, metrics)
                
            report = CorruptionReport(
                is_corrupted=is_corrupted,
                corruption_types=corruption_types,
                confidence_score=confidence,
                quality_metrics=metrics,
                issues_found=issues,
                recommendations=recommendations,
                corruption_timestamps=corruption_timestamps
            )
            
            # Log results
            if is_corrupted:
                logger.warning(f"🚨 CORRUPTION DETECTED in {os.path.basename(file_path)}")
                logger.warning(f"   Types: {[ct.value for ct in corruption_types]}")
                logger.warning(f"   Confidence: {confidence:.2f}")
            else:
                logger.info(f"✅ Audio quality OK: {os.path.basename(file_path)}")
                
            return report
            
        except Exception as e:
            logger.error(f"❌ Error analyzing {file_path}: {e}")
            # Return empty report indicating analysis failure
            return CorruptionReport(
                is_corrupted=True,  # Assume corrupted if we can't analyze
                corruption_types=[CorruptionType.DIGITAL_ARTIFACTS],
                confidence_score=0.5,
                quality_metrics=QualityMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
                issues_found=[f"Analysis failed: {str(e)}"],
                recommendations=["Regenerate this audio chunk"],
                corruption_timestamps=[]
            )
            
    def _generate_recommendations(self, corruption_types: List[CorruptionType], 
                                metrics: QualityMetrics) -> List[str]:
        """Generate recommendations based on detected corruption"""
        recommendations = []
        
        if CorruptionType.SUDDEN_CUTOFF in corruption_types:
            recommendations.extend([
                "🔄 Regenerate this chunk - API response was truncated",
                "⚡ Try reducing chunk size or using safe chunk mode",
                "🔌 Check internet connection stability"
            ])
            
        if CorruptionType.EXCESSIVE_SILENCE in corruption_types:
            recommendations.extend([
                "🔇 Check input text for excessive whitespace",
                "📝 Verify text preprocessing is working correctly",
                "🔄 Regenerate with different prompt"
            ])
            
        if CorruptionType.STATIC_NOISE in corruption_types:
            recommendations.extend([
                "📡 API corruption detected - regenerate immediately",
                "🛡️ Enable safe chunk mode to reduce API stress",
                "⏳ Wait a few seconds before retrying"
            ])
            
        if CorruptionType.VOLUME_SPIKE in corruption_types:
            recommendations.extend([
                "🔊 Severe API corruption - regenerate required",
                "⚠️ May indicate API server issues",
                "🛡️ Use safe chunk mode and smaller chunks"
            ])
            
        if CorruptionType.CLIPPING in corruption_types:
            recommendations.extend([
                "📈 Audio levels too high - API configuration issue",
                "🔧 Check TTS voice settings",
                "🔄 Regenerate with different voice or prompt"
            ])
            
        if CorruptionType.LOW_QUALITY in corruption_types:
            recommendations.extend([
                "📉 Poor audio quality detected",
                "🎤 Try different narrator voice",
                "✨ Use more descriptive prompts for better quality"
            ])
            
        if CorruptionType.SPEED_DISTORTION in corruption_types:
            recommendations.extend([
                "⚡ Speed distortion detected - severe API corruption",
                "🔄 Regenerate immediately with safe chunk mode",
                "🛡️ Use smaller chunks to reduce API stress",
                "⏳ Wait before retrying - may indicate server overload"
            ])
            
        if CorruptionType.REVERSE_SPEECH in corruption_types:
            recommendations.extend([
                "🔄 Reverse speech corruption - critical API failure",
                "🚨 Regenerate immediately - this is severe corruption",
                "🛡️ Enable safe chunk mode and reduce chunk sizes",
                "📞 Consider reporting this to Google AI support"
            ])
            
        if CorruptionType.GIBBERISH_ARTIFACTS in corruption_types:
            recommendations.extend([
                "🗣️ Gibberish/artifacts detected - API processing failure",
                "🔄 Regenerate with different prompt or voice",
                "📝 Check input text for unusual characters or formatting",
                "🛡️ Use safe chunk mode for more reliable processing"
            ])
            
        if not recommendations:
            recommendations.append("✅ Audio quality is acceptable")
            
        return recommendations
        
    def _find_corruption_timestamps(self, audio: np.ndarray, sr: int,
                                  corruption_types: List[CorruptionType]) -> List[Tuple[float, float]]:
        """Find timestamps where corruption occurs"""
        timestamps = []
        
        if CorruptionType.SUDDEN_CUTOFF in corruption_types:
            # Find the last significant audio
            silence_segments = self._detect_silence_segments(audio, sr)
            if silence_segments:
                last_silence = silence_segments[-1]
                if last_silence[1] >= len(audio)/sr - 0.1:  # Ends with silence
                    timestamps.append((last_silence[0], last_silence[1]))
                    
        if CorruptionType.VOLUME_SPIKE in corruption_types:
            spikes = self._detect_volume_spikes(audio, sr)
            timestamps.extend(spikes)
            
        return timestamps
        
    def _save_analysis_plots(self, audio: np.ndarray, sr: int, 
                           file_path: str, metrics: QualityMetrics):
        """Save visualization plots of the analysis"""
        if not MATPLOTLIB_AVAILABLE:
            return
            
        try:
            fig, axes = plt.subplots(2, 2, figsize=(12, 8))
            fig.suptitle(f'Audio Analysis: {os.path.basename(file_path)}')
            
            # Time domain plot
            time = np.arange(len(audio)) / sr
            axes[0, 0].plot(time, audio)
            axes[0, 0].set_title('Waveform')
            axes[0, 0].set_xlabel('Time (s)')
            axes[0, 0].set_ylabel('Amplitude')
            
            # Frequency domain plot
            freqs = np.fft.rfftfreq(len(audio), 1/sr)
            fft_mag = np.abs(np.fft.rfft(audio))
            axes[0, 1].semilogx(freqs, 20*np.log10(fft_mag + 1e-10))
            axes[0, 1].set_title('Frequency Spectrum')
            axes[0, 1].set_xlabel('Frequency (Hz)')
            axes[0, 1].set_ylabel('Magnitude (dB)')
            
            # Spectrogram
            if LIBROSA_AVAILABLE:
                D = librosa.amplitude_to_db(np.abs(librosa.stft(audio)), ref=np.max)
                librosa.display.specshow(D, y_axis='hz', x_axis='time', sr=sr, ax=axes[1, 0])
                axes[1, 0].set_title('Spectrogram')
            else:
                axes[1, 0].text(0.5, 0.5, 'Spectrogram requires librosa', 
                              transform=axes[1, 0].transAxes, ha='center')
                
            # Energy plot
            frame_length = int(0.025 * sr)
            hop_length = int(0.010 * sr)
            frame_times = []
            energies = []
            
            for i in range(0, len(audio) - frame_length, hop_length):
                frame = audio[i:i + frame_length]
                energy = self._compute_rms_energy(frame)
                frame_times.append(i / sr)
                energies.append(20 * np.log10(energy + 1e-10))
                
            axes[1, 1].plot(frame_times, energies)
            axes[1, 1].axhline(y=self.silence_threshold, color='r', linestyle='--', 
                             label='Silence Threshold')
            axes[1, 1].set_title('Energy Over Time')
            axes[1, 1].set_xlabel('Time (s)')
            axes[1, 1].set_ylabel('Energy (dB)')
            axes[1, 1].legend()
            
            plt.tight_layout()
            
            # Save plot
            plot_path = file_path.replace('.wav', '_analysis.png')
            plt.savefig(plot_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.info(f"📊 Analysis plot saved: {plot_path}")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not save analysis plot: {e}")


def quick_corruption_check(file_path: str) -> bool:
    """
    Quick corruption check function for simple use cases
    
    Args:
        file_path: Path to audio file
        
    Returns:
        True if corruption detected, False otherwise
    """
    detector = AudioQualityDetector()
    report = detector.detect_corruption(file_path, generate_report=False)
    return report.is_corrupted


def analyze_audio_batch(file_paths: List[str], 
                       output_dir: Optional[str] = None) -> Dict[str, CorruptionReport]:
    """
    Analyze multiple audio files for corruption
    
    Args:
        file_paths: List of audio file paths
        output_dir: Optional directory to save analysis plots
        
    Returns:
        Dictionary mapping file paths to corruption reports
    """
    detector = AudioQualityDetector()
    results = {}
    
    logger.info(f"🔍 Analyzing {len(file_paths)} audio files...")
    
    for i, file_path in enumerate(file_paths, 1):
        logger.info(f"📁 Processing {i}/{len(file_paths)}: {os.path.basename(file_path)}")
        
        save_plots = output_dir is not None
        report = detector.detect_corruption(file_path, save_plots=save_plots)
        results[file_path] = report
        
    # Summary
    corrupted_count = sum(1 for report in results.values() if report.is_corrupted)
    logger.info(f"📊 Analysis complete: {corrupted_count}/{len(file_paths)} files corrupted")
    
    return results


if __name__ == "__main__":
    # Example usage and testing
    import sys
    
    if len(sys.argv) > 1:
        # Command line usage
        file_path = sys.argv[1]
        
        print("wowitsjack's Audio Quality Detector")
        print("=" * 50)
        
        detector = AudioQualityDetector()
        report = detector.detect_corruption(file_path, save_plots=True)
        
        print(f"\n📁 File: {file_path}")
        print(f"🔍 Corrupted: {'YES' if report.is_corrupted else 'NO'}")
        print(f"🎯 Confidence: {report.confidence_score:.2f}")
        
        if report.corruption_types:
            print(f"\n🚨 Corruption Types:")
            for ct in report.corruption_types:
                print(f"   • {ct.value}")
                
        if report.issues_found:
            print(f"\n⚠️ Issues Found:")
            for issue in report.issues_found:
                print(f"   • {issue}")
                
        if report.recommendations:
            print(f"\n💡 Recommendations:")
            for rec in report.recommendations:
                print(f"   • {rec}")
                
        print(f"\n📊 Quality Metrics:")
        metrics = report.quality_metrics
        print(f"   Duration: {metrics.duration:.2f}s")
        print(f"   RMS Energy: {metrics.rms_energy:.4f}")
        print(f"   Peak Amplitude: {metrics.peak_amplitude:.4f}")
        print(f"   Silence: {metrics.silence_percentage:.1f}%")
        print(f"   SNR: {metrics.snr_estimate:.1f} dB")
        print(f"   Clipping: {metrics.clipping_percentage:.2f}%")
        
    else:
        print("wowitsjack's Audio Quality Detector")
        print("Usage: python audio_quality_detector.py <audio_file>")
        print("\nThis module detects corruption in TTS-generated audio!")