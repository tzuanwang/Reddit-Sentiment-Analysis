# backend/app/sentiment_analyzer.py
import re
import nltk
import spacy
import numpy as np
from typing import Dict, List, Any, Optional
from transformers import AutoModelForSequenceClassification, AutoTokenizer, AutoConfig
from scipy.special import softmax
from collections import Counter
from sklearn.feature_extraction.text import CountVectorizer
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# Download NLTK resources if needed
try:
    nltk.data.find('vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon')

# Initialize sentiment analyzer
sia = SentimentIntensityAnalyzer()

# Load spaCy model - using medium model instead of large to reduce resource usage
nlp = spacy.load("en_core_web_md", disable=["ner"])

# Load RoBERTa model for sentiment analysis
MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"
try:
    sentiment_tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    sentiment_config = AutoConfig.from_pretrained(MODEL_NAME)
    sentiment_model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
except Exception as e:
    print(f"Warning: Could not load RoBERTa model. Using NLTK VADER instead. Error: {e}")
    sentiment_tokenizer = None
    sentiment_config = None
    sentiment_model = None

def deEmojify(text: str) -> str:
    """
    Removes emoji from string
    
    :param text: a standard string object
    :return: a cleaned string without emojis
    """
    regrex_pattern = re.compile(pattern = "["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           "]+", flags = re.UNICODE)
    return regrex_pattern.sub(r'', text)

def extract_url(text: str) -> str:
    """
    Extract URL if it exists in content
    
    :param text: input text
    :return: URL if found, empty string otherwise
    """
    try:
        return re.findall(r'http\S+', text)[0]
    except IndexError:
        return ''

def clean_text(text: str) -> Dict[str, Any]:
    """
    Cleans text and returns metadata
    
    :param text: input text
    :return: dictionary with clean text and metadata
    """
    hash_pattern = r"#\S+"
    at_pattern = r"@\S+"
    
    # Basic cleaning
    clean_text = re.sub(hash_pattern, "", text)
    clean_text = re.sub(at_pattern, "@person", clean_text)
    clean_text = re.sub(" +", " ", clean_text)
    clean_text = re.sub(r"http\S+", "http", clean_text)
    
    # Extract metrics
    char_count = len(clean_text)
    word_count = len(clean_text.split())
    
    # Lemmatization
    clean_for_lemma = re.sub(at_pattern, "", clean_text)
    clean_for_lemma = deEmojify(clean_for_lemma)
    doc = nlp(clean_for_lemma)
    lemmas = [token.lemma_ for token in doc if (not token.is_punct and not token.is_space)]
    lemma_text = ' '.join(lemmas)
    
    return {
        "clean": clean_text,
        "lemma": lemma_text,
        "char_count": char_count,
        "word_count": word_count
    }

def analyze_sentiment_roberta(text: str) -> Dict[str, float]:
    """
    Analyzes sentiment using RoBERTa model
    
    :param text: preprocessed text
    :return: sentiment scores (positive, negative, neutral)
    """
    if sentiment_tokenizer is None or sentiment_model is None:
        # Fallback to VADER if RoBERTa model wasn't loaded
        vader_scores = sia.polarity_scores(text)
        return {
            "positive": vader_scores["pos"],
            "negative": vader_scores["neg"],
            "neutral": vader_scores["neu"]
        }
    
    # Limit text length to fit in model's context window
    truncated_text = text[:512]
    
    encoded_input = sentiment_tokenizer(truncated_text, return_tensors="pt", truncation=True)
    output = sentiment_model(**encoded_input)
    scores = output[0][0].detach().numpy()
    scores = softmax(scores)
    
    result = {}
    for i in range(scores.shape[0]):
        label = sentiment_config.id2label[i]
        score = float(scores[i])
        result[label] = score
    
    return result

