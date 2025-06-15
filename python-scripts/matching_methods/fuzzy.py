import re
from datetime import datetime
from thefuzz import fuzz

def fuzzy_matching(invoice_data, product_db, threshold=85):
    """
    Enhanced invoice processing with fuzzy matching.
    """
    if 'items' not in invoice_data:
        return invoice_data

    enhanced_items = []
    for item in invoice_data['items']:
        enhanced_item = fuzzy_match_product(item, product_db, threshold)
        
        # Override subtotal
        if enhanced_item.get('quantity') and enhanced_item.get('unit_price'):
            enhanced_item['subtotal'] = enhanced_item['quantity'] * enhanced_item['unit_price']
            
        enhanced_items.append(enhanced_item)

    invoice_data['items'] = enhanced_items
    invoice_data['processed_at'] = datetime.now().isoformat()
    
    return invoice_data

def normalize_text(text):
    """
    Normalize text by lowercasing, removing extra spaces, and special characters.
    """
    text = text.lower()
    text = text.replace('\\', '/')  # Convert backslashes to forward slashes
    text = re.sub(r'[\(\)/,-]', ' ', text)  # Remove forward slashes and other special chars
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def fuzzy_match_product(item, product_db, threshold=80):
    """
    Finds the best product match for an item using fuzzy string matching.
    """
    input_name = item.get('product_name', '')
    if not input_name:
        return {**item, 'product_id': None, 'matched_name': None, 'match_score': 0}

    normalized_input_name = normalize_text(input_name)
    best_match = None
    highest_score = 0

    for product in product_db:
        db_product_name = product.get('product_name', '')
        if not db_product_name:
            continue

        normalized_db_name = normalize_text(db_product_name)
        
        # Using token_set_ratio which is good for matching strings of different lengths
        score = fuzz.token_set_ratio(normalized_input_name, normalized_db_name)

        if score > highest_score:
            highest_score = score
            best_match = product

    enhanced_item = item.copy()
    if 'product_name' in enhanced_item:
        enhanced_item['original_name'] = enhanced_item.pop('product_name')

    if highest_score >= threshold and best_match:
        enhanced_item.update({
            'product_id': best_match.get('product_id'),
            'matched_name': best_match.get('product_name'),
            'product_unit': best_match.get('unit'),
            'product_currency': best_match.get('currency'),
            'match_score': highest_score
        })
    else:
        enhanced_item.update({
            'product_id': None,
            'matched_name': None,
            'match_score': highest_score
        })
        
    return enhanced_item 