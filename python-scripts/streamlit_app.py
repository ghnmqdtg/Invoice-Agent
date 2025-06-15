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

# --- Sidebar for File Uploads ---
st.sidebar.header("Upload Invoice")
invoice_file = st.sidebar.file_uploader(
    "Upload your invoice", type=["pdf", "png", "jpg", "jpeg"]
)

if invoice_file:
    st.sidebar.write(f"Uploaded file: `{invoice_file.name}`")
    if st.sidebar.button("Process Invoice"):
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
    st.header("Review Required")
    st.write("The following items could not be matched with high confidence. Please select the correct product.")

    items_to_review = [
        (i, item) for i, item in enumerate(st.session_state.processed_data['items'])
        if item.get('product_id') is None and 'possible_matches' in item and item['possible_matches']
    ]

    if not items_to_review:
        st.info("No items require manual review.")
    else:
        # Initialize a place to store user's choices
        if 'user_selections' not in st.session_state:
            st.session_state.user_selections = {}

        for index, item in items_to_review:
            st.subheader(f"Invoice Item: `{item.get('original_name')}`")
            
            # Prepare options for selectbox
            possible_matches = item['possible_matches']
            options = ["--- NOT A MATCH ---"] + [
                f"{p['matched_name']} (Score: {p['match_score']})" for p in possible_matches
            ]
            
            # Create a mapping from option string back to product data
            option_map = {f"{p['matched_name']} (Score: {p['match_score']})": p for p in possible_matches}

            selection = st.selectbox(
                "Select the correct product:",
                options=options,
                key=f"select_{index}" # Unique key for each selectbox
            )

            # If user indicates no match, show a search box for the entire DB
            if selection == "--- NOT A MATCH ---":
                all_product_names = [""] + [p['product_name'] for p in st.session_state.product_db if p.get('product_name')]
                manual_selection_name = st.selectbox(
                    "Search for a product in the database",
                    options=all_product_names,
                    key=f"manual_select_{index}"
                )
                
                # Find the full product details from the selected name
                if manual_selection_name:
                    selected_product = next((p for p in st.session_state.product_db if p['product_name'] == manual_selection_name), None)
                    st.session_state.user_selections[index] = selected_product
                else:
                    st.session_state.user_selections[index] = None
            else:
                st.session_state.user_selections[index] = option_map.get(selection)

        if st.button("Finalize and Generate JSON"):
            final_data = st.session_state.processed_data.copy()
            
            for index, selection in st.session_state.user_selections.items():
                if selection:
                    # Update the item with the user's choice
                    final_data['items'][index].update({
                        'product_id': selection.get('product_id'),
                        'matched_name': selection.get('product_name'),
                        'product_unit': selection.get('unit'),
                        'product_currency': selection.get('currency'),
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
