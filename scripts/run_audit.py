import requests
import json

def query_trained_model(curriculum_section_text):
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "trained-curriculum-ai", # Model built from the pdf/ folder Modelfile
        "prompt": f"Review this curriculum section:\n{curriculum_section_text}",
        "format": "json",
        "stream": False
    })
    
    return response.json()["response"]
