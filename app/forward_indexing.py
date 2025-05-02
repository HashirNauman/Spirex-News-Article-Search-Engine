import pickle
from lexicon import tokenize_and_normalize

def create_forward_index(documents):
    forward_index = {}
    for doc_id, content in documents.items():
        forward_index[doc_id] = tokenize_and_normalize(content)
    return forward_index

def save_index_to_disk(index, filename):
    with open(filename, 'wb') as file:
        pickle.dump(index, file)
    print(f"Index saved successfully to {filename}")

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
