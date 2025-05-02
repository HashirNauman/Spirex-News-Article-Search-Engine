from flask import Flask, request, jsonify
from flask_cors import cross_origin
from search import search
from inverted_indexing import create_inverted_index, incremental_save_index, tokenize_and_normalize
from forward_indexing import create_forward_index, load_index_from_disk
from lexicon import create_lexicon, process_in_batches
import pandas as pd
from barrels import divide_index_into_barrels, load_all_barrels
import os
from concurrent.futures import ThreadPoolExecutor
import math
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Global variables
MAX_ROWS = 50000
DATASET_PATH = "../datasets/data.csv"
PROCESSED_DATA_PATH = "../datasets/processed_data.csv"
documents = {}
inverted_index = {}
forward_index = {}
idf_cache = {}
total_documents = 0
avg_doc_length = 0

def initialize_indexes():
    global documents, inverted_index, forward_index, idf_cache, total_documents, avg_doc_length

    # Load dataset into memory to avoid repetitive I/O
    total_rows_processed = 0
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Dataset file not found at {DATASET_PATH}")

    # Create processed_data.csv by selecting MAX_ROWS from the original data.csv
    if not os.path.exists(PROCESSED_DATA_PATH):
        dataset = pd.read_csv(DATASET_PATH)
        processed_data = dataset.head(MAX_ROWS)  # Take the first MAX_ROWS rows
        processed_data.to_csv(PROCESSED_DATA_PATH, index=False)
        logging.info(f"Processed data saved to {PROCESSED_DATA_PATH}")

    # Read the processed data for further operations
    chunks = pd.read_csv(PROCESSED_DATA_PATH, chunksize=5000)
    for chunk in chunks:
        if total_rows_processed >= MAX_ROWS:
            break
        remaining_rows = MAX_ROWS - total_rows_processed
        if len(chunk) > remaining_rows:
            chunk = chunk.head(remaining_rows)
        new_documents = process_in_batches(chunk)
        documents.update(new_documents)
        total_rows_processed += len(chunk)

    logging.debug(f"Processed {total_rows_processed} rows into documents. Sample: {list(documents.items())[:5]}")

    lexicon, inverted_index = create_lexicon(documents)
    logging.debug(f"Lexicon created. Sample terms: {list(lexicon.keys())[:5]}")
    
    inverted_index = create_inverted_index(documents)
    logging.debug(f"Inverted index created. Sample: {list(inverted_index.items())[:5]}")

    forward_index = create_forward_index(documents)
    logging.debug(f"Forward index created. Sample: {list(forward_index.items())[:5]}")

    total_documents = len(documents)
    avg_doc_length = sum(len(content) for content in forward_index.values()) / total_documents

    logging.info(f"Total documents: {total_documents}, Average document length: {avg_doc_length}")

    # Precompute IDF and cache
    idf_cache = {
        term: math.log((total_documents - len(doc_list) + 0.5) / (len(doc_list) + 0.5) + 1.0) 
        for term, doc_list in inverted_index.items()
    }
    logging.debug(f"IDF cache created. Sample: {list(idf_cache.items())[:5]}")
    print("Size of lexicon:", len(lexicon))
    print("Size of inverted_index:", len(inverted_index))
    print("Size of forward_index:", len(forward_index))
    incremental_save_index(lexicon, './lexicon.pkl')
    incremental_save_index(inverted_index, './inverted_index.pkl')
    incremental_save_index(forward_index, './forward_index.pkl')

    divide_index_into_barrels(inverted_index, num_barrels=4, base_filename="inverted_index")

