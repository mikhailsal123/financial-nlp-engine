import json
p='data/output/deep_analysis/AAPL_analysis_data_20251206_154613.json'
with open(p,'r',encoding='utf-8') as f:
    j=json.load(f)
report=j['report']['sections']['pos_neg_neutral']
print('Positives:')
for i in report.get('positives',[]):
    print('-', i.get('text','')[:200].replace('\n',' '), f'({i.get("source")},{i.get("confidence")})')
print('\nNegatives:')
for i in report.get('negatives',[]):
    print('-', i.get('text','')[:200].replace('\n',' '), f'({i.get("source")},{i.get("confidence")})')
