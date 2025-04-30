import re
import numpy as np
import pandas as pd
import collections
from transformers import AutoModelForSequenceClassification, AutoTokenizer, AutoConfig
from scipy.special import softmax
from sklearn.preprocessing import StandardScaler
from pysentimiento import create_analyzer
from datetime import datetime, timezone

# Load sentiment model
SENTIMENT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
tokenizer = AutoTokenizer.from_pretrained(SENTIMENT_MODEL)
config = AutoConfig.from_pretrained(SENTIMENT_MODEL)
model = AutoModelForSequenceClassification.from_pretrained(SENTIMENT_MODEL)

# Load emotion and hate analyzers
emotion_analyzer = create_analyzer(task="emotion", lang="en")
hate_speech_analyzer = create_analyzer(task="hate_speech", lang="en")

def deEmojify(text):
    regrex_pattern = re.compile(pattern="["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        "]+", flags=re.UNICODE)
    return regrex_pattern.sub(r'', text)

def clean_text(text):
    text = deEmojify(text)
    text = re.sub(r"http\S+", "http", text)
    text = re.sub(r"@\S+", "@user", text)
    text = re.sub(r"#\S+", "", text)
    return text.strip()

def use_model(text):
    text = clean_text(text)
    encoded_input = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    output = model(**encoded_input)
    scores = output[0][0].detach().numpy()
    scores = softmax(scores)
    
    ranking = np.argsort(scores)[::-1]
    results = {}
    for i in range(scores.shape[0]):
        label = config.id2label[ranking[i]]
        score = scores[ranking[i]]
        results[label] = float(score)
    return results

def predict_label(text):
    scores = use_model(text)
    return max(scores, key=scores.get)

def normalize(sentiment, wordcount):
    return {k: v / wordcount for k, v in sentiment.items() if wordcount > 0}

def sentiment_analysis(text):
    sentiment_scores = use_model(text)
    wordcount = len(text.split())
    return normalize(sentiment_scores, wordcount)

def emotion_analysis(text):
    cleaned = clean_text(text)
    probas = emotion_analyzer.predict(cleaned).probas
    return dict(probas)

def hate_analysis(text):
    cleaned = clean_text(text)
    probas = hate_speech_analyzer.predict(cleaned).probas
    return dict(probas)

def full_analysis(text):
    return {
        "sentiment": use_model(text),
        "emotion": emotion_analysis(text),
        "hate": hate_analysis(text)
    }

def save_to_csv(text: str, result: dict, csv_path="sentiment_logs.csv"):
    flat = {
        "text": text,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    for category in ["sentiment", "emotion", "hate"]:
        for label, score in result.get(category, {}).items():
            flat[f"{category}_{label}"] = score
    df = pd.DataFrame([flat])
    df.to_csv(csv_path, mode='a', header=not pd.io.common.file_exists(csv_path), index=False)
