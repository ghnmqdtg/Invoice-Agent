# Invoice Agent

An automated invoice processing system using n8n and a Python backend to extract data from invoices, match products against a database, and learn from manual corrections.

<img src="assets/Screenshot_UI.png" alt="Streamlit App" width="800">

## Features

- **Automated Invoice Parsing**: Uses Google's Gemini 2.5 Flash model to extract structured data from uploaded invoice files (e.g., PDF, PNG, JPG).
- **Product Fuzzy Matching**: Matches extracted line items against a product database using a combination of alias map and fuzzy matching algorithms.
- **Self-Learning Alias System**: Learns from manually corrected product matches to improve accuracy over time. A human-in-the-loop workflow.
- **Containerized**: The entire application is containerized using Docker and managed with Docker Compose for easy setup and deployment.
- **Web Interface**: Includes a Streamlit application for interacting with the uploading and product matching functionality.

## Architecture

The system consists of two main services orchestrated by Docker Compose:

1.  **n8n Service**: A workflow automation tool that orchestrates the entire invoice processing pipeline, from receiving the file to calling the AI model and our Python service.
2.  **Python Service**: A Flask-based web service that handles the logic for product matching and maintains a database of product aliases.
    > Since the n8n Code node doesn't support the installation of Python or JavaScript libraries, we need to use this extra service to handle the complex logic.

## Getting Started

### Prerequisites

- Docker Desktop
- A Google Gemini API Key
- A Google Drive API Credential (GCP)

### Setup

1.**Clone the repository:**
`bash
    git clone https://github.com/ghnmqdtg/Invoice-Agent.git
    cd Invoice-Agent
    `

2.  **Run the docker:**

    ```bash
    docker-compose up -d
    ```

3.  **Configure n8n:**

    - Go to `http://localhost:8080` and login with your n8n account.
    - Import `workflow/Invoice_Agent.json` into your n8n workflow.
    - Update the Gemini API Key in the `Extract Invoice Data` node within the n8n workflow.
    - Create a folder in Google Drive and add it to `Save result to Google Drive` node.

4.  **Prepare product database:**

    - Put product database in `DB` folder and rename it to `product_dataset.xlsx`.
    - Convert the xlsx to csv.
      ```bash
      python utils/excel_converter.py
      ```

5.  **Set the config.json:**

    - Copy the example config file:
      ```bash
      cp python-scripts/config.json.example python-scripts/config.json
      ```
    - Update the `N8N_PROCESS_INVOICE_WEBHOOK` and `N8N_GDRIVE_UPLOAD_WEBHOOK` in `python-scripts/config.json` with the webhook URLs of the n8n workflow.

6.  **Initialize Streamlit App:**

    Run the following command to initialize the Streamlit app.

    ```bash
    streamlit run python-scripts/streamlit_app.py
    ```

## Workflow

The core logic is orchestrated in n8n and relies on the Python backend for specialized tasks.

### n8n Workflow

<img src="assets/Screenshot_workflow.png" alt="Invoice Processing Workflow" width="800">

The n8n workflow automates the entire process, from receiving an invoice to learning from user corrections. It's divided into two main parts as shown in the diagram:

**1. Uploading Invoice & Return the Detection Result in JSON**

This workflow is triggered when an invoice is uploaded.

- **`Listen to File Upload`**: A webhook node receives the invoice file from a client like the Streamlit app.
- **File Preparation**: The file is converted to a Base64 string and its MIME type is identified.
- **`Extract Invoice Data`**: The prepared file data is sent to the Google Gemini API to extract structured information. The prompt is provided in [Appendix](Appendix.md).
- **Data Processing**: The Gemini output is formatted into a JSON object, which is then sent to the Python service for product matching.
- **`Respond to Webhook`**: The final JSON, enriched with product matching results, is returned to the client.

**2. Uploading Reviewed JSON**

This workflow handles human-in-the-loop corrections to improve the system over time.

- **`Listen to the completed JSON Upload`**: A webhook receives the corrected JSON from the client.
- **Data Persistence**: The corrected JSON is saved to Google Drive for record-keeping.
- **Learning from Corrections**: The data is also sent to the `/update-alias` endpoint of the Python service. The service updates its product alias map, which improves future matching accuracy.
- **`Respond to Webhook`**: A confirmation is sent back to the client.

### Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant Streamlit App
    participant n8n as n8n Workflow
    participant GeminiAPI as Google Gemini API
    participant PythonService as Python Service
    participant GDrive as Google Drive

    Note over User, PythonService: Initial Invoice Processing
    User->>Streamlit App: Uploads invoice file
    Streamlit App->>n8n: POST to Invoice Webhook with file
    activate n8n
    n8n->>GeminiAPI: Extract data from invoice
    activate GeminiAPI
    GeminiAPI-->>n8n: Returns structured data
    deactivate GeminiAPI
    n8n->>PythonService: POST /process-invoice with extracted data
    activate PythonService
    PythonService-->>n8n: Returns data with matched products
    deactivate PythonService
    n8n-->>Streamlit App: Responds with processed data
    deactivate n8n
    Streamlit App->>User: Displays processed data for review

    Note over User, GDrive: Human-in-the-Loop Correction
    User->>Streamlit App: Corrects matches and submits
    Streamlit App->>n8n: POST to Reviewed JSON Webhook with corrections
    activate n8n
    n8n->>GDrive: Save corrected JSON
    n8n->>PythonService: POST /update-alias with corrections
    activate PythonService
    PythonService-->>n8n: Confirms alias update
    deactivate PythonService
    n8n-->>Streamlit App: Responds with success
    deactivate n8n
    Streamlit App->>User: Displays success message
```

### Human-in-the-Loop (HITL) & Alias Mapping Workflow

Sometimes the AI fails to match the items correctly. We need to manually correct the `matched_name` for these items in the frontend. The workflow is as follows:

1.  The user receives the processed JSON with unmatched items.
2.  They correct the `matched_name` for these items.
3.  The corrected JSON is submitted to a dedicated `Uploading Reviewed JSON` webhook in n8n. It triggers the `Update Alias` node, which calls the `/update-alias` endpoint on the Python service.
4.  Python service then updates the `product_alias.csv` with the corrected `original_name` as `alias_name`. Also, pair the `product_id` with the `alias_name`. This helps the workflow to match them in the next run.

## File Structure

```
.
├── workflow/
│   └── Invoice_Agent.json      # n8n workflow backup
├── docker-compose.yml          # Docker Compose configuration
├── DB/
│   └── product_dataset.csv     # Product database
├── utils/
│   ├── excel_converter.py      # Excel to CSV converter
│   └── prompt_converter.py     # Convert prompt to single line
├── README.md                   # This file
├── python-scripts/
│   ├── product_matching.py     # Main Flask app for product matching
│   ├── streamlit_app.py        # Streamlit UI for testing
│   ├── matching_methods/       # Product matching algorithms
│   ├── config.json.example     # Example config file
│   └── requirements.txt        # Python dependencies
└── shared/
    ├── product_db.csv          # Your master product list
    └── product_alias.csv       # Auto-generated alias list for learning
```
