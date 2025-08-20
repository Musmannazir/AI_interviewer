// interview.js (Updated for manual start/stop recording, webcam integration, animations, progress tracking, error handling, and face detection with MediaPipe)
let mediaRecorder;
let chunks = [];
let isRecording = false;
let videoStream;
let timerInterval;
let recordingTime = 0;
let faceDetector;
let detectionInterval;

// Function to load MediaPipe Face Detector
async function loadFaceDetector() {
    try {
        const vision = await FilesetResolver.forVisionTasks(
            "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/wasm"
        );
        faceDetector = await FaceDetector.createFromOptions(vision, {
            baseOptions: {
                modelAssetPath: "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite"
            },
            runningMode: "VIDEO",
            minDetectionConfidence: 0.5
        });
        console.log('Face detector loaded successfully');
    } catch (error) {
        console.error('Error loading face detector:', error);
        alert('Failed to load face detection model. Face detection will be disabled.');
        faceDetector = null; // Disable face detection if loading fails
    }
}

// Function to detect faces and check count
async function detectAndCheckFaces(video) {
    if (!faceDetector || !video || video.readyState !== 4) return;

    const nowInMs = Date.now();
    try {
        const detections = await faceDetector.detectForVideo(video, nowInMs).detections;
        const faceCount = detections ? detections.length : 0;

        if (faceCount === 0) {
            console.log('No faces detected - stopping interview');
            alert('No face detected. Interview stopped.');
            stopInterview();
        } else if (faceCount > 1) {
            console.log('Multiple faces detected - stopping interview');
            alert('Multiple faces detected. Only one person allowed. Interview stopped.');
            stopInterview();
        }
    } catch (error) {
        console.error('Face detection error:', error);
    }
}

// Helper to stop the interview
function stopInterview() {
    if (isRecording) {
        mediaRecorder.stop();
        clearInterval(timerInterval);
        clearInterval(detectionInterval);
        isRecording = false;
    }
    stopWebcamPreview(document.querySelector(".webcam-preview"));
    endInterview();
}

// Function to start/stop recording with toggle, webcam preview, timer, and face detection
function toggleRecording(button, questionText) {
    const container = button.parentElement;
    const webcamPreview = container.querySelector(".webcam-preview");
    const timerDisplay = container.querySelector(".timer");
    const transcriptDisplay = container.querySelector(".transcript");
    const feedbackDisplay = container.querySelector(".feedback");
    const nextButton = container.querySelector(".next-question");

    if (isRecording) {
        // Stop recording
        mediaRecorder.stop();
        clearInterval(timerInterval);
        clearInterval(detectionInterval); // Stop face detection
        button.textContent = "Speak Your Answer";
        button.classList.remove("btn-danger");
        button.classList.add("btn-primary");
        stopWebcamPreview(webcamPreview);
        isRecording = false;
    } else {
        // Start recording with audio + video
        navigator.mediaDevices.getUserMedia({ audio: true, video: true })
            .then(stream => {
                videoStream = stream;
                mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
                chunks = [];

                // Show webcam preview
                showWebcamPreview(webcamPreview, stream);

                // Update button to "Stop Recording" and red
                button.textContent = "Stop Recording";
                button.classList.remove("btn-primary");
                button.classList.add("btn-danger");

                // Start timer animation
                recordingTime = 0;
                timerInterval = setInterval(() => {
                    recordingTime++;
                    timerDisplay.innerText = `Recording: ${recordingTime}s`;
                    if (recordingTime > 60) { // Max 60 seconds recording
                        stopInterview();
                        alert('Recording time exceeded 60 seconds. Interview stopped.');
                    }
                }, 1000);

                // Start face detection interval (every 500ms for performance)
                detectionInterval = setInterval(() => detectAndCheckFaces(webcamPreview), 500);

                mediaRecorder.ondataavailable = e => chunks.push(e.data);

                mediaRecorder.onstop = () => {
                    // Animate feedback loading
                    feedbackDisplay.innerText = "Analyzing...";
                    container.classList.add("animate__animated", "animate__fadeIn");

                    const blob = new Blob(chunks, { type: "video/webm" });
                    const formData = new FormData();
                    formData.append("audio", blob, "answer.webm");
                    formData.append("question", questionText || "No question provided");

                    fetch("/process_audio", {
                        method: "POST",
                        body: formData
                    })
                    .then(res => {
                        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                        return res.json();
                    })
                    .then(data => {
                        if (data.error) {
                            transcriptDisplay.innerText = `Error: ${data.error}`;
                            feedbackDisplay.innerText = "";
                        } else {
                            transcriptDisplay.innerText = `Transcript: ${data.transcript || 'No transcription'}`;
                            feedbackDisplay.innerText = `Feedback: ${data.feedback || 'No feedback'}`;
                            if (data.feedback && data.feedback.includes("10")) {
                                // Confetti animation on perfect score
                                confetti({
                                    particleCount: 100,
                                    spread: 70,
                                    origin: { y: 0.6 }
                                });
                            }
                        }
                        // Enable next question button
                        if (nextButton) nextButton.disabled = false;
                    })
                    .catch(error => {
                        console.error("Fetch error:", error);
                        transcriptDisplay.innerText = "Error processing audio";
                        feedbackDisplay.innerText = "";
                        if (nextButton) nextButton.disabled = false;
                    })
                    .finally(() => {
                        // Clean up animation
                        container.classList.remove("animate__animated", "animate__fadeIn");
                    });
                };

                mediaRecorder.start();
                isRecording = true;
            })
            .catch(err => {
                console.error("Media access denied:", err);
                alert("Please allow microphone and camera access for the live interview.");
                button.textContent = "Speak Your Answer";
                button.classList.remove("btn-danger");
                button.classList.add("btn-primary");
            });
    }
}

