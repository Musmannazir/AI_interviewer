# question_generator.py (Unchanged, validated for integration)
import os
import requests
from dotenv import load_dotenv
import logging
import time

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load Together API key
load_dotenv()
api_key = os.getenv("TOGETHER_API_KEY")

def generate_questions(cv_text, num_questions=5):
    if not api_key:
        logger.error("TOGETHER_API_KEY not set in environment")
        raise ValueError("API key not configured")

    prompt = f"Based on this CV:\n\n{cv_text}\n\nAsk {num_questions} technical or situational interview questions, including a mix of easy, medium, and hard levels."
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Raw API response: {data}")
            content = data["choices"][0]["message"]["content"]
            if not content or not content.strip():
                logger.warning("API returned empty or invalid content")
                return "\n".join([f"Question {i+1}?" for i in range(num_questions)])
            questions = content.split('\n')
            if len(questions) < num_questions:
                logger.warning(f"Expected {num_questions} questions, got {len(questions)}. Padding with defaults.")
                questions.extend([f"Question {i+1}?" for i in range(num_questions - len(questions))])
            logger.info(f"Generated {len(questions)} questions")
            return "\n".join(questions)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to generate questions (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            continue
    logger.error("No questions generated after retries")
    return "\n".join([f"Question {i+1}?" for i in range(num_questions)])