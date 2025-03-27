import numpy as np
import pandas as pd
from scipy import signal
from scipy.fft import fft
import pywt

class ECGAnalyzer:
    """Advanced ECG analysis tool for detecting various arrhythmias."""
    
    def __init__(self, sampling_rate=250):
        """Initialize the ECG analyzer with specific sampling rate."""
        self.sampling_rate = sampling_rate
        # Define normal ranges for various measurements
        self.normal_ranges = {
            'hr': (60, 100),              # Normal heart rate range (bpm)
            'rr_interval': (0.6, 1.0),    # Normal R-R interval range (seconds)
            'pr_interval': (0.12, 0.20),  # Normal PR interval range (seconds)
            'qrs_duration': (0.06, 0.10), # Normal QRS duration range (seconds)
            'qt_interval': (0.35, 0.45),  # Normal QT interval range (seconds)
        }
        
    def detect_r_peaks(self, ecg_signal, threshold_factor=0.6):
        """
        Detect R peaks in ECG signal using Pan-Tompkins algorithm.
        
        Args:
            ecg_signal (array): The ECG signal
            threshold_factor (float): Factor to adjust detection sensitivity
            
        Returns:
            array: Indices of the R peak locations
        """
        # Bandpass filter (5-15 Hz)
        nyq = 0.5 * self.sampling_rate
        low = 5 / nyq
        high = 15 / nyq
        b, a = signal.butter(3, [low, high], btype='band')
        filtered_ecg = signal.filtfilt(b, a, ecg_signal)
        
        # Derivative
        derivative = np.diff(filtered_ecg)
        squared = derivative ** 2
        
        # Moving window integration
        window_size = int(0.08 * self.sampling_rate)
        window = np.ones(window_size) / window_size
        integrated = np.convolve(squared, window, mode='same')
        
        # Find peaks with adaptive threshold
        threshold = threshold_factor * np.mean(integrated)
        peaks, _ = signal.find_peaks(integrated, height=threshold, 
                                    distance=int(0.2 * self.sampling_rate))
        
        # Adjust peaks to original signal if needed
        r_peaks = []
        search_window = int(0.025 * self.sampling_rate)
        
        for peak in peaks:
            if peak < search_window or peak >= len(ecg_signal) - search_window:
                continue
                
            # Find the maximum point in original signal around the detected peak
            search_start = max(0, peak - search_window)
            search_end = min(len(ecg_signal), peak + search_window)
            max_idx = search_start + np.argmax(ecg_signal[search_start:search_end])
            r_peaks.append(max_idx)
        
        return np.array(r_peaks)
    
    def analyze_rr_intervals(self, r_peaks):
        """
        Analyze R-R intervals for variability and irregularity.
        
        Args:
            r_peaks (array): Indices of R-peak locations
            
        Returns:
            dict: RR interval analysis results including:
                - rr_intervals: The intervals in samples
                - rr_intervals_sec: The intervals in seconds
                - average_hr: Average heart rate
                - sdnn: Standard deviation of NN intervals
                - rmssd: Root mean square of successive differences
                - pnn50: Percentage of successive RR intervals differing by >50 ms
                - irregularity: Boolean indicating if rhythm is irregular
                - bradycardia: Boolean indicating bradycardia
                - tachycardia: Boolean indicating tachycardia
        """
        if len(r_peaks) < 2:
            return None
            
        # Calculate R-R intervals in samples
        rr_intervals = np.diff(r_peaks)
        
        # Convert to seconds
        rr_intervals_sec = rr_intervals / self.sampling_rate
        
        # Heart rate calculation
        heart_rates = 60 / rr_intervals_sec
        average_hr = np.mean(heart_rates)
        
        # HRV metrics (time domain)
        sdnn = np.std(rr_intervals_sec)  # Standard deviation of NN intervals
        
        # RMSSD - Root mean square of successive differences
        rmssd = np.sqrt(np.mean(np.square(np.diff(rr_intervals_sec))))
        
        # pNN50 - Percentage of successive RR intervals differing by >50 ms
        differences = np.abs(np.diff(rr_intervals_sec))
        pnn50 = 100 * np.sum(differences > 0.05) / len(differences)
        
        # Determine if rhythm is irregular
        cv = sdnn / np.mean(rr_intervals_sec)  # Coefficient of variation
        irregularity = cv > 0.1 or pnn50 > 10
        
        # Detect bradycardia and tachycardia
        bradycardia = average_hr < self.normal_ranges['hr'][0]
        tachycardia = average_hr > self.normal_ranges['hr'][1]
        
        return {
            'rr_intervals': rr_intervals,
            'rr_intervals_sec': rr_intervals_sec,
            'average_hr': average_hr,
            'sdnn': sdnn,
            'rmssd': rmssd,
            'pnn50': pnn50,
            'irregularity': irregularity,
            'bradycardia': bradycardia,
            'tachycardia': tachycardia
        }
    
    def detect_p_waves(self, ecg_signal, r_peaks):
        """
        Detect P-waves and analyze their relationship to QRS complexes.
        
        Args:
            ecg_signal (array): The ECG signal
            r_peaks (array): Indices of R-peak locations
            
        Returns:
            dict: P wave analysis including:
                - p_present: Boolean array indicating if P wave was detected before each QRS
                - pr_intervals: PR intervals in seconds
                - p_wave_locations: Locations of detected P waves
                - afib_probability: Probability of atrial fibrillation based on P wave analysis
        """
        if len(r_peaks) < 2:
            return None
            
        # Filter for P wave detection (1-10 Hz bandpass is good for P waves)
        nyq = 0.5 * self.sampling_rate
        low = 1 / nyq
        high = 10 / nyq
        b, a = signal.butter(3, [low, high], btype='band')
        filtered_ecg = signal.filtfilt(b, a, ecg_signal)
        
        # Initialize results
        p_present = np.zeros(len(r_peaks), dtype=bool)
        pr_intervals = np.zeros(len(r_peaks))
        p_wave_locations = []
        
        # Search for P wave before each R peak
        search_window_sec = 0.2  # Search up to 200 ms before R peak
        search_window = int(search_window_sec * self.sampling_rate)
        
        for i, r_peak in enumerate(r_peaks):
            if r_peak <= search_window:
                continue
                
            # Define search area for P wave (PR interval typically 120-200ms)
            search_start = r_peak - search_window
            search_end = r_peak - int(0.05 * self.sampling_rate)  # End 50ms before R
            
            if search_end <= search_start:
                continue
                
            # Extract segment for P wave search
            segment = filtered_ecg[search_start:search_end]
            
            # Find local maxima that could be P waves
            p_candidates, _ = signal.find_peaks(segment, height=0.05*np.max(segment),
                                             distance=int(0.05*self.sampling_rate))
                                             
            if len(p_candidates) > 0:
                # Take the most prominent peak as the P wave
                p_idx = p_candidates[np.argmax(segment[p_candidates])]
                p_loc = search_start + p_idx
                p_wave_locations.append(p_loc)
                p_present[i] = True
                
                # Calculate PR interval in seconds
                pr_intervals[i] = (r_peak - p_loc) / self.sampling_rate
        
        # Calculate AFIB probability based on P wave analysis
        p_wave_percentage = np.sum(p_present) / len(r_peaks) * 100
        p_wave_regularity = 0
        
        if len(p_wave_locations) > 1:
            pp_intervals = np.diff(p_wave_locations)
            p_wave_regularity = np.std(pp_intervals) / np.mean(pp_intervals)
            
        # High percentage of missing P waves and irregular P waves suggest AFIB
        afib_probability = 0
        if p_wave_percentage < 70:  # Less than 70% of QRS complexes have preceding P waves
            afib_probability = (100 - p_wave_percentage) / 30  # Scale to 0-100%
            
        if p_wave_regularity > 0.2:  # Irregular P wave timings
            afib_probability += 20 * p_wave_regularity  # Add penalty for irregularity
            
        afib_probability = min(100, afib_probability)  # Cap at 100%
        
        return {
            'p_present': p_present,
            'pr_intervals': pr_intervals,
            'p_wave_locations': p_wave_locations,
            'afib_probability': afib_probability
        }
    
    def analyze_qrs_morphology(self, ecg_signal, r_peaks):
        """
        Analyze QRS morphology to detect possible ventricular arrhythmias.
        
        Args:
            ecg_signal (array): The ECG signal
            r_peaks (array): Indices of R-peak locations
            
        Returns:
            dict: QRS morphology analysis including:
                - qrs_durations: QRS durations in seconds
                - qrs_areas: Areas under QRS complexes
                - qrs_amplitudes: QRS amplitudes
                - abnormal_qrs: Boolean array indicating abnormal QRS complexes
                - pvc_locations: Indices of potential PVCs (premature ventricular contractions)
                - lbbb_probability: Probability of left bundle branch block
                - rbbb_probability: Probability of right bundle branch block
        """
        if len(r_peaks) < 2:
            return None
            
        # Initialize result containers
        qrs_durations = np.zeros(len(r_peaks))
        qrs_areas = np.zeros(len(r_peaks))
        qrs_amplitudes = np.zeros(len(r_peaks))
        qrs_areas_norm = np.zeros(len(r_peaks))
        abnormal_qrs = np.zeros(len(r_peaks), dtype=bool)
        pvc_locations = []
        
        # QRS complex typically spans 80-120ms (0.08-0.12s)
        qrs_half_width = int(0.06 * self.sampling_rate)  # 60ms on each side
        
        # Analyze each QRS complex
        for i, r_peak in enumerate(r_peaks):
            if r_peak - qrs_half_width < 0 or r_peak + qrs_half_width >= len(ecg_signal):
                continue
                
            # Extract QRS region
            qrs_start = max(0, r_peak - qrs_half_width)
            qrs_end = min(len(ecg_signal), r_peak + qrs_half_width)
            qrs_complex = ecg_signal[qrs_start:qrs_end]
            
            # Find Q and S points (local minima before and after R)
            first_half = qrs_complex[:qrs_half_width]
            second_half = qrs_complex[qrs_half_width:]
            
            # Find Q point (local minimum before R)
            q_idx = np.argmin(first_half)
            q_point = qrs_start + q_idx
            
            # Find S point (local minimum after R)
            s_idx = np.argmin(second_half)
            s_point = qrs_start + qrs_half_width + s_idx
            
            # Calculate QRS duration
            qrs_durations[i] = (s_point - q_point) / self.sampling_rate
            
            # Calculate area under the curve
            qrs_areas[i] = np.trapz(np.abs(ecg_signal[q_point:s_point]))
            
            # Calculate amplitude (R peak height)
            r_height = ecg_signal[r_peak]
            q_depth = ecg_signal[q_point]
            s_depth = ecg_signal[s_point]
            qrs_amplitudes[i] = r_height - min(q_depth, s_depth)
        
        # Normalize areas by amplitude for comparison
        non_zero_amps = qrs_amplitudes > 0
        qrs_areas_norm[non_zero_amps] = qrs_areas[non_zero_amps] / qrs_amplitudes[non_zero_amps]
        
        # Identify baseline values from majority of beats
        median_duration = np.median(qrs_durations[qrs_durations > 0])
        median_area_norm = np.median(qrs_areas_norm[qrs_areas_norm > 0])
        
        # Identify abnormal QRS complexes
        for i in range(len(r_peaks)):
            # Check for wide QRS (potential bundle branch block or ventricular rhythm)
            if qrs_durations[i] > 0.12:  # 120ms is threshold for wide QRS
                abnormal_qrs[i] = True
            
            # Check for abnormal morphology based on area
            if qrs_areas_norm[i] > 1.5 * median_area_norm or qrs_areas_norm[i] < 0.5 * median_area_norm:
                abnormal_qrs[i] = True
                
            # PVC detection logic:
            # 1. Premature beat (short RR interval)
            # 2. Wide QRS complex
            # 3. Different morphology (area)
            if i > 0 and i < len(r_peaks)-1:
                rr_interval = (r_peaks[i] - r_peaks[i-1]) / self.sampling_rate
                next_rr = (r_peaks[i+1] - r_peaks[i]) / self.sampling_rate
                
                if (rr_interval < 0.8 * median_duration and  # Premature
                    next_rr > 1.2 * median_duration and      # Compensatory pause
                    qrs_durations[i] > 0.12 and             # Wide QRS
                    (qrs_areas_norm[i] < 0.7 * median_area_norm or 
                     qrs_areas_norm[i] > 1.3 * median_area_norm)):  # Different morphology
                    pvc_locations.append(r_peaks[i])
        
        # Check for bundle branch blocks
        # LBBB: wide QRS, predominantly positive in V1, deep S wave
        # RBBB: wide QRS, RSR' pattern in V1 (we'll approximate with our limited data)
        
        lbbb_probability = 0
        rbbb_probability = 0
        
        # Count wide QRS complexes
        wide_qrs_count = np.sum(qrs_durations > 0.12)
        if wide_qrs_count > 0.7 * len(qrs_durations):  # If >70% of QRS are wide
            # We can only approximate since we don't have 12-lead data
            # Check for negative dominant deflection (approximating LBBB)
            neg_deflection = np.zeros(len(r_peaks), dtype=bool)
            for i, r_peak in enumerate(r_peaks):
                if r_peak - qrs_half_width < 0 or r_peak + qrs_half_width >= len(ecg_signal):
                    continue
                    
                # Get QRS complex
                qrs_start = max(0, r_peak - qrs_half_width)
                qrs_end = min(len(ecg_signal), r_peak + qrs_half_width)
                qrs_complex = ecg_signal[qrs_start:qrs_end]
                
                # Check if area of negative deflection is larger than positive
                pos_area = np.sum(np.maximum(0, qrs_complex))
                neg_area = np.sum(np.minimum(0, qrs_complex)) * -1
                
                neg_deflection[i] = neg_area > pos_area
            
            # If mostly negative deflections, likely LBBB (in lead II perspective)
            lbbb_count = np.sum(neg_deflection)
            
            if lbbb_count > 0.7 * len(neg_deflection):
                lbbb_probability = 80
            elif lbbb_count > 0.5 * len(neg_deflection):
                lbbb_probability = 50
                
            # If not predominantly negative, check for notched R wave pattern (RBBB)
            # This is very simplified and would be more accurate with 12-lead ECG
            notched_r = 0
            for i, r_peak in enumerate(r_peaks):
                if not neg_deflection[i]:  # Only check beats that aren't negative dominant
                    if r_peak - qrs_half_width < 0 or r_peak + qrs_half_width >= len(ecg_signal):
                        continue
                        
                    # Get second half of QRS (after R peak)
                    qrs_second_half = ecg_signal[r_peak:r_peak + qrs_half_width]
                    
                    # Look for a second peak after R (the R' of RSR')
                    if len(qrs_second_half) > 10:  # Ensure enough data points
                        r_prime_candidates, _ = signal.find_peaks(qrs_second_half)
                        if len(r_prime_candidates) > 0 and r_prime_candidates[0] < 0.06 * self.sampling_rate:
                            notched_r += 1
                            
            if notched_r > 0.3 * len(r_peaks):  # If >30% have RSR' pattern
                rbbb_probability = 70
            elif notched_r > 0.1 * len(r_peaks):  # If >10% have RSR' pattern
                rbbb_probability = 40
        
        return {
            'qrs_durations': qrs_durations,
            'qrs_areas': qrs_areas,
            'qrs_amplitudes': qrs_amplitudes,
            'abnormal_qrs': abnormal_qrs,
            'pvc_locations': pvc_locations,
            'wide_qrs_percentage': 100 * wide_qrs_count / len(qrs_durations),
            'lbbb_probability': lbbb_probability,
            'rbbb_probability': rbbb_probability
        }
    
    def frequency_domain_analysis(self, ecg_signal, r_peaks):
        """
        Perform frequency domain analysis on ECG signal and RR intervals.
        
        Args:
            ecg_signal (array): The ECG signal
            r_peaks (array): Indices of R-peak locations
            
        Returns:
            dict: Frequency domain analysis including:
                - ecg_fft: FFT of the ECG signal
                - ecg_freqs: Frequency bins
                - ecg_psd: Power spectral density
                - hrv_lf: Low frequency power (0.04-0.15 Hz)
                - hrv_hf: High frequency power (0.15-0.4 Hz)
                - lf_hf_ratio: LF/HF ratio (sympatho-vagal balance)
                - wavelet_coeffs: Wavelet transform coefficients
                - afib_probability: AF probability based on frequency analysis
        """
        if len(ecg_signal) < 1000 or len(r_peaks) < 10:
            return None
            
        # FFT of the ECG signal
        n = len(ecg_signal)
        ecg_fft = fft(ecg_signal)
        ecg_freqs = np.fft.fftfreq(n, 1/self.sampling_rate)
        ecg_psd = np.abs(ecg_fft)**2
        
        # Only keep positive frequencies for display
        positive_freqs = ecg_freqs > 0
        ecg_freqs = ecg_freqs[positive_freqs]
        ecg_psd = ecg_psd[positive_freqs]
        
        # Normalize PSD
        ecg_psd = ecg_psd / np.max(ecg_psd)
        
        # HRV frequency analysis
        if len(r_peaks) < 10:
            return {
                'ecg_fft': ecg_fft,
                'ecg_freqs': ecg_freqs,
                'ecg_psd': ecg_psd,
                'hrv_lf': None,
                'hrv_hf': None,
                'lf_hf_ratio': None,
                'wavelet_coeffs': None,
                'afib_probability': None
            }
            
        # Get RR intervals in seconds
        rr_intervals = np.diff(r_peaks) / self.sampling_rate
        
        # Interpolate RR intervals to get evenly sampled signal
        # Use cubic spline interpolation at 4 Hz
        t_rr = np.cumsum(rr_intervals)
        t_rr = np.insert(t_rr, 0, 0)  # Add zero at the beginning
        
        # Create regular time grid for interpolation
        fs_interp = 4  # 4 Hz is standard for HRV analysis
        t_interp = np.arange(0, t_rr[-1], 1/fs_interp)
        
        # Interpolate RR intervals
        rr_interp = np.interp(t_interp, t_rr, np.concatenate(([rr_intervals[0]], rr_intervals)))
        
        # Remove linear trend
        rr_interp = signal.detrend(rr_interp)
        
        # Calculate PSD using Welch method for HRV
        f_hrv, psd_hrv = signal.welch(rr_interp, fs=fs_interp, nperseg=256)
        
        # Calculate LF and HF power
        lf_mask = (f_hrv >= 0.04) & (f_hrv <= 0.15)
        hf_mask = (f_hrv >= 0.15) & (f_hrv <= 0.4)
        
        hrv_lf = np.sum(psd_hrv[lf_mask])
        hrv_hf = np.sum(psd_hrv[hf_mask])
        
        # LF/HF ratio (indicator of sympatho-vagal balance)
        lf_hf_ratio = hrv_lf / hrv_hf if hrv_hf > 0 else float('inf')
        
        # Use redundancy of LF component to detect AFIB
        # AFIB typically has reduced LF power and increased HF power
        total_power = np.sum(psd_hrv)
        lf_norm = hrv_lf / total_power if total_power > 0 else 0
        hf_norm = hrv_hf / total_power if total_power > 0 else 0
        
        afib_probability = 0
        
        # AFIB often has low LF/HF ratio and high HF component
        if lf_hf_ratio < 0.5:
            afib_probability += 30
        if hf_norm > 0.5:
            afib_probability += 30
            
        # Calculate wavelet decomposition for QRS pattern analysis
        # We'll use 4-level wavelet decomposition with db4 wavelet
        # This is good for extracting morphological features
        try:
            coeffs = pywt.wavedec(ecg_signal, 'db4', level=4)
            
            # Check high frequency noise (D1 coefficient energy)
            d1_energy = np.sum(coeffs[1]**2)
            d2_energy = np.sum(coeffs[2]**2)
            total_energy = sum(np.sum(c**2) for c in coeffs)
            
            # High d1_energy/total_energy ratio indicates noise or AFib
            noise_ratio = d1_energy / total_energy if total_energy > 0 else 0
            if noise_ratio > 0.4:  # High noise or irregularity
                afib_probability += 20
            
            wavelet_coeffs = coeffs
        except:
            wavelet_coeffs = None
        
        # Cap probability at 100%
        afib_probability = min(afib_probability, 100)
        
        return {
            'ecg_fft': ecg_fft,
            'ecg_freqs': ecg_freqs,
            'ecg_psd': ecg_psd,
            'hrv_lf': hrv_lf,
            'hrv_hf': hrv_hf,
            'lf_hf_ratio': lf_hf_ratio,
            'wavelet_coeffs': wavelet_coeffs,
            'afib_probability': afib_probability
        }

    def analyze_ecg(self, ecg_signal):
        """
        Perform comprehensive ECG analysis.
        
        Args:
            ecg_signal (array): The ECG signal
            
        Returns:
            dict: Comprehensive analysis results with all metrics and arrhythmia probabilities
        """
        # Detect R peaks
        r_peaks = self.detect_r_peaks(ecg_signal)
        
        if len(r_peaks) < 2:
            return {
                'error': 'Insufficient R peaks detected for analysis',
                'r_peaks': r_peaks
            }
            
        # Analyze RR intervals
        rr_analysis = self.analyze_rr_intervals(r_peaks)
        
        # Detect P waves and analyze PR intervals
        p_wave_analysis = self.detect_p_waves(ecg_signal, r_peaks)
        
        # Analyze QRS morphology
        qrs_analysis = self.analyze_qrs_morphology(ecg_signal, r_peaks)
        
        # Perform frequency domain analysis
        freq_analysis = self.frequency_domain_analysis(ecg_signal, r_peaks)
        
        # Combine all analysis results
        result = {
            'r_peaks': r_peaks,
            'rr_analysis': rr_analysis,
            'p_wave_analysis': p_wave_analysis,
            'qrs_analysis': qrs_analysis,
            'freq_analysis': freq_analysis,
        }
        
        # Determine arrhythmia probabilities by combining multiple factors
        arrhythmias = self.determine_arrhythmias(result)
        result['arrhythmias'] = arrhythmias
        
        return result
    
    def determine_arrhythmias(self, analysis_results):
        """
        Determine arrhythmia types and probabilities based on all analyses.
        
        Args:
            analysis_results (dict): Results from all analysis methods
            
        Returns:
            dict: Arrhythmia probabilities and confidence levels
        """
        arrhythmias = {
            'sinus_rhythm': {'probability': 100, 'confidence': 'high'},
            'bradycardia': {'probability': 0, 'confidence': 'low'}, 
            'tachycardia': {'probability': 0, 'confidence': 'low'},
            'afib': {'probability': 0, 'confidence': 'low'},
            'pvc': {'probability': 0, 'confidence': 'low'},
            'heart_block': {'probability': 0, 'confidence': 'low'},
            'lbbb': {'probability': 0, 'confidence': 'low'},
            'rbbb': {'probability': 0, 'confidence': 'low'},
        }
        
        # Extract required components from the analysis
        rr = analysis_results.get('rr_analysis', {})
        p_wave = analysis_results.get('p_wave_analysis', {})
        qrs = analysis_results.get('qrs_analysis', {})
        freq = analysis_results.get('freq_analysis', {})
        
        if not rr:
            return arrhythmias
            
        # Initialize evidence counters for arrhythmia types
        evidence = {k: 0 for k in arrhythmias.keys()}
        
        # Check for bradycardia
        if rr.get('bradycardia', False):
            arrhythmias['bradycardia']['probability'] = 90
            arrhythmias['bradycardia']['confidence'] = 'high'
            arrhythmias['sinus_rhythm']['probability'] -= 30  # Reduce normal probability
            evidence['bradycardia'] += 1
        
        # Check for tachycardia
        if rr.get('tachycardia', False):
            arrhythmias['tachycardia']['probability'] = 90
            arrhythmias['tachycardia']['confidence'] = 'high'
            arrhythmias['sinus_rhythm']['probability'] -= 30
            evidence['tachycardia'] += 1
        
        # Check for atrial fibrillation (combining multiple evidence sources)
        afib_probability = 0
        afib_evidence = 0
        
        # Evidence from P wave analysis
        if p_wave and p_wave.get('afib_probability', 0) > 50:
            afib_probability += p_wave.get('afib_probability', 0) * 0.4  # 40% weight
            afib_evidence += 1
        
        # Evidence from RR irregularity
        if rr.get('irregularity', False) and rr.get('rmssd', 0) > 0.1:
            afib_probability += 60  # Add 60% probability for irregular RR with high RMSSD
            afib_evidence += 1
            
        # Evidence from frequency analysis
        if freq and freq.get('afib_probability', 0) > 50:
            afib_probability += freq.get('afib_probability', 0) * 0.3  # 30% weight
            afib_evidence += 1
        
        # Only diagnose AFib if we have multiple pieces of evidence
        if afib_evidence >= 2:
            arrhythmias['afib']['probability'] = min(95, afib_probability)
            arrhythmias['afib']['confidence'] = 'medium' if afib_evidence == 2 else 'high'
            # AFib makes sinus rhythm very unlikely
            arrhythmias['sinus_rhythm']['probability'] = max(0, 
                arrhythmias['sinus_rhythm']['probability'] - arrhythmias['afib']['probability'])
            evidence['afib'] = afib_evidence
        
        # Check for PVCs
        if qrs and len(qrs.get('pvc_locations', [])) > 0:
            pvc_count = len(qrs.get('pvc_locations', []))
            r_peaks_count = len(analysis_results.get('r_peaks', []))
            
            if r_peaks_count > 0:
                pvc_percentage = (pvc_count / r_peaks_count) * 100
                
                if pvc_percentage > 10:
                    arrhythmias['pvc']['probability'] = 90
                    arrhythmias['pvc']['confidence'] = 'high'
                    arrhythmias['sinus_rhythm']['probability'] -= 50
                elif pvc_percentage > 5:
                    arrhythmias['pvc']['probability'] = 70
                    arrhythmias['pvc']['confidence'] = 'medium'
                    arrhythmias['sinus_rhythm']['probability'] -= 30
                else:
                    arrhythmias['pvc']['probability'] = 50
                    arrhythmias['pvc']['confidence'] = 'low'
                    arrhythmias['sinus_rhythm']['probability'] -= 10
                
                evidence['pvc'] = pvc_count
        
        # Check for heart block via PR interval
        if p_wave and len(p_wave.get('pr_intervals', [])) > 0:
            pr_intervals = np.array(p_wave.get('pr_intervals', []))
            pr_intervals = pr_intervals[pr_intervals > 0]
            
            if len(pr_intervals) > 0:
                # First-degree AV block: PR interval > 200 ms
                avg_pr = np.mean(pr_intervals)
                if avg_pr > 0.2:  # > 200 ms
                    arrhythmias['heart_block']['probability'] = 80
                    arrhythmias['heart_block']['confidence'] = 'high'
                    arrhythmias['sinus_rhythm']['probability'] -= 30
                    evidence['heart_block'] += 1
                
                # Second-degree AV block: some P waves not followed by QRS
                p_present = p_wave.get('p_present', [])
                missing_qrs = np.sum(p_present) - len(analysis_results.get('r_peaks', []))
                if missing_qrs > 0:
                    arrhythmias['heart_block']['probability'] = max(
                        arrhythmias['heart_block']['probability'], 70)
                    arrhythmias['heart_block']['confidence'] = 'medium'
                    arrhythmias['sinus_rhythm']['probability'] -= 40
                    evidence['heart_block'] += 1
        
        # Check for bundle branch blocks
        if qrs:
            lbbb_prob = qrs.get('lbbb_probability', 0)
            rbbb_prob = qrs.get('rbbb_probability', 0)
            
            if lbbb_prob > 60:
                arrhythmias['lbbb']['probability'] = lbbb_prob
                arrhythmias['lbbb']['confidence'] = 'medium'
                arrhythmias['sinus_rhythm']['probability'] -= 20
                evidence['lbbb'] += 1
                
            if rbbb_prob > 60:
                arrhythmias['rbbb']['probability'] = rbbb_prob
                arrhythmias['rbbb']['confidence'] = 'medium'
                arrhythmias['sinus_rhythm']['probability'] -= 20
                evidence['rbbb'] += 1
        
        # Ensure probabilities are in valid range
        for k, v in arrhythmias.items():
            arrhythmias[k]['probability'] = max(0, min(100, v['probability']))
        
        # If any arrhythmia has high probability, reduce sinus rhythm probability
        if any(v['probability'] > 70 for k, v in arrhythmias.items() if k != 'sinus_rhythm'):
            arrhythmias['sinus_rhythm']['probability'] = max(10, arrhythmias['sinus_rhythm']['probability'])
        
        # Add the evidence counts to the result
        arrhythmias['evidence_counts'] = evidence
        
        return arrhythmias
        
    def load_ecg_file(self, file_path):
        """
        Load ECG data from a file.
        
        Args:
            file_path (str): Path to the ECG file
            
        Returns:
            tuple: (ecg_data, sampling_rate)
        """
        # Handle different file types
        if file_path.endswith('.csv'):
            try:
                # Try to load as CSV with headers
                df = pd.read_csv(file_path)
                
                # Common column names for ECG data
                possible_columns = ['ecg', 'ECG', 'signal', 'data', 'values', 'amplitude']
                
                # Find the first column that matches
                ecg_column = None
                for col in possible_columns:
                    if col in df.columns:
                        ecg_column = col
                        break
                
                # If no match, use the first numeric column
                if ecg_column is None:
                    for col in df.columns:
                        if np.issubdtype(df[col].dtype, np.number):
                            ecg_column = col
                            break
                
                if ecg_column:
                    return df[ecg_column].values, self.sampling_rate
                else:
                    # If no suitable column found, try loading without headers
                    df = pd.read_csv(file_path, header=None)
                    # Use the first column
                    return df[0].values, self.sampling_rate
                    
            except Exception as e:
                raise Exception(f"Error loading CSV file: {e}")
                
        elif file_path.endswith('.txt'):
            try:
                # Try to load as simple text file with one value per line
                data = np.loadtxt(file_path)
                return data, self.sampling_rate
            except:
                try:
                    # Try with comma separator
                    data = np.loadtxt(file_path, delimiter=',')
                    # If multiple columns, use the first one
                    if len(data.shape) > 1:
                        return data[:, 0], self.sampling_rate
                    return data, self.sampling_rate
                except Exception as e:
                    raise Exception(f"Error loading text file: {e}")
                    
        elif file_path.endswith('.npy'):
            try:
                # Load NumPy array
                data = np.load(file_path)
                return data, self.sampling_rate
            except Exception as e:
                raise Exception(f"Error loading NumPy file: {e}")
        else:
            raise Exception("Unsupported file format. Please use .csv, .txt, or .npy files.")
    
    def preprocess_signal(self, ecg_signal):
        """
        Preprocess ECG signal to remove baseline wander and noise.
        
        Args:
            ecg_signal (array): Raw ECG signal
            
        Returns:
            array: Preprocessed ECG signal
        """
        # Remove baseline wander using high-pass filter
        nyq = 0.5 * self.sampling_rate
        high_pass_cutoff = 0.5 / nyq  # 0.5 Hz cutoff
        b, a = signal.butter(2, high_pass_cutoff, btype='high')
        ecg_filtered = signal.filtfilt(b, a, ecg_signal)
        
        # Remove high-frequency noise using low-pass filter
        low_pass_cutoff = 40 / nyq  # 40 Hz cutoff
        b, a = signal.butter(3, low_pass_cutoff, btype='low')
        ecg_filtered = signal.filtfilt(b, a, ecg_filtered)
        
        # Notch filter for 50/60 Hz power line interference
        # Use 50 Hz for Europe/Asia, 60 Hz for Americas
        for notch_freq in [50, 60]:
            notch_cutoff = notch_freq / nyq
            b, a = signal.iirnotch(notch_cutoff, 30, self.sampling_rate)
            ecg_filtered = signal.filtfilt(b, a, ecg_filtered)
        
        return ecg_filtered
