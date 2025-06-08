# services/spam_service.py

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os

# Завантаження моделі з кореня проєкту
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "spam_model")

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model    = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)

# Якщо доступний GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()

LABELS = ["ham", "spam"]
SPAM_THRESHOLD = 0.5  # поріг скору, можна налаштовувати

def detect_spam(text: str) -> tuple[int, float]:
    txt = text.strip()
    if not txt:
        print(f"[detect_spam] empty text → spam=1, ham=0")
        return 1, 1.0

    inputs = tokenizer(txt, return_tensors="pt", truncation=True, padding=True).to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)[0].cpu().numpy()

    ham_score, spam_score = float(probs[0]), float(probs[1])
    print(f"[detect_spam] spam_score={spam_score:.3f} | ham_score={ham_score:.3f} for text={txt!r}")

    is_spam = 1 if spam_score >= SPAM_THRESHOLD else 0
    return is_spam, spam_score
