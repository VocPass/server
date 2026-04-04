import json

with open("school.json", "r", encoding="utf-8") as f:
    data = json.load(f)

def vision_sort_key(item):
    v = item[1].get("vision", "")
    if v == "demo":
        return (0, 0)
    if v.startswith("v"):
        try:
            return (1, int(v[1:]))
        except ValueError:
            return (1, 0)
    return (2, 0)

sorted_data = dict(sorted(data.items(), key=vision_sort_key))

with open("school.json", "w", encoding="utf-8") as f:
    json.dump(sorted_data, f, ensure_ascii=False, indent=4)

for name, info in sorted_data.items():
    print(f"  {info.get('vision', '?'):>6}  {name}")
