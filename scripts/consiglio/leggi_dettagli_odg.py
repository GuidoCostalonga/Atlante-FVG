import json,re,html,sys,time,urllib.request
ids=json.load(open(sys.argv[1])); out_f=sys.argv[2]
out=json.load(open(out_f)) if len(sys.argv)>3 and sys.argv[3]=='--continua' else {}
UA={'User-Agent':'AtlanteFVG/1.0 (+https://atlantefvg.it/)'}
pul=lambda x: html.unescape(re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',x))).strip()
def tab(s,nome):
    m=re.search(r'<table id="ContentPlaceHolder1_%s"[^>]*>(.*?)</table>'%nome,s,re.S); return m.group(1) if m else ''
n=0
for url,info in ids.items():
    if url in out: continue
    try: s=urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=60).read().decode('utf-8','ignore')
    except Exception as e: print('errore',url[-50:],e); continue
    d={'url':url,'lista':info}
    testa=pul(tab(s,'T_intestazioneODG'))
    m=re.search(r'Odg su (.*?) - (\d+)\s+(.*)$',testa); d['oggetto']=m.group(1).strip() if m else ''; d['numero']=int(m.group(2)) if m else None; d['titolo']=m.group(3).strip() if m else testa
    prov=tab(s,'T_provvedimento_riferimentoODG'); pt=pul(prov)
    m=re.search(r'Progetto N° ?(\d+)',pt); d['ddl']=m.group(1) if m else ''
    m=re.search(r'Legge: N°\s*(\d+/\d{4})',pt); d['legge']=m.group(1) if m else ''
    m=re.search(r'href="(https?://[^"]+\.pdf)"',prov); d['allegato']=m.group(1) if m else ''
    m=re.search(r'Data presentazione:\s*(\d\d/\d\d/\d{4})',pt); d['data']=m.group(1) if m else ''
    d['esito']=pul(tab(s,'T_Esito_votazioneODG')).replace('Esito votazione','').strip()
    pres=tab(s,'T_PresentatoreODG'); d['proponenti']=[x.strip().upper() for x in re.findall(r'<a id="ContentPlaceHolder1_\d+PR\d+"[^>]*title="([^"]+)"',pres)]
    d['relatori']=pul(re.search(r'id="ContentPlaceHolder1_RelatoriAppoggianti">(.*?)</div>',pres,re.S).group(1)) if 'RelatoriAppoggianti' in pres else ''
    d['invio']=pul(tab(s,'T_Invio_competentiODG')).replace('Invio ai soggetti competenti per il seguito','').strip()
    d['note']=pul(tab(s,'T_noteODG')).replace('Note','',1).strip()
    out[url]=d; n+=1
    if n%25==0: json.dump(out,open(out_f,'w'),ensure_ascii=False,indent=0); print(n,'letti',time.strftime('%H:%M:%S'),flush=True)
    time.sleep(0.3)
json.dump(out,open(out_f,'w'),ensure_ascii=False,indent=0); print('totale',len(out))
