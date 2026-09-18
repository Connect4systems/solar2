const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");

async function check() {
    const handlers = [];
    const frappe = { ui: { form: { on: (dt, events) => handlers.push(events) } } };
    const root = path.join(__dirname, "..");
    new Function("frappe", fs.readFileSync(path.join(root,
        "solar2/solar2/doctype/financial_movement/financial_movement.js"), "utf8"))(frappe);
    const scripts = JSON.parse(fs.readFileSync(path.join(root,
        "solar2/fixtures/client_script.json"), "utf8"));
    for (const script of scripts.filter(row => row.dt === "Financial Movement" && row.enabled)) {
        new Function("frappe", script.script)(frappe);
    }
    let query;
    const properties = {};
    const frm = {
        doc: { custom_party_category: "العميل", party_type: "Customer", party: "Existing Customer" },
        fields_dict: { party: {} },
        set_df_property: (field, property, value) => { properties[`${field}.${property}`] = value; },
        set_query: (field, callback) => { assert.equal(field, "party"); query = callback; },
        async set_value(field, value) {
            this.doc[field] = value;
            if (field === "party_type") await handlers[0].party_type(this);
        },
    };
    await handlers[0].onload(frm);
    assert.equal(frm.doc.party, "Existing Customer", "Loading must preserve a valid saved party");
    for (const [category, type, filter, value] of [
        ["المورد", "Supplier", "disabled", 0],
        ["الموظف", "Employee", "status", "Active"],
        ["العميل", "Customer", "disabled", 0],
    ]) {
        frm.doc.party = "Previous party";
        frm.doc.custom_party_category = category;
        for (const events of handlers) {
            if (events.custom_party_category) await events.custom_party_category(frm);
        }
        assert.equal(frm.doc.party, null, "Changing type must clear the previous party");
        assert.equal(properties["party.options"], "party_type");
        assert.equal(frm.doc[properties["party.options"]], type, "Dynamic Link resolves the selected DocType");
        assert.equal(query().filters[filter], value);
        assert.equal(query().query, undefined, "Use the standard permission-aware link search");
    }
    frm.doc.party = "Previous party";
    frm.doc.custom_party_category = "";
    for (const events of handlers) {
        if (events.custom_party_category) await events.custom_party_category(frm);
    }
    assert.equal(frm.doc.party, null);
    assert.equal(frm.doc.party_type, null);
    console.log("PASS: customer, supplier, employee selection; saved party preservation; clearing type");
}

module.exports = check;
if (require.main === module) {
    check().catch(error => { console.error(error); process.exitCode = 1; });
}
