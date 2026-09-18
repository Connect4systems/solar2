const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");

const rows = JSON.parse(fs.readFileSync(
    path.join(__dirname, "../solar2/fixtures/client_script.json"), "utf8"
));
const groups = new Map();
for (const row of rows) {
    new Function(row.script);
    if (!row.enabled) continue;
    const key = `${row.dt}/${row.view}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row.script);
}
for (const scripts of groups.values()) new Function(scripts.join("\n"));

for (const dt of ["Financial Movement", "Sales Invoice", "Purchase Invoice",
    "Account Statement", "Sales Order", "Purchase Order"]) {
    const registrations = [];
    const frappe = { ui: { form: { on: (target, handlers) => {
        assert.equal(target, dt, `Unexpected cross-form handler from ${dt}`);
        registrations.push(handlers);
    } } } };
    new Function("frappe", "setTimeout", groups.get(`${dt}/Form`).join("\n"))(frappe, () => {});
    assert.ok(registrations.length > 0);
    if (dt === "Sales Invoice" || dt === "Purchase Invoice") {
        assert.equal(registrations.filter(handlers => handlers.validate).length, 1,
            `Project synchronization registered more than once for ${dt}`);
    }
    if (dt === "Financial Movement") {
        const labels = {};
        const labelHandler = registrations.find(handlers => !handlers.validate);
        labelHandler.onload({
            fields_dict: { movement_type: {}, amount: {}, company: {} },
            set_df_property: (field, property, value) => { labels[field] = value; },
        });
        assert.equal(labels.movement_type, "نوع العملية");
        assert.equal(labels.amount, "القيمة");
        assert.equal(labels.company, "الشركة");
    }
}
console.log(`PASS: ${rows.length} scripts, ${groups.size} groups, form registrations and Arabic labels`);
