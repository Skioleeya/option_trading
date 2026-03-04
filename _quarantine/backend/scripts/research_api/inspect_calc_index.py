import longport.openapi as lp
import os
from dotenv import load_dotenv

print("Constants/Enums in longport.openapi:")
for name in dir(lp):
    if "Index" in name or "Calc" in name:
        print(f" - {name}")
        try:
            val = getattr(lp, name)
            if isinstance(val, type) and issubclass(val, (int, float, str)):
                print(f"   Value: {val}")
            elif hasattr(val, '__members__'):
                print(f"   Members: {list(val.__members__.keys())}")
        except:
            pass
