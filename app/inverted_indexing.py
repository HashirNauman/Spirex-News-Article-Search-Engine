from lexicon import tokenize_and_normalize
import pickle
import re
from collections import defaultdict

def create_inverted_index(documents):
    inverted_index = defaultdict(list)
    for doc_id, content in documents.items():
        terms = tokenize_and_normalize(content)
        term_freq = defaultdict(int)
        for term in terms:
            term_freq[term] += 1
        for term, freq in term_freq.items():
            inverted_index[term].append((doc_id, freq))
    return inverted_index

def save_index_to_disk(index, filename):
    with open(filename, 'wb') as file:
        pickle.dump(index, file)
    print(f"Index saved to {filename}")

def load_index_from_disk(filename):
    with open(filename, 'rb') as file:
        return pickle.load(file)

def incremental_save_index(index, filename):
    try:
        with open(filename, 'rb') as file:
            existing_index = pickle.load(file)
            existing_index.update(index)
    except (FileNotFoundError, EOFError):
        existing_index = index
    with open(filename, 'wb') as file:
        pickle.dump(existing_index, file)
    print(f"Index saved successfully to {filename}")

