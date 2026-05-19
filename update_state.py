import json

# Read portfolio_state.json
with open('portfolio_state.json', 'r', encoding='utf-8') as f:
    content = f.read()
    # Replace NaN with 0.0 manually if still there
    content = content.replace('NaN', '0.0')
    portfolio_data = json.loads(content)

# Create fresh fenerbahce state
fenerbahce_state = {
    "assets": [],
    "debts": [],
    "net_history": [],
    "cashflow_base_date": "2026-01-31",
    "baseline_date": "2026-04-17",
    "baseline_net": 0.0,
    "interest_last_date": "2026-04-17",
    "saved_at": "2026-05-01T12:00:00"
}

# Update assets with Yıllık Faiz (%) field
for asset in portfolio_data.get('assets', []):
    updated_asset = asset.copy()
    if 'Yıllık Faiz (%)' not in updated_asset:
        updated_asset['Yıllık Faiz (%)'] = 0.0
    fenerbahce_state['assets'].append(updated_asset)

# Update debts
fenerbahce_state['debts'] = portfolio_data.get('debts', [])

# Write back
with open('user_data/fenerbahce/state.json', 'w', encoding='utf-8') as f:
    json.dump(fenerbahce_state, f, ensure_ascii=False, indent=2)

print("✓ Updated successfully")
print(f"Assets: {len(fenerbahce_state['assets'])}")
print(f"Debts: {len(fenerbahce_state['debts'])}")
