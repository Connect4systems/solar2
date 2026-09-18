// Copyright (c) 2026, Solar and contributors
// For license information, please see license.txt

// Keep the DocType's party-query helpers local to this script.
(() => {
    const fm_party_map = {
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
    });
})();
