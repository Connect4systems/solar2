// Copyright (c) 2026, Solar and contributors
// For license information, please see license.txt

// Keep the DocType's party-query helpers local to this script.
(() => {
    const fm_party_map = {
        'العميل': 'Customer',
        'المورد': 'Supplier',
        'الموظف': 'Employee'
    };

    const fm_apply_party_query = (frm) => {
        if (!frm.fields_dict.party) return;
        // A Dynamic Link points to the field containing the DocType name.
        frm.set_df_property('party', 'options', 'party_type');
        frm.set_query('party', () => ({
            filters: frm.doc.party_type === 'Employee'
                ? { status: 'Active' }
                : { disabled: 0 }
        }));
    };

    const fm_sync_party_type = async (frm, clear_party = false) => {
        const party_type = fm_party_map[frm.doc.custom_party_category] || null;
        fm_apply_party_query(frm);
        if (frm.doc.party && (clear_party || (frm.doc.party_type && frm.doc.party_type !== party_type))) {
            await frm.set_value('party', null);
        }
        if (frm.doc.party_type !== party_type) {
            await frm.set_value('party_type', party_type);
        }
    };

    frappe.ui.form.on('Financial Movement', {
        onload(frm) {
            return fm_sync_party_type(frm);
        },
        refresh(frm) {
            fm_apply_party_query(frm);
        },
        custom_party_category(frm) {
            return fm_sync_party_type(frm, true);
        },
        party_type(frm) {
            fm_apply_party_query(frm);
        }
    });
})();
