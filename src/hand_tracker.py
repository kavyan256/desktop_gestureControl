import cv2
import mediapipe as mp
import pyautogui
import tkinter as tk
import time
import threading

from .gesture_detector import GestureDetector
from .cursor_controller import CursorController
from .scroll_controller import ScrollController
from .click_handler import ClickHandler
from .coordinate_mapper import CoordinateMapper
from .stability_filter import StabilityFilter
from .ui_overlay import UIOverlay

class HandTracker:
    def __init__(self):
        root = tk.Tk()
        self.screen_width = root.winfo_screenwidth()
        self.screen_height = root.winfo_screenheight()
        root.destroy()
        
        print(f"Screen resolution: {self.screen_width} x {self.screen_height}")
        
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.01
        
        try:
            import pyautogui._pyautogui_win as pag_win
            pag_win.MINIMUM_DURATION = 0
            pag_win.MINIMUM_SLEEP = 0
        except ImportError:
            pass
        
        self.initial_cursor_pos = pyautogui.position()
        print(f"Initial cursor position: {self.initial_cursor_pos}")
        
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # Initialize camera
        self.cap = None
        self.cam_width = 640
        self.cam_height = 480
        
        self.margin = 25
        self.tracking_area = {
            'left': self.margin,
            'right': self.cam_width - self.margin,
            'top': self.margin,
            'bottom': self.cam_height - self.margin
        }
        
        self.initial_position = None
        self.current_mode = "NONE"
        self.previous_mode = "NONE"
        
        self.click_threshold = 0.03
        self.is_clicking = False
        self.click_debounce = 0
        
        self.last_click_time = 0
        self.double_click_threshold = 0.15
        self.right_click_hold_time = 1.0
        self.click_start_time = 0
        self.click_start_pos = None
        
        self.scroll_initial_pos = None
        self.scroll_speed_multiplier = 1.0
        self.scroll_cooldown = 0.02
        self.last_scroll_time = 0
        self.scroll_direction_y = 0
        
        self.movement_threshold = 20
        self.stability_buffer = []
        self.buffer_size = 5
        
        # Initialize components
        self.gesture_detector = GestureDetector()
        self.cursor_controller = CursorController(self.screen_width, self.screen_height)
        self.scroll_controller = ScrollController()
        self.click_handler = ClickHandler()
        self.coordinate_mapper = CoordinateMapper(
            self.screen_width, self.screen_height, 
            self.cam_width, self.cam_height, 
            self.tracking_area
        )
        self.stability_filter = StabilityFilter(self.buffer_size, self.movement_threshold)
        self.ui_overlay = UIOverlay()
        
        # GUI control variables
        self.show_camera_feed = True
        self.show_overlay = True
        self.enabled_modes = {
            'MODE_1': True,
            'MODE_2': True,
            'MODE_3': True
        }
        self.cursor_sensitivity = 1.0
        self.smoothing_factor = 0.7
        self.running = False
        self.last_gesture = "None"
        self.fps = 0.0
        self.frame_count = 0
        self.fps_start_time = time.time()
        
        # Initialize camera immediately
        self._init_camera()
    
    def _init_camera(self):
        """Initialize camera"""
        if self.cap is None:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("Error: Could not open camera")
                return False
                
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            self.cam_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.cam_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            if self.cam_width == 0 or self.cam_height == 0:
                print("Error: Could not get camera resolution")
                self.cap.release()
                self.cap = None
                return False
                
            print(f"Camera resolution: {self.cam_width} x {self.cam_height}")
            
            # Update tracking area with actual camera dimensions
            self.tracking_area = {
                'left': self.margin,
                'right': self.cam_width - self.margin,
                'top': self.margin,
                'bottom': self.cam_height - self.margin
            }
            
            return True
        return True
    
    def _release_camera(self):
        """Release camera resources"""
        if self.cap:
            self.cap.release()
            self.cap = None
            cv2.destroyAllWindows()
    
    def process_frame(self, frame):
        """Process a single frame and return the processed frame and detection results"""
        frame = cv2.flip(frame, 1)
        
        self.ui_overlay.draw_tracking_area(frame, self.tracking_area)
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        detection_result = {
            'mode_detected': False,
            'hand_landmarks': None,
            'gesture': None,
            'current_mode': "NONE"
        }
        
        current_mode = "NONE"
        cam_x, cam_y = None, None
        click_action = "NONE"
        scroll_delta_y = 0
        screen_x, screen_y = None, None
        previous_position = getattr(self, '_previous_position', None)
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(
                    frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
                )
                
                current_mode = self.gesture_detector.detect_gesture_mode(hand_landmarks)
                
                if current_mode in ["MODE_1", "MODE_2", "MODE_3"]:
                    detection_result['mode_detected'] = True
                    detection_result['hand_landmarks'] = hand_landmarks
                    detection_result['gesture'] = current_mode
                    detection_result['current_mode'] = current_mode
                
                cam_x, cam_y = self.gesture_detector.get_finger_tip_position(hand_landmarks, frame.shape, current_mode)
                
                smooth_cam_pos = None
                
                if cam_x is not None and cam_y is not None:
                    current_pos = (cam_x, cam_y)
                    smooth_cam_pos = self.stability_filter.smooth_position(current_pos, previous_position)
                    self._previous_position = smooth_cam_pos
                    
                    if current_mode == "MODE_1":
                        click_action = self.click_handler.handle_click_detection(hand_landmarks, current_mode, smooth_cam_pos)
                        screen_x, screen_y = self.cursor_controller.calculate_relative_position(smooth_cam_pos, current_mode)
                    elif current_mode == "MODE_2":
                        _, scroll_delta_y = self.scroll_controller.handle_scroll_control(smooth_cam_pos, current_mode)
                        screen_x, screen_y = None, None
                    elif current_mode == "MODE_3":
                        click_action = self.click_handler.handle_click_detection(hand_landmarks, current_mode, smooth_cam_pos)
                        screen_x, screen_y = self.cursor_controller.calculate_relative_position(smooth_cam_pos, current_mode)
                    else:
                        screen_x, screen_y = None, None
                
                self.previous_mode = self.current_mode
                self.current_mode = current_mode
                self.last_gesture = current_mode
                
                # Draw visual feedback
                self._draw_visual_feedback(frame, current_mode, smooth_cam_pos, click_action, 
                                         scroll_delta_y, screen_x, screen_y)
        else:
            if self.current_mode in ["MODE_1", "MODE_2", "MODE_3"]:
                print("Hand lost - Resetting position")
                self._reset_tracking_state()
        
        self._draw_mode_info(frame, current_mode)
        self._draw_instructions(frame)
        
        return frame, detection_result
    
    def _draw_visual_feedback(self, frame, current_mode, smooth_cam_pos, click_action, 
                             scroll_delta_y, screen_x, screen_y):
        """Draw visual feedback on frame"""
        if current_mode in ["MODE_1", "MODE_2", "MODE_3"] and smooth_cam_pos is not None:
            cursor_color = (0, 255, 0)
            cv2.circle(frame, smooth_cam_pos, 10, cursor_color, -1)
            cv2.circle(frame, smooth_cam_pos, 15, cursor_color, 2)
            
            if self.initial_position and current_mode == "MODE_1":
                cv2.circle(frame, self.initial_position, 8, (0, 0, 255), 2)
                cv2.putText(frame, "START", 
                          (self.initial_position[0] - 25, self.initial_position[1] - 15),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            elif self.scroll_initial_pos and current_mode == "MODE_2":
                cv2.circle(frame, self.scroll_initial_pos, 8, (255, 0, 255), 2)
                cv2.putText(frame, "SCROLL", 
                          (self.scroll_initial_pos[0] - 30, self.scroll_initial_pos[1] - 15),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
        
        # Draw mode-specific information
        if current_mode == "MODE_1" and screen_x is not None and screen_y is not None:
            self._draw_mode1_info(frame, smooth_cam_pos, screen_x, screen_y, click_action)
        elif current_mode == "MODE_2":
            self._draw_mode2_info(frame, smooth_cam_pos, scroll_delta_y)
    
    def _draw_mode1_info(self, frame, smooth_cam_pos, screen_x, screen_y, click_action):
        """Draw MODE_1 specific information"""
        actual_cursor = pyautogui.position()
        
        in_tracking_area = (
            self.tracking_area['left'] <= smooth_cam_pos[0] <= self.tracking_area['right'] and
            self.tracking_area['top'] <= smooth_cam_pos[1] <= self.tracking_area['bottom']
        )
        
        status_color = (0, 255, 0) if in_tracking_area else (0, 0, 255)
        cv2.putText(frame, f"Camera: ({smooth_cam_pos[0]}, {smooth_cam_pos[1]})", 
                  (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Target: ({screen_x}, {screen_y})", 
                  (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        cv2.putText(frame, f"Actual: ({actual_cursor[0]}, {actual_cursor[1]})", 
                  (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Click feedback
        if hasattr(self.click_handler, 'detect_finger_touch') and self.click_handler.detect_finger_touch(
            getattr(self, '_last_hand_landmarks', None) if hasattr(self, '_last_hand_landmarks') else None
        ):
            if click_action == "DRAGGING":
                click_text = "DRAGGING - Move to drag object"
                click_color = (255, 0, 0)
            elif click_action == "RIGHT_CLICK_HOLD":
                click_text = "HOLD FOR RIGHT CLICK..."
                click_color = (0, 165, 255)
            elif click_action in ["TOUCHING", "TOUCH_START"]:
                click_text = "FINGERS TOUCHING"
                click_color = (0, 255, 255)
            else:
                click_text = "FINGERS DETECTED"
                click_color = (0, 255, 255)
        else:
            click_text = "Touch: Click | Hold: Right-click | Move while touch: Drag"
            click_color = (255, 255, 255)
            
        cv2.putText(frame, click_text, 
                  (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, click_color, 2)
        
        if click_action in ["SINGLE_CLICK", "DOUBLE_CLICK", "RIGHT_CLICK", "DRAG_END"]:
            action_text = f"Last Action: {click_action.replace('_', ' ')}"
            cv2.putText(frame, action_text, 
                      (10, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        stability_text = f"Stability: {len(self.stability_buffer)}/{self.buffer_size}"
        cv2.putText(frame, stability_text, 
                  (10, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 1)
    
    def _draw_mode2_info(self, frame, smooth_cam_pos, scroll_delta_y):
        """Draw MODE_2 specific information"""
        cv2.putText(frame, f"Camera: ({smooth_cam_pos[0]}, {smooth_cam_pos[1]})", 
                  (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Scroll Delta Y: {scroll_delta_y:+d}", 
                  (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
        
        delta_magnitude = abs(scroll_delta_y)
        cv2.putText(frame, f"Scroll Speed: {self.scroll_speed_multiplier:.1f}x (Distance: {delta_magnitude:.1f})", 
                  (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
        
        direction_text = ""
        if self.scroll_direction_y != 0:
            direction_text = "DOWN" if self.scroll_direction_y > 0 else "UP"
        
        if direction_text:
            cv2.putText(frame, f"Direction: {direction_text}", 
                      (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
        else:
            cv2.putText(frame, "Move finger up/down from start for vertical scrolling", 
                      (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
    
    def _draw_mode_info(self, frame, current_mode):
        """Draw current mode information"""
        mode_color = {
            "MODE_1": (0, 255, 0),
            "MODE_2": (255, 0, 255),
            "MODE_3": (255, 255, 0),
            "NONE": (128, 128, 128)
        }
        
        mode_text = {
            "MODE_1": "MODE 1: Precise Cursor Control (1:1)",
            "MODE_2": "MODE 2: Vertical Scroll Control",
            "MODE_3": "MODE 3: Exponential Cursor Control",
            "NONE": "No Gesture Detected"
        }
        
        cv2.putText(frame, mode_text[current_mode], 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, mode_color[current_mode], 2)
    
    def _draw_instructions(self, frame):
        """Draw instruction text"""
        cv2.putText(frame, "MODE 1: Index=Precise | MODE 2: Index+Middle=Vertical Scroll | MODE 3: Pinky=Exponential", 
                   (10, frame.shape[0] - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        cv2.putText(frame, "M1: 1:1 Control | M2: Up/Down=Scroll | M3: Fast Long Distance Movement", 
                   (10, frame.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        cv2.putText(frame, "FAILSAFE: Move mouse to top-left | Press 'q' to quit", 
                   (10, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    
    def _reset_tracking_state(self):
        """Reset tracking state"""
        self.initial_position = None
        self.scroll_initial_pos = None
        self.scroll_speed_multiplier = 1.0
        self.scroll_direction_y = 0
        self.current_mode = "NONE"
        self.is_clicking = False
        self.stability_buffer = []
    
    def _update_fps(self):
        """Update FPS calculation"""
        self.frame_count += 1
        current_time = time.time()
        
        if current_time - self.fps_start_time >= 1.0:  # Update every second
            self.fps = self.frame_count / (current_time - self.fps_start_time)
            self.frame_count = 0
            self.fps_start_time = current_time
    
    def stop(self):
        """Stop the hand tracker"""
        self.running = False
        self._release_camera()
    
    def run(self):
        """Main tracking loop"""
        print("Hand Tracking System started!")
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
        
        if not self._init_camera():
            print("Failed to initialize camera")
            return
        
        self.running = True
        
        try:
            while self.running:
                # Read frame
                ret, frame = self.cap.read()
                if not ret:
                    print("Error: Could not read frame")
                    break
                
                # Process frame
                processed_frame, detection_result = self.process_frame(frame)
                
                # Display frame if enabled
                if self.show_camera_feed:
                    cv2.imshow('Hand Tracking', processed_frame)
                
                # Update FPS
                self._update_fps()
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.01)
                    
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.stop()

if __name__ == "__main__":
    try:
        tracker = HandTracker()
        tracker.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        print("Make sure your camera is connected and not being used by another application")
    finally:
        print("Application terminated")