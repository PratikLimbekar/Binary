# import json
# import numpy as np
# import tensorflow as tf
# from tf_keras.preprocessing.text import Tokenizer
# from tf_keras.utils import pad_sequences
# from tf_keras.models import Sequential
# from tf_keras.layers import Embedding, GlobalAveragePooling1D, Dense, Dropout
# from sklearn.model_selection import train_test_split
# from sklearn.preprocessing import LabelEncoder
# import matplotlib.pyplot as plt
# import seaborn as sns
# from sklearn.metrics import classification_report, confusion_matrix

# warnings.filterwarnings('ignore')
# #Data collection
# with open('intents.json', 'r') as f:
#     data = json.load(f)

# #data cleaning: removes punctuation
# def clean(line):
#     cleaned_line = ' '
#     for char in line:
#         if char.isalpha():
#             cleaned_line += char
#         else:
#             cleaned_line += ' '
#     cleaned_line = ' '.join(cleaned_line.split())
#     return cleaned_line

# #data preproc: tokenization
# intents = []
# unique_intents = []
# textinput = []
# intentresponse = {}

# for intent in data['intents']:
#     if intent['intent'] not in unique_intents:
#         unique_intents.append(intent['intent'])
#     for text in intent['text']:
#         textinput.append(clean(text))
#         intents.append(intent['intent'])

# print("Intent :",intents[0])
# print("Number of Intent:",len(intents))
# print("Sample Input:", textinput[0])
# print('Length of text_input:',len(textinput))
