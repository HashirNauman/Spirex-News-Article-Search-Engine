import pickle
import os
from concurrent.futures import ThreadPoolExecutor

def create_barrel_filename(base_filename, barrel_id):
    return f"{base_filename}_barrel_{barrel_id}.pkl"

def divide_index_into_barrels(index, num_barrels=10, base_filename="inverted_index"):
    barrels = {i: {} for i in range(num_barrels)}
    sorted_terms = sorted(index.keys())
    
    # Ensure barrel_size is not zero
    if len(sorted_terms) < num_barrels:
        barrel_size = 1
    else:
        barrel_size = len(sorted_terms) // num_barrels

    for i, term in enumerate(sorted_terms):
        # Cap barrel_index to num_barrels - 1 to avoid overflow
        barrel_index = min(i // barrel_size, num_barrels - 1)
        barrels[barrel_index][term] = index[term]

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(save_barrel_to_disk, barrel, create_barrel_filename(base_filename, barrel_id)) 
                   for barrel_id, barrel in barrels.items()]
        for future in futures:
            future.result()
def save_barrel_to_disk(barrel, filename):
    with open(filename, 'wb') as f:
        pickle.dump(barrel, f)

def load_barrel_from_disk(filename):
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            return pickle.load(f)
    return {}

def load_all_barrels(base_filename, num_barrels=10):
    all_barrels = {}
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(load_barrel_from_disk, create_barrel_filename(base_filename, barrel_id)) 
                   for barrel_id in range(num_barrels)]
        for future in futures:
            barrel = future.result()
            all_barrels.update(barrel)
    return all_barrels
