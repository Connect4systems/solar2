import json
from pathlib import Path

path = Path(r'd:\2026\Apps\solar2\solar2\fixtures\client_script.json')

data = json.loads(path.read_text(encoding='utf-8'))
js = """const fm_party_map = {
    'العميل': 'Customer',
    'المورد': 'Supplier',
    'الموظف': 'Employee'
};

const fm_party_sort_field = (party_type) => {
    const map = {
        Customer: 'customer_name',
        Supplier: 'supplier_name',
        Employee: 'employee_name'
    };
    return map[party_type] || 'name';
};

const fm_apply_party_query = (frm) => {
    const party_type = frm.doc.party_type || fm_party_map[frm.doc.custom_party_category] || '';
    if (!party_type || !frm.fields_dict.party) return;

    frm.set_query('party', () => ({
        query: 'frappe.desk.search.search_link',
        doctype: party_type,
        filters: { disabled: 0 },
        order_by: `${fm_party_sort_field(party_type)} asc, name asc`,
        page_length: 200
    }));
};

frappe.ui.form.on('Financial Movement', {
    onload(frm) {
        fm_apply_party_query(frm);
    },
    refresh(frm) {
        fm_apply_party_query(frm);
    },
    custom_party_category(frm) {
        fm_apply_party_query(frm);
    },
    party_type(frm) {
        fm_apply_party_query(frm);
    }
});"""

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
