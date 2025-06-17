import re
from datetime import datetime

def basic_matching(invoice_data: dict, product_db: list[dict]) -> dict:
    """Enhanced invoice processing with basic exact matching"""
    # Pre-process product_db into a lookup map and handle duplicates
    product_map = {}
    seen_product_names = set()
    for product in product_db:
        product_name = product.get('product_name')
        # Skip if product name is empty or already processed
        if not product_name or product_name in seen_product_names:
            continue
        seen_product_names.add(product_name)

        # Get all variants of the product name
        parts, concatenated = get_product_name_variants(product_name)
        # Use dict comprehension for cleaner and more efficient mapping
        product_map.update({part: product for part in parts if part not in product_map})
        if concatenated not in product_map:
            product_map[concatenated] = product

    if 'items' not in invoice_data:
        return invoice_data
    
    # Initialize a list to store the enhanced items
    enhanced_items = []
    
    for item in invoice_data['items']:
        enhanced_item = basic_match_product(item, product_map)
        
        # Override subtotal
        if enhanced_item.get('quantity') and enhanced_item.get('unit_price'):
            enhanced_item['subtotal'] = enhanced_item['quantity'] * enhanced_item['unit_price']
        
        # Add the enhanced item to the list
        enhanced_items.append(enhanced_item)
    
    # Update the invoice data with the enhanced items
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

def get_product_name_variants(product_name: str) -> tuple[list[str], str]:
    """
    Get all variants of a product name (individual parts and concatenated).
    For example, "豬皮/肉皮\\豬皮" will be split into ["豬皮", "肉皮", "豬皮"] and "豬皮肉皮豬皮".
    This is to handle the case where the product name is not always in the same format.
    """
    # Normalize separators and split into parts
    normalized = normalize_text(product_name)
    parts = normalized.split('/')
    concatenated = ''.join(parts)
    
    # Return both parts and concatenated version
    return parts, concatenated

def basic_match_product(item: dict, product_map: dict) -> dict:
    """Basic exact string matching using a pre-processed product map."""
    # Get the input product name and copy the item
    input_name = item.get('product_name', '').strip().lower()
    enhanced_item = item.copy()
    
    # Rename product_name to original_name
    if 'product_name' in enhanced_item:
        enhanced_item['original_name'] = enhanced_item.pop('product_name')
    
    # Get the matched product from the product map
    matched_product = product_map.get(input_name)
    
    if matched_product:
        # Update the invoice data with the matched product
        enhanced_item['product_id'] = matched_product.get('product_id')
        enhanced_item['matched_name'] = matched_product.get('product_name')
        enhanced_item['unit'] = matched_product.get('unit')
    else:
        # If no match is found, set the product_id and matched_name to None
        enhanced_item['product_id'] = None
        enhanced_item['matched_name'] = None
    
    return enhanced_item 