# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"D:\WorkBuddyData\projects\agent-learning"


def show(p, keys_only=False):
    d = json.load(open(p, encoding="utf-8"))
    print("==", p.split("\\")[-1], "==")
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, (int, float, str)):
                print("  %s = %s" % (k, v))
            elif isinstance(v, list):
                print("  %s: list(%d)" % (k, len(v)))
    else:
        print("  list(%d)" % len(d))
        if d and isinstance(d[0], dict):
            ks = list(d[0].keys())
            print("  item keys:", ks)
            for key in ("score2", "score_aligned_k6", "score_fixed"):
                if key in ks:
                    vals = [x.get(key) for x in d if isinstance(x.get(key), (int, float))]
                    if vals:
                        print("  avg(%s) = %.4f (n=%d)" % (key, sum(vals) / len(vals), len(vals)))


show(BASE + r"\w6_eval_aligned_summary.json")
show(BASE + r"\w6_eval_final_k6.json")
