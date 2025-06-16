import re
from datetime import datetime

def basic_matching(invoice_data, product_db):
    """Enhanced invoice processing with basic exact matching"""
    # Pre-process product_db into a lookup map and handle duplicates
    product_map = {}
    seen_product_names = set()
    for product in product_db:
        product_name = product.get('product_name')
        if not product_name or product_name in seen_product_names:
            continue
        seen_product_names.add(product_name)
        
        parts, concatenated = get_product_name_variants(product_name)
        for part in parts:
            if part not in product_map:
                product_map[part] = product
        if concatenated not in product_map:
            product_map[concatenated] = product

    if 'items' not in invoice_data:
        return invoice_data
    
    enhanced_items = []
    match_stats = {"exact_matches": 0, "no_matches": 0}
    
    for item in invoice_data['items']:
        enhanced_item = basic_match_product(item, product_map)
        
        # Track matching statistics
        if enhanced_item.get('product_id'):
            match_stats["exact_matches"] += 1
        else:
            match_stats["no_matches"] += 1
        
        # Override subtotal
        if enhanced_item.get('quantity') and enhanced_item.get('unit_price'):
            enhanced_item['subtotal'] = enhanced_item['quantity'] * enhanced_item['unit_price']
        
        enhanced_items.append(enhanced_item)
    
    invoice_data['items'] = enhanced_items
    invoice_data['match_statistics'] = match_stats
    
    return invoice_data

def normalize_separators(text):
    """Convert all backslashes to forward slashes for consistent processing"""
    return text.replace('\\', '/')

def clean_product_name(name):
    """Remove parentheses and extra whitespace from product name"""
    return re.sub(r'\([^)]*\)', '', name).strip()

def get_product_name_variants(product_name):
    """Get all variants of a product name (individual parts and concatenated)"""
    normalized = normalize_separators(product_name.lower())
    parts = [clean_product_name(part) for part in normalized.split('/')]
    concatenated = ''.join(parts)
    return parts, concatenated

def basic_match_product(item, product_map):
    """Basic exact string matching using a pre-processed product map."""
    input_name = item.get('product_name', '').strip().lower()
    enhanced_item = item.copy()
    
    # Rename product_name to original_name
    if 'product_name' in enhanced_item:
        enhanced_item['original_name'] = enhanced_item.pop('product_name')
    
    matched_product = product_map.get(input_name)
    
    if matched_product:
        enhanced_item['product_id'] = matched_product.get('product_id')
        enhanced_item['matched_name'] = matched_product.get('product_name')
        enhanced_item['unit'] = matched_product.get('unit')
        enhanced_item['currency'] = matched_product.get('currency')
    else:
        enhanced_item['product_id'] = None
        enhanced_item['matched_name'] = None
    
    return enhanced_item 