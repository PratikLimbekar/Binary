import os
import json
import torch
from sentence_transformers import SentenceTransformer, util

model = None
template_embeddings = None
template_sentences = []
intent_labels = []

def load_intents():
    """Loads intent templates from the assets directory."""
    global template_sentences, intent_labels
    
    intent_file = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'intents.json')
    
    if os.path.exists(intent_file):
        with open(intent_file, 'r') as f:
            intents_data = json.load(f)
            
        template_sentences = []
        intent_labels = []
        
        for label, examples in intents_data.items():
            if isinstance(examples, str):
                examples = [examples]
            template_sentences.extend(examples)
            intent_labels.extend([label] * len(examples))
    else:
        # Fallback to a minimal set if JSON is missing
        print(f"Warning: {intent_file} not found. Using minimal fallback intents.")
        INTENT_TEMPLATES = {
            "ask_question": ["What is this?", "Help me"],
            "introductions": ["Hi", "Hello"]
        }
        for label, examples in INTENT_TEMPLATES.items():
            template_sentences.extend(examples)
            intent_labels.extend([label] * len(examples))

# Initial load of intent strings
load_intents()

# model.encode(...) runs those example sentences through the sentence transformer model,
# turning each one into a fixed-size vector (e.g., 384 values).
# convert_to_tensor=True returns PyTorch tensors instead of plain lists. 
# These are needed for fast similarity math later on.
# So this step creates a reference library of vectors, one for each intent.
# These are precomputed when the model is first loaded.


def ensure_model_loaded():
    global model, template_embeddings
    if model is None:
        model = SentenceTransformer("all-MiniLM-L6-v2")
        template_embeddings = model.encode(template_sentences, convert_to_tensor=True)

def classify_intent(user_input: str)-> str:
    """Classifies user intent from user string by comparing to predef values
    returns top predicted intent label"""
    ensure_model_loaded()
    input_embedding = model.encode(user_input, convert_to_tensor=True) #converted to vector
    cosine_scores = util.pytorch_cos_sim(input_embedding, template_embeddings)[0]
    #cosine similarity measures the angle bw vectors
    #closer to 1.0 -> more similar

    best_match_idx = torch.argmax(cosine_scores).item()
    bestscore = cosine_scores[best_match_idx].item()

    print(f"[IntentClassifier] Match: {intent_labels[best_match_idx]} (score: {bestscore:.2f})")
    if bestscore < 0.40:
        return "fallback"
    else:
        return intent_labels[best_match_idx]
