import streamlit as st
import pandas as pd
import json
import requests
import os
from matching_methods import basic_matching, fuzzy_matching

st.set_page_config(layout="wide")

st.title("Invoice Product Matching Assistant")

st.info("""
**Workflow:**
1. Upload your invoice file (PDF, PNG, or JPG).
2. Click "Process Invoice" to have AI extract and match the products.
3. Correct any uncertain matches in the table below.
""")

# --- Load Product Database from a fixed path ---
@st.cache_data
def load_product_db():
    # Path relative to the script location
    script_dir = os.path.dirname(__file__)
    db_path = os.path.join(script_dir, "shared", "product_db.csv")
    try:
        df = pd.read_csv(db_path)
        return df.to_dict(orient='records')
    except FileNotFoundError:
        st.error(f"Error: Product database not found at `{db_path}`. Please ensure the file exists.")
        return None

product_db = load_product_db()
if product_db:
    st.session_state.product_db = product_db

# --- File Uploads ---
st.header("Upload Invoice")
invoice_file = st.file_uploader(
    "Upload your invoice", type=["pdf", "png", "jpg", "jpeg"]
)

if invoice_file:
    st.write(f"Uploaded file: `{invoice_file.name}`")
    if st.button("Process Invoice"):
        n8n_webhook_url = "http://localhost:8080/webhook-test/e77b5a73-f0ef-42ff-9519-8e5bbb7d7af4"
        
        files = {"file": (invoice_file.name, invoice_file.getvalue(), invoice_file.type)}
        with st.spinner("Processing invoice via n8n... This may take a moment."):
            try:
                response = requests.post(n8n_webhook_url, files=files, timeout=300)
                print(response.text) # For debugging
                response.raise_for_status()
                
                processed_json = response.json()
                
                # The python service nests the data in a 'processed_data' key.
                # We extract it here. If not found, we assume the whole response is the data.
                st.session_state.processed_data = processed_json.get('processed_data', processed_json)
                
                st.success("Invoice processed! Please review the matches below.")
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to process invoice: {e}")
                # Try to show more helpful error from response
                try:
                    st.error(f"Response content: {response.text}")
                except NameError:
                    pass # response object may not exist

