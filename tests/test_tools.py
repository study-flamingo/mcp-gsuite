import pytest
import pytest_asyncio
from typing import Any
from fastmcp import FastMCP, Client

@pytest.fixture
def mcp_server():
    """Test FastMCP instantiation"""
    server = FastMCP(
        name="TestServer",
        instructions="This is a test server.",
        version="1.0.0",
        tools=[]
        )
    
    return server    

async def test_mcp_server():
    
    server = mcp_server()
    
    @server.tool
    def greet(name: str) -> str:
        return f"Hello, {name}!"
    
    assert server.name == "TestServer"
    assert server.instructions == "This is a test server."
    assert server._mcp_server.version == "1.0.0"
    
    tools = await server.get_tools()
    
    assert len(tools) == 1
    
    tools_list = list(tools.keys())
    
    assert tools_list == ["greet"]
        
    return


async def test_tool_functionality(mcp_server):
    # Pass the server directly to the Client constructor
    async with Client(mcp_server) as client:
        result = await client.call_tool("greet", {"name": "World"})
        assert result.data == "Hello, World!"