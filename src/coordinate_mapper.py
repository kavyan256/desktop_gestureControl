# File: /hand-tracker-project/hand-tracker-project/src/coordinate_mapper.py

class CoordinateMapper:
    def __init__(self, screen_width, screen_height, cam_width, cam_height, tracking_area):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.cam_width = cam_width
        self.cam_height = cam_height
        self.tracking_area = tracking_area
    
    def map_to_screen(self, cam_x, cam_y):
        """Map camera coordinates to screen coordinates"""
        # Constrain to tracking area
        constrained_x = max(self.tracking_area['left'], 
                           min(self.tracking_area['right'], cam_x))
        constrained_y = max(self.tracking_area['top'], 
                           min(self.tracking_area['bottom'], cam_y))
        
        # Convert to relative position within tracking area
        rel_x = (constrained_x - self.tracking_area['left']) / (
            self.tracking_area['right'] - self.tracking_area['left'])
        rel_y = (constrained_y - self.tracking_area['top']) / (
            self.tracking_area['bottom'] - self.tracking_area['top'])
        
        # Map to screen coordinates
        screen_x = int(rel_x * self.screen_width)
        screen_y = int(rel_y * self.screen_height)
        
        return screen_x, screen_y