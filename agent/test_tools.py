from tools import health_check_tool, query_tool

print("--- Health Check ---")
print(health_check_tool())

print("\n--- Query Tool: legitimate SELECT ---")
print(query_tool("SELECT name, email FROM customers;"))

print("\n--- Query Tool: attempted DELETE (should be rejected) ---")
print(query_tool("DELETE FROM orders WHERE id = 1;"))