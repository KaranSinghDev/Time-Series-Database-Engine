# ==============================================================================
#                 EXPLORATION SCRIPT: Core Concepts of PyQt6
# ==============================================================================
#
# This script is a hands-on tutorial to understand the fundamental building blocks
# of PyQt, which we will use to build our diagnostic dashboard.
# To run: python explore_pyqt.py
#
# ==============================================================================

import sys
import random
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel
)
from PyQt6.QtCore import QTimer
import pyqtgraph as pg

# --- CONCEPT 1: The Application and the Main Window ---
# Every PyQt application needs one (and only one) QApplication instance.
# It's the event loop that listens for clicks, key presses, etc.
# The QMainWindow is the top-level container for our application,
# holding toolbars, status bars, and the central content.

class ExplorationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt Exploration Sandbox")
        self.setGeometry(200, 200, 800, 500) # x, y, width, height

        # --- CONCEPT 2: Widgets and Layouts ---
        # Applications are built by arranging 'Widgets' (buttons, labels, etc.)
        # inside 'Layouts'. Layouts manage the size and position of widgets.
        # QVBoxLayout stacks widgets vertically.
        # QHBoxLayout stacks widgets horizontally.

        # Create a central widget to hold our main layout.
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # The main layout will stack our controls and our graph vertically.
        main_layout = QVBoxLayout(central_widget)
        
        # A horizontal layout for our controls.
        controls_layout = QHBoxLayout()

        # Let's create some basic QtWidgets.
        self.info_label = QLabel("Click the button to generate new data.")
        self.update_button = QPushButton("Generate New Data")
        
        # Add the widgets to the horizontal controls layout.
        controls_layout.addWidget(self.info_label)
        controls_layout.addStretch() # Adds a spacer
        controls_layout.addWidget(self.update_button)

        # --- CONCEPT 3: Integrating a Plotting Library (PyQtGraph) ---
        # PyQtGraph is a powerful plotting library designed to integrate seamlessly
        # with PyQt. Its PlotWidget is just another widget we can add to our layouts.
        
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w') # White background
        self.plot_widget.setLabel('left', 'Value')
        self.plot_widget.setLabel('bottom', 'Time (seconds)')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # We get a "PlotDataItem" to which we can send data.
        # We'll store a reference to it so we can update it later.
        self.data_line = self.plot_widget.plot([], [], pen=pg.mkPen('b', width=2))
        
        # Now, we add our horizontal controls layout and our plot widget
        # to the main vertical layout.
        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.plot_widget)
        
        # --- CONCEPT 4: The Signals and Slots Mechanism ---
        # This is the heart of PyQt's interactivity.
        # When an event happens (e.g., a button is clicked), the widget emits a 'Signal'.
        # We can 'connect' this signal to a function (called a 'Slot').
        
        # Here, we connect the 'clicked' signal of our button
        # to a custom function (a 'slot') that we will define.
        self.update_button.clicked.connect(self.update_plot_data)
        
        # Let's also create a timer to simulate real-time data updates.
        self.timer = QTimer()
        self.timer.setInterval(1000) # Update every 1000 ms (1 second)
        self.timer.timeout.connect(self.add_new_point) # The 'timeout' signal
        self.timer.start()
        
        # Initialize the plot with some starting data.
        self.x_data = list(range(10))
        self.y_data = [random.uniform(0, 10) for _ in range(10)]
        self.data_line.setData(self.x_data, self.y_data)
        
        print("Exploration Window Initialized.")
        print(" - Observe the basic layout of widgets.")
        print(" - Click the 'Generate New Data' button to see the 'clicked' signal in action.")
        print(" - Notice the plot updating every second from the QTimer's 'timeout' signal.")


    def update_plot_data(self):
        """This function is called ONLY when the update_button's 'clicked' signal is emitted."""
        print("Signal received: update_button was clicked. Regenerating plot data.")
        

        self.x_data = list(range(10))
        self.y_data = [random.uniform(0, 10) for _ in range(10)]
        
        # Update the data on our existing plot line.
        self.data_line.setData(self.x_data, self.y_data)
        self.info_label.setText("Data was regenerated via button click!")

    def add_new_point(self):
        """This slot is called ONLY when the QTimer's 'timeout' signal is emitted."""
        
        # Add a new data point to the end of our lists.
        new_x = self.x_data[-1] + 1 if self.x_data else 0
        new_y = self.y_data[-1] + random.uniform(-0.5, 0.5) if self.y_data else 5
        
        self.x_data.append(new_x)
        self.y_data.append(new_y)
        
        # To keep the plot from getting too crowded, we'll only show the last 50 points.
        self.data_line.setData(self.x_data[-50:], self.y_data[-50:])
        # The info label won't be updated by the timer, only the button.

# --- The Boilerplate to Run the Application ---
if __name__ == '__main__':
    print("Starting PyQt Exploration Script...")
    
    # Create the main application instance.
    app = QApplication(sys.argv)
    
    # Create an instance of our custom window.
    window = ExplorationWindow()
    
    # Show the window.
    window.show()
    
    # Start the application's event loop.
    print("Application event loop started. The script will now wait for user interaction.")
    sys.exit(app.exec())