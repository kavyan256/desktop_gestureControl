# Hand Tracker - Vision Touchscreen Phase 1

Simple hand tracking using OpenCV and MediaPipe to track finger movements.

## Setup

1. Install the required packages:
```bash
pip install -r requirements.txt
```

2. Run the hand tracker:
```bash
python hand_tracker.py
```

## Features

- Tracks one hand in real-time
- Detects index finger tip position
- Applies smoothing to reduce jitter
- Displays video feed with hand landmarks
- Shows cursor position coordinates

## Controls

- Point with your index finger to see tracking
- Press 'q' to quit

## Next Steps

This is the foundation for the vision touchscreen system. Future phases will include:
- Screen coordinate mapping
- Cursor control
- Gesture recognition for clicks and scrolls
