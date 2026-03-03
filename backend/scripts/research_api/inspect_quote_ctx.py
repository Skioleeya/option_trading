from longport.openapi import QuoteContext, Config
import os
from dotenv import load_dotenv

# Load .env if it exists
load_dotenv()

app_key = os.getenv("LONGPORT_APP_KEY")
app_secret = os.getenv("LONGPORT_APP_SECRET")
access_token = os.getenv("LONGPORT_ACCESS_TOKEN")

# Dummy config to initialize
config = Config(app_key=app_key or "xx", app_secret=app_secret or "xx", access_token=access_token or "xx")
ctx = QuoteContext(config)

print("Methods in QuoteContext:")
for method in dir(ctx):
    if not method.startswith("_"):
        print(f" - {method}")