def analyze_emotion(text: str) -> Dict[str, float]:
    """
    Analyzes emotion using rule-based approach with vocabulary and NLTK
    
    :param text: input text
    :return: emotion scores
    """
    # Basic emotion lexicon
    emotion_keywords = {
        "joy": ["happy", "joy", "delighted", "thrilled", "excited", "glad", "pleased", "satisfied", "great", "amazing", "awesome", "excellent", "love", "wonderful", "fantastic"],
        "sadness": ["sad", "unhappy", "depressed", "miserable", "gloomy", "disappointed", "upset", "distressed", "sorry", "regret", "grief", "heartbroken", "lonely", "tragic", "cry"],
        "anger": ["angry", "mad", "furious", "outraged", "irritated", "annoyed", "frustrated", "rage", "hate", "hostile", "bitter", "resentful", "infuriated", "threatened", "offensive"],
        "fear": ["afraid", "scared", "frightened", "terrified", "nervous", "anxious", "worried", "panic", "horror", "shock", "alarmed", "dread", "terror", "apprehensive", "concern"],
        "surprise": ["surprised", "amazed", "astonished", "shocked", "stunned", "startled", "unexpected", "wow", "incredible", "unbelievable", "remarkable", "extraordinary", "strange"],
        "other": ["neutral", "calm", "balanced", "okay", "fine", "normal", "standard", "regular", "typical", "common", "usual", "routine", "everyday"]
    }
    
    # Convert to lowercase for matching
    text_lower = text.lower()
    
    # Count occurrences of emotional keywords
    emotion_counts = {emotion: 0 for emotion in emotion_keywords}
    for emotion, keywords in emotion_keywords.items():
        for keyword in keywords:
            # Check for whole word match
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matches = re.findall(pattern, text_lower)
            emotion_counts[emotion] += len(matches)
    
    # Calculate sentiment intensity with VADER
    vader_scores = sia.polarity_scores(text)
    
    # Weight emotions based on sentiment
    if vader_scores["compound"] >= 0.05:
        # Positive text, boost joy
        emotion_counts["joy"] = max(emotion_counts["joy"], 1) * (1 + vader_scores["pos"])
        # Reduce negative emotions
        emotion_counts["sadness"] *= 0.8
        emotion_counts["anger"] *= 0.8
        emotion_counts["fear"] *= 0.8
    elif vader_scores["compound"] <= -0.05:
        # Negative text, boost negative emotions
        emotion_counts["sadness"] = max(emotion_counts["sadness"], 1) * (1 + vader_scores["neg"])
        emotion_counts["anger"] = max(emotion_counts["anger"], 1) * (1 + vader_scores["neg"])
        emotion_counts["fear"] = max(emotion_counts["fear"], 1) * (1 + vader_scores["neg"])
        # Reduce joy
        emotion_counts["joy"] *= 0.8
    else:
        # Neutral text, boost "other"
        emotion_counts["other"] = max(emotion_counts["other"], 1) * (1 + vader_scores["neu"])
    
    # Normalize to probabilities
    total = sum(emotion_counts.values()) or 1  # Avoid division by zero
    emotion_probs = {emotion: count / total for emotion, count in emotion_counts.items()}
    
    return emotion_probs

def analyze_hate_speech(text: str) -> Dict[str, float]:
    """
    Analyzes hate speech using keyword-based approach
    
    :param text: input text
    :return: hate speech scores
    """
    # Simple lexicon for different hate speech categories
    hate_keywords = {
        "hateful": ["hate", "despise", "loathe", "detest", "abhor"],
        "offensive": ["offensive", "insult", "rude", "vulgar", "crude", "profane"],
        "targeted_hate": ["racist", "sexist", "bigot", "discriminate", "prejudice"],
        "none": ["respectful", "polite", "civil", "friendly", "kind", "nice"]
    }
    
    # Convert to lowercase for matching
    text_lower = text.lower()
    
    # Count occurrences of hate keywords
    hate_counts = {category: 0 for category in hate_keywords}
    for category, keywords in hate_keywords.items():
        for keyword in keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matches = re.findall(pattern, text_lower)
            hate_counts[category] += len(matches)
    
    # Get VADER negative score as an indicator
    vader_scores = sia.polarity_scores(text)
    negativity = vader_scores["neg"]
    
    # Adjust scores based on negativity
    hate_counts["hateful"] = hate_counts["hateful"] * (1 + negativity)
    hate_counts["offensive"] = hate_counts["offensive"] * (1 + negativity)
    hate_counts["targeted_hate"] = hate_counts["targeted_hate"] * (1 + negativity)
    
    # Adjust "none" score based on positivity
    positivity = vader_scores["pos"]
    hate_counts["none"] = hate_counts["none"] * (1 + positivity) + (1 - negativity)
    
    # If no hate indicators were found, increase the "none" score
    if sum(hate_counts.values()) < 0.5:
        hate_counts["none"] = 1.0
    
    # Normalize to probabilities
    total = sum(hate_counts.values()) or 1  # Avoid division by zero
    hate_probs = {category: count / total for category, count in hate_counts.items()}
    
    return hate_probs

