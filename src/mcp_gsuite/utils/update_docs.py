import requests
import os
import sys

def update_dev_docs(
    mcp_docs_dir: str = "docs",
    fastmcp_docs_dir: str = "docs",
    mcp_docs_filename: str = "MCP_llms.txt",
    fastmcp_docs_filename: str = "FastMCP_docs.txt"
    ):
    """
    Updates the following docs from the given URLs:
    
    ### docs/MCP_llms.txt
    - Source: [https://modelcontextprotocol.io/llms-full.txt](https://modelcontextprotocol.io/llms-full.txt)
    
    ### docs/FastMCP_docs.txt
    - Source: [https://gofastmcp.com/llms-full.txt](https://gofastmcp.com/llms-full.txt)
    
    """
    mcp_docs_url = "https://modelcontextprotocol.io/llms-full.txt"
    mcp_docs_path = os.path.abspath(os.path.join(mcp_docs_dir, mcp_docs_filename))
    mcp_docs_path = os.path.join(mcp_docs_dir, mcp_docs_filename)
    
    fastmcp_docs_url = "https://gofastmcp.com/llms-full.txt"
    fastmcp_docs_path = os.path.abspath(os.path.join(fastmcp_docs_dir, fastmcp_docs_filename))
    

    try:
        # MCP_llms.txt
        response = requests.get(mcp_docs_url)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)

        # Ensure the directory exists
        os.makedirs(os.path.dirname(mcp_docs_path), exist_ok=True)
        
        with open(mcp_docs_path, "x", encoding="utf-8") as f:
            f.write(response.text)
        print(f"Successfully updated {mcp_docs_path}")

        # FastMCP_llms.txt
        response = requests.get(fastmcp_docs_url)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)

        # Ensure the directory exists
        os.makedirs(os.path.dirname(fastmcp_docs_path), exist_ok=True)

        with open(fastmcp_docs_path, "x", encoding="utf-8") as f:
            f.write(response.text)
        print(f"Successfully updated {fastmcp_docs_path}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error downloading the file: {e}")
    except IOError as e:
        print(f"Error writing to file {fastmcp_docs_path}: {e}")

if __name__ == "__main__":
    update_dev_docs()