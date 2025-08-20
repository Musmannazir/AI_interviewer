# speech_to_text.py (Updated with debugging)
import whisper
import os
from moviepy.editor import VideoFileClip

model = whisper.load_model("base")

def transcribe_audio(path):
    audio_path = None
    try:
        if path.endswith((".mp4", ".webm")):  # Handle video files from webcam
            video = VideoFileClip(path)
            audio_path = path.replace(".mp4", ".wav").replace(".webm", ".wav")
            video.audio.write_audiofile(audio_path, codec="pcm_s16le")  # Ensure compatible audio format
            video.close()  # Explicitly close the video file
            result = model.transcribe(audio_path, fp16=False)  # Disable FP16 on CPU
            print(f"Transcription result: {result}")  # Debug output
        else:
            result = model.transcribe(path)
            print(f"Transcription result: {result}")  # Debug output
        return result['text']
    except Exception as e:
        print(f"Transcription error: {str(e)}")  # Debug error
        raise e
    finally:
        # Clean up temporary audio file
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                print(f"Deleted temporary audio file: {audio_path}")
            except PermissionError as pe:
                print(f"Warning: Could not delete {audio_path}: {pe}")
