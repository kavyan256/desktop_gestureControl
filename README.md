# Hand Tracking Project

This project implements a hand tracking system that allows users to control a cursor on their screen using hand gestures. The system utilizes a webcam for real-time tracking and employs various gesture detection techniques to interpret user actions.

## Project Structure

```
hand-tracker-project
├── src
│   ├── hand_tracker.py          # Contains the HandTracker class for managing the tracking system
│   ├── gesture_detector.py       # Contains methods for detecting gestures
│   ├── cursor_controller.py      # Contains methods for cursor movement based on hand gestures
│   ├── scroll_controller.py      # Contains methods for handling scrolling actions
│   ├── click_handler.py          # Contains methods for handling click actions
│   ├── coordinate_mapper.py      # Contains methods for mapping camera coordinates to screen coordinates
│   ├── stability_filter.py       # Contains methods for applying stability filters to reduce jitter
│   └── ui_overlay.py             # Contains methods for drawing the user interface overlay
├── main.py                       # Entry point for the application
├── requirements.txt              # Lists the dependencies required for the project
└── README.md                     # Documentation for the project
```

## Installation

To install the required dependencies, run:

```
pip install -r requirements.txt
```

## Usage

To run the hand tracking application, execute the following command:

```
python main.py
```

Ensure that your webcam is connected and not being used by another application.

## Features

- **Gesture Detection**: Recognizes various hand gestures to control cursor movement, scrolling, and clicking.
- **Cursor Control**: Allows precise cursor movement based on hand position.
- **Scrolling**: Enables vertical scrolling through hand gestures.
- **Click Handling**: Supports single and double clicks as well as right-click actions.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.