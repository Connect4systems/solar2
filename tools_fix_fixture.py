import json
from pathlib import Path

root = Path(__file__).resolve().parent
path = root / 'solar2/fixtures/client_script.json'

data = json.loads(path.read_text(encoding='utf-8'))
# Reuse the scoped DocType script rather than injecting duplicate top-level constants.
js = (root / 'solar2/solar2/doctype/financial_movement/financial_movement.js').read_text(encoding='utf-8')

for item in data:
    if item.get('doctype') == 'Client Script' and item.get('dt') == 'Financial Movement':
        script = item.get('script', '')
        if 'fm_apply_party_query' in script:
            print('Already contains fm_apply_party_query')
            break
        if "frappe.ui.form.on('Financial Movement', {" in script:
            script = script.replace("frappe.ui.form.on('Financial Movement', {", js + "\n\nfrappe.ui.form.on('Financial Movement', {", 1)
        else:
            script = script + "\n\n" + js
        item['script'] = script
        print('Updated Financial Movement fixture entry.')
        break
else:
    raise RuntimeError('Financial Movement Client Script entry not found')

path.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding='utf-8')
print('JSON_OK')
