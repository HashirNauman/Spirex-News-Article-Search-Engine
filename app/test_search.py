import pickle
import csv
import re
from collections import defaultdict

# Function to process and tokenize the text
def tokenize(text):
    # Basic text cleaning (remove non-alphanumeric characters and split by spaces)
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    return text.lower().split()

# Initialize an empty inverted index
inverted_index = defaultdict(list)

# Increase the CSV field size limit
csv.field_size_limit(10000000)  # Adjust the size limit to handle large fields

# Load your CSV file containing the article data
csv_file = '../datasets/data.csv'  # Update with your actual CSV file path
with open(csv_file, 'r') as file:
    reader = csv.DictReader(file)  # Assumes the CSV has a header row
    for row in reader:
        article_id = int(row['article_id'])  # Assuming the column for article ID is named 'article_id'
        content = row['content']  # Assuming the column for the article content is named 'content'

        # Tokenize the article content
        terms = tokenize(content)

        # Update the inverted index
        for term in set(terms):  # Use a set to avoid duplicates in the index
            inverted_index[term].append(article_id)

# Save the updated inverted index to a pickle file
with open('inverted_index.pkl', 'wb') as file:
    pickle.dump(inverted_index, file)

print("Inverted index has been updated and saved.")


# Function to search for a term in the inverted index
def search_term(query):
    query = query.lower()  # Ensure the query is in lowercase
    with open('.//inverted_index.pkl', 'rb') as file:
        inverted_index = pickle.load(file)

    # Search for the query in the inverted index
    if query in inverted_index:
        print(f"Documents containing '{query}': {inverted_index[query]}")
    else:
        print(f"'{query}' is not found in the inverted index.")

# Test with the query 'Himalayan' (or any other term you'd like to search for)
search_term("Himalayan")

