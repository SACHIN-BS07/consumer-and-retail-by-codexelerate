import re
import spacy

# Load English NLP model for Noise Reduction
try:
    nlp = spacy.load("en_core_web_sm")
except:
    nlp = None

def clean_review(text):
    """Layer 1: Noise Reduction & Hinglish Handling"""
    if not isinstance(text, str): return ""
    text = re.sub(r'[^\w\s]', '', text).lower()
    
    # Hinglish Signal Mapping
    h_map = {"dikkat": "problem", "acha": "good", "bekar": "bad", "bakwas": "useless"}
    for word, rep in h_map.items():
        text = text.replace(word, rep)
    
    if nlp:
        doc = nlp(text)
        text = " ".join([t.text for t in doc if not t.is_stop])
    return text.strip()

def get_sentiment_score(text):
    """Calculates polarity for Layer 2 insights"""
    pos = ["amazing", "good", "great", "excellent", "fast", "acha", "perfect"]
    neg = ["bad", "slow", "broken", "dikkat", "disappointed", "bakwas", "problem"]
    score = 0
    for word in text.split():
        if word in pos: score += 0.5
        if word in neg: score -= 0.5
    return max(-1.0, min(1.0, score))

def extract_granular_features(text):
    """Layer 2: Feature-Level Extraction & Confidence Scoring"""
    feature_map = {
        "battery_life": ["battery", "charge", "power", "backup"],
        "packaging_quality": ["packaging", "box", "wrap", "pack", "delivery"],
        "delivery_speed": ["delivery", "shipped", "arrived", "fast", "slow"],
        "product_build": ["quality", "build", "material", "durability", "broken"]
    }
    extracted = []
    for feature, keywords in feature_map.items():
        if any(kw in text.lower() for kw in keywords):
            sentiment = get_sentiment_score(text.lower())
            # Confidence Score logic based on review depth
            confidence = 0.90 if len(text) > 30 else 0.65
            extracted.append({"feature": feature, "sentiment": sentiment, "confidence": confidence})
    return extracted

def calculate_batch_drift(current_scores, baseline_avg=0.4, threshold=-0.3):
    """Layer 3: Temporal Drift Detection Math"""
    if not current_scores:
        return {"status": "Stable", "drift_score": 0, "msg": "Insufficient data for drift analysis"}
    
    current_mu = sum(current_scores) / len(current_scores)
    drift_score = current_mu - baseline_avg
    
    # If the current batch is significantly lower than baseline, trigger alert
    status = "🚨 Systemic Issue Detected" if drift_score < threshold else "✅ Stable"
    
    return {
        "status": status,
        "drift_score": round(drift_score, 2),
        "current_batch_avg": round(current_mu, 2),
        "baseline_comparison": baseline_avg
    }