if 'processed_data' in st.session_state:
    st.header("Invoice Summary")
    st.write("You can edit the invoice summary details here if anything is missing or incorrect.")
    invoice_data = st.session_state.processed_data
    
    col1, col2 = st.columns(2)

    with col1:
        vendor_name = st.text_input(
            "Vendor Name",
            value=invoice_data.get("vendor_name") or ""
        )
        invoice_date = st.text_input(
            "Invoice Date",
            value=invoice_data.get("invoice_date") or ""
        )

    with col2:
        invoice_number = st.text_input(
            "Invoice Number",
            value=invoice_data.get("invoice_number") or ""
        )
        
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            try:
                current_total = int(invoice_data.get("total_amount", 0))
            except (ValueError, TypeError):
                current_total = 0
            total_amount = st.number_input(
                "Total Amount",
                value=current_total,
                step=1,
                format="%d"
            )
        with sub_col2:
            currency = st.text_input(
                "Currency",
                value=invoice_data.get("currency") or ""
            )

    # Update the session state with the potentially modified values
    st.session_state.processed_data['vendor_name'] = vendor_name
    st.session_state.processed_data['invoice_date'] = invoice_date
    st.session_state.processed_data['invoice_number'] = invoice_number
    st.session_state.processed_data['total_amount'] = total_amount
    st.session_state.processed_data['currency'] = currency

    st.header("Processed Items")
    st.write("Below are all items extracted from the invoice. Items requiring your attention are highlighted.")

    if 'items' in invoice_data and invoice_data['items']:
        # Prepare data for the table
        table_data = []
        for item in invoice_data['items']:
            item_copy = item.copy()
            if item_copy.get('product_id') is None and 'possible_matches' in item_copy and item_copy['possible_matches']:
                item_copy['status'] = 'Review Required'
            elif item_copy.get('product_id'):
                item_copy['status'] = 'Matched'
            else:
                item_copy['status'] = 'Not Matched'
            table_data.append(item_copy)
            
        df = pd.DataFrame(table_data)

        # Define columns to display, and filter for those that exist in the DataFrame
        display_cols = [
            'status', 'product_id', 'original_name', 'matched_name', 'quantity', 
            'unit', 'unit_price', 'subtotal'
        ]
        existing_cols = [col for col in display_cols if col in df.columns]
        
        # Styler function to highlight rows
        def highlight_review_rows(row):
            color = '#FFF3CD' if row.get('status') == 'Review Required' else ''
            return [f'background-color: {color}' for _ in row]

        if existing_cols:
            st.dataframe(
                df[existing_cols].style.apply(highlight_review_rows, axis=1),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Could not display items table as no relevant columns were found.")

    else:
        st.info("No items were extracted from the invoice.")

    st.header("Review Required")
    st.write("The following items could not be matched with high confidence. Please select the correct product.")

    items_to_review = [
        (i, item) for i, item in enumerate(st.session_state.processed_data['items'])
        if item.get('product_id') is None or item.get('match_score') < 85
    ]

    if not items_to_review:
        st.info("No items require manual review.")
    else:
        # Initialize a place to store user's choices
        if 'user_selections' not in st.session_state:
            st.session_state.user_selections = {}

        for index, item in items_to_review:
            st.subheader(f"Invoice Item: `{item.get('original_name')}`")
            
            # --- Combined Product Selection ---
            
            # 1. Prepare suggestions from possible_matches
            possible_matches = item.get('possible_matches', [])
            suggestion_options = []
            suggestion_map = {}
            if possible_matches and isinstance(possible_matches[0], dict):
                for p in possible_matches:
                    option_str = f"{p['matched_name']} (Score: {p['match_score']})"
                    suggestion_options.append(option_str)
                    suggestion_map[option_str] = p
            
            # 2. Prepare all other products from DB
            all_products = st.session_state.get('product_db', [])
            product_db_map = {p['product_name']: p for p in all_products if p.get('product_name')}
            
            # 3. Filter out suggestions from all products to avoid duplicates
            suggestion_names = {p['matched_name'] for p in possible_matches if isinstance(p, dict)}
            other_product_names = [name for name in product_db_map.keys() if name not in suggestion_names]
            
            # 4. Combine options
            options = suggestion_options + sorted(other_product_names)

            # 5. The single selectbox
            selection = st.selectbox(
                "Select the correct product or search from the list:",
                options=options,
                key=f"select_{index}",
                placeholder="--- NOT A MATCH ---",
                index=0 if options else None  # Set first option as default
            )
            
            # 6. Logic to handle selection
            selected_product = None
            if selection is None:
                selected_product = None
            elif selection in suggestion_map:
                selected_product = suggestion_map[selection]
            elif selection in product_db_map:
                selected_product = product_db_map[selection]

            st.session_state.user_selections[index] = selected_product

        if st.button("Finalize and Generate JSON"):
            final_data = st.session_state.processed_data.copy()
            
            for index, selection in st.session_state.user_selections.items():
                if selection:
                    # Update the item with the user's choice
                    final_data['items'][index].update({
                        'product_id': selection.get('product_id'),
                        'matched_name': selection.get('matched_name'),
                        'original_name': final_data['items'][index].get('original_name'),
                        'unit': selection.get('unit'),
                        'currency': selection.get('currency'),
                        'match_score': selection.get('match_score', 100),
                        'possible_matches': []
                    })
                else:
                    # Handle cases where "NOT A MATCH" was selected and no manual product was chosen
                    final_data['items'][index].update({
                        'product_id': None,
                        'matched_name': None,
                        'match_score': 0,
                        'possible_matches': []
                    })

            st.session_state.final_data = final_data

if 'final_data' in st.session_state:
    st.header("Completed JSON")
    st.json(st.session_state.final_data)
    st.download_button(
        label="Download Final JSON",
        data=json.dumps(st.session_state.final_data, indent=2),
        file_name="final_invoice_data.json",
        mime="application/json"
    )

    if st.button("Upload a new one"):
        # Clear the session state to allow for a new upload, preserving the product DB
        for key in list(st.session_state.keys()):
            if key != 'product_db':
                del st.session_state[key]
        st.rerun() 
