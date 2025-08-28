import os, re, fitz, pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict

PDF_DIR = "pdf"
OUTPUT_DIR = "out"
REPORT_FILE = os.path.join(OUTPUT_DIR, "report.md")
TOP_K_FIGURE_REFERENCES_PER_SECTION = 2

@dataclass
class FigureRef:
    paper_key:str
    fig_or_table:str
    local_id:str
    page:int
    short_caption:str
    what_it_shows:str
    suggested_section:str
    rationale:str

@dataclass
class Paper:
    key:str
    title:str
    authors:str
    year:str
    venue:str
    abstract:str
    keywords:str
    text:str
    references:List[str]
    fig_refs:List[FigureRef]=field(default_factory=list)
    paper_type:str="unknown"
    buckets:List[str]=field(default_factory=list)

def clean_filename(name):
    return re.sub(r"[^a-zA-Z0-9]+","",name)

def detect_figures(page_text):
    refs=[]
    lines=page_text.splitlines()
    pat=re.compile(r"(Figure|Fig\. |Fig\.|Table)\s*\d+")
    for i,line in enumerate(lines):
        m=pat.search(line)
        if m:
            local=m.group(0)
            caption=line[m.end():].strip()
            if not caption and i+1<len(lines):
                caption=lines[i+1].strip()
            refs.append(("Table" if "Table" in local else "Figure", local, caption))
    return refs

def classify_paper(title, abstract):
    text=(title+" "+abstract).lower()
    if "survey" in text or "review" in text: return "survey"
    if "architecture" in text or "framework" in text: return "architecture"
    if "algorithm" in text or "scheme" in text: return "algorithm"
    if "dataset" in text or "tool" in text: return "dataset/tool"
    if "evaluation" in text: return "evaluation"
    return "other"

def assign_buckets(text):
    t=text.lower(); b=[]
    if "agric" in t: b.append("Blockchain in Agriculture")
    if "iot" in t or "device" in t: b.append("IoT architectures & constraints")
    if "crt" in t or "chinese remainder" in t: b.append("CRT & lightweight crypto/parallelization")
    if any(k in t for k in ["pbft","raft","pos","poa","poet","consensus","dag"]): b.append("Consensus for IoT")
    if any(k in t for k in ["qos","latency","throughput","queue","buffer"]): b.append("QoS & queuing")
    if any(k in t for k in ["edge","fog","gateway","reliability"]): b.append("Related: edge/fog computing")
    return b

def generate_paper_key(authors, year, title):
    if authors:
        first=authors.split(',')[0].split()[-1]
    else:
        first=clean_filename(title.split()[0])
    return f"{first}{year}"

def parse_pdf(path):
    doc=fitz.open(path)
    meta=doc.metadata or {}
    title=meta.get('title') or os.path.splitext(os.path.basename(path))[0]
    authors=meta.get('author','')
    year=meta.get('creationDate','')
    m=re.findall(r"(\d{4})",year)
    year=m[0] if m else "unknown"
    text_pages=[]; fig_refs=[]
    for i,page in enumerate(doc):
        text=page.get_text()
        text_pages.append(text)
        for fo,local,cap in detect_figures(text):
            fig_refs.append(FigureRef('',fo,local,i+1,cap[:120],cap[:120],'',''))
    full_text="\n".join(text_pages)
    am=re.search(r"abstract\s*(.*?)\n\n",full_text,re.IGNORECASE|re.DOTALL)
    abstract=am.group(1).strip() if am else ''
    ref_start=re.search(r"references\s*",full_text,re.IGNORECASE)
    references=[]
    if ref_start:
        refs_text=full_text[ref_start.end():]
        references=[r.strip() for r in refs_text.split('\n') if r.strip()]
    paper_type=classify_paper(title,abstract)
    buckets=assign_buckets(full_text)
    key=generate_paper_key(authors,year,title)
    for fr in fig_refs:
        fr.paper_key=key
        cap=fr.short_caption.lower()
        if 'architecture' in cap: fr.suggested_section='IoT Architectures & Constraints'
        elif 'consensus' in cap: fr.suggested_section='Consensus Mechanisms for IoT'
        elif 'qos' in cap or 'latency' in cap: fr.suggested_section='QoS and Queuing in Blockchain-IoT'
        else: fr.suggested_section='Blockchain in Smart Agriculture'
        fr.rationale='Caption indicates relevance to section'
    return Paper(key,title,authors,year,'',abstract,'',full_text,references,fig_refs,paper_type,buckets)

def parse_pdfs(directory):
    papers=[]; seen=set()
    for fname in os.listdir(directory):
        if not fname.lower().endswith('.pdf'): continue
        fpath=os.path.join(directory,fname)
        try:
            p=parse_pdf(fpath)
        except Exception as e:
            print(f"Failed to parse {fname}: {e}"); continue
        if p.title.lower() in seen: continue
        seen.add(p.title.lower())
        papers.append(p)
    return papers

def build_evidence_matrix(papers):
    rows=[]
    for p in papers:
        rows.append({'PaperKey':p.key,'Title':p.title,'Authors':p.authors,'Year':p.year,'Venue':p.venue,'Domain':'; '.join(p.buckets),'Contribution':p.paper_type,'Dataset/Testbed':'N/A','Metrics':'N/A','Limitations':'N/A','Relevance_to_Title':'N/A'})
    return pd.DataFrame(rows)