def normalize_scores(scores: Dict[str, float], word_count: int) -> Dict[str, float]:
    """
    Normalizes scores by word count
    
    :param scores: dictionary with scores
    :param word_count: number of words in the text
    :return: normalized scores
    """
    if word_count == 0:
        return scores
    return {k: v / word_count for k, v in scores.items()}

def analyze_text(text: str) -> Dict[str, Any]:
    """
    Runs complete analysis on text
    
    :param text: raw input text
    :return: dictionary with all analysis results
    """
    # Handle empty or None text
    if not text or text.strip() == "":
        return {
            "cleaned": {"clean": "", "lemma": "", "char_count": 0, "word_count": 0},
            "sentiment": {},
            "normalized_sentiment": {},
            "emotion": {},
            "normalized_emotion": {},
            "hate_speech": {},
            "normalized_hate_speech": {}
        }
    
    # Clean text
    cleaned = clean_text(text)
    
    # Run analysis
    sentiment_scores = analyze_sentiment_roberta(cleaned["clean"])
    emotion_scores = analyze_emotion(cleaned["clean"])
    hate_speech_scores = analyze_hate_speech(cleaned["clean"])
    
    # Normalize scores
    word_count = cleaned["word_count"]
    normalized_sentiment = normalize_scores(sentiment_scores, word_count)
    normalized_emotion = normalize_scores(emotion_scores, word_count)
    normalized_hate_speech = normalize_scores(hate_speech_scores, word_count)
    
    return {
        "cleaned": cleaned,
        "sentiment": sentiment_scores,
        "normalized_sentiment": normalized_sentiment,
        "emotion": emotion_scores,
        "normalized_emotion": normalized_emotion,
        "hate_speech": hate_speech_scores,
        "normalized_hate_speech": normalized_hate_speech
    }

def calculate_overall_scores(items: List[Dict[str, Any]], score_type: str) -> Dict[str, float]:
    """
    Calculates overall scores across multiple items
    
    :param items: list of analysis results
    :param score_type: type of score to aggregate ('sentiment', 'emotion', or 'hate_speech')
    :return: aggregated scores
    """
    counter = Counter()
    for item in items:
        if score_type in item and item[score_type]:
            counter.update(item[score_type])
    
    # Convert to dictionary
    result = dict(counter)
    
    # Normalize by number of items
    if items:
        result = {k: v / len(items) for k, v in result.items()}
    
    return result

def find_examples(items: List[Dict[str, Any]], texts: List[str], 
                 score_type: str, category: str, top_n: int = 1) -> List[str]:
    """
    Finds top examples for a specific category
    
    :param items: list of analysis results
    :param texts: original texts
    :param score_type: type of score ('sentiment', 'emotion', or 'hate_speech')
    :param category: category to find examples for
    :param top_n: number of examples to return
    :return: list of example texts
    """
    if not items or not texts or len(items) != len(texts):
        return []
    
    # Extract scores for the specific category
    scores = []
    for item in items:
        if score_type in item and item[score_type] and category in item[score_type]:
            scores.append(item[score_type][category])
        else:
            scores.append(0)
    
    # Get indices of top scores
    top_indices = np.argsort(scores)[-top_n:][::-1]
    
    # Get corresponding texts
    return [texts[i] for i in top_indices]