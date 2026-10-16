'use strict';
/* Editorial text renderer: appended to the existing, otherwise unchanged app.js. */
(function(){
  const oldRender = renderStories, oldLoad = loadIssue;
  const editorialFile = 'berichte/redaktionell-2026-10-16.json';
  function textnode(tag, value, klass=''){
    const n=document.createElement(tag); if(klass)n.className=klass; n.textContent=value; return n;
  }
  function inline(parent, raw){
    const rx=/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|\*\*([^*]+)\*\*|\*([^*]+)\*/g;
    let m,last=0;
    while((m=rx.exec(raw))){
      if(m.index>last)parent.append(document.createTextNode(raw.slice(last,m.index)));
      if(m[1]){
        const a=textnode('a',m[1]);a.href=m[2];a.target='_blank';a.rel='noopener noreferrer';parent.append(a);
      }else if(m[3]) parent.append(textnode('strong',m[3]));
      else parent.append(textnode('em',m[4]));
      last=rx.lastIndex;
    }
    if(last<raw.length)parent.append(document.createTextNode(raw.slice(last)));
  }
  function renderMarkdown(target, value){
    const lines=String(value||'').split(/\r?\n/);
    let p=[],table=[];
    const flushP=()=>{if(p.length){const e=document.createElement('p');inline(e,p.join(' '));target.append(e);p=[];}};
    const flushTable=()=>{
      if(!table.length)return;
      const t=document.createElement('table');t.className='editorial-table';
      table.forEach((row,i)=>{
        if(i===1&&row.every(v=>/^:?-{2,}:?$/.test(v)))return;
        const tr=document.createElement('tr');
        for(const v of row){const c=document.createElement(i===0?'th':'td');inline(c,v);tr.append(c);}
        t.append(tr);
      });target.append(t);table=[];
    };
    for(const line of lines){
      const s=line.trim();
      if(s.startsWith('|')&&s.endsWith('|')){flushP();table.push(s.slice(1,-1).split('|').map(c=>c.trim()));continue;}
      flushTable();
      if(!s){flushP();continue;}
      if(s==='---'){flushP();continue;}
      const h=/^(#{1,5})\s+(.+)$/.exec(s);
      if(h){flushP();const level=Math.max(3,Math.min(5,h[1].length+1));const e=document.createElement('h'+level);inline(e,h[2]);target.append(e);continue;}
      const item=/^[-*]\s+(.+)$/.exec(s);
      if(item){flushP();const last=target.lastElementChild;const ul=last?.tagName==='UL'?last:document.createElement('ul');if(ul!==last)target.append(ul);const li=document.createElement('li');inline(li,item[1]);ul.append(li);continue;}
      p.push(s);
    }
    flushP();flushTable();
  }
  function sourcesFrom(report){
    const entries=report.linked_sources||report.quellen||report.sources||[];
    const seen=new Set(),out=[];
    for(const src of entries){if(!src||!validUrl(src.url)||seen.has(src.url))continue;seen.add(src.url);out.push(src);}
    return out;
  }
  function sectionCard(label,markdown){
    const article=textnode('section','','story');
    article.append(textnode('h3',label,'section-heading'));
    renderMarkdown(article,markdown);return article;
  }
  function sectionsFromOriginal(markdown){
    const chunks=String(markdown).split(/^#\s+(\d+)\.\s+(.+)$/m);
    const out=[];
    for(let i=1;i+2<chunks.length;i+=3)out.push({number:Number(chunks[i]),title:chunks[i+1],markdown:chunks[i+2]});
    return out;
  }
  function renderEditorial(){
    const root=$('stories');root.replaceChildren();const report=selected;
    if(!report)return oldRender();
    let sections=Array.isArray(report.sections)?report.sections:sectionsFromOriginal(report.original_markdown);
    if(!sections.length)return oldRender();
    const original=report.original_markdown||'';
    const intro=original.split(/^#\s+1\.\s+/m)[0];
    if(active.has('zusammenfassung')&&intro){
      const match=intro.indexOf('## Das Wichtigste im Überblick');
      if(match!==-1){
        const before=intro.slice(0,match).replace(/^#\s+.*$/m,'').replace(/^\*\*.*?\*\*\s*$/gm,'').trim();
        if(before){const lead=textnode('section','','story');renderMarkdown(lead,before);root.append(lead);}
        root.append(sectionCard('Das Wichtigste im Überblick',intro.slice(match).replace(/^## Das Wichtigste im Überblick\s*/,'')));
      }
    }
    const ids=['international','deutschland','europa','wissenschaft','ki','umwelt'];
    for(const section of sections){
      const id=ids[section.number-1];if(!id||!active.has(id))continue;
      const block=sectionCard(section.title,String(section.markdown||'').replace(/^---\s*$/gm,''));
      root.append(block);
    }
    const total=sections.find(x=>x.number===7);
    if(total){
      const subs=total.subsections||[];
      if(subs.length){
        const sections7=[['gesamtbewertung','Gesamtbewertung des Tages',subs.slice(0,-2)],['ausblick','Worauf in den kommenden Tagen besonders zu achten ist',subs.slice(-2,-1)],['zusammenfassung','Fazit',subs.slice(-1)]];
        for(const [id,name,parts] of sections7){
          if(!active.has(id)||!parts.length)continue;
          const content=parts.map(x=>'## '+x.title+'\n\n'+x.markdown).join('\n\n');
          root.append(sectionCard(name,content));
        }
      }else if(active.has('gesamtbewertung')){
        root.append(sectionCard('Gesamtbewertung des Tages',total.markdown));
      }
    }
    if(active.has('quellen')){
      const sources=sourcesFrom(report);
      if(sources.length){
        const card=sectionCard('Quellen','');
        const ul=document.createElement('ul');
        sources.forEach(src=>{const li=document.createElement('li');const a=textnode('a',src.label||src.url);a.href=src.url;a.target='_blank';a.rel='noopener noreferrer';li.append(a);ul.append(li);});
        card.append(ul);root.append(card);
      }
    }
    if(!root.childNodes.length)root.append(textnode('div','Für diese Auswahl enthält die Ausgabe keine Inhalte.','empty'));
  }
  renderStories=function(){if(selected?.original_markdown)renderEditorial();else oldRender();};
  loadIssue=async function(date){
    if(date!=='2026-10-16')return oldLoad(date);
    try{
      const response=await fetch(editorialFile,{cache:'no-store'});
      if(!response.ok)throw Error('Redaktionelle Ausgabe nicht verfuegbar');
      const data=await response.json();
      if(data.date!==date||!data.original_markdown||!Array.isArray(data.sections))throw Error('Redaktionelle Ausgabe ungueltig');
      selected=data;
      $('issue-date').textContent=formatDate(date);
      $('issue-status').textContent='Veröffentlicht';
      $('edition-label').textContent=formatDate(date);
      $('report-heading').textContent='Täglicher Themenüberblick · '+formatDate(date);
      renderStories();
    }catch(err){console.error('Redaktionelle Ausgabe nicht geladen:',err);oldLoad(date);}
  };
})();
