from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io, hashlib, math, requests, os, json
from datetime import datetime
from google import genai 
from pymongo import MongoClient

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- 1. DATABASE SETUP ---
MONGO_URI = "mongodb+srv://gphoto35961_db_user:LWGxPOw58IlyqVoD@cluster0.gu2n0ne.mongodb.net/?retryWrites=true&w=majority"

history_collection = None
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    db = client["neural_sentinel_db"]
    history_collection = db["analysis_history"]
    client.admin.command('ping')
    print("✅ MongoDB Atlas Connected Successfully")
except Exception as e:
    print(f"❌ Database Connection Failed: {e}")

# --- 2. LLM SETUP ---
client_ai = genai.Client(api_key="AIzaSyCGtYJW6yvbtnnEiBgjqMq0seuFtUVbmQM")

async def generate_llm_insight(stats, trends):
    try:
        prompt = f"Role: Supply Chain Strategist. Stats: Total {stats['total']}, Bots {stats['bots']}. Task: 2-sentence Executive Action Plan based on trends."
        response = client_ai.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        return response.text.strip()
    except: return "Strategic insight temporarily unavailable."

async def llm_refinement(text):
    """Layer 2: LLM Validation to detect features and translation without keywords."""
    try:
        prompt = f"""
        Analyze this review: "{text}"
        1. Identify the primary Feature: (Logistics Speed, Packaging Quality, Customer Support, Product Integrity, or Battery Performance).
        2. Sentiment Score: -1 (Negative), 0 (Neutral), or 1 (Positive).
        3. Translate to English if needed.
        Return ONLY a JSON object: {{"feat": "name", "score": 0, "trans": "English text"}}
        """
        response = client_ai.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        data = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
        return data
    except:
        return None

# --- 3. ANALYTICS ENGINE ---
async def generate_final_summary(final_res):
    """LLM analyzes the complete output to provide a 3-sentence strategic summary."""
    try:
        stats = final_res['stats']
        # Convert list of trend dicts into a string for the AI to read
        trend_summary = ", ".join([t['summary'] for t in final_res['trends']])
        
        prompt = f"""
        Analyze these results:
        - Total Processed: {stats['total']}
        - Bot Threats Blocked: {stats['bots']}
        - Trends Detected: {trend_summary}

        Task: Provide a clean, executive summary in EXACTLY 3 sentences. 
        Focus on the overall system health, the most critical issue, and the recommended next step.
        """
        response = client_ai.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        return response.text.strip()
    except:
        return "Analysis complete. System health is stable, though specific drift patterns require manual review of the neural feed."

def find_review_column(df):
    exact_targets = ['review text', 'review', 'comments', 'content', 'body', 'text']
    for col in df.columns:
        if col.lower().strip() in exact_targets: return col
    eligible = [c for c in df.columns if df[c].dtype == 'object']
    return df[eligible].apply(lambda x: x.astype(str).str.len().mean()).idxmax() if eligible else df.columns[0]

def neural_processor(text):
    t = str(text).lower()
    attrs = {
        "Logistics Speed": ["delivery", "shipping", "package", "lost", "driver", "tracking", "late", "slow"],
        "Packaging Quality": ["packaging", "paking", "box", "dikkat", "phata", "damaged", "sealed", "wrap"],
        "Customer Support": ["service", "support", "refund", "replacement", "account", "verify", "blocked"],
        "Product Integrity": ["broken", "sturdy", "quality", "material", "bekar", "bakwas", "failed", "impossible"],
        "Battery Performance": ["battery", "charge", "drain", "backup"]
    }
    feat, sent, matches = "General Observation", 0, 0
    for full_name, kws in attrs.items():
        m_list = [k for k in kws if k in t]
        if m_list:
            feat, matches = full_name, len(m_list)
            p_score = sum(1 for w in ["good", "great", "best", "acha", "mast"] if w in t)
            n_score = sum(1 for w in ["bad", "worst", "poor", "terrible", "failed", "horrible", "bekar"] if w in t)
            sent = -1 if n_score > p_score else (1 if p_score > n_score else 0)
            break
    words = t.split()
    conf = min(round((math.log(matches + 1) / math.log(len(words) + 5)) * 1.8, 2), 0.99) if words and matches else 0.45
    is_sarcasm = any(x in t for x in ["thanks", "great job", "wonderful"]) and sent == -1
    return {"Feature": feat, "Sentimental Score": sent, "Confidence Score": conf}

