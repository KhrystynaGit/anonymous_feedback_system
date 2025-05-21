from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from langdetect import detect

model_name = "tabularisai/multilingual-sentiment-analysis"
tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
model     = AutoModelForSequenceClassification.from_pretrained(model_name)
sentiment_pipeline = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

def detect_language(text: str) -> str:
    try:
        return detect(text)
    except:
        return "unknown"

def analyze_sentiment(text: str) -> str:
    try:
        return sentiment_pipeline(text[:512])[0]["label"]
    except:
        return "neutral"
