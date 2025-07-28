# stability_filter.py

class StabilityFilter:
    def __init__(self, buffer_size=5, movement_threshold=20):
        self.stability_buffer = []
        self.buffer_size = buffer_size
        self.movement_threshold = movement_threshold
    
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