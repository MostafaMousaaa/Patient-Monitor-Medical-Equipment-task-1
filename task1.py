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
                             QTabWidget, QSplitter, QGroupBox, QStackedWidget)
from PyQt5.QtCore import QTimer, Qt, QSize, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor, QFont, QPalette, QLinearGradient, QBrush, QIcon

# Main color scheme based on Philips monitoring systems
PHILIPS_DARK_BLUE = "#000F30"
PHILIPS_MEDIUM_BLUE = "#002060"  
PHILIPS_LIGHT_BLUE = "#0070C0"
PHILIPS_YELLOW = "#FFB800"
PHILIPS_RED = "#FF0000"
PHILIPS_GREEN = "#00BD3F"
PHILIPS_CYAN = "#00FFFF"
PHILIPS_ORANGE = "#FF7D00"

class VitalSignDisplay(QFrame):
    def __init__(self, title, unit, normal_range, value="--", parent=None, color=PHILIPS_GREEN):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.color = color
        
        # Set dark background with blue gradient like Philips monitors
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(PHILIPS_DARK_BLUE))
        gradient.setColorAt(1, QColor(PHILIPS_MEDIUM_BLUE))
        
        palette = self.palette()
        palette.setBrush(QPalette.Window, QBrush(gradient))
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        
        # Set minimum size for each vital sign display
        self.setMinimumSize(QSize(180, 120))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)
        
        # Title with parameter name (like Philips - top left corner)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"color: {PHILIPS_YELLOW}; font-size: 14px; font-weight: bold; background: transparent;")
        self.title_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.title_label)
        
        # Value display - large font and centered
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {color}; font-size: 40px; font-weight: bold; background: transparent;")
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label, 1)  # Give more space to value
        
        # Unit and normal range as footer
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(5)
        
        self.unit_label = QLabel(unit)
        self.unit_label.setStyleSheet("color: white; font-size: 12px; background: transparent;")
        info_layout.addWidget(self.unit_label)
        
        info_layout.addStretch()
        
        self.range_label = QLabel(f"({normal_range})")
        self.range_label.setStyleSheet("color: #AAAAAA; font-size: 11px; background: transparent;")
        self.range_label.setAlignment(Qt.AlignRight)
        info_layout.addWidget(self.range_label)
        
        layout.addLayout(info_layout)
        
        # Add thin bottom border like Philips monitors
        bottom_line = QFrame()
        bottom_line.setFrameShape(QFrame.HLine)
        bottom_line.setStyleSheet(f"background-color: {PHILIPS_LIGHT_BLUE}; max-height: 2px;")
        layout.addWidget(bottom_line)
        
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
            self.value_label.setStyleSheet(f"color: {self.color}; font-size: 40px; font-weight: bold; background: transparent;")
        else:
            self.value_label.setStyleSheet(f"color: {PHILIPS_RED}; font-size: 40px; font-weight: bold; background: transparent;")
    
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
        self.setWindowTitle("Philips Patient Monitoring System")
        self.setGeometry(50, 50, 1400, 800)
        self.setStyleSheet(f"background-color: {PHILIPS_DARK_BLUE};")
        
        # Apply modern style
        self.apply_modern_style()
        
        # Create a central widget with border layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(4, 4, 4, 4)  # Minimal margins like medical displays
        self.main_layout.setSpacing(4)  # Tight spacing
        
        # Initialize data attributes before creating sections
        self.ecg_data = None
        self.pleth_data = None  # Add pleth data
        self.resp_data = None   # Add respiratory data
        self.current_index = 0
        self.sampling_rate = 250  # Hz
        self.display_seconds = 6  # Philips typically shows 6 seconds
        self.is_monitoring = False
        self.alarm_active = False
        self.waveform_colors = {
            "ECG": PHILIPS_GREEN,
            "SpO2": PHILIPS_CYAN,
            "RESP": PHILIPS_YELLOW
        }
        
        # Upper section with patient info and vital signs
        self.create_header_section()
        
        # Main section with ECG and other waveforms
        self.create_main_section()
        
        # Control section
        self.create_control_section()
        
        # Initialize timer for real-time simulation
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_monitor)
        
        # Add animation capabilities
        self.setup_animations()
        
        # Generate initial sample data
        self.generate_sample_data()
        
        # Put monitor in demo mode
        self.monitor_btn.setEnabled(True)
        
        self.show()
        
        # Start monitoring automatically in demo mode
        self.toggle_monitoring()
    
    def apply_modern_style(self):
        # Apply modern font and styling to entire application
        app = QApplication.instance()
        font = QFont("Segoe UI", 9)  # Modern, clean font
        app.setFont(font)
        
        # Set window icon if available
        try:
            self.setWindowIcon(QIcon("hospital_icon.png"))
        except:
            pass  # Ignore if icon not found
    
    def setup_animations(self):
        # Setup animations for alarm state changes
        self.alarm_animation = QPropertyAnimation(self, b"windowOpacity")
        self.alarm_animation.setDuration(500)
        self.alarm_animation.setStartValue(1.0)
        self.alarm_animation.setEndValue(0.9)
        self.alarm_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Animation for other visual elements can be added here
    
    def create_header_section(self):
        header_frame = QFrame()
        header_frame.setStyleSheet(f"background-color: {PHILIPS_DARK_BLUE}; border-bottom: 1px solid {PHILIPS_LIGHT_BLUE};")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(5, 2, 5, 2)
        
        # Left side - Patient info
        info_box = QGroupBox("")
        info_box.setStyleSheet(f"""
            QGroupBox {{
                border: none;
                margin-top: 0px;
            }}
        """)
        info_layout = QGridLayout(info_box)
        info_layout.setContentsMargins(5, 2, 5, 2)
        info_layout.setHorizontalSpacing(15)
        info_layout.setVerticalSpacing(2)
        
        # Add patient information in Philips style - compact row
        patient_id = QLabel("ID: P12345")
        patient_id.setStyleSheet(f"color: white; font-size: 12px;")
        info_layout.addWidget(patient_id, 0, 0)
        
        patient_name = QLabel("DOE, John")
        patient_name.setStyleSheet(f"color: white; font-size: 12px; font-weight: bold;")
        info_layout.addWidget(patient_name, 0, 1)
        
        patient_age = QLabel("45y M")
        patient_age.setStyleSheet(f"color: white; font-size: 12px;")
        info_layout.addWidget(patient_age, 0, 2)
        
        patient_room = QLabel("ICU-107")
        patient_room.setStyleSheet(f"color: white; font-size: 12px;")
        info_layout.addWidget(patient_room, 0, 3)
        
        header_layout.addWidget(info_box, 1)
        
        # Center - empty space or hospital logo
        logo_label = QLabel("SBME 26 Patient Monitoring System")
        logo_label.setStyleSheet(f"color: {PHILIPS_LIGHT_BLUE}; font-size: 14px; font-weight: bold;")
        logo_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(logo_label, 2)
        
        # Right side - Time and system status
        time_box = QWidget()
        time_layout = QHBoxLayout(time_box)
        time_layout.setContentsMargins(5, 0, 5, 0)
        
        self.date_time_label = QLabel("2023-05-02  14:30:45")
        self.date_time_label.setStyleSheet(f"color: white; font-size: 12px; font-weight: bold;")
        self.date_time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        time_layout.addWidget(self.date_time_label)
        
        header_layout.addWidget(time_box, 1)
        
        self.main_layout.addWidget(header_frame, 0)
        
        # Create vitals section (large numeric vital signs)
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
        vitals_frame.setStyleSheet(f"background-color: {PHILIPS_DARK_BLUE};")
        vitals_layout = QHBoxLayout(vitals_frame)
        vitals_layout.setContentsMargins(2, 2, 2, 2)
        vitals_layout.setSpacing(6)  # Small gap between vital signs
        
        # Create vital sign displays with appropriate colors (Philips standard colors)
        self.hr_display = VitalSignDisplay("HR", "bpm", "60-100", "--", color=PHILIPS_GREEN)
        self.bp_display = VitalSignDisplay("NBP", "mmHg", "120/80", "--/--", color=PHILIPS_RED)
        self.spo2_display = VitalSignDisplay("SpO₂", "%", "95-100", "--", color=PHILIPS_CYAN)
        self.resp_display = VitalSignDisplay("RESP", "rpm", "12-20", "--", color=PHILIPS_YELLOW)
        self.temp_display = VitalSignDisplay("TEMP", "°C", "36.5-37.5", "--", color=PHILIPS_ORANGE)
        
        # Add all vital displays to the layout
        vitals_layout.addWidget(self.hr_display)
        vitals_layout.addWidget(self.bp_display) 
        vitals_layout.addWidget(self.spo2_display)
        vitals_layout.addWidget(self.resp_display)
        vitals_layout.addWidget(self.temp_display)
        
        # Add system status indicator
        status_frame = QFrame()
        status_layout = QVBoxLayout(status_frame)
        
        self.system_status_label = QLabel("NORMAL")
        self.system_status_label.setStyleSheet(f"color: {PHILIPS_GREEN}; font-size: 14px; font-weight: bold; background: transparent;")
        self.system_status_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.system_status_label)
        
        vitals_layout.addWidget(status_frame)
        
        self.main_layout.addWidget(vitals_frame, 0)
    
    def create_main_section(self):
        # In Philips monitors, waveforms are stacked vertically with parameter labels on the left
        waveforms_frame = QFrame()
        waveforms_frame.setStyleSheet(f"background-color: {PHILIPS_DARK_BLUE}; border: 1px solid {PHILIPS_LIGHT_BLUE};")
        waveforms_layout = QVBoxLayout(waveforms_frame)
        waveforms_layout.setContentsMargins(2, 2, 2, 2)
        waveforms_layout.setSpacing(1)  # Minimal spacing between waveforms
        
        # ECG waveform (largest portion)
        ecg_frame = QFrame()
        ecg_layout = QHBoxLayout(ecg_frame)
        ecg_layout.setContentsMargins(0, 0, 0, 0)
        
        # Parameter label on left side
        ecg_param_frame = QFrame()
        ecg_param_frame.setMaximumWidth(60)  # Fixed width for parameter column
        ecg_param_layout = QVBoxLayout(ecg_param_frame)
        ecg_param_layout.setContentsMargins(2, 2, 0, 2)
        
        ecg_label = QLabel("ECG II")
        ecg_label.setStyleSheet(f"color: {PHILIPS_GREEN}; font-size: 12px; font-weight: bold;")
        ecg_param_layout.addWidget(ecg_label)
        ecg_param_layout.addStretch()
        
        ecg_layout.addWidget(ecg_param_frame)
        
        # ECG waveform plot
        self.create_ecg_graph(ecg_layout)
        
        waveforms_layout.addWidget(ecg_frame, 5)  # ECG gets more space
        
        # Add divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"background-color: {PHILIPS_LIGHT_BLUE}; max-height: 1px;")
        waveforms_layout.addWidget(divider)
        
        # SpO2 Pleth waveform (smaller)
        spo2_frame = QFrame()
        spo2_layout = QHBoxLayout(spo2_frame)
        spo2_layout.setContentsMargins(0, 0, 0, 0)
        
        # Parameter label
        spo2_param_frame = QFrame()
        spo2_param_frame.setMaximumWidth(60)
        spo2_param_layout = QVBoxLayout(spo2_param_frame)
        spo2_param_layout.setContentsMargins(2, 2, 0, 2)
        
        spo2_label = QLabel("PLETH")
        spo2_label.setStyleSheet(f"color: {PHILIPS_CYAN}; font-size: 12px; font-weight: bold;")
        spo2_param_layout.addWidget(spo2_label)
        spo2_param_layout.addStretch()
        
        spo2_layout.addWidget(spo2_param_frame)
        
        # Add pleth waveform plot instead of placeholder
        self.create_pleth_graph(spo2_layout)
        
        waveforms_layout.addWidget(spo2_frame, 2)  # Smaller than ECG
        
        # Add divider
        divider2 = QFrame()
        divider2.setFrameShape(QFrame.HLine)
        divider2.setStyleSheet(f"background-color: {PHILIPS_LIGHT_BLUE}; max-height: 1px;")
        waveforms_layout.addWidget(divider2)
        
        # Respiration waveform (smaller)
        resp_frame = QFrame()
        resp_layout = QHBoxLayout(resp_frame)
        resp_layout.setContentsMargins(0, 0, 0, 0)
        
        # Parameter label
        resp_param_frame = QFrame()
        resp_param_frame.setMaximumWidth(60)
        resp_param_layout = QVBoxLayout(resp_param_frame)
        resp_param_layout.setContentsMargins(2, 2, 0, 2)
        
        resp_label = QLabel("RESP")
        resp_label.setStyleSheet(f"color: {PHILIPS_YELLOW}; font-size: 12px; font-weight: bold;")
        resp_param_layout.addWidget(resp_label)
        resp_param_layout.addStretch()
        
        resp_layout.addWidget(resp_param_frame)
        
        # Add respiratory waveform plot instead of placeholder
        self.create_resp_graph(resp_layout)
        
        waveforms_layout.addWidget(resp_frame, 2)  # Same size as SpO2
        
        # Add arrhythmia detection section at the bottom
        self.create_arrhythmia_section(waveforms_layout)
        
        self.main_layout.addWidget(waveforms_frame, 7)  # Waveforms take up most of the screen
    
    def create_ecg_graph(self, parent_layout):
        graph_frame = QFrame()
        graph_layout = QVBoxLayout(graph_frame)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create ECG figure with dark background like Philips monitors
        self.figure = Figure(figsize=(5, 3), facecolor=PHILIPS_DARK_BLUE, dpi=100)
        self.figure.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.05)
        
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor(PHILIPS_DARK_BLUE)
        
        # Configure grid and labels - Philips style with major and minor grid lines
        self.ax.grid(which='major', color='#005000', linestyle='-', linewidth=0.5, alpha=0.7)
        self.ax.grid(which='minor', color='#003000', linestyle=':', linewidth=0.3, alpha=0.4)
        self.ax.minorticks_on()
        
        # Hide axis labels but keep ticks for time reference
        self.ax.set_xticks(range(0, self.display_seconds + 1))
        self.ax.tick_params(axis='x', colors='#004000', labelsize=8)
        self.ax.tick_params(axis='y', colors=PHILIPS_DARK_BLUE)  # Hide Y ticks by making them same as background
        
        # Remove axis labels and title
        self.ax.set_xlabel('')
        self.ax.set_ylabel('')
        self.ax.set_title('')
        
        # Add reference lines for ECG scale - 1mV standard
        self.ax.axhline(y=0, color='#003000', linestyle='-', linewidth=0.8)
        self.ax.axhline(y=1, color='#003000', linestyle='--', linewidth=0.5)
        self.ax.axhline(y=-1, color='#003000', linestyle='--', linewidth=0.5)
        
        # Initialize line with empty data
        display_points = int(self.display_seconds * self.sampling_rate)
        self.time_data = np.arange(display_points) / self.sampling_rate
        self.line, = self.ax.plot(self.time_data, np.zeros(display_points), 
                               color=PHILIPS_GREEN, linewidth=1.5)
        self.ax.set_ylim(-1.5, 1.5)
        
        # Add to layout
        graph_layout.addWidget(self.canvas)
        
        parent_layout.addWidget(graph_frame, 1)
    
    def create_pleth_graph(self, parent_layout):
        """Create the plethysmogram (SpO2) waveform display"""
        graph_frame = QFrame()
        graph_layout = QVBoxLayout(graph_frame)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create figure with same dark background as ECG
        self.pleth_figure = Figure(figsize=(5, 1.5), facecolor=PHILIPS_DARK_BLUE, dpi=100)
        self.pleth_figure.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.05)
        
        self.pleth_canvas = FigureCanvas(self.pleth_figure)
        self.pleth_ax = self.pleth_figure.add_subplot(111)
        self.pleth_ax.set_facecolor(PHILIPS_DARK_BLUE)
        
        # Configure grid - simpler than ECG
        self.pleth_ax.grid(True, color='#005050', linestyle='-', linewidth=0.3, alpha=0.5)
        
        # Hide axis labels
        self.pleth_ax.set_xticks([])
        self.pleth_ax.tick_params(axis='x', colors=PHILIPS_DARK_BLUE)
        self.pleth_ax.tick_params(axis='y', colors=PHILIPS_DARK_BLUE)
        
        # Remove axis labels and title
        self.pleth_ax.set_xlabel('')
        self.pleth_ax.set_ylabel('')
        self.pleth_ax.set_title('')
        
        # Initialize line with empty data
        display_points = int(self.display_seconds * self.sampling_rate)
        self.pleth_line, = self.pleth_ax.plot(self.time_data, np.zeros(display_points), 
                                        color=PHILIPS_CYAN, linewidth=1.5)
        self.pleth_ax.set_ylim(-0.5, 1.5)
        
        # Add to layout
        graph_layout.addWidget(self.pleth_canvas)
        
        parent_layout.addWidget(graph_frame, 1)
    
    def create_resp_graph(self, parent_layout):
        """Create the respiration waveform display"""
        graph_frame = QFrame()
        graph_layout = QVBoxLayout(graph_frame)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create figure with same dark background as ECG
        self.resp_figure = Figure(figsize=(5, 1.5), facecolor=PHILIPS_DARK_BLUE, dpi=100)
        self.resp_figure.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.05)
        
        self.resp_canvas = FigureCanvas(self.resp_figure)
        self.resp_ax = self.resp_figure.add_subplot(111)
        self.resp_ax.set_facecolor(PHILIPS_DARK_BLUE)
        
        # Configure grid - simpler than ECG
        self.resp_ax.grid(True, color='#505000', linestyle='-', linewidth=0.3, alpha=0.5)
        
        # Hide axis labels
        self.resp_ax.set_xticks([])
        self.resp_ax.tick_params(axis='x', colors=PHILIPS_DARK_BLUE)
        self.resp_ax.tick_params(axis='y', colors=PHILIPS_DARK_BLUE)
        
        # Remove axis labels and title
        self.resp_ax.set_xlabel('')
        self.resp_ax.set_ylabel('')
        self.resp_ax.set_title('')
        
        # Initialize line with empty data
        display_points = int(self.display_seconds * self.sampling_rate)
        self.resp_line, = self.resp_ax.plot(self.time_data, np.zeros(display_points), 
                                      color=PHILIPS_YELLOW, linewidth=1.5)
        self.resp_ax.set_ylim(-1.0, 1.0)
        
        # Add to layout
        graph_layout.addWidget(self.resp_canvas)
        
        parent_layout.addWidget(graph_frame, 1)
    
    def create_arrhythmia_section(self, parent_layout):
        arrhythmia_frame = QFrame()
        arrhythmia_frame.setStyleSheet(f"background-color: {PHILIPS_DARK_BLUE}; border-top: 1px solid {PHILIPS_LIGHT_BLUE};")
        arrhythmia_layout = QHBoxLayout(arrhythmia_frame)
        arrhythmia_layout.setContentsMargins(5, 3, 5, 3)
        
        # Create compact arrhythmia status indicators
        self.create_status_indicator(arrhythmia_layout, "BRADY", "---")
        self.create_status_indicator(arrhythmia_layout, "TACHY", "---")
        self.create_status_indicator(arrhythmia_layout, "A-FIB", "---")
        
        # Add spacer
        arrhythmia_layout.addStretch(1)
        
        # Main alarm indicator - more subtle than before, like Philips
        self.alarm_label = QLabel("ECG: Normal")
        self.alarm_label.setStyleSheet(f"color: {PHILIPS_GREEN}; font-weight: bold;")
        self.alarm_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        arrhythmia_layout.addWidget(self.alarm_label)
        
        # Alarm controls
        alarm_controls = QFrame()
        alarm_controls_layout = QHBoxLayout(alarm_controls)
        alarm_controls_layout.setContentsMargins(0, 0, 0, 0)
        alarm_controls_layout.setSpacing(5)
        
        self.mute_btn = QPushButton("Silence")
        self.mute_btn.setStyleSheet("""
            QPushButton {
                background-color: #404000;
                color: #FFFF00;
                font-weight: bold;
                border: 1px solid #707000;
                border-radius: 3px;
                padding: 3px 10px;
            }
            QPushButton:disabled {
                background-color: #202000;
                color: #808060;
                border: 1px solid #404000;
            }
        """)
        self.mute_btn.setFixedHeight(24)
        self.mute_btn.clicked.connect(self.mute_alarm)
        self.mute_btn.setEnabled(False)
        alarm_controls_layout.addWidget(self.mute_btn)
        
        arrhythmia_layout.addWidget(alarm_controls)
        
        parent_layout.addWidget(arrhythmia_frame, 0)
    
    def create_status_indicator(self, layout, name, status):
        indicator_frame = QFrame()
        indicator_layout = QHBoxLayout(indicator_frame)
        indicator_layout.setContentsMargins(2, 2, 2, 2)
        indicator_layout.setSpacing(5)
        
        title_label = QLabel(name)
        title_label.setStyleSheet(f"color: {PHILIPS_LIGHT_BLUE}; font-size: 11px; font-weight: bold;")
        indicator_layout.addWidget(title_label)
        
        status_label = QLabel(status)
        status_label.setStyleSheet(f"color: {PHILIPS_GREEN}; font-size: 11px; font-weight: bold;")
        indicator_layout.addWidget(status_label)
        
        # Store reference to status label using attribute name
        setattr(self, f"{name.lower().replace('-', '_').replace(' ', '_')}_label", status_label)
        
        layout.addWidget(indicator_frame)
    
    def create_control_section(self):
        control_frame = QFrame()
        control_frame.setStyleSheet(f"background-color: {PHILIPS_MEDIUM_BLUE}; border-top: 1px solid {PHILIPS_LIGHT_BLUE};")
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(5, 3, 5, 3)
        
        # Group buttons together on the left
        left_controls = QFrame()
        left_controls_layout = QHBoxLayout(left_controls)
        left_controls_layout.setContentsMargins(0, 0, 0, 0)
        left_controls_layout.setSpacing(8)
        
        # Load data button - styled like Philips softkeys
        self.load_btn = QPushButton("Load ECG")
        self.load_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PHILIPS_MEDIUM_BLUE};
                color: white;
                font-weight: bold;
                border: 1px solid {PHILIPS_LIGHT_BLUE};
                border-radius: 3px;
                padding: 5px 10px;
            }}
            QPushButton:hover {{
                background-color: {PHILIPS_LIGHT_BLUE};
            }}
        """)
        self.load_btn.setFixedHeight(28)
        self.load_btn.clicked.connect(self.load_data)
        left_controls_layout.addWidget(self.load_btn)
        
        # Start/stop monitoring button
        self.monitor_btn = QPushButton("Start")
        self.monitor_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PHILIPS_DARK_BLUE};
                color: white;
                font-weight: bold;
                border: 1px solid {PHILIPS_LIGHT_BLUE};
                border-radius: 3px;
                padding: 5px 10px;
            }}
            QPushButton:hover {{
                background-color: {PHILIPS_LIGHT_BLUE};
            }}
        """)
        self.monitor_btn.setFixedHeight(28)
        self.monitor_btn.clicked.connect(self.toggle_monitoring)
        left_controls_layout.addWidget(self.monitor_btn)
        
        # Speed control with label - more compact
        speed_frame = QFrame()
        speed_layout = QHBoxLayout(speed_frame)
        speed_layout.setContentsMargins(0, 0, 0, 0)
        speed_layout.setSpacing(2)
        
        speed_label = QLabel("Speed:")
        speed_label.setStyleSheet("color: white; font-size: 11px;")
        speed_layout.addWidget(speed_label)
        
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["12.5 mm/s", "25 mm/s", "50 mm/s"])
        self.speed_combo.setCurrentIndex(1)  # Default to 25 mm/s (standard)
        self.speed_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {PHILIPS_DARK_BLUE};
                color: white;
                border: 1px solid {PHILIPS_LIGHT_BLUE};
                border-radius: 3px;
                padding: 2px 5px;
                min-height: 22px;
                max-height: 22px;
                font-size: 11px;
            }}
            QComboBox::drop-down {{
                border: 0px;
                width: 14px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {PHILIPS_DARK_BLUE};
                color: white;
                selection-background-color: {PHILIPS_LIGHT_BLUE};
            }}
        """)
        self.speed_combo.setFixedWidth(80)
        speed_layout.addWidget(self.speed_combo)
        
        left_controls_layout.addWidget(speed_frame)
        
        control_layout.addWidget(left_controls)
        
        # Spacer to push buttons apart
        control_layout.addStretch(1)
        
        # Add right-side controls
        right_controls = QFrame()
        right_controls_layout = QHBoxLayout(right_controls)
        right_controls_layout.setContentsMargins(0, 0, 0, 0)
        right_controls_layout.setSpacing(8)
        
        # Additional controls as in Philips monitors
        record_btn = QPushButton("Record")
        record_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PHILIPS_MEDIUM_BLUE};
                color: white;
                font-weight: bold;
                border: 1px solid {PHILIPS_LIGHT_BLUE};
                border-radius: 3px;
                padding: 5px 10px;
            }}
            QPushButton:hover {{
                background-color: {PHILIPS_LIGHT_BLUE};
            }}
        """)
        record_btn.setFixedHeight(28)
        right_controls_layout.addWidget(record_btn)
        
        # Reset button
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PHILIPS_MEDIUM_BLUE};
                color: white;
                font-weight: bold;
                border: 1px solid {PHILIPS_LIGHT_BLUE};
                border-radius: 3px;
                padding: 5px 10px;
            }}
            QPushButton:hover {{
                background-color: {PHILIPS_LIGHT_BLUE};
            }}
        """)
        self.reset_btn.setFixedHeight(28)
        self.reset_btn.clicked.connect(self.reset_display)
        right_controls_layout.addWidget(self.reset_btn)
        
        control_layout.addWidget(right_controls)
        
        self.main_layout.addWidget(control_frame, 0)
    
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
        
        # Generate plethysmogram (SpO2) waveform data
        seconds = 60
        t = np.linspace(0, seconds, int(seconds * self.sampling_rate))
        pleth_wave = np.zeros_like(t)
        
        # Create a realistic pleth waveform (simplified model)
        for i in range(0, seconds * 2):  # Match the heart rate of ECG
            center = i / 2
            # Main pulse wave
            pulse = 0.8 * np.exp(-((t - center) ** 2) / 0.01)
            # Dicrotic notch (smaller secondary peak)
            notch = 0.2 * np.exp(-((t - (center + 0.15)) ** 2) / 0.005)
            pleth_wave += pulse + notch
        
        # Add mild noise
        pleth_noise = 0.03 * np.random.randn(len(t))
        pleth_wave += pleth_noise
        
        # Add variations based on respiratory rate
        resp_modulation = 0.2 * np.sin(2 * np.pi * t / 4)  # ~4 second respiration cycle
        pleth_wave *= (1 + resp_modulation)
        
        # Apply section-specific variations like with ECG
        # Tachycardia section - higher frequency, lower amplitude
        tach_start = int(20 * self.sampling_rate)
        tach_end = int(30 * self.sampling_rate)
        tach_pleth = np.zeros_like(pleth_wave[tach_start:tach_end])
        
        for i in range(0, 150):  # Match the tachycardia heart rate
            center = i / 5
            if center > 10:
                break
            pulse = 0.6 * np.exp(-((np.arange(tach_end - tach_start) / self.sampling_rate - center) ** 2) / 0.005)
            notch = 0.1 * np.exp(-((np.arange(tach_end - tach_start) / self.sampling_rate - (center + 0.1)) ** 2) / 0.002)
            tach_pleth += pulse + notch
            
        pleth_wave[tach_start:tach_end] = tach_pleth
        
        # Bradycardia section - lower frequency, more pronounced dicrotic notch
        brady_start = int(40 * self.sampling_rate)
        brady_end = int(50 * self.sampling_rate)
        brady_pleth = np.zeros_like(pleth_wave[brady_start:brady_end])
        
        for i in range(0, 8):  # Match the bradycardia heart rate
            center = i / 0.8
            if center > 10:
                break
            pulse = 0.9 * np.exp(-((np.arange(brady_end - brady_start) / self.sampling_rate - center) ** 2) / 0.015)
            notch = 0.3 * np.exp(-((np.arange(brady_end - brady_start) / self.sampling_rate - (center + 0.25)) ** 2) / 0.01)
            brady_pleth += pulse + notch
        
        pleth_wave[brady_start:brady_end] = brady_pleth
        
        # Generate respiration waveform data - slower frequency than cardiac cycles
        resp_wave = np.zeros_like(t)
        
        # Normal respiration - about 16 breaths per minute
        for i in range(0, int(seconds / 4)):  # ~4 seconds per breath
            center = i * 4 + 2  # Center of each breath
            # Inspiration (faster)
            insp = 0.8 * np.exp(-((t - center) ** 2) / 0.8)
            # Expiration (slower)
            exp = -0.6 * np.exp(-((t - (center + 1.5)) ** 2) / 1.5)
            resp_wave += insp + exp
        
        # Add noise
        resp_noise = 0.05 * np.random.randn(len(t))
        resp_wave += resp_noise
        
        # Adjust respiration based on sections
        # Tachypnea during tachycardia
        tachy_resp = np.zeros_like(resp_wave[tach_start:tach_end])
        for i in range(0, int(10 / 3)):  # ~3 seconds per breath (faster)
            center = tach_start / self.sampling_rate + i * 3 + 1.5
            # Shallower, faster breathing
            insp = 0.6 * np.exp(-((t[tach_start:tach_end] - center) ** 2) / 0.4)
            exp = -0.4 * np.exp(-((t[tach_start:tach_end] - (center + 1)) ** 2) / 0.8)
            tachy_resp += insp + exp
        
        resp_wave[tach_start:tach_end] = tachy_resp
        
        # Slow, deep breathing during bradycardia
        brady_resp = np.zeros_like(resp_wave[brady_start:brady_end])
        for i in range(0, int(10 / 6)):  # ~6 seconds per breath (slower)
            center = brady_start / self.sampling_rate + i * 6 + 3
            # Deeper, slower breathing
            insp = 1.0 * np.exp(-((t[brady_start:brady_end] - center) ** 2) / 1.2)
            exp = -0.8 * np.exp(-((t[brady_start:brady_end] - (center + 2)) ** 2) / 2.0)
            brady_resp += insp + exp
        
        resp_wave[brady_start:brady_end] = brady_resp
        
        # Save all the waveform data
        self.ecg_data = ecg_wave
        self.pleth_data = pleth_wave
        self.resp_data = resp_wave
        
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
            self.monitor_btn.setText("Stop")
            self.monitor_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PHILIPS_DARK_BLUE};
                    color: white;
                    font-weight: bold;
                    border: 1px solid {PHILIPS_LIGHT_BLUE};
                    border-radius: 3px;
                    padding: 5px 10px;
                }}
                QPushButton:hover {{
                    background-color: {PHILIPS_LIGHT_BLUE};
                }}
            """)
            
            # Get speed factor
            speed_text = self.speed_combo.currentText()
            speed_factor = float(speed_text.split()[0]) / 25  # Convert to factor based on 25 mm/s
            
            update_interval = int(50 / speed_factor)  # Base update rate 50ms
            self.timer.start(update_interval)
        else:
            self.is_monitoring = False
            self.monitor_btn.setText("Start")
            self.monitor_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PHILIPS_DARK_BLUE};
                    color: white;
                    font-weight: bold;
                    border: 1px solid {PHILIPS_LIGHT_BLUE};
                    border-radius: 3px;
                    padding: 5px 10px;
                }}
                QPushButton:hover {{
                    background-color: {PHILIPS_LIGHT_BLUE};
                }}
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
        
        # Update displays with more professional formatting
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
            alarm_message = "Low HR"
        elif self.vital_signs["hr"] > 100:
            alarm_triggered = True
            alarm_message = "High HR"
        
        # Check SpO2
        if self.vital_signs["spo2"] < 95:
            alarm_triggered = True
            if alarm_message:
                alarm_message += " | Low SpO₂"
            else:
                alarm_message = "Low SpO₂"
        
        # Check temperature
        if self.vital_signs["temp"] > 37.5:
            alarm_triggered = True
            if alarm_message:
                alarm_message += " | Fever"
            else:
                alarm_message = "Fever"
        elif self.vital_signs["temp"] < 36.5:
            alarm_triggered = True
            if alarm_message:
                alarm_message += " | Low Temp"
            else:
                alarm_message = "Low Temp"
        
        # Update system status based on alarms - more subtly like Philips
        if alarm_triggered and not self.alarm_active:
            self.system_status_label.setText("ALERT")
            self.system_status_label.setStyleSheet(f"color: {PHILIPS_RED}; font-size: 14px; font-weight: bold;")
        elif not alarm_triggered:
            self.system_status_label.setText("NORMAL")
            self.system_status_label.setStyleSheet(f"color: {PHILIPS_GREEN}; font-size: 14px; font-weight: bold;")
    
    def update_plot(self):
        if self.ecg_data is None or self.current_index >= len(self.ecg_data):
            return
        
        display_points = int(self.display_seconds * self.sampling_rate)
        
        # Get the relevant slice of data for all waveforms
        end_idx = min(self.current_index + display_points, len(self.ecg_data))
        ecg_slice = self.ecg_data[self.current_index:end_idx]
        pleth_slice = self.pleth_data[self.current_index:end_idx]
        resp_slice = self.resp_data[self.current_index:end_idx]
        
        # If we don't have enough data to fill the display, pad with zeros
        if len(ecg_slice) < display_points:
            ecg_slice = np.pad(ecg_slice, (0, display_points - len(ecg_slice)))
            pleth_slice = np.pad(pleth_slice, (0, display_points - len(pleth_slice)))
            resp_slice = np.pad(resp_slice, (0, display_points - len(resp_slice)))
        
        # Update the ECG line
        self.line.set_ydata(ecg_slice)
        
        # Update the pleth and resp lines
        self.pleth_line.set_ydata(pleth_slice)
        self.resp_line.set_ydata(resp_slice)
        
        # Add markers for heartbeats (R peaks) for better visualization
        r_peak_indices = self.detect_r_peaks(ecg_slice)
        
        # Clear previous R peak markers by removing all non-line plot elements
        for item in self.ax.collections + self.ax.patches:
            item.remove()
        
        # Add new R peak markers
        for idx in r_peak_indices:
            if 0 <= idx < len(ecg_slice):
                self.ax.plot(self.time_data[idx], ecg_slice[idx], 'o', 
                           color=PHILIPS_YELLOW, markersize=4)
        
        # Draw all canvases
        self.canvas.draw()
        self.pleth_canvas.draw()
        self.resp_canvas.draw()
        
        # Detect arrhythmias
        self.detect_arrhythmias(ecg_slice)
        
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
            
            # Reset all waveforms
            self.line.set_ydata(self.ecg_data[:end_idx])
            self.pleth_line.set_ydata(self.pleth_data[:end_idx])
            self.resp_line.set_ydata(self.resp_data[:end_idx])
            
            self.canvas.draw()
            self.pleth_canvas.draw()
            self.resp_canvas.draw()
            
        # Reset all status indicators
        for attr in dir(self):
            if attr.endswith('_label') and attr != 'heart_rate_label':
                label = getattr(self, attr)
                if isinstance(label, QLabel) and label != self.alarm_label:
                    if attr not in ['date_time_label', 'system_status_label']:
                        label.setText("---")
                        label.setStyleSheet(f"color: {PHILIPS_GREEN}; font-size: 11px; font-weight: bold;")
        
        self.alarm_label.setText("ECG: Normal")
        self.alarm_label.setStyleSheet(f"color: {PHILIPS_GREEN}; font-weight: bold;")
        self.alarm_active = False
        self.mute_btn.setEnabled(False)
        
        # Reset system status
        self.system_status_label.setText("NORMAL")
        self.system_status_label.setStyleSheet(f"color: {PHILIPS_GREEN}; font-size: 14px; font-weight: bold;")
    
    def detect_arrhythmias(self, data_slice):
        # Simple arrhythmia detection based on heart rate for demonstration
        # In a real application, more sophisticated algorithms would be used
        
        heart_rate = self.vital_signs["hr"]
        
        # Check for bradycardia (slow heart rate)
        brady_label = self.brady_label
        if heart_rate < 60:
            brady_label.setText("YES")
            brady_label.setStyleSheet(f"color: {PHILIPS_RED}; font-size: 11px; font-weight: bold;")
            self.trigger_alarm("BRADYCARDIA")
        else:
            brady_label.setText("---")
            brady_label.setStyleSheet(f"color: {PHILIPS_GREEN}; font-size: 11px; font-weight: bold;")
        
        # Check for tachycardia (fast heart rate)
        tachy_label = self.tachy_label
        if heart_rate > 100:
            tachy_label.setText("YES")
            tachy_label.setStyleSheet(f"color: {PHILIPS_RED}; font-size: 11px; font-weight: bold;")
            self.trigger_alarm("TACHYCARDIA")
        else:
            tachy_label.setText("---")
            tachy_label.setStyleSheet(f"color: {PHILIPS_GREEN}; font-size: 11px; font-weight: bold;")
        
        # Detect atrial fibrillation using a simplified approach
        # For demo purposes, use a combination of factors
        atrial_fib_label = getattr(self, "a_fib_label")
        
        # Simple detection of irregular rhythm for demo
        # In real applications, use more sophisticated algorithms
        if self.current_index > 5 * self.sampling_rate:
            # In this simulation, just detect A-fib during the tachycardia section
            # with some randomness to simulate irregular detection
            if (20 * self.sampling_rate < self.current_index < 30 * self.sampling_rate and 
                    heart_rate > 100 and np.random.random() < 0.3):
                atrial_fib_label.setText("YES")
                atrial_fib_label.setStyleSheet(f"color: {PHILIPS_RED}; font-size: 11px; font-weight: bold;")
                self.trigger_alarm("ATRIAL FIB")
            else:
                atrial_fib_label.setText("---")
                atrial_fib_label.setStyleSheet(f"color: {PHILIPS_GREEN}; font-size: 11px; font-weight: bold;")
    
    def calculate_heart_rate(self, data):
        # This method is no longer used directly - heart rate comes from vital signs
        # But we keep it for compatibility
        return int(self.vital_signs["hr"])
    
    def trigger_alarm(self, message):
        if not self.alarm_active:
            self.alarm_active = True
            self.alarm_label.setText(f"ALERT: {message}")
            self.alarm_label.setStyleSheet(f"color: {PHILIPS_RED}; font-weight: bold;")
            self.mute_btn.setEnabled(True)
            
            # Visual feedback with animation
            self.alarm_animation.setDirection(QPropertyAnimation.Forward)
            self.alarm_animation.start()
            
            # In a real application, you would also trigger audible alarms
            # Just show a message box in this simulation - but make it less intrusive
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setText(f"<b>{message}</b>")
            msg.setInformativeText("Click 'Silence' to mute this alarm.")
            msg.setWindowTitle("Arrhythmia Alert")
            msg.setStandardButtons(QMessageBox.Ok)
            
            # Style the message box
            msg.setStyleSheet(f"""
                QMessageBox {{
                    background-color: {PHILIPS_DARK_BLUE};
                    color: white;
                }}
                QLabel {{
                    color: white;
                }}
                QPushButton {{
                    background-color: {PHILIPS_MEDIUM_BLUE};
                    color: white;
                    border: 1px solid {PHILIPS_LIGHT_BLUE};
                    padding: 5px;
                    border-radius: 3px;
                }}
            """)
            
            msg.exec_()
    
    def mute_alarm(self):
        self.alarm_active = False
        self.alarm_label.setStyleSheet(f"color: {PHILIPS_YELLOW}; font-weight: bold;")
        self.alarm_label.setText("Alarm Silenced")
        self.mute_btn.setEnabled(False)
        
        # Stop alarm animation
        self.alarm_animation.setDirection(QPropertyAnimation.Backward)
        self.alarm_animation.start()
        
        # Start a timer to restore alarm capability after a period
        QTimer.singleShot(30000, self.restore_alarm_capability)  # 30 seconds
    
    def detect_r_peaks(self, data):
        """Simple R peak detection for visualization purposes"""
        # This is a very simplified R-peak detection
        # In a real application, use a more robust algorithm
        
        # Find peaks that are higher than a threshold and distance
        r_peaks = []
        threshold = 0.6
        min_distance = int(self.sampling_rate * 0.2)  # Min distance between peaks
        
        for i in range(1, len(data)-1):
            if (data[i] > threshold and 
                data[i] > data[i-1] and 
                data[i] >= data[i+1]):
                
                # Check if this peak is far enough from the previous one
                if not r_peaks or (i - r_peaks[-1]) > min_distance:
                    r_peaks.append(i)
        
        return r_peaks
    
    def restore_alarm_capability(self):
        if not self.alarm_active:
            self.alarm_label.setText("ECG: Normal")
            self.alarm_label.setStyleSheet(f"color: {PHILIPS_GREEN}; font-weight: bold;")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Enable high DPI scaling for modern displays
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Set application-wide style
    app.setStyle('Fusion')  # Consistent style across platforms
    
    # Create and show the main window
    window = ECGMonitor()
    sys.exit(app.exec_())