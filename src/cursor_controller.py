# filepath: /hand-tracker-project/hand-tracker-project/src/cursor_controller.py
import pyautogui
import time
import numpy as np
from .coordinate_mapper import CoordinateMapper
from .stability_filter import StabilityFilter

class CursorController:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Initialize missing attributes
        self.previous_mode = None
        self.initial_position = None
        self.initial_cursor_pos = None  # Add this line
        self.last_move_time = 0
        self.drag_active = False
        self.last_cursor_pos = None

    def calculate_relative_position(self, current_cam_pos, mode):
        if current_cam_pos is None:
            return None, None

        if mode not in ["MODE_1", "MODE_2", "MODE_3"]:
            self.initial_position = None
            self.initial_cursor_pos = None
            self.previous_mode = mode
            return None, None

        # If mode changed or we don't have initial positions
        if mode != self.previous_mode or self.initial_position is None:
            self.initial_position = current_cam_pos
            self.initial_cursor_pos = pyautogui.position()
            self.previous_mode = mode

            # Set a short cooldown to ignore movement
            self.last_move_time = time.time()
            return None, None

        # Optional: Ignore small time intervals to prevent jitter
        if time.time() - self.last_move_time < 0.05:
            return None, None

        delta_x = current_cam_pos[0] - self.initial_position[0]
        delta_y = current_cam_pos[1] - self.initial_position[1]

        # Ignore small movements
        movement_threshold = 5
        if abs(delta_x) < movement_threshold and abs(delta_y) < movement_threshold:
            return None, None

        # Remove this problematic line that resets positions every frame:
        # self.initial_position = current_cam_pos
        # self.initial_cursor_pos = pyautogui.position()

        if mode == "MODE_1":
            sensitivity = 1.0
            scaled_delta_x = int(delta_x * sensitivity)
            scaled_delta_y = int(delta_y * sensitivity)

        elif mode == "MODE_3":
            def exponential_scale(delta):
                base_sensitivity = 1.0
                exp_factor = 0.015
                max_multiplier = 15.0

                magnitude = abs(delta)
                exp_component = 1 - np.exp(-exp_factor * magnitude)
                multiplier = base_sensitivity + (max_multiplier - base_sensitivity) * exp_component

                return int(delta * multiplier) if delta != 0 else 0

            scaled_delta_x = exponential_scale(delta_x)
            scaled_delta_y = exponential_scale(delta_y)

        else:  # MODE_2
            sensitivity = 2.0
            scaled_delta_x = int(delta_x * sensitivity)
            scaled_delta_y = int(delta_y * sensitivity)

        new_cursor_x = self.initial_cursor_pos[0] + scaled_delta_x
        new_cursor_y = self.initial_cursor_pos[1] + scaled_delta_y

        new_cursor_x = max(0, min(self.screen_width - 1, new_cursor_x))
        new_cursor_y = max(0, min(self.screen_height - 1, new_cursor_y))

        # Update last move time
        self.last_move_time = time.time()

        if mode in ["MODE_1", "MODE_3"]:
            try:
                pyautogui.moveTo(new_cursor_x, new_cursor_y)
            except Exception as e:
                print(f"Cursor movement error: {e}")

        return new_cursor_x, new_cursor_y


    def map_to_screen_coordinates(self, cam_x, cam_y, tracking_area):
        cam_x = max(tracking_area['left'], min(tracking_area['right'], cam_x))
        cam_y = max(tracking_area['top'], min(tracking_area['bottom'], cam_y))
        
        tracking_width = tracking_area['right'] - tracking_area['left']
        tracking_height = tracking_area['bottom'] - tracking_area['top']
        
        if tracking_width <= 0 or tracking_height <= 0:
            return 0, 0
        
        rel_x = (cam_x - tracking_area['left']) / tracking_width
        rel_y = (cam_y - tracking_area['top']) / tracking_height
        
        screen_x = int(rel_x * self.screen_width)
        screen_y = int(rel_y * self.screen_height)
        
        return screen_x, screen_y