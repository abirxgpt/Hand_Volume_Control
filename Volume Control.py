import cv2
import time
import numpy as np
import mediapipe as mp
import HandTrackingModule as htm
import math
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

#####################################
wCAM, hCAM = 640, 480


#####################################

class VolumeController:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(3, wCAM)
        self.cap.set(4, hCAM)
        self.pTime = 0

        # Hand detector
        self.detector = htm.handDetector(detectionCon=0.8)

        # Audio setup
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        self.volume = cast(interface, POINTER(IAudioEndpointVolume))

        volRange = self.volume.GetVolumeRange()
        self.minVol = volRange[0]
        self.maxVol = volRange[1]

        # UI State
        self.showMenu = False
        self.currentVol = 0
        self.volPer = 0
        self.isMuted = False
        self.lastGesture = ""
        self.gestureTimer = 0

        # Color themes based on volume
        self.colors = {
            'silent': (128, 128, 128),  # Gray
            'low': (255, 144, 30),  # Blue
            'medium': (0, 255, 0),  # Green
            'high': (0, 255, 255),  # Yellow
            'max': (0, 0, 255)  # Red
        }

        print("Enhanced Volume Controller Initialized!")
        print("Gestures: ✌️ Peace = Toggle Menu, 👊 Fist = Mute, 👍 Thumb = Max Volume")

    def get_dynamic_color(self, volume_percent):
        """Get color based on volume level"""
        if volume_percent == 0:
            return self.colors['silent']
        elif volume_percent <= 25:
            return self.colors['low']
        elif volume_percent <= 50:
            return self.colors['medium']
        elif volume_percent <= 75:
            return self.colors['high']
        else:
            return self.colors['max']

    def create_gradient_background(self, img, volume_percent):
        """Create dynamic gradient background"""
        height, width = img.shape[:2]

        # Create gradient based on volume
        color = self.get_dynamic_color(volume_percent)

        # Create subtle gradient overlay
        overlay = np.zeros_like(img)
        for i in range(height):
            alpha = (i / height) * 0.1  # Very subtle gradient
            overlay[i, :] = [int(c * alpha) for c in color]

        # Blend with original image
        img = cv2.addWeighted(img, 0.95, overlay, 0.05, 0)
        return img

    def recognize_gesture(self, lmList):
        """Recognize hand gestures"""
        if len(lmList) < 21:
            return "none"

        fingers = self.detector.fingersUp()

        # Peace sign (Index and Middle up, others down)
        if fingers == [0, 1, 1, 0, 0]:
            return "peace"

        # Fist (all fingers down)
        elif fingers == [0, 0, 0, 0, 0]:
            return "fist"

        # Thumbs up (only thumb up)
        elif fingers == [1, 0, 0, 0, 0]:
            return "thumbs_up"

        # Open palm (all fingers up)
        elif fingers == [1, 1, 1, 1, 1]:
            return "open_palm"

        # Volume control (thumb and index up)
        elif fingers == [1, 1, 0, 0, 0]:
            return "volume_control"

        return "none"

    def handle_gesture(self, gesture):
        """Handle recognized gestures"""
        current_time = time.time()

        # Prevent rapid gesture triggering
        if gesture == self.lastGesture and current_time - self.gestureTimer < 1.0:
            return

        if gesture == "peace":
            self.showMenu = not self.showMenu
            self.gestureTimer = current_time
            self.lastGesture = gesture

        elif gesture == "fist":
            self.isMuted = not self.isMuted
            self.volume.SetMute(self.isMuted, None)
            self.gestureTimer = current_time
            self.lastGesture = gesture

        elif gesture == "thumbs_up":
            # Set volume to maximum
            self.volume.SetMasterVolumeLevel(self.maxVol, None)
            self.gestureTimer = current_time
            self.lastGesture = gesture

        elif gesture == "open_palm":
            # Set volume to 50%
            mid_vol = (self.maxVol + self.minVol) / 2
            self.volume.SetMasterVolumeLevel(mid_vol, None)
            self.gestureTimer = current_time
            self.lastGesture = gesture

    def draw_volume_bar(self, img, volume_percent, color):
        """Draw animated volume bar"""
        # Main volume bar
        bar_x, bar_y = 50, 150
        bar_width, bar_height = 35, 250

        # Background bar
        cv2.rectangle(img, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (50, 50, 50), -1)
        cv2.rectangle(img, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), color, 3)

        # Fill bar based on volume
        fill_height = int((volume_percent / 100) * bar_height)
        fill_y = bar_y + bar_height - fill_height

        # Gradient fill
        for i in range(fill_height):
            alpha = (i / fill_height) if fill_height > 0 else 0
            fill_color = [int(c * (0.5 + 0.5 * alpha)) for c in color]
            cv2.line(img, (bar_x + 2, fill_y + i), (bar_x + bar_width - 2, fill_y + i), fill_color, 1)

        # Volume percentage text
        cv2.putText(img, f'{int(volume_percent)}%', (bar_x - 10, bar_y + bar_height + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        # Mute indicator
        if self.isMuted:
            cv2.putText(img, "MUTED", (bar_x - 20, bar_y - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    def draw_gesture_menu(self, img):
        """Draw gesture menu overlay"""
        if not self.showMenu:
            return img

        # Semi-transparent overlay
        overlay = img.copy()
        cv2.rectangle(overlay, (150, 100), (490, 350), (0, 0, 0), -1)
        img = cv2.addWeighted(img, 0.7, overlay, 0.3, 0)

        # Menu title
        cv2.putText(img, "GESTURE MENU", (200, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        # Menu items
        menu_items = [
            "Peace: Toggle Menu",
            "Fist: Mute/Unmute",
            "Thumb: Max Volume",
            "Palm: 50% Volume",
            "Pinch: Volume Control"
        ]

        for i, item in enumerate(menu_items):
            y_pos = 170 + i * 30
            cv2.putText(img, item, (170, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return img

    def draw_pulsing_landmarks(self, img, lmList, color):
        """Draw pulsing hand landmarks"""
        if len(lmList) == 0:
            return

        pulse = int(10 + 5 * math.sin(time.time() * 5))  # Pulsing effect

        # Draw key landmarks with pulsing effect
        key_points = [4, 8, 12, 16, 20]  # Fingertips
        for point in key_points:
            if point < len(lmList):
                x, y = lmList[point][1], lmList[point][2]
                cv2.circle(img, (x, y), pulse, color, 2)
                cv2.circle(img, (x, y), 3, color, -1)

    def run(self):
        """Main application loop"""
        while True:
            success, img = self.cap.read()

            # Check if frame capture was successful AND img is not None
            if not success or img is None:
                print("Failed to capture frame from camera")
                continue  # Skip this iteration instead of breaking

            img = cv2.flip(img, 1)
            img = self.detector.findHands(img, draw=False)

            lmList, bbox = self.detector.findPosition(img, draw=False)

            if len(lmList) >= 21:
                # Recognize current gesture
                current_gesture = self.recognize_gesture(lmList)

                # Handle gestures
                self.handle_gesture(current_gesture)

                # Volume control with pinch gesture
                if current_gesture == "volume_control":
                    x1, y1 = lmList[4][1], lmList[4][2]  # Thumb
                    x2, y2 = lmList[8][1], lmList[8][2]  # Index

                    length = math.hypot(x2 - x1, y2 - y1)

                    # Map distance to volume
                    vol = np.interp(length, [25, 200], [self.minVol, self.maxVol])
                    self.volPer = np.interp(length, [25, 200], [0, 100])

                    if not self.isMuted:
                        self.volume.SetMasterVolumeLevel(vol, None)

                    # Draw connection line
                    color = self.get_dynamic_color(self.volPer)
                    cv2.line(img, (x1, y1), (x2, y2), color, 3)
                    cv2.circle(img, ((x1 + x2) // 2, (y1 + y2) // 2), 10, color, -1)

                # Get current volume for display
                try:
                    current_vol_db = self.volume.GetMasterVolumeLevel()
                    self.volPer = np.interp(current_vol_db, [self.minVol, self.maxVol], [0, 100])
                except:
                    pass

                # Draw pulsing landmarks
                color = self.get_dynamic_color(self.volPer)
                self.draw_pulsing_landmarks(img, lmList, color)

                # Display current gesture
                cv2.putText(img, f"Gesture: {current_gesture.replace('_', ' ').title()}",
                            (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # Create dynamic background
            img = self.create_gradient_background(img, self.volPer)

            # Draw UI elements
            color = self.get_dynamic_color(self.volPer)
            self.draw_volume_bar(img, self.volPer, color)
            img = self.draw_gesture_menu(img)

            # FPS counter
            cTime = time.time()
            fps = 1 / (cTime - self.pTime) if self.pTime != 0 else 0
            self.pTime = cTime
            cv2.putText(img, f"FPS: {int(fps)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # Instructions - Now safe to access img.shape since we verified img is not None
            if not self.showMenu:
                cv2.putText(img, "Show Peace sign for menu", (10, img.shape[0] - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            cv2.imshow("Enhanced Volume Controller", img)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.cap.release()
        cv2.destroyAllWindows()


# Run the application
if __name__ == "__main__":
    try:
        controller = VolumeController()
        controller.run()
    except Exception as e:
        print(f"Error occurred: {e}")
        # Clean up camera if still open
        try:
            cv2.destroyAllWindows()
        except:
            pass