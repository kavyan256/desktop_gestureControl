# File: /hand-tracker-project/hand-tracker-project/src/click_handler.py

import pyautogui
import time

class ClickHandler:
    def __init__(self):
        self.is_clicking = False
        self.click_debounce = 0

    def detect_finger_touch(self, landmarks):
        """Detect if middle finger and thumb tips are touching or very close"""
        if not landmarks:
            return False

        # Get thumb tip (landmark 4) and middle finger tip (landmark 12)
        thumb_tip = landmarks.landmark[4]
        middle_tip = landmarks.landmark[12]

        # Also check intermediate joints for better detection
        thumb_ip = landmarks.landmark[3]   # Thumb IP joint
        middle_pip = landmarks.landmark[10]  # Middle finger PIP joint

        # Calculate distance between thumb and middle finger tips
        tip_distance = ((thumb_tip.x - middle_tip.x)**2 + (thumb_tip.y - middle_tip.y)**2)**0.5

        # Also calculate distance between joints for more reliable detection
        joint_distance = ((thumb_ip.x - middle_pip.x)**2 + (thumb_ip.y - middle_pip.y)**2)**0.5

        # Check if either tips are close OR if the fingers are generally close together
        tips_close = tip_distance < 0.03
        joints_close = joint_distance < (0.03 * 1.2)  # Slightly larger threshold for joints

        return tips_close or joints_close

    def handle_click_detection(self, landmarks, mode, current_pos):
        """Handle simple single left click detection"""
        if mode != "MODE_1":
            return "NONE"

        # Check if fingers are touching
        fingers_touching = self.detect_finger_touch(landmarks)

        # Handle finger touch start
        if fingers_touching and not self.is_clicking and self.click_debounce <= 0:
            self.is_clicking = True
            self.click_debounce = 5  # Short debounce for touch detection
            return "TOUCH_START"

        # Handle finger touch release (perform single click)
        elif not fingers_touching and self.is_clicking:
            try:
                pyautogui.click()
            except Exception as e:
                print(f"Single click error: {e}")
            self.is_clicking = False
            return "SINGLE_CLICK"

        # Reduce debounce counter
        if self.click_debounce > 0:
            self.click_debounce -= 1

        # Return current state
        if self.is_clicking:
            return "TOUCHING"
        else:
            return "NONE"