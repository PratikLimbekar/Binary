
from sentence_transformers import SentenceTransformer, util
import torch

model = None


INTENT_TEMPLATES = {
    "get_system_info": [
        "How much battery or RAM do I have?",
        "Tell me about my CPU usage.",
        "What's my current battery level?",
        "Is my disk almost full?",
        "Do I have enough memory?"
    ],
    "open_app": [
        "Open Google Chrome",
        "Start Visual Studio Code",
        "Launch the file explorer",
        "Run Notion app",
        "Open my browser",
        "Open Edge"
    ],
    "web_search": [
        "Search for Python decorators",
        "Find info about the Eiffel Tower",
        "Look up the latest iPhone",
        "Search Google for AI in education",
        "Find how black holes form"
    ],
    "create_note": [
        "Take a note",
        "Create a to-do",
        "Write this down",
        "Remember this for later",
        "Make a note about groceries"
    ],
    "ask_question": [
        "What is the capital of France?",
        "Who discovered gravity?",
        "Explain quantum physics",
        "What's the tallest mountain?",
        "Tell me something interesting"
    ],
    "music_controls": [
        "Pause the music",
        "Stop the song",
        "Resume playing",
        "Play the next song",
        "Skip this track",
        "Go back to the previous song",
        "Play previous track",
        "Next song please",
        "Pause it",
        "Continue the music",
        "Rewind the track",
        "Back to the last song"
],
    "get_weather": [
        "What's the weather like?",
        "Tell me today's weather",
        "Do I need an umbrella?",
        "Is it sunny today?",
        "Give me the weather forecast"
    ],
    "get_news": [
        "Give me today's news",
        "What's happening in the world?",
        "Any headlines today?",
        "Latest news updates",
        "Read the news"
    ],
    "wikipedia_search": [
        "Search Wikipedia for Einstein",
        "Search on wikipedia about black holes",
        "Give me information about Python programming from wikipedia",
        "Look up the Great Wall of China on wikipedia",
        "Find facts about space on wikipedia"
    ],
    "introductions": [
        "Hi",
        "Hello there!",
        "Who are you?",
        "Introduce yourself",
        "What's your name?"
    ],
    "generate_image": [
    "Generate a futuristic owl",
    "Generate an image of a spaceship",
    "Create a picture of a robot",
    "Create an artwork of a digital city",
    "Make a picture of a cat in a spacesuit",
    "Generate a photo of an enchanted forest",
    "Create an illustration of a dragon",
    "Make an image of a glowing jellyfish",
    "Generate a drawing of a haunted castle",
    "Create a painting of a cyberpunk city"
]

}

# Precompute embeddings for the templates (optimization!)
template_sentences = [] #all examples (training set kinda)
intent_labels = [] #corresponding caterogies (like labels)

for label, examples in INTENT_TEMPLATES.items():
    if isinstance(examples, str):
        examples = [examples] #convert string to list for uniform handling
    template_sentences.extend(examples) #add all such sentences from that example to template_sentences
    intent_labels.extend([label] * len(examples)) #add same intent label to intent_labels once for every sentence
    #so we know which sentence maps to which intent

template_embeddings = None

# model.encode(...) runs those example sentences through the sentence transformer model,
# turning each one into a fixed-size vector (e.g., 384 values).
# convert_to_tensor=True returns PyTorch tensors instead of plain lists. 
# These are needed for fast similarity math later on.
# So this step creates a reference library of vectors, one for each intent.
# These are precomputed at the top of the file so you don't need to
# recalculate them for every single user input — that makes the code much faster.


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

    print(f"[IntentClassifier] Match: {intent_labels[best_match_idx]} (score: {bestscore:.2f})"f"[IntentClassifier] Match: {intent_labels[best_match_idx]} (score: {bestscore:.2f})")
    if bestscore < 0.40:
        return "fallback"
    else:
        return intent_labels[best_match_idx]
