#!/usr/bin/env python3
"""
Test script for wowitsjack's audio corruption detection system
Tests the detection system on real corrupted audio files
"""

import os
import sys
from audio_quality_detector import AudioQualityDetector, quick_corruption_check

def test_corruption_detection(test_paths=None):
    """Test the corruption detection system"""
    print("=" * 60)
    print("wowitsjack's Audio Corruption Detection Test")
    print("=" * 60)
    
    # Default test files if none provided
    if not test_paths:
        test_files = [
            "/home/user/Documents/GitHub/CHATTER/farmdiary_002_combined.mp3"  # Known speed corruption
        ]
    else:
        test_files = []
        for path in test_paths:
            if os.path.isfile(path):
                test_files.append(path)
            elif os.path.isdir(path):
                # Find all audio files in directory
                for filename in sorted(os.listdir(path)):
                    if filename.lower().endswith(('.wav', '.mp3', '.flac', '.m4a', '.ogg')):
                        test_files.append(os.path.join(path, filename))
            else:
                print(f"⚠️ Path not found: {path}")
    
    # Initialize detector
    detector = AudioQualityDetector()
    
    print(f"\nTesting {len(test_files)} audio file(s)...")
    
    for i, file_path in enumerate(test_files, 1):
        print(f"\n📁 Test {i}: {os.path.basename(file_path)}")
        print("-" * 50)
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            continue
            
        try:
            # Quick corruption check
            print("🔍 Running quick corruption check...")
            is_corrupted_quick = quick_corruption_check(file_path)
            print(f"Quick check result: {'CORRUPTED' if is_corrupted_quick else 'CLEAN'}")
            
            # Detailed analysis
            print("\n🔬 Running detailed analysis...")
            report = detector.detect_corruption(file_path, generate_report=True, save_plots=True)
            
            # Display results
            print(f"\n📊 ANALYSIS RESULTS:")
            print(f"   Corrupted: {'YES' if report.is_corrupted else 'NO'}")
            print(f"   Confidence: {report.confidence_score:.2f}")
            
            if report.corruption_types:
                print(f"\n🚨 Corruption Types Detected:")
                for corruption_type in report.corruption_types:
                    print(f"   • {corruption_type.value}")
                    
            if report.issues_found:
                print(f"\n⚠️ Issues Found:")
                for issue in report.issues_found:
                    print(f"   • {issue}")
                    
            if report.recommendations:
                print(f"\n💡 Recommendations:")
                for rec in report.recommendations:
                    print(f"   • {rec}")
                    
            # Quality metrics
            print(f"\n📈 Quality Metrics:")
            metrics = report.quality_metrics
            print(f"   Duration: {metrics.duration:.2f}s")
            print(f"   Sample Rate: {metrics.sample_rate} Hz")
            print(f"   RMS Energy: {metrics.rms_energy:.4f}")
            print(f"   Peak Amplitude: {metrics.peak_amplitude:.4f}")
            print(f"   Silence: {metrics.silence_percentage:.1f}%")
            print(f"   SNR: {metrics.snr_estimate:.1f} dB")
            print(f"   High Freq Energy: {metrics.high_freq_energy*100:.1f}%")
            print(f"   Spectral Centroid: {metrics.spectral_centroid:.0f} Hz")
            print(f"   Zero Crossing Rate: {metrics.zero_crossing_rate:.3f}")
            print(f"   Clipping: {metrics.clipping_percentage:.2f}%")
            
            if report.corruption_timestamps:
                print(f"\n⏰ Corruption Timestamps:")
                for start, end in report.corruption_timestamps:
                    print(f"   {start:.2f}s - {end:.2f}s")
                    
        except Exception as e:
            print(f"❌ Error analyzing {file_path}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

def test_integration():
    """Test integration with the TTS workflow"""
    print("\n" + "=" * 60)
    print("Testing Integration with TTS Workflow")
    print("=" * 60)
    
    # Test configuration
    from app import ENABLE_CORRUPTION_DETECTION, CORRUPTION_RETRY_ATTEMPTS, CORRUPTION_AUTO_SPLIT
    
    print(f"Configuration:")
    print(f"   Corruption Detection: {'ENABLED' if ENABLE_CORRUPTION_DETECTION else 'DISABLED'}")
    print(f"   Retry Attempts: {CORRUPTION_RETRY_ATTEMPTS}")
    print(f"   Auto Split: {'ENABLED' if CORRUPTION_AUTO_SPLIT else 'DISABLED'}")
    
    try:
        from app import AUDIO_QUALITY_DETECTION_AVAILABLE
        print(f"   Audio Libraries: {'AVAILABLE' if AUDIO_QUALITY_DETECTION_AVAILABLE else 'MISSING'}")
        
        if not AUDIO_QUALITY_DETECTION_AVAILABLE:
            print(f"\n⚠️ Audio processing libraries not available!")
            print(f"   Install with: pip install librosa scipy soundfile numpy")
            
    except Exception as e:
        print(f"   Error checking libraries: {e}")

if __name__ == "__main__":
    # Check if we're in the right directory
    if not os.path.exists("audio_quality_detector.py"):
        print("❌ Please run this script from the gemini-2-tts directory")
        sys.exit(1)
        
    # Get command line arguments
    test_paths = sys.argv[1:] if len(sys.argv) > 1 else None
        
    # Run tests
    test_corruption_detection(test_paths)
    test_integration()
    
    print(f"\n🎯 To install audio processing libraries:")
    print(f"   pip install librosa scipy soundfile numpy matplotlib")
    
    print(f"\n📚 Example usage in your TTS workflow:")
    print(f"   from audio_quality_detector import quick_corruption_check")
    print(f"   if quick_corruption_check('output.wav'):")
    print(f"       print('Corruption detected! Regenerating...')")