import glob, json
files = glob.glob('data/output/news_articles/AAPL/*.json')
for f in sorted(files):
    j = json.load(open(f,'r',encoding='utf-8'))
    h = j.get('metadata',{}).get('headline')
    s = j.get('metadata',{}).get('source')
    print(f.split('\\')[-1],'|',s,'|',h)
