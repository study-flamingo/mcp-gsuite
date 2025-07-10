"""Helper utility for updating development documentation pulled from online sources."""

import requests
import os
import json
import traceback

DOCS_DIR = os.path.join(os.path.dirname(__file__), "../../../docs")


def update_dev_docs():
    """
    Updates the following docs from the given URLs:
    
    ### docs/MCP_llms.txt
    - Source: [https://modelcontextprotocol.io/llms-full.txt](https://modelcontextprotocol.io/llms-full.txt)
    
    ### docs/FastMCP_docs.txt
    - Source: [https://gofastmcp.com/llms-full.txt](https://gofastmcp.com/llms-full.txt)
    
    """
    global DOCS_DIR
    docs_dir = os.path.normpath(DOCS_DIR)
    
    
    # Ensure the docs directory exists
    os.makedirs(docs_dir, exist_ok=True)

    docs: dict = {}
    # Load settings
    try:
        with open(os.path.join(os.path.dirname(__file__), "docs.json"), "r") as f:
            docs = json.load(f)
        print("Successfully loaded docs.json 🎉")
    except FileNotFoundError:
        print(f"No docs.json found in {docs_dir}! Create a docs.json file with the following format:")
        print("""
    {
        "docs":
        [
            {
                "title": "<title of the doc>"
                "url": "<url of the doc>"
            },
            add more...
        ]
}
            """)
        exit(1)
    except Exception as e:
        print(f"Error loading docs.json: {e}")
        print(traceback.format_exc()) # For full traceback
        exit(1)

    print(f"Found settings for {len(docs.get('docs', []))} docs to update")

    # Download the docs
    for doc_item in docs.get("docs", []):
        name = doc_item.get("title")
        url = doc_item.get("url")
        
        if not name or not url:
            print(f"Skipping malformed doc entry: {doc_item}")
            continue

        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)

            doc_filepath = os.path.join(docs_dir, name)
            
            with open(doc_filepath, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"Successfully updated {doc_filepath}")
        except requests.exceptions.RequestException as e:
            print(f"Error downloading the file: {e}")
        except IOError as e:
            print(f"Error writing to file {doc_filepath}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            print(traceback.format_exc())

if __name__ == "__main__":
    update_dev_docs()
    