# File: /hand-tracker-project/hand-tracker-project/src/ui_overlay.py

import cv2

class UIOverlay:
    def draw_tracking_area(self, frame, tracking_area):
        """Draw the tracking area boundaries on the frame"""
        cv2.rectangle(frame, 
                     (tracking_area['left'], tracking_area['top']),
                     (tracking_area['right'], tracking_area['bottom']),
                     (255, 255, 0), 2)  # Yellow border
        
        corner_size = 20
        cv2.line(frame, (tracking_area['left'], tracking_area['top']),
                (tracking_area['left'] + corner_size, tracking_area['top']), (0, 255, 255), 3)
        cv2.line(frame, (tracking_area['left'], tracking_area['top']),
                (tracking_area['left'], tracking_area['top'] + corner_size), (0, 255, 255), 3)
        
        cv2.line(frame, (tracking_area['right'], tracking_area['top']),
                (tracking_area['right'] - corner_size, tracking_area['top']), (0, 255, 255), 3)
        cv2.line(frame, (tracking_area['right'], tracking_area['top']),
                (tracking_area['right'], tracking_area['top'] + corner_size), (0, 255, 255), 3)
        
        cv2.line(frame, (tracking_area['left'], tracking_area['bottom']),
                (tracking_area['left'] + corner_size, tracking_area['bottom']), (0, 255, 255), 3)
        cv2.line(frame, (tracking_area['left'], tracking_area['bottom']),
                (tracking_area['left'], tracking_area['bottom'] - corner_size), (0, 255, 255), 3)
        
        cv2.line(frame, (tracking_area['right'], tracking_area['bottom']),
                (tracking_area['right'] - corner_size, tracking_area['bottom']), (0, 255, 255), 3)
        cv2.line(frame, (tracking_area['right'], tracking_area['bottom']),
                (tracking_area['right'], tracking_area['bottom'] - corner_size), (0, 255, 255), 3)
        
        cv2.putText(frame, "TRACKING AREA", 
                   (tracking_area['left'] + 10, tracking_area['top'] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)