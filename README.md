# LAA-mini-project
Mini project 

# Gesture-Based Drawing System

## Project Statement
Traditional digital art tools rely heavily on physical peripherals like mice, styluses, or touchscreens. This project removes those physical barriers by creating a **vision-based "Air Canvas"** that allows users to draw, erase, and manipulate shapes in a 3D physical space using hand gestures captured via a standard webcam.

## Objective
The primary goal is to build a real-time human-computer interaction (HCI) system that:
* **Tracks hand movements** with high precision and low latency.
* **Recognizes specific gestures** to trigger different states (Draw, Erase, UI Selection).
* **Simulates standard drawing tools** (Freehand, Lines, Rectangles, Circles) without physical contact.
* **Provides a seamless UI overlay** for color and brush size customization.

---

## System Architecture
The system operates on a modular pipeline that processes video frames in real-time.

1.  **Input Layer**: Captures raw video frames from the webcam.
2.  **Preprocessing**: Flips the frame for "mirror effect" and converts BGR to RGB for AI processing.
3.  **Inference Engine (MediaPipe)**: Hand Landmarker model identifies 21 specific 3D hand joints.
4.  **Gesture Logic**: Analyzes the relationship between landmarks (e.g., finger tip vs. knuckle position) to determine the intended action.
5.  **Rendering Layer**: 
    * **Canvas**: A persistent black mask where drawing data is stored.
    * **Compositor**: Blends the drawing mask onto the live camera feed using bitwise operations.
6.  **Output Layer**: Displays the final combined image with UI elements.

---

## Technical Implementation

### Hand Landmark Detection
The system utilizes the **MediaPipe Hand Landmarker**. It tracks 21 coordinates $(x, y, z)$. For 2D drawing, the $z$-coordinate is discarded, and $(x, y)$ are mapped to the window resolution.

### Gesture Mapping Logic
* **Drawing**: Triggered when only the Index finger is extended.
* **Erasing**: Triggered when both Index and Middle fingers are up.
* **Mode Switching**: Detected when the Thumb is extended in isolation. To prevent "flickering," a **0.6-second cooldown timer** is implemented.
* **Shape Preview**: For shapes like Rectangles or Circles, the system creates a `snap_canvas` (a temporary copy) to allow dynamic resizing.

---

## Test Scenarios and Validation

| Scenario | Expected Result | Validation |
| :--- | :--- | :--- |
| **Index finger movement** | Continuous line follows the tip in FREE mode. | Pass |
| **Switch to Rectangle mode** | Shape appears to "drag" and resize. | Pass |
| **Color Selection** | Pinching over a color icon updates the brush color. | Pass |
| **Canvas Clearing** | Pressing 'C' wipes all drawing data. | Pass |

---

## Tools Used
* **Python**: Core programming language.
* **OpenCV**: Video capture and UI rendering.
* **MediaPipe**: Hand tracking framework.
* **NumPy**: Matrix operations for the canvas.
