
"""
agent.py — L'AGENT IA (utilise OpenAI / GPT)
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from extract import extract_text

load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
