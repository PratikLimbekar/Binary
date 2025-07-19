import wikipedia

def search_wikipedia(query: str) -> str:
    try:
        wikipedia.set_lang("en")
        summary = wikipedia.summary(query, sentences = 3)
        return summary
    except wikipedia.exceptions.DisambiguationError as e:
        return f'Too many results. Be more specific, hoo.'
    except wikipedia.exceptions.PageError:
        return "Couldn't find anything on that topic."
    except Exception as e:
        return "something went wrong with Wikipedia Search."