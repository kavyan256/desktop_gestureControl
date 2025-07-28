from src.hand_tracker import HandTracker
from src.gui_interface import HandTrackerGUI

if __name__ == "__main__":
    # Initialize tracker without wake word detection
    tracker = HandTracker()
    
    # Initialize GUI with the tracker
    gui = HandTrackerGUI(tracker)
    gui.run()