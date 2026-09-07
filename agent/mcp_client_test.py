import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    # This describes HOW to start the server -- as a subprocess,
    # running our mcp_server.py file with the same Python
    # interpreter currently running this script.
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # This is the actual MCP handshake -- the client
            # introduces itself to the server and negotiates
            # the protocol version.
            await session.initialize()

            # Ask the server: "what tools do you actually offer?"
            tools_response = await session.list_tools()
            print("Tools the server exposes:")
            for tool in tools_response.tools:
                print(f"  - {tool.name}: {tool.description}")

            # Now genuinely CALL the tool, over the real protocol
            result = await session.call_tool("check_database_health", arguments={})
            print("\nReal result from calling the tool via MCP:")
            print(result.content)


if __name__ == "__main__":
    asyncio.run(main())