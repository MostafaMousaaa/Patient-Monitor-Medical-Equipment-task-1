# Patient Monitoring System

![Patient Monitor](screenshots/monitor_preview.png)

## Overview

This patient monitoring system is a comprehensive medical simulation platform that displays real-time electrocardiogram (ECG) signals along with vital signs. The system includes automatic arrhythmia detection algorithms capable of identifying bradycardia, tachycardia, and atrial fibrillation, with alarm functionality to alert medical staff when abnormal heart rhythms are detected.

The project contains two implementations:
- **PyQt Implementation** - A desktop application with professional medical device styling
- **Dash Implementation** - A web-based interface that can run in any modern browser

## Features

### Waveform Displays
- **ECG Waveform**: High-fidelity electrocardiogram display with multiple lead options
- **Plethysmogram (SpO₂)**: Oxygen saturation waveform with realistic pulse characteristics
- **Respiration Waveform**: Visual representation of breathing patterns

### Vital Sign Monitoring
- Heart Rate (HR): Continuous monitoring with normal range 60-100 BPM
- Blood Pressure (NBP): Systolic/Diastolic representation
- Oxygen Saturation (SpO₂): Percentage display with normal range 95-100%
- Respiration Rate (RESP): Breaths per minute with normal range 12-20
- Temperature (TEMP): Patient temperature with normal range 36.5-37.5°C

### Arrhythmia Detection Algorithms
- **Bradycardia**: Detects heart rates below 60 BPM
- **Tachycardia**: Identifies heart rates above 100 BPM
- **Atrial Fibrillation**: Detects irregular heart rhythms characteristic of A-fib

### Clinical Alarms
- Visual and audible alarms for abnormal conditions
- Silence capability with automatic reset after 30 seconds
- Color-coded vital sign displays (green for normal, red for abnormal)

### Additional Features
- **Multiple ECG Lead Views**: Switch between leads I, II, III, and V1
- **Adjustable Display Speed**: Options for 12.5 mm/s, 25 mm/s, and 50 mm/s
- **Patient Information Display**: Shows patient ID, name, age, and room number
- **Data Loading**: Import ECG data from CSV files
- **Date and Time Display**: Real-time clock display

## Technical Implementation

### PyQt Implementation

The desktop application is built using PyQt5 with Matplotlib for waveform rendering. It follows professional medical device UI standards with a color scheme inspired by Philips patient monitors.

**Key components:**
- Custom vital sign display widgets
- Real-time waveform rendering
- R-peak detection algorithm for heart beat visualization
- Gradient styling for professional appearance
- High DPI support for modern displays

### Dash Implementation

The web-based interface uses Plotly Dash to create a responsive application that can be accessed from any device with a web browser. It maintains the same professional appearance as the PyQt version.

**Key components:**
- Responsive layout that works across different screen sizes
- Interactive waveform displays with Plotly
- Bootstrap components for consistent styling
- Web-standard interface elements
- Flask backend for data processing

## Installation and Setup

### Prerequisites
- Python 3.7 or higher
- Required packages

### PyQt Implementation

```bash
# Install required packages
pip install PyQt5 matplotlib numpy pandas

# Run the application
python task1.py
```

### Dash Implementation

```bash
# Install required packages
pip install dash dash-bootstrap-components plotly pandas numpy flask

# Run the application
python dash_monitor.py
```

After starting the Dash application, open a web browser and navigate to http://127.0.0.1:8050/

## Usage

1. **Start Monitoring**: Click the "Start" button to begin real-time monitoring
2. **Load ECG Data**: Use the "Load ECG" button to import custom ECG data from CSV files
3. **Adjust Display Speed**: Select from 12.5, 25, or 50 mm/s for the waveform display
4. **Respond to Alarms**: Click "Silence" when an alarm is triggered to temporarily mute it
5. **Reset Display**: Use the "Reset" button to restart monitoring from the beginning

## Arrhythmia Detection

The system uses the following methods to detect arrhythmias:

- **Bradycardia**: Detected when the heart rate falls below 60 BPM
- **Tachycardia**: Identified when the heart rate exceeds 100 BPM
- **Atrial Fibrillation**: Detected through a combination of heart rate variability and irregular intervals between beats

## Demo Data

The system includes simulated patient data with the following sections:
- 0-20s: Normal sinus rhythm
- 20-30s: Tachycardia episode
- 30-40s: Return to normal rhythm
- 40-50s: Bradycardia episode
- 50-60s: Return to normal rhythm

## Development

This project was developed as part of the Medical Instrumentation course at SBME. It demonstrates the application of signal processing techniques and medical device interface design principles.

## License

This project is available for academic and educational purposes.

## Authors

- SBME 26 Team
