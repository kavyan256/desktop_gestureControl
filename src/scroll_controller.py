# File: /hand-tracker-project/hand-tracker-project/src/scroll_controller.py

import pyautogui
import time
import numpy as np

class ScrollController:
    def __init__(self):
        self.scroll_initial_pos = None
        self.scroll_speed_multiplier = 1.0
        self.scroll_direction_y = 0
        self.last_scroll_time = time.time()

    def handle_scroll_control(self, current_cam_pos, mode):
        """Handle continuous exponential speed scroll control - Y direction (vertical)"""
        
        if mode != "MODE_2":
            # Reset scroll state when exiting mode
            self.scroll_initial_pos = None
            self.scroll_speed_multiplier = 1.0
            self.scroll_direction_y = 0
            return None, None
            
        current_time = time.time()
        
        # Define scroll cooldown in seconds (e.g., 0.05s for 20Hz scroll rate)
        scroll_cooldown = 0.05

        # Set initial scroll position and direction
        if self.scroll_initial_pos is None and current_cam_pos is not None:
            self.scroll_initial_pos = current_cam_pos
            self.last_scroll_time = current_time
            self.scroll_speed_multiplier = 1.0
            return 0, 0
            
        if current_cam_pos is None or self.scroll_initial_pos is None:
            return 0, 0
            
        # Check if enough time has passed since last scroll
        if current_time - self.last_scroll_time < scroll_cooldown:
            return 0, self.scroll_direction_y
            
        # Calculate scroll deltas - only use Y direction for vertical scroll
        delta_y = current_cam_pos[1] - self.scroll_initial_pos[1]
        
        # Minimum threshold for detecting scroll direction
        direction_threshold = 20
        
        # Determine scroll direction based on Y delta (inverted for natural scrolling)
        if abs(delta_y) > direction_threshold:
            # Update scroll direction based on current delta (inverted for natural scroll)
            self.scroll_direction_y = -1 if delta_y > 0 else 1  # Invert for natural scroll
        else:
            self.scroll_direction_y = 0
        
        # Exponential speed increase based on delta magnitude - Y only
        delta_magnitude = abs(delta_y)
        if delta_magnitude > direction_threshold:
            # Exponential growth: speed = base * (growth_rate ^ delta_magnitude)
            base_speed = 2.5
            growth_factor = 0.07
            max_speed = 50.0
            
            # Exponential scaling
            self.scroll_speed_multiplier = min(base_speed * np.exp(growth_factor * delta_magnitude), max_speed)
        else:
            # Reset to base speed if delta is too small
            self.scroll_speed_multiplier = 5.0
        
        # Calculate actual scroll amounts with exponential scaling - Y only
        scroll_y = int(self.scroll_direction_y * self.scroll_speed_multiplier)
        
        # Execute continuous scroll - vertical only
        if self.scroll_direction_y != 0:
            try:
                if scroll_y != 0:
                    pyautogui.scroll(scroll_y)  # Vertical scroll
                    
                self.last_scroll_time = current_time
                print(f"Vertical Scroll: Y={scroll_y} (Delta: {abs(delta_y):.1f}, Speed: {self.scroll_speed_multiplier:.1f}x)")
            except Exception as e:
                print(f"Scroll error: {e}")
                
        return 0, delta_y