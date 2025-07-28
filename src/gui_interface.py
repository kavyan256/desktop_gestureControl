import tkinter as tk
from tkinter import ttk
import threading
import time

class HandTrackerGUI:
    def __init__(self, hand_tracker):
        self.hand_tracker = hand_tracker  # Keep reference to the tracker
        self.tracker = hand_tracker       # Alias for compatibility
        
        self.root = tk.Tk()
        self.root.title("Hand Tracker Control Panel")
        self.root.geometry("400x600")
        
        # Initialize all GUI variables first
        self.is_active = tk.BooleanVar(value=True)  # Always active now
        self.current_mode = tk.StringVar(value="NONE")
        self.gesture_detected = tk.StringVar(value="None")
        self.fps = tk.StringVar(value="0.0")
        self.show_camera_feed = tk.BooleanVar(value=True)
        self.show_overlay = tk.BooleanVar(value=True)
        self.mode_1_enabled = tk.BooleanVar(value=True)
        self.mode_2_enabled = tk.BooleanVar(value=True)
        self.mode_3_enabled = tk.BooleanVar(value=True)
        
        self.setup_ui()
        
        # Start status update thread
        self.update_thread = threading.Thread(target=self.update_status_loop, daemon=True)
        self.update_thread.start()
        
        # Start tracker in background
        self.tracker_thread = threading.Thread(target=self.tracker.run, daemon=True)
        self.tracker_thread.start()
    
    def setup_ui(self):
        # Title
        title_label = tk.Label(self.root, text="Hand Tracker Control Panel", 
                              font=("Arial", 16, "bold"), fg="blue")
        title_label.pack(pady=10)
        
        # Status Frame
        status_frame = ttk.LabelFrame(self.root, text="Tracking Status", padding=10)
        status_frame.pack(fill="x", padx=10, pady=5)
        
        # Current mode
        mode_label = tk.Label(status_frame, text="Current Mode:")
        mode_label.grid(row=0, column=0, sticky="w", padx=5)
        
        current_mode_label = tk.Label(status_frame, textvariable=self.current_mode,
                                     font=("Arial", 10), fg="blue")
        current_mode_label.grid(row=0, column=1, padx=5)
        
        # Gesture detected
        gesture_label = tk.Label(status_frame, text="Gesture:")
        gesture_label.grid(row=1, column=0, sticky="w", padx=5, pady=2)
        
        gesture_value_label = tk.Label(status_frame, textvariable=self.gesture_detected,
                                      font=("Arial", 10), fg="green")
        gesture_value_label.grid(row=1, column=1, padx=5, pady=2)
        
        # FPS
        fps_label = tk.Label(status_frame, text="FPS:")
        fps_label.grid(row=2, column=0, sticky="w", padx=5, pady=2)
        
        fps_value_label = tk.Label(status_frame, textvariable=self.fps,
                                  font=("Arial", 10), fg="purple")
        fps_value_label.grid(row=2, column=1, padx=5, pady=2)
        
        # Display Settings Frame
        display_frame = ttk.LabelFrame(self.root, text="Display Settings", padding=10)
        display_frame.pack(fill="x", padx=10, pady=5)
        
        camera_check = tk.Checkbutton(display_frame, text="Show Camera Feed",
                                     variable=self.show_camera_feed,
                                     command=self.update_display_settings)
        camera_check.pack(anchor="w", pady=2)
        
        overlay_check = tk.Checkbutton(display_frame, text="Show Overlay",
                                      variable=self.show_overlay,
                                      command=self.update_display_settings)
        overlay_check.pack(anchor="w", pady=2)
        
        # Mode Settings Frame
        mode_frame = ttk.LabelFrame(self.root, text="Gesture Modes", padding=10)
        mode_frame.pack(fill="x", padx=10, pady=5)
        
        mode1_check = tk.Checkbutton(mode_frame, text="MODE 1: Cursor Control (Index finger)",
                                    variable=self.mode_1_enabled,
                                    command=self.update_mode_settings)
        mode1_check.pack(anchor="w", pady=2)
        
        mode2_check = tk.Checkbutton(mode_frame, text="MODE 2: Scroll Control (Index + Middle)",
                                    variable=self.mode_2_enabled,
                                    command=self.update_mode_settings)
        mode2_check.pack(anchor="w", pady=2)
        
        mode3_check = tk.Checkbutton(mode_frame, text="MODE 3: Precision Mode",
                                    variable=self.mode_3_enabled,
                                    command=self.update_mode_settings)
        mode3_check.pack(anchor="w", pady=2)
        
        # Advanced Settings Frame
        advanced_frame = ttk.LabelFrame(self.root, text="Advanced Settings", padding=10)
        advanced_frame.pack(fill="x", padx=10, pady=5)
        
        # Sensitivity slider
        sensitivity_label = tk.Label(advanced_frame, text="Cursor Sensitivity:")
        sensitivity_label.pack(anchor="w")
        
        self.sensitivity_scale = tk.Scale(advanced_frame, from_=0.1, to=3.0, 
                                         resolution=0.1, orient="horizontal",
                                         command=self.update_sensitivity)
        self.sensitivity_scale.set(1.0)
        self.sensitivity_scale.pack(fill="x", pady=2)
        
        # Smoothing slider
        smoothing_label = tk.Label(advanced_frame, text="Movement Smoothing:")
        smoothing_label.pack(anchor="w")
        
        self.smoothing_scale = tk.Scale(advanced_frame, from_=0.1, to=1.0, 
                                       resolution=0.1, orient="horizontal",
                                       command=self.update_smoothing)
        self.smoothing_scale.set(0.7)
        self.smoothing_scale.pack(fill="x", pady=2)
        
        # Control buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(button_frame, text="Stop System", 
                  command=self.stop_system).pack(side="right", padx=5)
        
        # Instructions
        instructions_frame = ttk.LabelFrame(self.root, text="Instructions", padding=10)
        instructions_frame.pack(fill="x", padx=10, pady=5)
        
        instructions_text = """
📷 Camera is always active
🖐️ Make hand gestures to control cursor
Mode 1: Index finger - Precise cursor control
Mode 2: Index + Middle - Vertical scrolling  
Mode 3: Pinky finger - Fast cursor movement
        """
        
        instructions_label = tk.Label(instructions_frame, text=instructions_text.strip(),
                                     font=("Arial", 9), justify="left")
        instructions_label.pack(anchor="w")
    
    def update_display_settings(self):
        """Update display settings in hand tracker"""
        if hasattr(self.tracker, 'show_camera_feed'):
            self.tracker.show_camera_feed = self.show_camera_feed.get()
        if hasattr(self.tracker, 'show_overlay'):
            self.tracker.show_overlay = self.show_overlay.get()
    
    def update_mode_settings(self):
        """Update enabled modes in hand tracker"""
        if hasattr(self.tracker, 'enabled_modes'):
            self.tracker.enabled_modes = {
                'MODE_1': self.mode_1_enabled.get(),
                'MODE_2': self.mode_2_enabled.get(),
                'MODE_3': self.mode_3_enabled.get()
            }
    
    def update_sensitivity(self, value):
        """Update cursor sensitivity"""
        if hasattr(self.tracker, 'cursor_sensitivity'):
            self.tracker.cursor_sensitivity = float(value)
    
    def update_smoothing(self, value):
        """Update movement smoothing"""
        if hasattr(self.tracker, 'smoothing_factor'):
            self.tracker.smoothing_factor = float(value)
    
    def update_status_loop(self):
        """Update system status in a separate thread"""
        while True:
            try:
                # Update tracking status
                if hasattr(self.tracker, 'current_mode'):
                    self.current_mode.set(self.tracker.current_mode)
                if hasattr(self.tracker, 'last_gesture'):
                    self.gesture_detected.set(self.tracker.last_gesture)
                if hasattr(self.tracker, 'fps'):
                    self.fps.set(f"{self.tracker.fps:.1f}")
                
                time.sleep(0.1)  # Update every 100ms
                
            except Exception as e:
                print(f"Status update error: {e}")
                time.sleep(1)
    
    def stop_system(self):
        """Stop the entire system"""
        self.tracker.running = False
        if hasattr(self.tracker, 'stop'):
            self.tracker.stop()
        print("System stopped")
        self.root.quit()
    
    def run(self):
        """Start the GUI"""
        try:
            self.root.mainloop()
        finally:
            # Cleanup when GUI closes
            if hasattr(self.tracker, 'stop'):
                self.tracker.stop()