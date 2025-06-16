from .basic import basic_matching
from .fuzzy import fuzzy_matching
import pandas as pd

__all__ = ['basic_matching', 'fuzzy_matching', 'alias_match_item']

def alias_match_item(item, alias_map, product_id_map):
    """
    Matches a single item using the alias map.
    Returns the enhanced item if a match is found, otherwise None.
    """
    # Find the product_id from the alias_map if the input_name is in it
    input_name = item.get('product_name', '').strip()
    product_id = alias_map.get(input_name.lower())

    # Check if the product_id (alias) is in the product_id_map (database)
    if product_id and product_id in product_id_map:
        # Get the actual product_name from the product_id_map
        matched_product = product_id_map[product_id]
        enhanced_item = item.copy()
        # Rename product_name to original_name
        if 'product_name' in enhanced_item:
            enhanced_item['original_name'] = enhanced_item.pop('product_name')
        # Update the item with the matched product information
        enhanced_item.update({
            'product_id': matched_product.get('product_id'),
            'matched_name': matched_product.get('product_name'),
            'unit': matched_product.get('unit'),
            'currency': matched_product.get('currency'),
            'match_score': 100
        })
        return enhanced_item
    
    return None 