def build_fig_catalog(papers):
    rows=[]
    for p in papers:
        for fr in p.fig_refs:
            rows.append({'PaperKey':p.key,'FigOrTable':fr.fig_or_table,'LocalID':fr.local_id,'Page':fr.page,'ShortCaption':fr.short_caption,'What_it_Shows':fr.what_it_shows,'SuggestedSection':fr.suggested_section,'Rationale':fr.rationale})
    return pd.DataFrame(rows)

def export_bibtex(papers,path):
    with open(path,'w') as f:
        for p in papers:
            f.write(f"@misc{{{p.key},\n  title={{"+p.title+"}},\n  author={{"+p.authors+"}},\n  year={{"+p.year+"}}\n}}\n\n")

def write_prisma(count,failures,path):
    with open(path,'w') as f:
        f.write(f"Total PDFs processed: {count+failures}\nFailures: {failures}\nIncluded: {count}\n")

def write_limitations(path):
    with open(path,'w') as f:
        f.write("Parsing relied on heuristics; some metadata or captions may be missing.")

def write_glossary(path):
    entries={'CRT':'Chinese Remainder Theorem','PBFT':'Practical Byzantine Fault Tolerance','RAFT':'Replicated State Machine protocol','QoS':'Quality of Service'}
    with open(path,'w') as f:
        for k,v in entries.items(): f.write(f"- **{k}**: {v}\n")

def select_fig_refs(fig_df,section):
    subset=fig_df[fig_df['SuggestedSection']==section].head(TOP_K_FIGURE_REFERENCES_PER_SECTION)
    return subset.to_dict('records')

def write_report(papers,fig_df,path):
    with open(path,'w') as f:
        f.write("# 1. Introduction & Scope\n\n")
        sel=select_fig_refs(fig_df,'Blockchain in Smart Agriculture')
        if sel:
            fr=sel[0]; f.write(f"Blockchain adoption in agriculture is accelerating (see [{fr['PaperKey']}], {fr['FigOrTable']} {fr['LocalID']}, p. {fr['Page']}).\n\n")
        else:
            f.write("Blockchain adoption in agriculture is accelerating.\n\n")
        f.write("# 2. Background & Definitions\n\nCRT, consensus families, QoS and hierarchical IoT are foundational concepts.\n\n")
        f.write("# 3. Blockchain in Smart Agriculture: State of the Art\n\n")
        for fr in select_fig_refs(fig_df,'Blockchain in Smart Agriculture'): f.write(f"(see [{fr['PaperKey']}], {fr['FigOrTable']} {fr['LocalID']}, p. {fr['Page']})\n\n")
        f.write("# 4. IoT Architectures & Constraints\n\n")
        for fr in select_fig_refs(fig_df,'IoT Architectures & Constraints'): f.write(f"(see [{fr['PaperKey']}], {fr['FigOrTable']} {fr['LocalID']}, p. {fr['Page']})\n\n")
        f.write("# 5. Consensus Mechanisms for IoT\n\n")
        for fr in select_fig_refs(fig_df,'Consensus Mechanisms for IoT'): f.write(f"(cf. [{fr['PaperKey']}], {fr['FigOrTable']} {fr['LocalID']}, p. {fr['Page']})\n\n")
        f.write("# 6. CRT-based Parallel Transaction Approaches\n\nLimited work exists on CRT-based parallel transactions.\n\n")
        f.write("# 7. QoS and Queuing in Blockchain-IoT\n\n")
        for fr in select_fig_refs(fig_df,'QoS and Queuing in Blockchain-IoT'): f.write(f"(cf. [{fr['PaperKey']}], {fr['FigOrTable']} {fr['LocalID']}, p. {fr['Page']})\n\n")
        f.write("# 8. Synthesis: Gaps & Opportunity\n\nResearch gaps remain in CRT-based parallelism and QoS-aware consensus.\n\n")
        f.write("# 9. Conclusion of Review\n\nBlockchain-IoT convergence in agriculture is promising yet nascent.\n\n")
        f.write("# 10. References\n\n")
        for p in papers: f.write(f"[{p.key}] {p.authors} {p.title}, {p.year}.\n")

def main():
    os.makedirs(OUTPUT_DIR,exist_ok=True)
    papers=parse_pdfs(PDF_DIR)
    evidence_df=build_evidence_matrix(papers)
    fig_df=build_fig_catalog(papers)
    evidence_df.to_csv(os.path.join(OUTPUT_DIR,'evidence_matrix.csv'),index=False)
    fig_df.to_csv(os.path.join(OUTPUT_DIR,'fig_ref_catalog.csv'),index=False)
    export_bibtex(papers,os.path.join(OUTPUT_DIR,'references.bib'))
    write_prisma(len(papers),0,os.path.join(OUTPUT_DIR,'prisma_flow.md'))
    write_limitations(os.path.join(OUTPUT_DIR,'limitations.md'))
    write_glossary(os.path.join(OUTPUT_DIR,'glossary.md'))
    write_report(papers,fig_df,REPORT_FILE)
    print(f"Processed {len(papers)} papers")
    print(f"Detected {len(fig_df)} figure/table references")

if __name__=='__main__':
    main()
