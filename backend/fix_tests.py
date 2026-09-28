import re

with open("tests/test_import_excel.py", "r") as f:
    content = f.read()

# Replace all manual calls to /api/admin/import
content = re.sub(
    r'client\.post\(\s*"/api/admin/import",\s*data=\{"campaign_name": "[^"]+"\},',
    r'client.post( "/api/admin/campaigns/00000000-0000-0000-0000-000000000000/import",',
    content
)
with open("tests/test_import_excel.py", "w") as f:
    f.write(content)
