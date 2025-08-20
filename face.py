# face.py (Updated to ensure proper integration with Flask)
import cv2
import threading
import time
import requests

# Load pre-trained Haar Cascade for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Flag to control the face detection loop (set to False to stop interview)
is_interview_running = True

def detect_faces():
    global is_interview_running
    cap = cv2.VideoCapture(0)  # Open webcam (0 for default camera)
    
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    print("Face detection started. Press 'q' to quit manually.")

    while is_interview_running:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        num_faces = len(faces)

        if num_faces == 0:
            print("No face detected! Interview stopped.")
            stop_interview()
        elif num_faces > 1:
            print(f"Multiple faces detected ({num_faces})! Only one person allowed. Interview stopped.")
            stop_interview()

        # Draw rectangles around detected faces (optional visualization)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

        # Display the frame (optional)
        cv2.imshow('Face Detection', frame)

        # Press 'q' to quit manually
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        time.sleep(0.1)  # Check every 100ms to reduce CPU usage

    cap.release()
    cv2.destroyAllWindows()

def stop_interview():
    global is_interview_running
    is_interview_running = False
    print("Interview has been stopped.")
    # Integrate with Flask to end the session
    try:
        response = requests.get("http://localhost:5000/end_interview")
        response.raise_for_status()
        print("Successfully called end_interview endpoint.")
    except Exception as e:
        print(f"Failed to call end_interview endpoint: {str(e)}")

# Function to start face detection in a thread
def start_face_detection_thread():
    global is_interview_running
    is_interview_running = True
    thread = threading.Thread(target=detect_faces)
    thread.start()
    return thread

if __name__ == "__main__":
    # Standalone test: Run face detection
    start_face_detection_thread().join()
