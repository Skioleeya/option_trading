from longport.openapi import Period, AdjustType

def list_enum(cls):
    print(f"\nMembers in {cls.__name__}:")
    for name in dir(cls):
        if not name.startswith("_"):
            print(f" - {name}")

list_enum(Period)
list_enum(AdjustType)
