# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = json.load(open(r"D:\WorkBuddyData\projects\agent-learning\w6_eval_set_aligned.json", encoding="utf-8"))
print(type(d).__name__)
if isinstance(d, dict):
    print("keys:", list(d.keys()))
    for k, v in d.items():
        if isinstance(v, list):
            print(k, "->list", len(v))
            if v:
                print("item0 keys:", list(v[0].keys()))
                print("item0:", json.dumps(v[0], ensure_ascii=False)[:400])
        else:
            print(k, "=", str(v)[:200])
else:
    print("len", len(d))
    print("item0:", json.dumps(d[0], ensure_ascii=False)[:400])