// Helper to show webcam preview
function showWebcamPreview(videoElement, stream) {
    if (videoElement) {
        videoElement.srcObject = stream;
        videoElement.play().catch(e => console.error("Error playing video:", e));
        videoElement.classList.add("active");
    }
}

// Helper to stop webcam preview
function stopWebcamPreview(videoElement) {
    if (videoElement && videoElement.srcObject) {
        videoElement.srcObject.getTracks().forEach(track => track.stop());
        videoElement.classList.remove("active");
        videoElement.srcObject = null;
    }
}

// Add progress bar update
function updateProgress(current, total) {
    const progressBar = document.querySelector(".progress-bar");
    if (progressBar) {
        const percentage = (current / total) * 100;
        progressBar.style.width = `${percentage}%`;
        progressBar.setAttribute("aria-valuenow", percentage);
        progressBar.setAttribute("aria-label", `Progress: ${percentage}%`);
    }
}

// Function to load the next question
function loadNextQuestion() {
    fetch("/next_question")
        .then(res => {
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            return res.json();
        })
        .then(data => {
            const questionElement = document.getElementById("question-text");
            const progressBar = document.querySelector(".progress-bar");
            const nextButton = document.querySelector(".next-question");
            if (data.end) {
                questionElement.innerText = "Interview Ended. Results: []";
                if (progressBar) progressBar.style.width = "100%";
                if (nextButton) nextButton.disabled = true;
            } else if (data.error) {
                questionElement.innerText = `Error: ${data.error}`;
            } else {
                questionElement.innerText = `Q${data.index}/${data.total}: ${data.question || 'No question available'}`;
                updateProgress(data.index, data.total);
                // Disable next button until answer is processed
                if (nextButton) nextButton.disabled = true;
                const transcriptDisplay = document.querySelector(".transcript");
                const feedbackDisplay = document.querySelector(".feedback");
                if (transcriptDisplay) transcriptDisplay.innerText = "Transcript: ";
                if (feedbackDisplay) feedbackDisplay.innerText = "Feedback: ";
            }
        })
        .catch(error => {
            console.error("Error loading next question:", error);
            document.getElementById("question-text").innerText = "Error loading next question";
        });
}

// Function to end the interview
function endInterview() {
    fetch("/end_interview")
        .then(res => {
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            return res.json();
        })
        .then(data => {
            const questionElement = document.getElementById("question-text");
            const progressBar = document.querySelector(".progress-bar");
            const nextButton = document.querySelector(".next-question");
            if (data.error) {
                questionElement.innerText = `Error: ${data.error}`;
            } else {
                questionElement.innerText = `Interview Ended. Results: ${JSON.stringify(data.results || [])}`;
                if (progressBar) progressBar.style.width = "100%";
                if (nextButton) nextButton.disabled = true;
            }
        })
        .catch(error => {
            console.error("Error ending interview:", error);
            document.getElementById("question-text").innerText = "Error ending interview";
        });
}

// Initialize progress bar and event listeners on page load
document.addEventListener("DOMContentLoaded", async () => {
    await loadFaceDetector(); // Load face detector on page load

    // Fetch initial question to determine total questions
    fetch("/get_current_question")
        .then(res => {
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            return res.json();
        })
        .then(data => {
            const questionElement = document.getElementById("question-text");
            const progressBar = document.querySelector(".progress-bar");
            if (data.end) {
                questionElement.innerText = "Interview Ended. Results: []";
                if (progressBar) progressBar.style.width = "100%";
            } else if (data.error) {
                questionElement.innerText = `Error: ${data.error}`;
            } else {
                questionElement.innerText = `Q${data.index}/${data.total}: ${data.question || 'No question available'}`;
                updateProgress(data.index, data.total);
            }
        })
        .catch(error => {
            console.error("Error loading initial question:", error);
            document.getElementById("question-text").innerText = "Error loading initial question";
        });

    // Attach event listeners
    const speakButton = document.querySelector(".btn-primary");
    const nextButton = document.querySelector(".next-question");
    const endButton = document.querySelector(".btn-danger");

    if (speakButton) {
        const questionText = document.getElementById("question-text")?.innerText.split(': ')[1] || "No question provided";
        speakButton.addEventListener("click", () => toggleRecording(speakButton, questionText));
    }

    if (nextButton) {
        nextButton.addEventListener("click", loadNextQuestion);
    }

    if (endButton) {
        endButton.addEventListener("click", endInterview);
    }
});