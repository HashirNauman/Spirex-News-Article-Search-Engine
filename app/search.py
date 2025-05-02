import math
from collections import defaultdict
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# BM25 ranking function with debugging
def bm25(query, inverted_index, forward_index, idf_cache, total_documents, avg_doc_length, k1=1.2, b=0.75):
    scores = defaultdict(float)
    query_terms = query.lower().split()
    logging.debug(f"Tokenized query terms: {query_terms}")

    for term in query_terms:
        if term in inverted_index:
            idf = idf_cache.get(term, 0)
            for doc_id, doc_freq in inverted_index[term]:
                tf = forward_index.get(doc_id, []).count(term)  # Term Frequency in the document
                doc_length = len(forward_index.get(doc_id, []))  # Document Length
                score = idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_length / avg_doc_length))
                scores[doc_id] += score
                logging.debug(f"Term: {term}, DocID: {doc_id}, TF: {tf}, DocLength: {doc_length}, Score: {score}")
        else:
            logging.warning(f"Term '{term}' not found in inverted index.")
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)

# Main search function with debugging
def search(query, inverted_index, forward_index, idf_cache, total_documents, avg_doc_length):
    query = query.strip().lower()
    logging.info(f"Searching for query: {query}")
    results = bm25(query, inverted_index, forward_index, idf_cache, total_documents, avg_doc_length)
    logging.info(f"Found {len(results)} results.")
    return results