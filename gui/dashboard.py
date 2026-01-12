
import sys
import time
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QDateTimeEdit, QLabel, QMessageBox, QCheckBox, QLineEdit
from PyQt6.QtCore import QDateTime, Qt, QTimer
import pyqtgraph as pg
import requests
import numpy as np

# --- Configuration ---
API_BASE_URL = "http://127.0.0.1:8000"

class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sensor Telemetry - Diagnostic Dashboard (Insight-TSDB)")
        self.setGeometry(100, 100, 1200, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # --- FIX: The main layout is now VERTICAL ---
        main_layout = QVBoxLayout(central_widget)

        # --- Controls Layout (Now at the top) ---
        controls_layout = QHBoxLayout()
        self.start_time_edit = QDateTimeEdit(self)
        self.start_time_edit.setDateTime(QDateTime.currentDateTimeUtc().addSecs(-3600))
        self.start_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.start_time_edit.setCalendarPopup(True)
        
        self.end_time_edit = QDateTimeEdit(self)
        self.end_time_edit.setDateTime(QDateTime.currentDateTimeUtc())
        self.end_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_time_edit.setCalendarPopup(True)

        self.query_button = QPushButton("Query Telemetry Data", self)
        
        self.auto_refresh_checkbox = QCheckBox("Auto-refresh every 5s")
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(5000)

        controls_layout.addWidget(QLabel("Start (UTC):"))
        controls_layout.addWidget(self.start_time_edit)
        controls_layout.addWidget(QLabel("End (UTC):"))
        controls_layout.addWidget(self.end_time_edit)
        controls_layout.addWidget(self.query_button)
        controls_layout.addStretch() # Pushes the checkbox to the right
        controls_layout.addWidget(self.auto_refresh_checkbox)
        
        # --- Graphing Widget (Now takes up the main central space) ---
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setLabel('left', 'Sensor Value', color='black')
        self.plot_widget.setLabel('bottom', 'Time', color='black')
        self.plot_item = self.plot_widget.getPlotItem()
        self.plot_item.showGrid(x=True, y=True, alpha=0.3)
        self.plot_item.getAxis('bottom').setStyle(tickTextOffset=10)
        self.data_line = self.plot_item.plot([], [], pen=pg.mkPen('#0072B2', width=2))
        
        # --- Statistical Summary Panel (Now at the bottom) ---
        stats_layout = QHBoxLayout()
        self.stat_count = self.create_stat_box("Data Points")
        self.stat_mean = self.create_stat_box("Mean")
        self.stat_max = self.create_stat_box("Max Value")
        self.stat_min = self.create_stat_box("Min Value")
        stats_layout.addLayout(self.stat_count)
        stats_layout.addLayout(self.stat_mean)
        stats_layout.addLayout(self.stat_max)
        stats_layout.addLayout(self.stat_min)

        # --- FIX: Assemble the new Vertical Layout ---
        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.plot_widget) # Graph is the main widget
        main_layout.addLayout(stats_layout)
        
        # --- Crosshair and other features remain the same ---
        self.crosshair_v = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('k', style=Qt.PenStyle.DashLine))
        self.crosshair_h = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('k', style=Qt.PenStyle.DashLine))
        self.plot_widget.addItem(self.crosshair_v, ignoreBounds=True)
        self.plot_widget.addItem(self.crosshair_h, ignoreBounds=True)
        self.value_label = pg.TextItem(text="", color=(0, 0, 0), anchor=(0, 1))
        self.value_label.setZValue(10)
        self.plot_widget.addItem(self.value_label)

        # --- Connect Signals and Slots (no changes needed) ---
        self.query_button.clicked.connect(self.run_query_and_update_plot)
        self.auto_refresh_checkbox.stateChanged.connect(self.toggle_auto_refresh)
        self.plot_widget.scene().sigMouseMoved.connect(self.on_mouse_move)
        self.refresh_timer.timeout.connect(self.run_query_and_update_plot)

    # All other functions (create_stat_box, on_mouse_move, run_query_and_update_plot, etc.)
    # remain exactly the same. Only the __init__ layout logic has changed.

    def create_stat_box(self, name):
        layout = QVBoxLayout()
        label = QLabel(name)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value = QLineEdit("N/A")
        value.setReadOnly(True)
        value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; font-weight: bold;")
        layout.addWidget(label)
        layout.addWidget(value)
        return layout

    def on_mouse_move(self, event):
        if self.plot_item.vb.sceneBoundingRect().contains(event):
            mouse_point = self.plot_item.vb.mapSceneToView(event)
            self.crosshair_v.setPos(mouse_point.x())
            self.crosshair_h.setPos(mouse_point.y())
            self.value_label.setText(f"Time: {QDateTime.fromSecsSinceEpoch(int(mouse_point.x())).toString('HH:mm:ss')}, Value: {mouse_point.y():.2f}")
            self.value_label.setPos(mouse_point.x(), mouse_point.y())

    def toggle_auto_refresh(self, state):
        if state == Qt.CheckState.Checked.value:
            self.refresh_timer.start()
            self.run_query_and_update_plot()
        else:
            self.refresh_timer.stop()
            
    def run_query_and_update_plot(self):
        try:
            start_ts_ms = self.start_time_edit.dateTime().toMSecsSinceEpoch()
            end_ts_ms = self.end_time_edit.dateTime().toMSecsSinceEpoch()

            if start_ts_ms >= end_ts_ms and self.refresh_timer.isActive() == False:
                self.show_message_box("Invalid Time Range", "Start time must be before end time.", QMessageBox.Icon.Warning)
                return

            query_url = f"{API_BASE_URL}/api/query"
            params = {"start_ts": start_ts_ms, "end_ts": end_ts_ms}
            response = requests.get(query_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            points = data.get("points", [])
            
            self.plot_item.clear() # Clear previous plot items
            self.plot_item.addItem(self.crosshair_v) # Re-add crosshairs
            self.plot_item.addItem(self.crosshair_h)
            self.plot_item.addItem(self.value_label)
            
            self.reset_stats()

            if not points:
                # Don't show a pop-up if auto-refreshing, just clear the view
                if not self.refresh_timer.isActive():
                    self.show_message_box("No Data", "No telemetry data found for the selected time range.", QMessageBox.Icon.Information)
                return

            timestamps_s = np.array([p['timestamp'] / 1000 for p in points])
            values = np.array([p['value'] for p in points])

            self.data_line = self.plot_item.plot(timestamps_s, values, pen=pg.mkPen('#0072B2', width=2))
            
            axis = self.plot_widget.getAxis('bottom')
            if len(timestamps_s) > 1:
                tick_values = np.linspace(min(timestamps_s), max(timestamps_s), 5)
                axis.setTicks([[(t, QDateTime.fromSecsSinceEpoch(int(t)).toString("HH:mm:ss")) for t in tick_values]])
            
            self.update_stats(values)

        except requests.exceptions.RequestException:
            self.show_message_box("Connection Error", f"Could not connect to the database service at {API_BASE_URL}.\nPlease ensure the Docker container is running.", QMessageBox.Icon.Critical)
            self.refresh_timer.stop()
            self.auto_refresh_checkbox.setChecked(False)
        except Exception as e:
            self.show_message_box("An Error Occurred", f"An unexpected error occurred: {e}", QMessageBox.Icon.Critical)
    
    def update_stats(self, values):
        self.stat_count.itemAt(1).widget().setText(f"{len(values)}")
        self.stat_mean.itemAt(1).widget().setText(f"{np.mean(values):.2f}")
        self.stat_max.itemAt(1).widget().setText(f"{np.max(values):.2f}")
        self.stat_min.itemAt(1).widget().setText(f"{np.min(values):.2f}")
    
    def reset_stats(self):
        self.stat_count.itemAt(1).widget().setText("N/A")
        self.stat_mean.itemAt(1).widget().setText("N/A")
        self.stat_max.itemAt(1).widget().setText("N/A")
        self.stat_min.itemAt(1).widget().setText("N/A")

    def show_message_box(self, title, message, icon):
        msg_box = QMessageBox(self)
        msg_box.setIcon(icon)
        msg_box.setText(title)
        msg_box.setInformativeText(message)
        msg_box.setWindowTitle("Dashboard Notification")
        msg_box.exec()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = DashboardWindow()
    main_window.show()
    sys.exit(app.exec())