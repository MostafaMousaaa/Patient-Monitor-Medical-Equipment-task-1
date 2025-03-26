# Project 01 
# Patient Monitor 
# Statement: You are required Develop a graphical user interface (GUI) for a 
# patient monitoring system that displays real-time or recorded electrocardiogram 
# (ECG) signals. The system must incorporate algorithms to automatically detect 
# and classify at least three types of arrhythmias and trigger alarms to alert 
# users(staff) when abnormal heart rhythms are detected.

import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QComboBox,
                             QFileDialog, QMessageBox, QFrame, QGridLayout,
                             QTabWidget, QSplitter, QGroupBox)
from PyQt5.QtCore import QTimer, Qt, QSize
from PyQt5.QtGui import QColor, QFont, QPalette, QLinearGradient, QBrush

class VitalSignDisplay(QFrame):
    def __init__(self, title, unit, normal_range, value="--", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        
        # Set dark background with blue gradient like professional monitors
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(30, 30, 60))
        gradient.setColorAt(1, QColor(10, 10, 30))
        
        palette = self.palette()
        palette.setBrush(QPalette.Window, QBrush(gradient))
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        
        # Set minimum size for each vital sign display
        self.setMinimumSize(QSize(180, 120))
        
        layout = QVBoxLayout(self)
        
        # Title with parameter name
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: cyan; font-size: 14px; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)
        
        # Value display - large font for good visibility
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("color: #00FF00; font-size: 32px; font-weight: bold;")
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)
        
        # Unit and normal range
        info_layout = QHBoxLayout()
        
        self.unit_label = QLabel(unit)
        self.unit_label.setStyleSheet("color: white; font-size: 12px;")
        info_layout.addWidget(self.unit_label)
        
        self.range_label = QLabel(f"Range: {normal_range}")
        self.range_label.setStyleSheet("color: #AAAAAA; font-size: 10px;")
        self.range_label.setAlignment(Qt.AlignRight)
        info_layout.addWidget(self.range_label)
        
        layout.addLayout(info_layout)
        
        # Store normal range for alarm checking
        self.parse_normal_range(normal_range)
    
    def update_value(self, value):
        if isinstance(value, (int, float)):
            # Format numeric values nicely
            if value >= 100:
                formatted_value = f"{value:.0f}"
            else:
                formatted_value = f"{value:.1f}"
        else:
            formatted_value = str(value)
        
        self.value_label.setText(formatted_value)
        
        # Update color based on value (green if normal, red if out of range)
        if self.is_in_normal_range(value):
            self.value_label.setStyleSheet("color: #00FF00; font-size: 32px; font-weight: bold;")
        else:
            self.value_label.setStyleSheet("color: #FF0000; font-size: 32px; font-weight: bold;")
    
    def parse_normal_range(self, range_str):
        # Parse ranges like "60-100", "95-100%", etc.
        try:
            # Handle special case for blood pressure 
            if '/' in range_str:
                # Blood pressure has format like "120/80"
                systolic, diastolic = range_str.split('/')
                self.min_value = None  # Complex comparison handled separately
                self.max_value = None
                self.is_bp = True
                self.systolic_target = int(systolic)
                self.diastolic_target = int(diastolic)
            else:
                # Regular range format "min-max"
                range_str = range_str.replace('%', '').strip()
                parts = range_str.split('-')
                self.min_value = float(parts[0])
                self.max_value = float(parts[1])
                self.is_bp = False
        except:
            # Fallback if parsing fails
            self.min_value = 0
            self.max_value = 100
            self.is_bp = False
    
    def is_in_normal_range(self, value):
        if isinstance(value, str) or value is None:
            return True  # Can't determine if a string is in range
        
        if self.is_bp:
            try:
                # Blood pressure format: "120/80"
                if isinstance(value, str) and '/' in value:
                    sys_val, dia_val = value.split('/')
                    systolic = int(sys_val)
                    diastolic = int(dia_val)
                    
                    # Simplified BP check (in practice would be more nuanced)
                    return (systolic <= self.systolic_target + 20 and 
                            systolic >= self.systolic_target - 20 and 
                            diastolic <= self.diastolic_target + 10 and 
                            diastolic >= self.diastolic_target - 10)
                return True
            except:
                return True  # If can't parse, assume normal
        
        # Regular range check
        return self.min_value <= value <= self.max_value


class ECGMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Professional Patient Monitoring System")
        self.setGeometry(50, 50, 1500, 900)
        self.setStyleSheet("background-color: #000020;")  # Dark blue background like medical monitors
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Initialize data attributes before creating sections
        self.ecg_data = None
        self.current_index = 0
        self.sampling_rate = 250  # Hz
        self.display_seconds = 10  # seconds of data to display at once
        self.is_monitoring = False
        self.alarm_active = False
        
        # Upper section with patient info and vital signs
        self.create_header_section()
        
        # Main section with tabs for different visualizations
        self.create_main_section()
        
        # Control section
        self.create_control_section()
        
        # Initialize timer for real-time simulation
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_monitor)
        
        # Generate initial sample data
        self.generate_sample_data()
        
        # Put monitor in demo mode
        self.monitor_btn.setEnabled(True)
        
        self.show()
        
        # Start monitoring automatically in demo mode
        self.toggle_monitoring()
    
    def create_header_section(self):
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #000030;")
        header_layout = QHBoxLayout(header_frame)
        
        # Patient info
        info_box = QGroupBox("Patient Information")
        info_box.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 1px solid #3080A0;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        info_layout = QGridLayout(info_box)
        
        # Add patient information with medical styling
        self.add_info_field(info_layout, "Patient ID:", "P12345", 0, 0)
        self.add_info_field(info_layout, "Name:", "John Doe", 0, 2)
        self.add_info_field(info_layout, "Age/Sex:", "45/M", 1, 0)
        self.add_info_field(info_layout, "Room:", "ICU-107", 1, 2)
        self.add_info_field(info_layout, "Physician:", "Dr. Smith", 2, 0)
        self.add_info_field(info_layout, "Admission:", "2023-05-01", 2, 2)
        
        header_layout.addWidget(info_box, 1)
        
        # Time and system status
        time_box = QGroupBox()
        time_box.setStyleSheet("border: none;")
        time_layout = QVBoxLayout(time_box)
        
        self.date_time_label = QLabel("2023-05-02  14:30:45")
        self.date_time_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        self.date_time_label.setAlignment(Qt.AlignCenter)
        time_layout.addWidget(self.date_time_label)
        
        self.system_status_label = QLabel("System Status: NORMAL")
        self.system_status_label.setStyleSheet("color: #00FF00; font-size: 14px; font-weight: bold;")
        self.system_status_label.setAlignment(Qt.AlignCenter)
        time_layout.addWidget(self.system_status_label)
        
        header_layout.addWidget(time_box, 1)
        
        self.main_layout.addWidget(header_frame, 1)
        
        # Create vitals grid layout with all vital parameters
        self.create_vitals_section()
    
    def add_info_field(self, layout, label_text, value_text, row, col):
        label = QLabel(label_text)
        label.setStyleSheet("color: #88CCFF; font-size: 12px;")
        layout.addWidget(label, row, col)
        
        value = QLabel(value_text)
        value.setStyleSheet("color: white; font-size: 12px;")
        layout.addWidget(value, row, col + 1)
    
    def create_vitals_section(self):
        vitals_frame = QFrame()
        vitals_frame.setStyleSheet("background-color: #000040;")
        vitals_layout = QHBoxLayout(vitals_frame)
        
        # Create vital sign displays
        self.hr_display = VitalSignDisplay("HR", "bpm", "60-100", "--")
        self.bp_display = VitalSignDisplay("NIBP", "mmHg", "120/80", "--/--")
        self.spo2_display = VitalSignDisplay("SpO₂", "%", "95-100", "--")
        self.resp_display = VitalSignDisplay("RESP", "bpm", "12-20", "--")
        self.temp_display = VitalSignDisplay("TEMP", "°C", "36.5-37.5", "--")
        
        # Add all vital displays to the layout
        vitals_layout.addWidget(self.hr_display)
        vitals_layout.addWidget(self.bp_display)
        vitals_layout.addWidget(self.spo2_display)
        vitals_layout.addWidget(self.resp_display)
        vitals_layout.addWidget(self.temp_display)
        
        self.main_layout.addWidget(vitals_frame, 1)
    
    def create_main_section(self):
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3080A0;
                background: #000040;
            }
            QTabBar::tab {
                background: #102040;
                color: white;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #3080A0;
                color: white;
            }
        """)
        
        # ECG Tab
        ecg_tab = QWidget()
        ecg_layout = QVBoxLayout(ecg_tab)
        
        # Create ECG graph
        self.create_ecg_graph(ecg_layout)
        
        # Create arrhythmia detection section
        self.create_arrhythmia_section(ecg_layout)
        
        tab_widget.addTab(ecg_tab, "ECG")
        
        # Vitals History Tab (placeholder for future implementation)
        trends_tab = QWidget()
        tab_widget.addTab(trends_tab, "Trends")
        
        # Settings Tab (placeholder for future implementation)
        settings_tab = QWidget()
        tab_widget.addTab(settings_tab, "Settings")
        
        self.main_layout.addWidget(tab_widget, 5)  # Larger proportion for the main content
    
    def create_ecg_graph(self, parent_layout):
        graph_frame = QFrame()
        graph_layout = QVBoxLayout(graph_frame)
        
        # Create ECG figure with dark background like professional monitors
        self.figure = Figure(figsize=(12, 6), facecolor='#000020')
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#000020')
        
        # Configure grid and labels
        self.ax.grid(True, color='#004000', linestyle='-', linewidth=0.5)
        self.ax.tick_params(axis='x', colors='#00FF00')
        self.ax.tick_params(axis='y', colors='#00FF00')
        self.ax.set_xlabel('Time (s)', color='#00FF00')
        self.ax.set_ylabel('Amplitude (mV)', color='#00FF00')
        self.ax.set_title('ECG Waveform', color='#00FF00')
        
        # Initialize line with empty data
        display_points = int(self.display_seconds * self.sampling_rate)
        self.time_data = np.arange(display_points) / self.sampling_rate
        self.line, = self.ax.plot(self.time_data, np.zeros(display_points), 
                               color='#00FF00', linewidth=1.5)
        self.ax.set_ylim(-1.5, 1.5)
        
        # Add to layout
        graph_layout.addWidget(self.canvas)
        
        parent_layout.addWidget(graph_frame)
    
    def create_arrhythmia_section(self, parent_layout):
        arrhythmia_frame = QFrame()
        arrhythmia_frame.setStyleSheet("border: 1px solid #3080A0; border-radius: 5px;")
        arrhythmia_layout = QHBoxLayout(arrhythmia_frame)
        
        # Create arrhythmia status indicators
        self.create_status_indicator(arrhythmia_layout, "Bradycardia", "Normal")
        self.create_status_indicator(arrhythmia_layout, "Tachycardia", "Normal")
        self.create_status_indicator(arrhythmia_layout, "Atrial Fibrillation", "Normal")
        
        # Main alarm indicator
        self.alarm_label = QLabel("ECG Status: Normal")
        self.alarm_label.setStyleSheet(
            "background-color: #004000; color: #00FF00; padding: 10px; "
            "font-weight: bold; border: 1px solid #00FF00; border-radius: 5px;"
        )
        self.alarm_label.setAlignment(Qt.AlignCenter)
        arrhythmia_layout.addWidget(self.alarm_label)
        
        # Mute alarm button with medical styling
        self.mute_btn = QPushButton("Mute Alarm")
        self.mute_btn.setStyleSheet("""
            QPushButton {
                background-color: #A0A000;
                color: black;
                font-weight: bold;
                border: 2px solid #707000;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:disabled {
                background-color: #404000;
                color: #808080;
                border: 2px solid #404000;
            }
        """)
        self.mute_btn.clicked.connect(self.mute_alarm)
        self.mute_btn.setEnabled(False)
        arrhythmia_layout.addWidget(self.mute_btn)
        
        parent_layout.addWidget(arrhythmia_frame)
    
    def create_status_indicator(self, layout, name, status):
        status_frame = QFrame()
        status_layout = QVBoxLayout(status_frame)
        
        title_label = QLabel(name)
        title_label.setStyleSheet("color: #88CCFF; font-size: 12px;")
        title_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(title_label)
        
        status_label = QLabel(status)
        status_label.setStyleSheet(
            "background-color: #004000; color: #00FF00; padding: 5px; "
            "border: 1px solid #00FF00; border-radius: 5px;"
        )
        status_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(status_label)
        
        setattr(self, f"{name.lower().replace(' ', '_')}_label", status_label)
        layout.addWidget(status_frame)
    
    def create_control_section(self):
        control_frame = QFrame()
        control_frame.setStyleSheet("background-color: #000030;")
        control_layout = QHBoxLayout(control_frame)
        
        # Load data button
        self.load_btn = QPushButton("Load ECG Data")
        self.load_btn.setStyleSheet("""
            QPushButton {
                background-color: #003060;
                color: white;
                font-weight: bold;
                border: 2px solid #0060C0;
                border-radius: 5px;
                padding: 8px 16px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #0060A0;
            }
        """)
        self.load_btn.clicked.connect(self.load_data)
        control_layout.addWidget(self.load_btn)
        
        # Start/stop monitoring button
        self.monitor_btn = QPushButton("Start Monitoring")
        self.monitor_btn.setStyleSheet("""
            QPushButton {
                background-color: #006030;
                color: white;
                font-weight: bold;
                border: 2px solid #00C060;
                border-radius: 5px;
                padding: 8px 16px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #00A060;
            }
        """)
        self.monitor_btn.clicked.connect(self.toggle_monitoring)
        control_layout.addWidget(self.monitor_btn)
        
        # Speed control with label
        control_layout.addWidget(QLabel("Speed:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5x", "1.0x", "2.0x"])
        self.speed_combo.setCurrentIndex(1)  # Default to 1.0x
        self.speed_combo.setStyleSheet("""
            QComboBox {
                background-color: #202040;
                color: white;
                border: 1px solid #3080A0;
                border-radius: 3px;
                padding: 5px;
            }
            QComboBox::drop-down {
                border: 0px;
            }
            QComboBox::down-arrow {
                image: url(dropdown.png);
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #202040;
                color: white;
                selection-background-color: #3080A0;
            }
        """)
        control_layout.addWidget(self.speed_combo)
        
        # Spacer to push buttons to left and right
        control_layout.addStretch(1)
        
        # Print button (for printing reports)
        print_btn = QPushButton("Print Report")
        print_btn.setStyleSheet("""
            QPushButton {
                background-color: #604060;
                color: white;
                font-weight: bold;
                border: 2px solid #A060A0;
                border-radius: 5px;
                padding: 8px 16px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #805080;
            }
        """)
        control_layout.addWidget(print_btn)
        
        # Reset button
        self.reset_btn = QPushButton("Reset Display")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #800000;
                color: white;
                font-weight: bold;
                border: 2px solid #C00000;
                border-radius: 5px;
                padding: 8px 16px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #A00000;
            }
        """)
        self.reset_btn.clicked.connect(self.reset_display)
        control_layout.addWidget(self.reset_btn)
        
        self.main_layout.addWidget(control_frame, 1)
    
    # Keep load_data method 
    def load_data(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open ECG Data File", "", 
                                                  "CSV files (*.csv);;All Files (*)")
        
        if file_path:
            try:
                # Load ECG data from file
                # Simplified example - adapt to your actual data format
                data = pd.read_csv(file_path)
                self.ecg_data = data['ecg'].values  # Assuming column name is 'ecg'
                
                # Reset display
                self.current_index = 0
                self.reset_display()
                
                QMessageBox.information(self, "Data Loaded", f"Successfully loaded {len(self.ecg_data)} data points.")
                self.monitor_btn.setEnabled(True)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")
        else:
            # For demo purposes, generate sample data if no file is selected
            self.generate_sample_data()
    
    # Update generate_sample_data to also generate vital signs data
    def generate_sample_data(self):
        # Generate 60 seconds of sample ECG data for demonstration
        seconds = 60
        t = np.linspace(0, seconds, int(seconds * self.sampling_rate))
        
        # Base waveform (simplified ECG-like pattern)
        ecg_wave = np.zeros_like(t)
        
        # Generate P-QRS-T complex pattern and repeat
        for i in range(0, seconds * 2):  # Assuming ~2 beats per second (120 BPM)
            center = i / 2
            # P wave
            p_wave = 0.25 * np.exp(-((t - (center - 0.2)) ** 2) / 0.005)
            # QRS complex
            qrs = -0.3 * np.exp(-((t - center + 0.05) ** 2) / 0.002)
            qrs += 1.0 * np.exp(-((t - center) ** 2) / 0.0005)
            qrs += -0.3 * np.exp(-((t - center - 0.05) ** 2) / 0.002)
            # T wave
            t_wave = 0.35 * np.exp(-((t - (center + 0.3)) ** 2) / 0.01)
            
            ecg_wave += p_wave + qrs + t_wave
        
        # Add some noise
        noise = 0.05 * np.random.randn(len(t))
        ecg_wave += noise
        
        # Add some abnormalities for demonstration
        # Tachycardia section (faster rhythm)
        tach_start = int(20 * self.sampling_rate)
        tach_end = int(30 * self.sampling_rate)
        tach_pattern = np.zeros_like(ecg_wave[tach_start:tach_end])
        
        for i in range(0, 150):  # More beats in the same time period
            center = i / 5
            if center > 10:
                break
            qrs = -0.3 * np.exp(-((np.arange(tach_end - tach_start) / self.sampling_rate - center + 0.05) ** 2) / 0.002)
            qrs += 1.0 * np.exp(-((np.arange(tach_end - tach_start) / self.sampling_rate - center) ** 2) / 0.0005)
            qrs += -0.3 * np.exp(-((np.arange(tach_end - tach_start) / self.sampling_rate - center - 0.05) ** 2) / 0.002)
            tach_pattern += qrs
        
        ecg_wave[tach_start:tach_end] = tach_pattern + noise[tach_start:tach_end]
        
        # Bradycardia section (slower rhythm)
        brady_start = int(40 * self.sampling_rate)
        brady_end = int(50 * self.sampling_rate)
        brady_pattern = np.zeros_like(ecg_wave[brady_start:brady_end])
        
        for i in range(0, 8):  # Fewer beats in the same time period
            center = i / 0.8
            if center > 10:
                break
            qrs = -0.3 * np.exp(-((np.arange(brady_end - brady_start) / self.sampling_rate - center + 0.05) ** 2) / 0.002)
            qrs += 1.0 * np.exp(-((np.arange(brady_end - brady_start) / self.sampling_rate - center) ** 2) / 0.0005)
            qrs += -0.3 * np.exp(-((np.arange(brady_end - brady_start) / self.sampling_rate - center - 0.05) ** 2) / 0.002)
            brady_pattern += qrs
        
        ecg_wave[brady_start:brady_end] = brady_pattern + noise[brady_start:brady_end]
        
        # Generate additional vital sign data
        self.vital_signs = {
            # Normal ranges initially
            "hr": 75,
            "bp_systolic": 120,
            "bp_diastolic": 80,
            "spo2": 98,
            "resp": 16,
            "temp": 37.0
        }
        
        # Create variations for each section to match ECG
        self.vital_variations = {
            # Normal section (0-20s)
            "normal": {
                "hr": (70, 80),
                "bp_systolic": (115, 125),
                "bp_diastolic": (75, 85),
                "spo2": (97, 99),
                "resp": (14, 18),
                "temp": (36.8, 37.2)
            },
            # Tachycardia section (20-30s)
            "tachy": {
                "hr": (115, 130),
                "bp_systolic": (95, 110),  # Lower BP during tachycardia
                "bp_diastolic": (60, 70),
                "spo2": (94, 98),
                "resp": (20, 24),  # Faster breathing
                "temp": (37.0, 37.5)  # Slight fever
            },
            # Normal section (30-40s)
            "normal2": {
                "hr": (70, 80),
                "bp_systolic": (115, 125),
                "bp_diastolic": (75, 85),
                "spo2": (97, 99),
                "resp": (14, 18),
                "temp": (36.8, 37.2)
            },
            # Bradycardia section (40-50s)
            "brady": {
                "hr": (40, 55),
                "bp_systolic": (90, 110),  # Lower BP during bradycardia
                "bp_diastolic": (50, 65),
                "spo2": (90, 96),  # Lower oxygen
                "resp": (10, 14),  # Slower breathing
                "temp": (36.0, 36.5)  # Lower temperature
            },
            # Normal section (50-60s)
            "normal3": {
                "hr": (70, 80),
                "bp_systolic": (115, 125), 
                "bp_diastolic": (75, 85),
                "spo2": (97, 99),
                "resp": (14, 18),
                "temp": (36.8, 37.2)
            }
        }
        
        self.ecg_data = ecg_wave
        
        # No need to show message box for automatic data generation
    
    def toggle_monitoring(self):
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_btn.setText("Stop Monitoring")
            self.monitor_btn.setStyleSheet("""
                QPushButton {
                    background-color: #600000;
                    color: white;
                    font-weight: bold;
                    border: 2px solid #C00000;
                    border-radius: 5px;
                    padding: 8px 16px;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #A00000;
                }
            """)
            
            # Get speed factor
            speed_text = self.speed_combo.currentText()
            speed_factor = float(speed_text[:-1])  # Remove 'x' and convert to float
            
            update_interval = int(50 / speed_factor)  # Base update rate 50ms
            self.timer.start(update_interval)
        else:
            self.is_monitoring = False
            self.monitor_btn.setText("Start Monitoring")
            self.monitor_btn.setStyleSheet("""
                QPushButton {
                    background-color: #006030;
                    color: white;
                    font-weight: bold;
                    border: 2px solid #00C060;
                    border-radius: 5px;
                    padding: 8px 16px;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #00A060;
                }
            """)
            self.timer.stop()
    
    def update_monitor(self):
        # Update ECG plot
        self.update_plot()
        
        # Update vital signs based on current simulation time
        self.update_vital_signs()
        
        # Update date/time (in real application, would use actual system time)
        from datetime import datetime
        self.date_time_label.setText(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
    
    def update_vital_signs(self):
        # Determine which section of the simulation we're in
        if self.ecg_data is None:
            return
            
        current_second = self.current_index / self.sampling_rate
        
        if current_second < 20:
            variation_key = "normal"
        elif current_second < 30:
            variation_key = "tachy"
        elif current_second < 40:
            variation_key = "normal2"
        elif current_second < 50:
            variation_key = "brady"
        else:
            variation_key = "normal3"
        
        # Get current variation ranges
        variations = self.vital_variations[variation_key]
        
        # Update vital signs with some random variation within the specified ranges
        heart_rate = np.random.uniform(variations["hr"][0], variations["hr"][1])
        self.vital_signs["hr"] = heart_rate
        
        # Blood pressure - systolic and diastolic with appropriate relationship
        self.vital_signs["bp_systolic"] = np.random.uniform(
            variations["bp_systolic"][0], variations["bp_systolic"][1])
        self.vital_signs["bp_diastolic"] = np.random.uniform(
            variations["bp_diastolic"][0], variations["bp_diastolic"][1])
        
        # Other vitals
        self.vital_signs["spo2"] = np.random.uniform(variations["spo2"][0], variations["spo2"][1])
        self.vital_signs["resp"] = np.random.uniform(variations["resp"][0], variations["resp"][1])
        self.vital_signs["temp"] = np.random.uniform(variations["temp"][0], variations["temp"][1])
        
        # Update displays
        self.hr_display.update_value(int(self.vital_signs["hr"]))
        
        # Format BP as systolic/diastolic
        bp_text = f"{int(self.vital_signs['bp_systolic'])}/{int(self.vital_signs['bp_diastolic'])}"
        self.bp_display.update_value(bp_text)
        
        self.spo2_display.update_value(int(self.vital_signs["spo2"]))
        self.resp_display.update_value(int(self.vital_signs["resp"]))
        self.temp_display.update_value(self.vital_signs["temp"])
        
        # Check for abnormal vital signs and update system status
        self.check_vital_alarms()
    
    def check_vital_alarms(self):
        alarm_triggered = False
        alarm_message = ""
        
        # Check heart rate
        if self.vital_signs["hr"] < 60:
            alarm_triggered = True
            alarm_message = "Low Heart Rate"
        elif self.vital_signs["hr"] > 100:
            alarm_triggered = True
            alarm_message = "High Heart Rate"
        
        # Check SpO2
        if self.vital_signs["spo2"] < 95:
            alarm_triggered = True
            if alarm_message:
                alarm_message += " & Low SpO2"
            else:
                alarm_message = "Low SpO2"
        
        # Check temperature
        if self.vital_signs["temp"] > 37.5:
            alarm_triggered = True
            if alarm_message:
                alarm_message += " & Fever"
            else:
                alarm_message = "Fever"
        elif self.vital_signs["temp"] < 36.5:
            alarm_triggered = True
            if alarm_message:
                alarm_message += " & Hypothermia"
            else:
                alarm_message = "Hypothermia"
        
        # Update system status based on alarms
        if alarm_triggered and not self.alarm_active:
            self.system_status_label.setText(f"System Status: ALERT - {alarm_message}")
            self.system_status_label.setStyleSheet("color: #FF0000; font-size: 14px; font-weight: bold;")
        elif not alarm_triggered:
            self.system_status_label.setText("System Status: NORMAL")
            self.system_status_label.setStyleSheet("color: #00FF00; font-size: 14px; font-weight: bold;")
    
    def update_plot(self):
        if self.ecg_data is None or self.current_index >= len(self.ecg_data):
            return
        
        display_points = int(self.display_seconds * self.sampling_rate)
        
        # Get the relevant slice of data
        end_idx = min(self.current_index + display_points, len(self.ecg_data))
        data_slice = self.ecg_data[self.current_index:end_idx]
        
        # If we don't have enough data to fill the display, pad with zeros
        if len(data_slice) < display_points:
            data_slice = np.pad(data_slice, (0, display_points - len(data_slice)))
        
        # Update the plot
        self.line.set_ydata(data_slice)
        self.canvas.draw()
        
        # Detect arrhythmias
        self.detect_arrhythmias(data_slice)
        
        # Advance the index for the next update
        self.current_index += int(0.2 * self.sampling_rate)  # Advance by 0.2 seconds
        
        # If we're at the end of the data, loop back
        if self.current_index >= len(self.ecg_data) - display_points:
            self.current_index = 0
    
    def reset_display(self):
        self.current_index = 0
        if self.ecg_data is not None:
            display_points = int(self.display_seconds * self.sampling_rate)
            end_idx = min(display_points, len(self.ecg_data))
            self.line.set_ydata(self.ecg_data[:end_idx])
            self.canvas.draw()
            
        # Reset all status indicators
        for attr in dir(self):
            if attr.endswith('_label') and attr != 'heart_rate_label':
                label = getattr(self, attr)
                if isinstance(label, QLabel) and label != self.alarm_label:
                    if attr not in ['date_time_label', 'system_status_label']:
                        label.setText("Normal")
                        label.setStyleSheet("background-color: #004000; color: #00FF00; padding: 5px; "
                                            "border: 1px solid #00FF00; border-radius: 5px;")
        
        self.alarm_label.setText("ECG Status: Normal")
        self.alarm_label.setStyleSheet(
            "background-color: #004000; color: #00FF00; padding: 10px; "
            "font-weight: bold; border: 1px solid #00FF00; border-radius: 5px;"
        )
        self.alarm_active = False
        self.mute_btn.setEnabled(False)
        
        # Reset system status
        self.system_status_label.setText("System Status: NORMAL")
        self.system_status_label.setStyleSheet("color: #00FF00; font-size: 14px; font-weight: bold;")
    
    def detect_arrhythmias(self, data_slice):
        # Simple arrhythmia detection based on heart rate for demonstration
        # In a real application, more sophisticated algorithms would be used
        
        heart_rate = self.vital_signs["hr"]
        
        # Check for bradycardia (slow heart rate)
        brady_label = self.bradycardia_label
        if heart_rate < 60:
            brady_label.setText("DETECTED")
            brady_label.setStyleSheet(
                "background-color: #400000; color: #FF0000; padding: 5px; "
                "border: 1px solid #FF0000; border-radius: 5px;"
            )
            self.trigger_alarm("Bradycardia Detected")
        else:
            brady_label.setText("Normal")
            brady_label.setStyleSheet(
                "background-color: #004000; color: #00FF00; padding: 5px; "
                "border: 1px solid #00FF00; border-radius: 5px;"
            )
        
        # Check for tachycardia (fast heart rate)
        tachy_label = self.tachycardia_label
        if heart_rate > 100:
            tachy_label.setText("DETECTED")
            tachy_label.setStyleSheet(
                "background-color: #400000; color: #FF0000; padding: 5px; "
                "border: 1px solid #FF0000; border-radius: 5px;"
            )
            self.trigger_alarm("Tachycardia Detected")
        else:
            tachy_label.setText("Normal")
            tachy_label.setStyleSheet(
                "background-color: #004000; color: #00FF00; padding: 5px; "
                "border: 1px solid #00FF00; border-radius: 5px;"
            )
        
        # Detect atrial fibrillation using a simplified approach
        # For demo purposes, use a combination of factors
        atrial_fib_label = getattr(self, "atrial_fibrillation_label")
        
        # Simple detection of irregular rhythm for demo
        # In real applications, use more sophisticated algorithms
        if self.current_index > 5 * self.sampling_rate:
            # In this simulation, just detect A-fib during the tachycardia section
            # with some randomness to simulate irregular detection
            if (20 * self.sampling_rate < self.current_index < 30 * self.sampling_rate and 
                    heart_rate > 100 and np.random.random() < 0.3):
                atrial_fib_label.setText("DETECTED")
                atrial_fib_label.setStyleSheet(
                    "background-color: #400000; color: #FF0000; padding: 5px; "
                    "border: 1px solid #FF0000; border-radius: 5px;"
                )
                self.trigger_alarm("Atrial Fibrillation Detected")
            else:
                atrial_fib_label.setText("Normal")
                atrial_fib_label.setStyleSheet(
                    "background-color: #004000; color: #00FF00; padding: 5px; "
                    "border: 1px solid #00FF00; border-radius: 5px;"
                )
    
    def calculate_heart_rate(self, data):
        # This method is no longer used directly - heart rate comes from vital signs
        # But we keep it for compatibility
        return int(self.vital_signs["hr"])
    
    def trigger_alarm(self, message):
        if not self.alarm_active:
            self.alarm_active = True
            self.alarm_label.setText(f"ALERT: {message}")
            self.alarm_label.setStyleSheet(
                "background-color: #400000; color: #FF0000; padding: 10px; "
                "font-weight: bold; border: 1px solid #FF0000; border-radius: 5px;"
            )
            self.mute_btn.setEnabled(True)
            
            # In a real application, you would also trigger audible alarms
            # Just show a message box in this simulation
            QMessageBox.warning(self, "Arrhythmia Alert", message)
    
    def mute_alarm(self):
        self.alarm_active = False
        self.alarm_label.setStyleSheet(
            "background-color: #404000; color: #FFFF00; padding: 10px; "
            "font-weight: bold; border: 1px solid #FFFF00; border-radius: 5px;"
        )
        self.alarm_label.setText("Alarm Muted - Monitoring")
        self.mute_btn.setEnabled(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ECGMonitor()
    sys.exit(app.exec_())