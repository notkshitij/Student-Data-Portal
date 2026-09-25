# Excel Import Format

This document describes the supported Excel file format for the Student Data
Verification Portal's admin import feature.

## Overview

An administrator uploads an `.xlsx` workbook to create a new **campaign**.
Each workbook creates exactly one campaign. The system reads the headers and
rows dynamically — no code changes are needed when the Excel structure changes
between imports.

## File Structure

| Row | Purpose |
|-----|---------|
| **Row 1** | **Headers** — column/field names. Must never contain `[COLLECT]`. |
| **Row 2+** | **Student rows** — one row per student. |

## Identity Column: `Email ID*`

Every workbook **must** contain a column named `Email ID*` (case-insensitive
match).

This column identifies the student's portal login account. The importer uses
this — and only this — column to associate rows with student users.

Other columns may contain personal or contact email addresses. These are
treated as normal data fields and are **never** used as the login identity.

### Rules for `Email ID*`

| Rule | Behavior |
|------|----------|
| Missing column | Import rejected |
| Duplicate `Email ID*` headers | Import rejected |
| Empty cell | Import rejected |
| `[COLLECT]` value | Import rejected (login email cannot be collected from student) |
| Invalid email format | Import rejected |
| Domain not `poornima.edu.in` or `poornima.org` | Import rejected |
| Duplicate email within the same workbook | Import rejected |

## Dynamic Columns

Apart from `Email ID*`, all other columns are dynamic:

- Different workbooks may have **different column names**.
- Different workbooks may have **different numbers of columns**.
- The same application and database support all variations.
- Column ordering from the Excel file is preserved.

Each header becomes a `CampaignField` record. Values are stored in
`ImportedFieldValue` records — **no database columns are created** for
individual Excel fields.

## The `[COLLECT]` Marker

A data cell whose trimmed, case-insensitive value is **exactly** `[COLLECT]`
means that the student must provide this value later.

### `[COLLECT]` Rules

| Scenario | Treatment |
|----------|-----------|
| `[COLLECT]` in a data cell | Marks the field as requiring student input |
| `  [COLLECT]  ` (with whitespace) | Same as above |
| `[collect]` / `[Collect]` | Same (case-insensitive) |
| `My [COLLECT] information` | **Normal data** — not a marker |
| Header exactly `[COLLECT]` | **Import rejected** |
| Header containing `[COLLECT]` | **Import rejected** |
| `[COLLECT]` in `Email ID*` | **Import rejected** |
| Blank/empty cell | Normal data (no collection requirement inferred) |

### Per-Student Collection

Different students may have `[COLLECT]` in completely different columns.

**Example:**

| Name*          | Email ID*          | Phone       | Address   |
|----------------|--------------------|-------------|-----------|
| Student A      | a@poornima.edu.in  | `[COLLECT]` | Jaipur    |
| Student B      | b@poornima.edu.in  | 9876543210  | `[COLLECT]`|

In this example:
- Student A must provide their Phone number.
- Student B must provide their Address.

### What Happens to `[COLLECT]` Values

- `requires_student_input` is set to `true`.
- The imported value is stored as `NULL` (the `[COLLECT]` text is **not**
  stored as data).
- Student responses are stored separately and never overwrite imported values.

## Allowed Login Domains

Only these email domains are accepted for `Email ID*`:

- `poornima.edu.in`
- `poornima.org`

All other domains are rejected during import.

## Duplicate Handling

| Duplicate Type | Behavior |
|----------------|----------|
| Duplicate column headers (case-insensitive) | Import rejected |
| Duplicate `Email ID*` values within one workbook | Import rejected |

## Import Transaction Behavior

The import is **transactional**:

- All validation is performed before database writes.
- If any row fails validation, the entire import is rejected.
- No partial campaign, student, or field records are left behind on failure.

## Cell Value Handling

| Cell Type | Stored As |
|-----------|-----------|
| String | As-is |
| Integer | String (e.g., `42` → `"42"`) |
| Float (whole number, e.g. `1234.0`) | `"1234"` (no trailing `.0`) |
| Float (fractional, e.g. `8.5`) | `"8.5"` |
| Date/DateTime | ISO 8601 string |
| Formula | Cached result (openpyxl `data_only=True`) |
| Blank/None | `NULL` |

## Limits

| Limit | Default |
|-------|---------|
| Maximum file size | 10 MB |
| Maximum student rows | 10,000 |
| Maximum columns | 200 |

## User Creation

For each valid student row, the importer creates (or reuses) a `User` record:

- `role` = `STUDENT`
- `is_active` = `true`
- `google_subject_id` = `NULL` (set only when the student actually signs in)
- No password is ever generated.

A Google account does **not** receive portal access merely because it has a
Poornima domain. The account must correspond to a student already imported
through this process.

## Campaign Structure

Each import creates:

| Record | Purpose |
|--------|---------|
| `Campaign` | The data-collection campaign (status: DRAFT) |
| `CampaignField` | One per Excel column header |
| `CampaignStudent` | One per student row |
| `ImportedFieldValue` | One per student × field combination |
| `Import` | Metadata about the uploaded file |
| `AuditLog` | Record of the import action |
