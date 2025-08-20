# interview_analyzer.py (Unchanged, validated for integration)
import os
import requests
from dotenv import load_dotenv
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # Ensure logs go to console
)
logger = logging.getLogger(__name__)

# Load Together AI API key
load_dotenv()
api_key = os.getenv("TOGETHER_API_KEY")

def evaluate_answer(question, answer):
    """
    Evaluate an interview answer using the Together AI API and provide detailed feedback.
    Returns feedback string or fallback if API fails.
    """
    if not api_key:
        logger.error("TOGETHER_API_KEY not set in environment at %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        raise ValueError("API key not configured. Please set TOGETHER_API_KEY in .env file.")

    prompt = (
        f"Evaluate this answer to an interview question in detail:\n"
        f"Q: {question}\n"
        f"A: {answer}\n"
        f"Provide:\n"
        f"1. Overall score (1–10).\n"
        f"2. Strengths (bullet points).\n"
        f"3. Areas for improvement (bullet points).\n"
        f"4. Suggested better response (short example).\n"
        f"Keep feedback concise yet insightful."
    )

    # Default fallback response
    fallback_response = (
        f"Evaluation failed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} due to API issues. "
        f"Score: 0\n- No strengths\n- Incomplete answer\n- Provide a detailed response."
    )

    try:
        logger.info("Sending evaluation request for question: %s", question[:50])
        response = requests.post(
            "https://api.together.xyz/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.7  # Added for more consistent responses
            },
            timeout=10  # Added timeout to prevent hanging
        )
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()
        logger.debug("Raw API response: %s", data)

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content or not content.strip():
            logger.warning("API returned empty or invalid content")
            return fallback_response

        logger.info("Successfully evaluated answer")
        return content

    except requests.exceptions.RequestException as e:
        logger.error("Failed to evaluate answer: %s, Response: %s", str(e), getattr(e.response, 'text', 'No response'))
        return fallback_response
    except Exception as e:
        logger.error("Unexpected error during evaluation: %s", str(e), exc_info=True)
        return fallback_response