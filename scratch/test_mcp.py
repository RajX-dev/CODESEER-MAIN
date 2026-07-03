import asyncio
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.abspath("."))

from n3mo.mcp_server import handle_list_tools, handle_call_tool

async def main():
    tools = await handle_list_tools()
    print(f"Loaded {len(tools)} tools:")
    for t in tools:
        print(f"- {t.name}")
        
    print("\nTesting n3mo_search_symbol:")
    try:
        res = await handle_call_tool("n3mo_search_symbol", {"symbol_name": "TensorShape"})
        print(res[0].text)
    except Exception as e:
        print("Error:", e)

    print("\nTesting n3mo_get_dependencies:")
    try:
        res = await handle_call_tool("n3mo_get_dependencies", {"symbol_name": "TensorShape"})
        print(res[0].text)
    except Exception as e:
        print("Error:", e)
        
    print("\nTesting n3mo_get_file_symbols:")
    try:
        res = await handle_call_tool("n3mo_get_file_symbols", {"file_path": "tensor_shape"})
        print(res[0].text)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
