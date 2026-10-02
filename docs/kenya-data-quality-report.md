# Kenya/Nairobi Data Quality Report

Measured against an isolated SQLite database after migration and idempotent seed on 2026-09-30. This is a Kenya/Nairobi real-world reference dataset with synthetic operational data.

## SOURCE-VERIFIED REFERENCE DATA

- **Facilities:** 9 of 9 have [KMHFR](https://kmhfr.health.go.ke/public/about) record URLs and identifiers. Ownership: 6 Ministry of Health, 3 private practice. KEPH levels: three Level 4, four Level 5, two Level 6. Six public facilities are configured for the prototype transfer network; the three private facilities are reference context only.
- **Medicines:** 51 distinct name/form/strength combinations, all with KEML section and source link in the [Kenya Essential Medicines List 2023](https://extranet.who.int/cpcd/sites/default/files/public_file_repository/KEN_Kenya_Kenya-Essential-Medicines-List-2023_2023.pdf). Category counts: analgesics 5; antimicrobials 12; antimalarials 3; cardiovascular 6; diabetes 4; gastrointestinal 5; respiratory 3; maternal/newborn 4; mental health 4; emergency 2; dermatological 3. AWaRe was verified for 5 entries; null classifications are not inferred.
- **Supplier identity:** [KEMSA's official site](https://kemsa.go.ke/) verifies the organization name only. The seeded order is synthetic.
- **Provenance:** KMHFR, KEML and KEMSA references were retrieved on 2026-09-30. Each facility and medicine stores its source metadata. The Aga Khan registry/website naming discrepancy and Pumwani maternity-bed registry value are retained in facility notes.

## SYNTHETIC DEMONSTRATION DATA

- **Consumption:** 90,520 daily observations from 2025-10-01 through 2026-09-30, covering 248 medicine–facility series across six facilities. Deterministic seed: 20260930.
- **Inventory:** 248 deliberate historical stockout intervals, with receipts and adjustments recorded in the transaction ledger. Every tested balance equals the signed sum of its ledger transactions.
- **Redistribution:** 4 configured scenario types; 3 persisted recommendations and 1 completed synthetic transfer with approval, dispatch, receipt and audit entries. The no-donor case returns NO_FEASIBLE_DONOR; the Oxytocin recommendation respects donor safety stock.
- **Users:** 6 invented demo personas: 4 Inventory Officers, 1 Supply Chain Manager, 1 Administrator. Facility assignments: Kenyatta National Hospital 2; Mbagathi, Mama Lucy, Pumwani and Mathari 1 each. All have non-deliverable .example email addresses and explicit demo flags.

No patient table or patient-identifying information is present. Inventory, consumption, procurement, staff personas and transfer activity are simulated, not live hospital data.
