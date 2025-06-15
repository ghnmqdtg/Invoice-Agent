import re
from datetime import datetime
from thefuzz import fuzz

def fuzzy_matching(invoice_data, product_db, threshold=85, suggestion_threshold=60):
    """
    Enhanced invoice processing with fuzzy matching.
    """
    # Deduplicate product_db based on 'product_name'
    unique_products = []
    seen_product_names = set()
    for product in product_db:
        product_name = product.get('product_name')
        if product_name and product_name not in seen_product_names:
            unique_products.append(product)
            seen_product_names.add(product_name)

    if 'items' not in invoice_data:
        return invoice_data

    enhanced_items = []
    for item in invoice_data['items']:
        enhanced_item = fuzzy_match_product(item, unique_products, threshold, suggestion_threshold)
        
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
    text = re.sub(r'[\(\)/,-]', '', text)  # Remove forward slashes and other special chars
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def fuzzy_match_product(item, product_db, threshold=85, suggestion_threshold=60):
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
    for product in product_db:
        db_product_name = product.get('product_name', '')
        if not db_product_name:
            continue

        normalized_db_name = normalize_text(db_product_name)
        
        # Using token_set_ratio which is good for matching strings of different lengths
        score = fuzz.token_set_ratio(normalized_input_name, normalized_db_name)

        if score >= suggestion_threshold:
            scored_products.append({
                'product': product,
                'score': score
            })

    enhanced_item = item.copy()
    if 'product_name' in enhanced_item:
        enhanced_item['original_name'] = enhanced_item.pop('product_name')

    if not scored_products:
        enhanced_item.update({
            'product_id': None,
            'matched_name': None,
            'match_score': 0,
            'possible_matches': [""]
        })
        return enhanced_item

    scored_products.sort(key=lambda x: x['score'], reverse=True)
    
    best_match_info = scored_products[0]
    highest_score = best_match_info['score']
    best_match = best_match_info['product']

    if highest_score >= threshold:
        enhanced_item.update({
            'product_id': best_match.get('product_id'),
            'matched_name': best_match.get('product_name'),
            'unit': best_match.get('unit'),
            'currency': best_match.get('currency'),
            'match_score': highest_score
        })
    else:
        suggestions = [{
            'product_id': p['product'].get('product_id'),
            'matched_name': p['product'].get('product_name'),
            'unit': p['product'].get('unit'),
            'currency': p['product'].get('currency'),
            'match_score': p['score']
        } for p in scored_products]
        
        enhanced_item.update({
            'product_id': None,
            'matched_name': None,
            'match_score': highest_score,
            'possible_matches': suggestions
        })
        
    return enhanced_item 