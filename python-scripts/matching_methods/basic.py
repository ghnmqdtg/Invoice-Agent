import re
from datetime import datetime

def basic_matching(invoice_data, product_db):
    """Enhanced invoice processing with basic exact matching"""
    if 'items' not in invoice_data:
        return invoice_data
    
    enhanced_items = []
    match_stats = {"exact_matches": 0, "no_matches": 0}
    
    for item in invoice_data['items']:
        enhanced_item = basic_match_product(item, product_db)
        
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
    invoice_data['processed_at'] = datetime.now().isoformat()
    
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

def check_exact_match(input_name, product_name_parts):
    """Check if input matches any individual product name part exactly"""
    return input_name in product_name_parts

def check_concatenated_match(input_name, concatenated):
    """Check if input matches the concatenated product name"""
    return input_name == concatenated

def basic_match_product(item, product_db):
    """Basic exact string matching with support for both / and \ separators"""
    input_name = item.get('product_name', '').strip().lower()
    enhanced_item = item.copy()
    
    # Rename product_name to original_name
    if 'product_name' in enhanced_item:
        enhanced_item['original_name'] = enhanced_item.pop('product_name')
    
    for product in product_db:
        db_product_name = product.get('product_name', '').strip()
        parts, concatenated = get_product_name_variants(db_product_name)
        
        # Check for exact match with any individual part
        if check_exact_match(input_name, parts):
            enhanced_item['product_id'] = product.get('product_id')
            enhanced_item['matched_name'] = product.get('product_name')
            enhanced_item['product_unit'] = product.get('unit')
            enhanced_item['product_currency'] = product.get('currency')
            break
        
        # Check for concatenated match
        if check_concatenated_match(input_name, concatenated):
            enhanced_item['product_id'] = product.get('product_id')
            enhanced_item['matched_name'] = product.get('product_name')
            enhanced_item['product_unit'] = product.get('unit')
            enhanced_item['product_currency'] = product.get('currency')
            break
    else:
        enhanced_item['product_id'] = None
        enhanced_item['matched_name'] = None
    
    return enhanced_item 