#!/usr/bin/env python3
from pathlib import Path
import json

APPROVALS = Path(__file__).resolve().parent.parent / 'approvals'
for p in sorted(APPROVALS.glob('*.pending.json')):
    try:
        data = json.loads(p.read_text())
        print(p.name, '-', data.get('id'), '-', data.get('type'))
    except Exception as e:
        print(p.name, '- invalid json')
