from db import get_store
store = get_store()
for coll in ["devices", "captures", "readings", "rejections" , "forecasts"]:
    print("==", coll)
    for d in store.list_all(coll, 30):
        d.pop("frames", None)
        print(d)