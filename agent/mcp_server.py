import os
import sys
from mcp.server.fastmcp import FastMCP

sys.path.append(os.path.dirname(__file__))
from tools import health_check_tool as real_health_check

# This creates the actual MCP server object -- "db-health-server"
# is just a name, shown to any client that connects.
mcp = FastMCP("db-health-server")


@mcp.tool()
def check_database_health() -> dict:
    """
    Checks current PostgreSQL health: connection usage percentage
    and any idle-in-transaction sessions.
    """
    return real_health_check()


if __name__ == "__main__":
    mcp.run()