@app.route('/search', methods=['GET'])
@cross_origin(origins='*')
def search_query():
    query = request.args.get('query')
    page = int(request.args.get('page', 1))  # Default to page 1
    size = int(request.args.get('size', 10))  # Default to 10 results per page
    
    if query:
        logging.info(f"Received search query: {query}")
        
        with ThreadPoolExecutor() as executor:
            future = executor.submit(load_all_barrels, "inverted_index", num_barrels=4)
            all_barrels = future.result()
            logging.debug(f"Loaded all barrels. Sample keys: {list(all_barrels.keys())[:5]}")
        
        results = search(query, all_barrels, forward_index, idf_cache, total_documents, avg_doc_length)
        logging.debug(f"Search results (article_id, score): {results}")

        # Apply pagination to the results
        start = (page - 1) * size
        end = start + size
        paginated_results = results[start:end]

        dataset = pd.read_csv(PROCESSED_DATA_PATH)  # Use processed_data.csv
        dataset = dataset.set_index('article_id')

        formatted_results = []
        for result in paginated_results:
            article_id, score = result
            if article_id in dataset.index:
                try:
                    row = dataset.loc[article_id]
                    if isinstance(row, pd.DataFrame):
                        row = row.iloc[0]
                    formatted_results.append({
                        "score": score,
                        "article_id": article_id,
                        "source_id": row.get('source_id') if pd.notna(row.get('source_id')) else None,
                        "title": row.get('title') if pd.notna(row.get('title')) else None,
                        "content": row.get('description') if pd.notna(row.get('description')) else "",  # Default to empty string
                        "published": row.get('published_at') if pd.notna(row.get('published_at')) else None,
                        "url": row.get('url') if pd.notna(row.get('url')) else None
                    })
                except Exception as e:
                    logging.error(f"Error processing article_id {article_id}: {e}")
        return jsonify({
            "query": query,
            "results": formatted_results,
            "page": page,
            "size": size,
            "total_results": len(results)
        })
    else:
        logging.warning("No query provided in request.")
        return jsonify({"message": "Please provide a query."})

@app.route('/add_document', methods=['POST'])
@cross_origin(origins='*')
def add_document():
    """
    Handles the addition of a new document to the dataset and updates indexes dynamically.
    """
    document_data = request.json  # Get the new document data from the request
    try:
        # Validate the required fields
        required_fields = ['article_id', 'title', 'description', 'content', 'full_content', 'source_id', 'url', 'published_at']
        for field in required_fields:
            if field not in document_data:
                logging.warning(f"Missing field: {field} in document: {document_data}")
                return jsonify({"message": f"Missing required field: {field}"}), 400

        # Validate article_id format
        try:
            document_id = int(document_data['article_id'])
        except ValueError:
            logging.error(f"Invalid article_id: {document_data['article_id']}")
            return jsonify({"message": "Invalid article_id. Must be an integer."}), 400

        # Convert the document into a DataFrame for batch-like processing
        new_data = pd.DataFrame([document_data])

        # Match column order with the existing processed_data.csv file
        processed_data_columns = pd.read_csv(PROCESSED_DATA_PATH, nrows=0).columns.tolist()

        # Add missing columns with default values
        for col in processed_data_columns:
            if col not in new_data.columns:
                new_data[col] = None  # Assign a default value (e.g., None or an empty string)

        # Ensure the new DataFrame matches the schema of the processed_data.csv file
        new_data = new_data[processed_data_columns]

        # Append the new data to the processed dataset file
        new_data.to_csv(PROCESSED_DATA_PATH, mode='a', header=False, index=False)

        # Process the new document for indexing
        processed_documents = process_in_batches(new_data)
        if not processed_documents:
            logging.warning("Document content is invalid or empty after processing.")
            return jsonify({"message": "Document content is invalid or empty after processing."}), 400

        # Add the processed document to global variables
        documents.update(processed_documents)

        # Update indexes
        lexicon, updated_inverted_index = create_lexicon(processed_documents)
        inverted_index.update(updated_inverted_index)
        forward_index[document_id] = processed_documents[document_id]

        # Recalculate IDF cache
        global idf_cache
        idf_cache = {
            term: math.log((total_documents - len(doc_list) + 0.5) / (len(doc_list) + 0.5) + 1.0)
            for term, doc_list in inverted_index.items()
        }
        print("Size of lexicon:", len(lexicon))
        print("Size of inverted_index:", len(inverted_index))
        print("Size of forward_index:", len(forward_index))
        # Incremental saving of indexes
        incremental_save_index(lexicon, './lexicon.pkl')
        incremental_save_index(inverted_index, './inverted_index.pkl')
        incremental_save_index(forward_index, './forward_index.pkl')

        # Recompute barrels for the new content
        divide_index_into_barrels(inverted_index, num_barrels=4, base_filename="inverted_index")

        logging.info(f"Document {document_id} added successfully.")
        return jsonify({"message": "Document added successfully!"}), 200

    except Exception as e:
        logging.error(f"Error adding document {document_data.get('article_id')}: {e}", exc_info=True)
        return jsonify({"message": "Failed to add document"}), 500

if __name__ == "__main__":
    try:
        logging.info("Initializing indexes...")
        initialize_indexes()
        logging.info("Indexes initialized successfully.")
    except Exception as e:
        logging.error(f"Error during initialization: {e}")
        exit(1)

    app.run(host='0.0.0.0', debug=True, port=5000)