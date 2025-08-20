# app.py (Updated with enhanced logging and session validation)
from flask import Flask, request, render_template, jsonify, session
from resume_parser import extract_text_from_pdf
from question_generator import generate_questions
from interview_analyzer import evaluate_answer
from speech_to_text import transcribe_audio
from face import start_face_detection_thread, stop_interview

import os
import tempfile
import uuid
import logging
import threading

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Prevent session issues
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global variable to store the face detection thread
face_detection_thread = None

def _generate_questions_internal(text, num_questions=5):
    """Helper function to generate questions without Flask request context."""
    if not text:
        logger.error("Text not provided in _generate_questions_internal")
        return None
    try:
        questions = generate_questions(text, num_questions)
        if not questions or not questions.strip():
            logger.warning("_generate_questions_internal returned empty or invalid data")
            return None
        logger.info(f"Generated {num_questions} questions: {questions[:100]}...")
        return questions.split('\n')
    except Exception as e:
        logger.error(f"Error generating questions in _generate_questions_internal: {str(e)}")
        return None

@app.route("/api/generate_questions", methods=["POST"])
def api_generate_questions():
    data = request.get_json()
    text = data.get("text")
    num_questions = data.get("num_questions", 5)

    questions = _generate_questions_internal(text, num_questions)
    if questions is None:
        return jsonify({"error": "No questions generated"}), 400
    return jsonify({"questions": questions})

@app.route("/api/evaluate_answer", methods=["POST"])
def api_evaluate_answer():
    data = request.get_json()
    question = data.get("question")
    answer = data.get("answer")

    if not question or not answer:
        logger.error("Question or answer missing in evaluate_answer request")
        return jsonify({"error": "Question and answer required"}), 400

    try:
        feedback = evaluate_answer(question, answer)
        logger.info(f"Evaluated answer for question: {question[:50]}...")
        return jsonify({"feedback": feedback})
    except Exception as e:
        logger.error(f"Evaluation failed: {str(e)}")
        return jsonify({"error": f"Evaluation failed: {str(e)}"}), 500

@app.route("/", methods=["GET", "POST"])
def index():
    global face_detection_thread
    if request.method == "POST":
        if "cv" not in request.files:
            logger.error("No CV file provided in POST request")
            return jsonify({"error": "No CV file provided"}), 400

        file = request.files["cv"]
        num_questions = int(request.form.get("num_questions", 5))
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)

        try:
            text = extract_text_from_pdf(path)
            if not text or not text.strip():
                logger.error("extract_text_from_pdf returned empty or invalid text")
                text = "Sample CV text: Software Engineer, Python, Flask"
            questions = _generate_questions_internal(text, num_questions)
            if not questions:
                logger.error("No questions generated or parsed from response")
                questions = ["What is Python?", "Explain Flask.", "Describe your experience."]
            session['questions'] = questions
            session['current_question'] = 0
            session['session_id'] = str(uuid.uuid4())
            session['answers'] = []
            session['progress'] = 0
            logger.info(f"New session started: {session['session_id']} with {len(session['questions'])} questions")

            # Start face detection thread when interview begins
            face_detection_thread = start_face_detection_thread()
            logger.info("Face detection thread started")

            return render_template("interview.html")
        except Exception as e:
            logger.error(f"Error processing CV or generating questions: {str(e)}")
            return jsonify({"error": f"Failed to start interview: {str(e)}"}), 500
        finally:
            if os.path.exists(path):
                os.unlink(path)  # Clean up uploaded file

    return render_template("index.html")

@app.route("/get_current_question", methods=["GET"])
def get_current_question():
    if 'current_question' not in session or 'questions' not in session:
        logger.error("No active session or questions in get_current_question")
        return jsonify({"error": "No active session or questions available"}), 400

    idx = session['current_question']
    if idx >= len(session['questions']):
        logger.info("End of questions reached")
        return jsonify({"end": True})
    question = session['questions'][idx].strip()
    if not question:
        logger.error(f"Empty question at index {idx}")
        return jsonify({"error": "Invalid question data"}), 400
    progress = (idx + 1) / len(session['questions']) * 100
    session['progress'] = progress
    logger.info(f"Serving question {idx + 1}/{len(session['questions'])}: {question[:50]}... with progress {progress}%")
    return jsonify({"question": question, "index": idx + 1, "total": len(session['questions']), "progress": progress})

@app.route("/process_audio", methods=["POST"])
def process_audio():
    if "audio" not in request.files or "question" not in request.form:
        logger.error("Audio or question missing in process_audio request")
        return jsonify({"error": "Audio and question required", "transcript": "", "feedback": ""}), 400

    audio = request.files["audio"]
    question = request.form["question"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
        audio.save(f.name)
        try:
            transcript = transcribe_audio(f.name)
            if not transcript or not transcript.strip():
                logger.warning("Transcription returned empty or invalid result")
                transcript = "No transcription available"
            feedback = evaluate_answer(question, transcript)
            if not feedback or not feedback.strip():
                logger.warning("Feedback returned empty or invalid result")
                feedback = "No feedback available"
            session['answers'].append({"question": question, "transcript": transcript, "feedback": feedback})
            logger.info(f"Processed audio for question: {question[:50]}... Transcript: {transcript[:50]}... Feedback: {feedback[:50]}...")
            return jsonify({"transcript": transcript, "feedback": feedback})
        except Exception as e:
            logger.error(f"Processing audio failed: {str(e)}")
            return jsonify({"error": str(e), "transcript": "", "feedback": ""}), 500
        finally:
            if os.path.exists(f.name):
                try:
                    os.remove(f.name)
                    logger.info(f"Deleted temp file {f.name}")
                except PermissionError as pe:
                    logger.warning(f"Could not delete {f.name}: {pe}")

@app.route("/next_question", methods=["GET"])
def next_question():
    if 'current_question' not in session:
        logger.error("No active session in next_question")
        return jsonify({"error": "No active session", "end": False}), 400

    session['current_question'] += 1
    logger.info(f"Moving to next question: {session['current_question']}")
    return get_current_question()

@app.route("/end_interview", methods=["GET"])
def end_interview():
    global face_detection_thread
    if 'answers' not in session or 'session_id' not in session:
        logger.error("No answers or session_id found in end_interview")
        return jsonify({"error": "No active session or answers available", "results": []}), 400

    results = session.get('answers', [])
    logger.info(f"Ending interview for session {session['session_id']}. Results count: {len(results)}")

    # Stop face detection thread if it exists
    if face_detection_thread and face_detection_thread.is_alive():
        stop_interview()
        face_detection_thread.join(timeout=2)
        if face_detection_thread.is_alive():
            logger.warning("Face detection thread did not terminate gracefully")
        else:
            logger.info("Face detection thread terminated")
        face_detection_thread = None

    session.clear()
    return jsonify({"results": results})

@app.route("/check_questions", methods=["GET"])
def check_questions():
    if 'questions' not in session:
        return jsonify({"error": "No questions in session", "questions": None, "count": 0})
    return jsonify({"questions": session['questions'], "count": len(session['questions'])})

@app.route("/debug_session", methods=["GET"])
def debug_session():
    logger.info(f"Debugging session: {dict(session)}")
    return jsonify(dict(session))

if __name__ == "__main__":
    app.run(debug=True)