async def analyze_logic(df, source_name="Uploaded File"):
    text_col = find_review_column(df)
    df[text_col] = df[text_col].fillna("").astype(str)
    
    # L1: BOT BUNKER
    df['hash'] = df[text_col].apply(lambda x: hashlib.md5(x.lower().strip().encode()).hexdigest())
    is_bot = df.duplicated(subset=['hash'], keep='first')
    bot_list = df[is_bot][text_col].tolist()
    clean_df = df[~is_bot].copy()

    # L2: KEYWORD + LLM HYBRID PROCESSING
    feed_data = []
    # Index-based processing for LLM batching
    for i, (idx, r) in enumerate(clean_df.iterrows()):
        # Step 1: Default Keyword Analysis
        analysis = neural_processor(r[text_col])
        final_review_text = r[text_col]
        
        # Step 2: Refine first 20 with LLM for high accuracy/translation
        if i < 20:
            llm_data = await llm_refinement(r[text_col])
            if llm_data:
                analysis["Feature"] = llm_data.get("feat", analysis["Feature"])
                analysis["Sentimental Score"] = llm_data.get("score", analysis["Sentimental Score"])
                final_review_text = llm_data.get("trans", r[text_col])

        entry = {"review": final_review_text}
        entry.update(analysis)
        feed_data.append(entry)

    # L3: TREND DETECTION
    # Using the processed feed_data to ensure trends reflect LLM refinements
    trend_results = []
    features = ["Packaging Quality", "Battery Performance", "Logistics Speed", "Product Integrity", "Customer Support"]
    
    # Helper to calculate rates from the new feed_data list
    def calculate_trend(feat_name, data_list):
        relevant = [x for x in data_list if x['Feature'] == feat_name]
        if not relevant: return 0.0
        neg = [x for x in relevant if x['Sentimental Score'] == -1]
        return round((len(neg) / len(relevant)) * 100, 1)

    for f_name in features:
        curr = calculate_trend(f_name, feed_data[-50:] if len(feed_data) > 50 else feed_data)
        prev = calculate_trend(f_name, feed_data[:-50] if len(feed_data) > 50 else feed_data)
        drift = round(curr - prev, 2)
        
        trend_results.append({  
            "feature": f_name, 
            "summary": f"{f_name} complaints at {curr}%, previously {prev}%", 
            "drift": drift, 
            "anomaly": True if drift > 10 else False, 
            "class": "Critical Issue" if curr > 15   else "Systemic Issue" if curr > 5 else "Isolated Case"
        })

    # L4: LEADERBOARD
    comparison = []
    prod_col = next((c for c in df.columns if any(x in c.lower() for x in ['product', 'item'])), None)
    if prod_col:
        for prod in clean_df[prod_col].dropna().unique():
            # Get indices for this product to map back to feed_data
            prod_indices = [j for j, (idx, row) in enumerate(clean_df.iterrows()) if row[prod_col] == prod]
            prod_feed = [feed_data[j] for j in prod_indices]
            
            row = {"Product": str(prod)}
            for ft in ["Packaging Quality", "Logistics Speed", "Product Integrity"]:
                f_neg = [x for x in prod_feed if x['Feature'] == ft and x['Sentimental Score'] == -1]
                row[ft] = f"{round((len(f_neg)/len(prod_feed))*100, 1) if prod_feed else 0}% Fail"
            comparison.append(row)

    stats = {"total": len(df), "bots": len(bot_list)}
    ai_insight = await generate_llm_insight(stats, trend_results)
    
    final_res = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": source_name,
        "stats": stats, 
        "ai_insight": ai_insight,
        "trends": trend_results, 
        "feed": feed_data, 
        "bots": bot_list,
        "comparison": comparison
    }

    # ... after final_res is defined ...
    
    # Generate the clean 3-sentence summary
    final_res["ai_insight"] = await generate_final_summary(final_res)

    # Save to DB (ensuring the new insight is included)
    if history_collection is not None:
        try:
            db_entry = {k: v for k, v in final_res.items() if k not in ["feed", "bots"]}
            history_collection.insert_one(db_entry)
        except: pass

    return final_res
@app.post("/analyze")
async def analyze_file(file: UploadFile = File(...)):
    df = pd.read_csv(io.BytesIO(await file.read()), engine='python').dropna(how='all')
    return await analyze_logic(df, source_name=file.filename)

@app.get("/history")
async def get_history():
    if history_collection is None: return []
    return list(history_collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(10))