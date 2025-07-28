# File: /hand-tracker-project/hand-tracker-project/src/gesture_detector.py

import math
import mediapipe as mp

class GestureDetector:
    def __init__(self):
        pass
    
    def detect_gesture_mode(self, hand_landmarks):
        """Detect gesture mode based on extended fingers"""
        if not hand_landmarks:
            return None
            
        index_tip = hand_landmarks.landmark[8]
        index_pip = hand_landmarks.landmark[6]
        index_extended = index_tip.y < index_pip.y
        
        middle_tip = hand_landmarks.landmark[12]
        middle_pip = hand_landmarks.landmark[10]
        middle_extended = middle_tip.y < middle_pip.y
        
        pinky_tip = hand_landmarks.landmark[20]
        pinky_pip = hand_landmarks.landmark[18]
        pinky_extended = pinky_tip.y < pinky_pip.y
        
        if index_extended and not middle_extended and not pinky_extended:
            return "MODE_1"
            
        if index_extended and middle_extended and not pinky_extended:
            index_mcp = hand_landmarks.landmark[5]
            middle_mcp = hand_landmarks.landmark[9]
            
            index_vector_x = index_tip.x - index_mcp.x
            index_vector_y = index_tip.y - index_mcp.y
            
            middle_vector_x = middle_tip.x - middle_mcp.x
            middle_vector_y = middle_tip.y - middle_mcp.y
            
            index_angle = math.atan2(index_vector_y, index_vector_x)
            middle_angle = math.atan2(middle_vector_y, middle_vector_x)
            
            angle_diff = abs(index_angle - middle_angle)
            if angle_diff > math.pi:
                angle_diff = 2 * math.pi - angle_diff
            
            if angle_diff < 0.52:
                return "MODE_2"
        
        if pinky_extended and not index_extended and not middle_extended:
            return "MODE_3"
        
        return "NONE"
    
    def get_finger_tip_position(self, hand_landmarks, frame_shape, mode):
        """Get finger tip position based on mode"""
        if hand_landmarks:
            h, w, _ = frame_shape
            
            if mode == "MODE_1" or mode == "MODE_2":
                finger_tip = hand_landmarks.landmark[8]
            elif mode == "MODE_3":
                finger_tip = hand_landmarks.landmark[20]
            else:
                return None, None
            
            x = int(finger_tip.x * w)
            y = int(finger_tip.y * h)
            
            return x, y
        return None, None
    
    def is_finger_extended(self, landmarks, finger_tips, finger_pips):
        """Check if finger is extended"""
        extended = []
        for tip, pip in zip(finger_tips, finger_pips):
            tip_y = landmarks.landmark[tip].y
            pip_y = landmarks.landmark[pip].y
            extended.append(tip_y < pip_y)
        return extended

    # Add any other methods with proper self parameter