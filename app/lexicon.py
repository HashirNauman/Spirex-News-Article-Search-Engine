from collections import defaultdict
import pickle
import re
from nltk.corpus import stopwords
STOPWORDS = set(stopwords.words('english'))
def tokenize_and_normalize(text):
    if not isinstance(text, str):# if text is not str
        return []# return empty list
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)# Only A-Z, a-z and 0-9 are allowed
    tokens = text.lower().split()# convert to lowercase and split into words
    return [token for token in tokens if token not in STOPWORDS]# remove stopwords


def process_in_batches(chunk):#process relevent fields in each chunk
    documents = {}
    for _, row in chunk.iterrows():
        # Concatenate text from multiple fields
        content = f"{row.get('title', '')} {row.get('description', '')} {row.get('content', '')} {row.get('full_content', '')}"
        processed_content = ' '.join(tokenize_and_normalize(content))

        if processed_content:  # if content is valid
            article_id = int(row['article_id'])  # convert article_id into integer
            documents[article_id] = processed_content  # store article_id(key) and content in them
    return documents


def create_lexicon(documents):
    lexicon = {}
    inverted_index = {}

    for doc_id, content in documents.items():
        words = content.split()
        term_freq = defaultdict(int)

        # Calculate term frequencies
        for word in words:
            term_freq[word] += 1

        for word, freq in term_freq.items():
            if word not in lexicon:
                lexicon[word] = len(lexicon)  # Assign unique ID

            if word not in inverted_index:
                inverted_index[word] = []  # Initialize the inverted index

            # Append (doc_id, freq) instead of just doc_id
            inverted_index[word].append((doc_id, freq))

    return lexicon, inverted_index
def save_lexicon_to_disk(lexicon, file_path):# save the lexicon
    with open(file_path, 'wb') as f:
        pickle.dump(lexicon, f)
    print(f"Lexicon saved to {file_path}")


def save_index_to_disk(index, file_path):# save the inverted index
    with open(file_path, 'wb') as f:
        pickle.dump(index, f)
    print(f"Inverted index saved to {file_path}")

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




