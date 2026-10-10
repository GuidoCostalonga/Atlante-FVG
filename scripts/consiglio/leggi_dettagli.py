import json,re,html,sys,time,urllib.request
ids=json.load(open(sys.argv[1])); out_f=sys.argv[2]
out=json.load(open(out_f)) if len(sys.argv)>3 and sys.argv[3]=='--continua' else {}
UA={'User-Agent':'AtlanteFVG/1.0 (+https://atlantefvg.it/)'}
def campo(s,tab):
    m=re.search(r'id="ContentPlaceHolder1_%s".*?</td>\s*<td[^>]*>(.*?)</td>'%tab,s,re.S)
    return html.unescape(re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',m.group(1)))).strip() if m else ''
n=0
for url,info in ids.items():
    if url in out: continue
    try:
        s=urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=60).read().decode('utf-8','ignore')
    except Exception as e:
        print('errore',url[-60:],e); continue
    d={'url':url,'lista':info}
    d['numero']=campo(s,'lbl_Numero') or (re.search(r'id="ContentPlaceHolder1_lbl_Numero">([^<]*)<',s) or [None,''])[1]
    m=re.search(r'id="ContentPlaceHolder1_lbl_Numero">([^<]*)<',s); d['numero']=html.unescape(m.group(1)).strip() if m else ''
    for k,tab in [('titolo','T_Titolo'),('data','T_data_presentazione'),('proponenti','T_Presentatore'),('assessore','T_assessore'),('testo','T_testo_mozione')]:
        d[k]=campo(s,tab)
    d['proponenti']=[x.strip(' ,') for x in re.findall(r'title="([^"]+)"[^>]*>[^<]*</a>',re.search(r'id="ContentPlaceHolder1_PanelPresentatori">(.*?)</div>',s,re.S).group(1))] if 'PanelPresentatori' in s else []
    m=re.search(r'href="(https://www\.consiglio\.regione\.fvg\.it/pagineinterne/Portale/Attivita/GestDoc\.aspx\?idP=\d+)"',s); d['allegato']=m.group(1) if m else ''
    # tutte le altre tabelle con etichetta in grassetto: esito, seduta, note
    altre={}
    for m in re.finditer(r'<table id="ContentPlaceHolder1_(T_[A-Za-z_]+)"[^>]*>.*?<td[^>]*font-weight:bold[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>',s,re.S):
        if m.group(1) in ('T_Titolo','T_data_presentazione','T_Presentatore','T_assessore','T_testo_mozione'): continue
        altre[m.group(1)]=[html.unescape(re.sub('<[^>]+>',' ',m.group(2))).strip(), html.unescape(re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',m.group(3)))).strip()[:300]]
    d['altre']=altre
    out[url]=d; n+=1
    if n%20==0: json.dump(out,open(out_f,'w'),ensure_ascii=False,indent=0); print(n,'letti',time.strftime('%H:%M:%S'))
    time.sleep(0.4)
json.dump(out,open(out_f,'w'),ensure_ascii=False,indent=0); print('totale',len(out))
