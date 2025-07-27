import cv2
import mediapipe as mp
import numpy as np
import tkinter as tk
import pyautogui

class HandTracker:
    def __init__(self):
        # Get screen dimensions
        root = tk.Tk()
        self.screen_width = root.winfo_screenwidth()
        self.screen_height = root.winfo_screenheight()
        root.destroy()
        
        print(f"Screen resolution: {self.screen_width} x {self.screen_height}")
        
        # Configure PyAutoGUI
        pyautogui.FAILSAFE = True  # Move mouse to top-left corner to abort
        pyautogui.PAUSE = 0.01  # Reduce pause for smoother movement
        
        # Disable PyAutoGUI's built-in delay for faster response
        try:
            import pyautogui._pyautogui_win as pag_win
            pag_win.MINIMUM_DURATION = 0
            pag_win.MINIMUM_SLEEP = 0
        except ImportError:
            pass  # Not on Windows or different PyAutoGUI version
        
        # Get initial cursor position
        self.initial_cursor_pos = pyautogui.position()
        print(f"Initial cursor position: {self.initial_cursor_pos}")
        
        # Initialize MediaPipe hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,  # Track only one hand for simplicity
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # Initialize webcam
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Error: Could not open camera")
            raise RuntimeError("Camera initialization failed")
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Get actual webcam resolution
        self.cam_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.cam_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        if self.cam_width == 0 or self.cam_height == 0:
            print("Error: Could not get camera resolution")
            self.cap.release()
            raise RuntimeError("Camera resolution detection failed")
            
        print(f"Camera resolution: {self.cam_width} x {self.cam_height}")
        
        # Define tracking area margins (to avoid edge issues)
        self.margin = 25  # pixels from edge
        self.tracking_area = {
            'left': self.margin,
            'right': self.cam_width - self.margin,
            'top': self.margin,
            'bottom': self.cam_height - self.margin
        }
        
        # Relative positioning variables
        self.initial_position = None
        self.current_mode = "NONE"
        self.previous_mode = "NONE"
        
        # Click detection variables
        self.click_threshold = 0.03  # Increased threshold for easier clicking
        self.is_clicking = False
        self.click_debounce = 0  # Prevent multiple clicks
        
        # Advanced click variables
        self.last_click_time = 0
        self.double_click_threshold = 0.15  # Seconds for double click
        self.right_click_hold_time = 1.0  # Seconds to hold for right click
        self.click_start_time = 0
        self.click_start_pos = None
        
        # Scroll variables
        self.scroll_initial_pos = None
        self.scroll_speed_multiplier = 1.0
        self.scroll_cooldown = 0.02
        self.last_scroll_time = 0
        self.scroll_direction_y = 0  # Change to Y direction for vertical scroll
        
        # Stability variables for reducing drift
        self.movement_threshold = 20  # Minimum pixel movement to register
        self.stability_buffer = []  # Buffer for position averaging
        self.buffer_size = 5  # Number of positions to average
        
    def get_finger_tip_position(self, landmarks, frame_shape, mode):
        """Get the appropriate finger tip position based on mode"""
        if landmarks:
            h, w, _ = frame_shape
            
            if mode == "MODE_1" or mode == "MODE_2":
                # Index finger tip for MODE_1 and MODE_2
                finger_tip = landmarks.landmark[8]
            elif mode == "MODE_3":
                # Pinky finger tip for MODE_3
                finger_tip = landmarks.landmark[20]
            else:
                return None, None
            
            # Convert normalized coordinates to pixel coordinates
            x = int(finger_tip.x * w)
            y = int(finger_tip.y * h)
            
            return x, y
        return None, None
    
    def detect_gesture_mode(self, landmarks):
        """Detect gesture modes based on finger positions"""
        if not landmarks:
            return None
            
        # Get landmark positions for key fingers
        # Index: 5, 6, 7, 8 (tip=8)
        # Middle: 9, 10, 11, 12 (tip=12)
        # Pinky: 17, 18, 19, 20 (tip=20)
        
        # Check if index finger is extended
        index_tip = landmarks.landmark[8]
        index_pip = landmarks.landmark[6]
        index_extended = index_tip.y < index_pip.y
        
        # Check if middle finger is extended
        middle_tip = landmarks.landmark[12]
        middle_pip = landmarks.landmark[10]
        middle_extended = middle_tip.y < middle_pip.y
        
        # Check if pinky finger is extended
        pinky_tip = landmarks.landmark[20]
        pinky_pip = landmarks.landmark[18]
        pinky_extended = pinky_tip.y < pinky_pip.y
        
        # Mode 1: Only index finger extended (1:1 precise control)
        if index_extended and not middle_extended and not pinky_extended:
            return "MODE_1"
            
        # Mode 2: Both index and middle fingers extended (vertical scroll)
        if index_extended and middle_extended and not pinky_extended:
            # Check if fingers are roughly parallel
            index_mcp = landmarks.landmark[5]
            middle_mcp = landmarks.landmark[9]
            
            index_vector_x = index_tip.x - index_mcp.x
            index_vector_y = index_tip.y - index_mcp.y
            
            middle_vector_x = middle_tip.x - middle_mcp.x
            middle_vector_y = middle_tip.y - middle_mcp.y
            
            import math
            index_angle = math.atan2(index_vector_y, index_vector_x)
            middle_angle = math.atan2(middle_vector_y, middle_vector_x)
            
            angle_diff = abs(index_angle - middle_angle)
            if angle_diff > math.pi:
                angle_diff = 2 * math.pi - angle_diff
            
            if angle_diff < 0.52:  # Within 30 degrees
                return "MODE_2"
        
        # Mode 3: Only pinky finger extended (exponential movement)
        if pinky_extended and not index_extended and not middle_extended:
            return "MODE_3"
        
        return "NONE"
    
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
        tips_close = tip_distance < self.click_threshold
        joints_close = joint_distance < (self.click_threshold * 1.2)  # Slightly larger threshold for joints
        
        return tips_close or joints_close
    
    def handle_click_detection(self, landmarks, mode, current_pos):
        """Handle simple single left click detection"""
        import time
        
        if mode != "MODE_1":
            self.is_clicking = False
            self.click_debounce = 0
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
                print("Single click detected!")
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
    
    def handle_scroll_control(self, current_cam_pos, mode):
        """Handle continuous exponential speed scroll control - Y direction (vertical)"""
        import time
        
        if mode != "MODE_2":
            # Reset scroll state when exiting mode
            self.scroll_initial_pos = None
            self.scroll_speed_multiplier = 1.0
            self.scroll_direction_y = 0
            return None, None
            
        current_time = time.time()
        
        # Set initial scroll position and direction
        if self.scroll_initial_pos is None and current_cam_pos is not None:
            self.scroll_initial_pos = current_cam_pos
            self.last_scroll_time = current_time
            self.scroll_speed_multiplier = 1.0
            return 0, 0
            
        if current_cam_pos is None or self.scroll_initial_pos is None:
            return 0, 0
            
        # Check if enough time has passed since last scroll
        if current_time - self.last_scroll_time < self.scroll_cooldown:
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
    
    def calculate_relative_position(self, current_cam_pos, mode):
        """Calculate relative position from initial detection point and move cursor"""
        if current_cam_pos is None:
            return None, None
            
        # Apply stability filter to reduce micro-movements
        stable_pos = self.apply_stability_filter(current_cam_pos)
        if stable_pos is None:
            stable_pos = current_cam_pos
            
        # If mode changed or no initial position, set new initial position
        if mode != self.previous_mode or self.initial_position is None:
            if mode in ["MODE_1", "MODE_2", "MODE_3"]:
                self.initial_position = stable_pos
                # Get current cursor position when gesture starts
                self.initial_cursor_pos = pyautogui.position()
                print(f"New {mode} detected - Setting initial position: {stable_pos}")
                print(f"Current cursor position: {self.initial_cursor_pos}")
                # Clear stability buffer for fresh start
                self.stability_buffer = []
                # Return current cursor position
                return self.initial_cursor_pos[0], self.initial_cursor_pos[1]
            else:
                self.initial_position = None
                self.stability_buffer = []
                return None, None
        
        # If we have an initial position and we're in an active mode
        if self.initial_position and mode in ["MODE_1", "MODE_2", "MODE_3"]:
            # Calculate movement delta from initial position
            delta_x = stable_pos[0] - self.initial_position[0]
            delta_y = stable_pos[1] - self.initial_position[1]
            
            if mode == "MODE_1":
                # 1:1 precise control - no exponential scaling
                sensitivity = 1.0  # Direct 1:1 mapping
                scaled_delta_x = int(delta_x * sensitivity)
                scaled_delta_y = int(delta_y * sensitivity)
                
            elif mode == "MODE_3":
                # Exponential scaling for pinky finger mode (long distance movement)
                def exponential_scale(delta):
                    """Apply exponential scaling to movement delta for long distance"""
                    # Enhanced parameters for longer distance movement
                    base_sensitivity = 1.0   # Minimum movement multiplier
                    exp_factor = 0.015       # Exponential growth rate (reduced for smoother scaling)
                    max_multiplier = 15.0    # Higher maximum for longer distances
                    
                    # Calculate magnitude
                    magnitude = abs(delta)
                    
                    # Exponential scaling: multiplier = base + (max - base) * (1 - e^(-exp_factor * magnitude))
                    exp_component = 1 - np.exp(-exp_factor * magnitude)
                    multiplier = base_sensitivity + (max_multiplier - base_sensitivity) * exp_component
                    
                    # Apply direction and return scaled delta
                    return int(delta * multiplier) if delta != 0 else 0
                
                scaled_delta_x = exponential_scale(delta_x)
                scaled_delta_y = exponential_scale(delta_y)
                
            else:  # MODE_2 - keep original scaling
                sensitivity = 2.0
                scaled_delta_x = int(delta_x * sensitivity)
                scaled_delta_y = int(delta_y * sensitivity)
            
            # Calculate new cursor position from initial cursor position
            new_cursor_x = self.initial_cursor_pos[0] + scaled_delta_x
            new_cursor_y = self.initial_cursor_pos[1] + scaled_delta_y
            
            # Clamp to screen boundaries
            new_cursor_x = max(0, min(self.screen_width - 1, new_cursor_x))
            new_cursor_y = max(0, min(self.screen_height - 1, new_cursor_y))
            
            # Move the actual cursor (for MODE_1 and MODE_3)
            if mode in ["MODE_1", "MODE_3"]:
                try:
                    pyautogui.moveTo(new_cursor_x, new_cursor_y)
                except Exception as e:
                    print(f"Cursor movement error: {e}")
            
            return new_cursor_x, new_cursor_y
        
        return None, None
    
    def map_to_screen_coordinates(self, cam_x, cam_y):
        """Map camera coordinates to screen coordinates"""
        # Clamp to tracking area
        cam_x = max(self.tracking_area['left'], min(self.tracking_area['right'], cam_x))
        cam_y = max(self.tracking_area['top'], min(self.tracking_area['bottom'], cam_y))
        
        # Calculate relative position within tracking area (0.0 to 1.0)
        tracking_width = self.tracking_area['right'] - self.tracking_area['left']
        tracking_height = self.tracking_area['bottom'] - self.tracking_area['top']
        
        # Safety check for division by zero
        if tracking_width <= 0 or tracking_height <= 0:
            return 0, 0
        
        rel_x = (cam_x - self.tracking_area['left']) / tracking_width
        rel_y = (cam_y - self.tracking_area['top']) / tracking_height
        
        # Map to screen coordinates
        screen_x = int(rel_x * self.screen_width)
        screen_y = int(rel_y * self.screen_height)
        
        return screen_x, screen_y
    
    def draw_tracking_area(self, frame):
        """Draw the tracking area boundaries on the frame"""
        # Draw tracking area rectangle
        cv2.rectangle(frame, 
                     (self.tracking_area['left'], self.tracking_area['top']),
                     (self.tracking_area['right'], self.tracking_area['bottom']),
                     (255, 255, 0), 2)  # Yellow border
        
        # Draw corner markers
        corner_size = 20
        # Top-left
        cv2.line(frame, (self.tracking_area['left'], self.tracking_area['top']),
                (self.tracking_area['left'] + corner_size, self.tracking_area['top']), (0, 255, 255), 3)
        cv2.line(frame, (self.tracking_area['left'], self.tracking_area['top']),
                (self.tracking_area['left'], self.tracking_area['top'] + corner_size), (0, 255, 255), 3)
        
        # Top-right
        cv2.line(frame, (self.tracking_area['right'], self.tracking_area['top']),
                (self.tracking_area['right'] - corner_size, self.tracking_area['top']), (0, 255, 255), 3)
        cv2.line(frame, (self.tracking_area['right'], self.tracking_area['top']),
                (self.tracking_area['right'], self.tracking_area['top'] + corner_size), (0, 255, 255), 3)
        
        # Bottom-left
        cv2.line(frame, (self.tracking_area['left'], self.tracking_area['bottom']),
                (self.tracking_area['left'] + corner_size, self.tracking_area['bottom']), (0, 255, 255), 3)
        cv2.line(frame, (self.tracking_area['left'], self.tracking_area['bottom']),
                (self.tracking_area['left'], self.tracking_area['bottom'] - corner_size), (0, 255, 255), 3)
        
        # Bottom-right
        cv2.line(frame, (self.tracking_area['right'], self.tracking_area['bottom']),
                (self.tracking_area['right'] - corner_size, self.tracking_area['bottom']), (0, 255, 255), 3)
        cv2.line(frame, (self.tracking_area['right'], self.tracking_area['bottom']),
                (self.tracking_area['right'], self.tracking_area['bottom'] - corner_size), (0, 255, 255), 3)
        
        # Add labels
        cv2.putText(frame, "TRACKING AREA", 
                   (self.tracking_area['left'] + 10, self.tracking_area['top'] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    
    def smooth_position(self, current_pos, previous_pos, smoothing_factor=0.7):
        """Simple smoothing algorithm to reduce jitter"""
        if previous_pos is None:
            return current_pos
        
        if current_pos is None:
            return previous_pos
            
        # Weighted average for smoothing
        smooth_x = int(smoothing_factor * current_pos[0] + (1 - smoothing_factor) * previous_pos[0])
        smooth_y = int(smoothing_factor * current_pos[1] + (1 - smoothing_factor) * previous_pos[1])
        
        return smooth_x, smooth_y
    
    def apply_stability_filter(self, current_pos):
        """Apply stability filter to reduce micro-movements and drift"""
        if current_pos is None:
            return None
            
        # Add current position to buffer
        self.stability_buffer.append(current_pos)
        
        # Keep buffer at fixed size
        if len(self.stability_buffer) > self.buffer_size:
            self.stability_buffer.pop(0)
        
        # If buffer not full, return current position
        if len(self.stability_buffer) < self.buffer_size:
            return current_pos
        
        # Calculate average position
        avg_x = sum(pos[0] for pos in self.stability_buffer) / len(self.stability_buffer)
        avg_y = sum(pos[1] for pos in self.stability_buffer) / len(self.stability_buffer)
        
        # Check if movement is significant enough
        movement_distance = ((current_pos[0] - avg_x)**2 + (current_pos[1] - avg_y)**2)**0.5
        
        # Only return new position if movement is above threshold
        if movement_distance > self.movement_threshold:
            return current_pos
        else:
            # Return averaged position for stability
            return (int(avg_x), int(avg_y))
    
    def run(self):
        """Main tracking loop"""
        print("Hand tracking started. Press 'q' to quit.")
        print("Advanced Cursor Control System:")
        print("  - FAILSAFE: Move mouse to top-left corner to abort")
        print("Gesture Modes:")
        print("  MODE 1: Index finger extended")
        print("    - Move finger = Exponential cursor movement (slow->precise, fast->rapid)")
        print("    - Quick touch = Single click")
        print("    - Double touch = Double click")
        print("    - Hold touch = Right click")
        print("    - Touch & move = Drag and drop")
        print("  MODE 2: Index + Middle fingers extended (parallel)")
        print("    - Set direction = Continuous delta-based scroll")
        print("    - Speed increases exponentially with finger distance")
        print("    - Move finger further for faster scroll")
        
        previous_position = None
        
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    print("Error: Could not read frame from camera")
                    break
                    
                # Flip frame horizontally for mirror effect
                frame = cv2.flip(frame, 1)
                
                # Draw tracking area first (behind everything else)
                self.draw_tracking_area(frame)
                
                # Convert BGR to RGB for MediaPipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Process the frame
                results = self.hands.process(rgb_frame)
                
                # Initialize variables
                current_mode = "NONE"
                cam_x, cam_y = None, None
                click_action = "NONE"
                scroll_delta_y = 0  # Fix: Change from scroll_delta_x to scroll_delta_y
                screen_x, screen_y = None, None
                
                # Draw hand landmarks if detected
                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        # Draw landmarks
                        self.mp_draw.draw_landmarks(
                            frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
                        )
                        
                        # Detect gesture mode
                        current_mode = self.detect_gesture_mode(hand_landmarks)
                        
                        # Get appropriate finger tip position based on mode
                        cam_x, cam_y = self.get_finger_tip_position(hand_landmarks, frame.shape, current_mode)
                        
                        # Initialize smooth_cam_pos with default value
                        smooth_cam_pos = None
                        
                        if cam_x is not None and cam_y is not None:
                            # Apply smoothing to camera coordinates
                            current_pos = (cam_x, cam_y)
                            smooth_cam_pos = self.smooth_position(current_pos, previous_position)
                            previous_position = smooth_cam_pos
                            
                            if current_mode == "MODE_1":
                                # Handle advanced click detection (precise 1:1 control)
                                click_action = self.handle_click_detection(hand_landmarks, current_mode, smooth_cam_pos)
                                # Calculate relative screen coordinates and move cursor
                                screen_x, screen_y = self.calculate_relative_position(smooth_cam_pos, current_mode)
                            elif current_mode == "MODE_2":
                                # Handle variable speed vertical scroll control
                                _, scroll_delta_y = self.handle_scroll_control(smooth_cam_pos, current_mode)
                                screen_x, screen_y = None, None
                            elif current_mode == "MODE_3":
                                # Handle exponential cursor movement (long distance)
                                click_action = self.handle_click_detection(hand_landmarks, current_mode, smooth_cam_pos)
                                screen_x, screen_y = self.calculate_relative_position(smooth_cam_pos, current_mode)
                            else:
                                screen_x, screen_y = None, None
                        
                        # Update mode tracking
                        self.previous_mode = self.current_mode
                        self.current_mode = current_mode
                        
                        # Draw cursor position on camera feed (only in active modes and when smooth_cam_pos exists)
                        if current_mode in ["MODE_1", "MODE_2", "MODE_3"] and smooth_cam_pos is not None:
                            # Different colors for different modes
                            if current_mode == "MODE_1":
                                # Precise control mode
                                if click_action == "DRAGGING":
                                    cursor_color = (255, 0, 0)  # Blue for dragging
                                elif click_action in ["TOUCHING", "RIGHT_CLICK_HOLD"]:
                                    cursor_color = (0, 0, 255)  # Red when touching
                                else:
                                    cursor_color = (0, 255, 0)  # Green normal
                            elif current_mode == "MODE_2":
                                cursor_color = (255, 0, 255)  # Magenta for scroll mode
                            elif current_mode == "MODE_3":
                                # Exponential movement mode
                                if click_action == "DRAGGING":
                                    cursor_color = (255, 128, 0)  # Orange for dragging
                                elif click_action in ["TOUCHING", "RIGHT_CLICK_HOLD"]:
                                    cursor_color = (0, 128, 255)  # Light blue when touching
                                else:
                                    cursor_color = (255, 255, 0)  # Yellow normal
                                    
                            cv2.circle(frame, smooth_cam_pos, 10, cursor_color, -1)
                            cv2.circle(frame, smooth_cam_pos, 15, cursor_color, 2)
                            
                            # Draw initial position marker if available
                            if self.initial_position and current_mode == "MODE_1":
                                cv2.circle(frame, self.initial_position, 8, (0, 0, 255), 2)  # Red circle for initial position
                                cv2.putText(frame, "START", 
                                          (self.initial_position[0] - 25, self.initial_position[1] - 15),
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                            elif self.scroll_initial_pos and current_mode == "MODE_2":
                                cv2.circle(frame, self.scroll_initial_pos, 8, (255, 0, 255), 2)  # Magenta circle for scroll start
                                cv2.putText(frame, "SCROLL", 
                                          (self.scroll_initial_pos[0] - 30, self.scroll_initial_pos[1] - 15),
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
                        
                        # Check if finger is within tracking area (only if smooth_cam_pos exists)
                        if smooth_cam_pos is not None:
                            in_tracking_area = (
                                self.tracking_area['left'] <= smooth_cam_pos[0] <= self.tracking_area['right'] and
                                self.tracking_area['top'] <= smooth_cam_pos[1] <= self.tracking_area['bottom']
                            )
                        else:
                            in_tracking_area = False
                        
                        # Display coordinates and status based on mode (only if smooth_cam_pos exists)
                        if current_mode == "MODE_1" and screen_x is not None and screen_y is not None and smooth_cam_pos is not None:
                            # Get actual current cursor position
                            actual_cursor = pyautogui.position()
                            
                            status_color = (0, 255, 0) if in_tracking_area else (0, 0, 255)
                            cv2.putText(frame, f"Camera: ({smooth_cam_pos[0]}, {smooth_cam_pos[1]})", 
                                      (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                            cv2.putText(frame, f"Target: ({screen_x}, {screen_y})", 
                                      (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
                            cv2.putText(frame, f"Actual: ({actual_cursor[0]}, {actual_cursor[1]})", 
                                      (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                            
                            # Show advanced click status with improved feedback
                            if self.detect_finger_touch(hand_landmarks):
                                if click_action == "DRAGGING":
                                    click_text = "DRAGGING - Move to drag object"
                                    click_color = (255, 0, 0)
                                elif click_action == "RIGHT_CLICK_HOLD":
                                    click_text = "HOLD FOR RIGHT CLICK..."
                                    click_color = (0, 165, 255)  # Orange
                                elif click_action in ["TOUCHING", "TOUCH_START"]:
                                    click_text = "FINGERS TOUCHING"
                                    click_color = (0, 255, 255)  # Cyan
                                else:
                                    click_text = "FINGERS DETECTED"
                                    click_color = (0, 255, 255)
                            else:
                                click_text = "Touch: Click | Hold: Right-click | Move while touch: Drag"
                                click_color = (255, 255, 255)
                                
                            cv2.putText(frame, click_text, 
                                      (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, click_color, 2)
                            
                            # Show recent action
                            if click_action in ["SINGLE_CLICK", "DOUBLE_CLICK", "RIGHT_CLICK", "DRAG_END"]:
                                action_text = f"Last Action: {click_action.replace('_', ' ')}"
                                cv2.putText(frame, action_text, 
                                          (10, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                            
                            # Show stability info
                            stability_text = f"Stability: {len(self.stability_buffer)}/{self.buffer_size}"
                            cv2.putText(frame, stability_text, 
                                      (10, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 1)
                                      
                        elif current_mode == "MODE_2":
                            cv2.putText(frame, f"Camera: ({smooth_cam_pos[0]}, {smooth_cam_pos[1]})", 
                                      (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                            cv2.putText(frame, f"Scroll Delta Y: {scroll_delta_y:+d}", 
                                      (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
                            
                            # Show delta-based scroll information - Y only
                            delta_magnitude = abs(scroll_delta_y)
                            cv2.putText(frame, f"Scroll Speed: {self.scroll_speed_multiplier:.1f}x (Distance: {delta_magnitude:.1f})", 
                                      (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
                            
                            # Show scroll direction - Y only
                            direction_text = ""
                            if self.scroll_direction_y != 0:
                                direction_text = "DOWN" if self.scroll_direction_y > 0 else "UP"
                            
                            if direction_text:
                                cv2.putText(frame, f"Direction: {direction_text}", 
                                          (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
                            else:
                                cv2.putText(frame, "Move finger up/down from start for vertical scrolling", 
                                          (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
                else:
                    # No hand detected - reset if we lose tracking
                    if self.current_mode in ["MODE_1", "MODE_2", "MODE_3"]:
                        print("Hand lost - Resetting position")
                        self.initial_position = None
                        self.scroll_initial_pos = None
                        self.scroll_speed_multiplier = 1.0
                        self.scroll_direction_y = 0
                        self.current_mode = "NONE"
                        self.is_clicking = False
                        self.stability_buffer = []
                
                # Display current gesture mode
                mode_color = {
                    "MODE_1": (0, 255, 0),      # Green - Precise
                    "MODE_2": (255, 0, 255),    # Magenta - Scroll
                    "MODE_3": (255, 255, 0),    # Yellow - Exponential
                    "NONE": (128, 128, 128)     # Gray
                }
                
                mode_text = {
                    "MODE_1": "MODE 1: Precise Cursor Control (1:1)",
                    "MODE_2": "MODE 2: Vertical Scroll Control",
                    "MODE_3": "MODE 3: Exponential Cursor Control",
                    "NONE": "No Gesture Detected"
                }
                
                cv2.putText(frame, mode_text[current_mode], 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, mode_color[current_mode], 2)
                
                # Display instructions
                cv2.putText(frame, "MODE 1: Index=Precise | MODE 2: Index+Middle=Vertical Scroll | MODE 3: Pinky=Exponential", 
                           (10, frame.shape[0] - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                cv2.putText(frame, "M1: 1:1 Control | M2: Up/Down=Scroll | M3: Fast Long Distance Movement", 
                           (10, frame.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                cv2.putText(frame, "FAILSAFE: Move mouse to top-left | Press 'q' to quit", 
                           (10, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                # Show the frame (MOVED INSIDE the while loop)
                cv2.imshow('Hand Tracking - Gesture Modes', frame)
                
                # Break on 'q' press (MOVED INSIDE the while loop)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break  # This break is CORRECT - don't replace it
                
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            # Cleanup
            print("Cleaning up resources...")
            if hasattr(self, 'hands'):
                self.hands.close()
            if hasattr(self, 'cap'):
                self.cap.release()
            cv2.destroyAllWindows()
            print("Cleanup complete")

if __name__ == "__main__":
    try:
        # Create and run hand tracker
        tracker = HandTracker()
        tracker.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        print("Make sure your camera is connected and not being used by another application")
    finally:
        print("Application terminated")
