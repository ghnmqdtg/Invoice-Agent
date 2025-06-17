import re
from datetime import datetime
from thefuzz import fuzz

def fuzzy_matching(invoice_data: dict, product_db: list[dict], threshold: int = 85, suggestion_threshold: int = 60) -> dict:
    """
    Enhanced invoice processing with fuzzy matching.
    """
    # Pre-process product_db into a lookup map and handle duplicates
    unique_products = []
    seen_product_names = set()
    for product in product_db:
        product_name = product.get('product_name')
        # Skip if product name is empty or already processed
        if not product_name or product_name in seen_product_names:
            continue
        unique_products.append(product)
        seen_product_names.add(product_name)

    if 'items' not in invoice_data:
        return invoice_data

    # Initialize a list to store the enhanced items
    enhanced_items = []
    for item in invoice_data['items']:
        enhanced_item = fuzzy_match_product(item, unique_products, threshold, suggestion_threshold)
        
        # Override subtotal
        if enhanced_item.get('quantity') and enhanced_item.get('unit_price'):
            enhanced_item['subtotal'] = enhanced_item['quantity'] * enhanced_item['unit_price']
            
        enhanced_items.append(enhanced_item)

    invoice_data['items'] = enhanced_items
    
    return invoice_data

def normalize_text(text: str) -> str:
    """
    Normalize text by lowercasing, removing extra spaces, and special characters.
    """
    text = text.lower()
    text = text.replace('\\', '/')  # Convert backslashes to forward slashes
    text = re.sub(r'[\(\)/,-]', '', text)  # Remove forward slashes and other special chars
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def fuzzy_match_product(item: dict, product_db: list[dict], threshold: int = 85, suggestion_threshold: int = 60) -> dict:
    """
    Finds the best product match for an item using fuzzy string matching.
    If no match is found above the threshold, it returns a list of possible matches.
    """
    input_name = item.get('product_name', '')
    
    # If no product name, return empty JSON
    if not input_name:
        return {**item, 'product_id': None, 'matched_name': None, 'match_score': 0, 'possible_matches': []}

    normalized_input_name = normalize_text(input_name)
    
    scored_products = []
    # Calculate the match score for each product
    for product in product_db:
        db_product_name = product.get('product_name', '')
        if not db_product_name:
            continue

        normalized_db_name = normalize_text(db_product_name)
        
        # Using token_set_ratio which is good for matching strings of different lengths
        match_score = fuzz.token_set_ratio(normalized_input_name, normalized_db_name)

        # If the match score is greater than the suggestion threshold, add the product to the list
        # For example, the default suggestion threshold is 60
        # If the match score is 60 or higher, it will be added to the list
        if match_score >= suggestion_threshold:
            scored_products.append({
                'product': product,
                'match_score': match_score
            })

    # Copy the item and rename product_name to original_name
    enhanced_item = item.copy()
    if 'product_name' in enhanced_item:
        enhanced_item['original_name'] = enhanced_item.pop('product_name')

    # If no possible matches are found, set the product_id and matched_name to None
    if not scored_products:
        enhanced_item.update({
            'product_id': None,
            'matched_name': None,
            'match_score': 0,
            'possible_matches': [""]
        })
        return enhanced_item

    # Sort the scored products by match_score in descending order
    scored_products.sort(key=lambda x: x['match_score'], reverse=True)
    
    # Get the best match from the list
    best_match_info = scored_products[0]
    highest_score = best_match_info['match_score']
    best_match = best_match_info['product']

    # If the best match score is greater than the threshold, update the enhanced item
    # For example, the default threshold is 85
    # If the match score is 85 or higher, it will be updated
    if highest_score >= threshold:
        enhanced_item.update({
            'product_id': best_match.get('product_id'),
            'matched_name': best_match.get('product_name'),
            'unit': best_match.get('unit'),
            'match_score': highest_score
        })
    else:
        # Otherwise, set the possible matches
        suggestions = [{
            'product_id': p['product'].get('product_id'),
            'matched_name': p['product'].get('product_name'),
            'unit': p['product'].get('unit'),
            'match_score': p['match_score']
        } for p in scored_products]
        
        enhanced_item.update({
            'product_id': None,
            'matched_name': None,
            'match_score': highest_score,
            'possible_matches': suggestions
        })
        
    return enhanced_item