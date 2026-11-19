import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const root=process.cwd();
const out=process.argv[2];
const {chromium}=createRequire(root+'/package.json')('playwright-core');
let fixture;
const server=http.createServer((req,res)=>{
 if(req.method!=='GET'){res.writeHead(405);res.end();return;}
 const u=new URL(req.url,'http://localhost');
 if(u.pathname.startsWith('/api/')){res.setHeader('Content-Type','application/json');res.end(JSON.stringify(u.pathname.includes('detail')?fixture:u.pathname.includes('products')?{products:[fixture.product]}:u.pathname.includes('auth')?{user:null}:{}));return;}
 let f=path.join(root,'build',u.pathname);if(!fs.existsSync(f)||fs.statSync(f).isDirectory())f=path.join(root,'build/index.html');
 res.setHeader('Content-Type',f.endsWith('.js')?'application/javascript':f.endsWith('.css')?'text/css':f.endsWith('.woff2')?'font/woff2':'text/html');res.end(fs.readFileSync(f));
});
await new Promise(r=>server.listen(18095,'127.0.0.1',r));
const browser=await chromium.launch({executablePath:process.env.CHROME_BINARY||'/opt/google/chrome/chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const results=[];
try {
 for(const kind of ['current','historical','melted']){
  fixture=JSON.parse(fs.readFileSync(out+'/'+kind+'-ui-private.json','utf8'));
  const context=await browser.newContext({acceptDownloads:true});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const url='http://127.0.0.1:18095/scan/report?link='+encodeURIComponent(fixture.product.link);
  await page.goto(url);await page.getByRole('heading',{name:fixture.product.name,exact:true}).waitFor();
  if(await page.getByRole('button',{name:'Explore',exact:true}).isVisible()){await page.getByRole('button',{name:'Explore',exact:true}).click();await page.waitForURL('**/enter');await page.goto(url);}
  const summary=await page.getByRole('group',{name:'Product review result'}).innerText();
  if(kind==='current')assert.match(summary,/considering this product/i);
  else if(kind==='historical')assert.match(summary,/earlier|older|again/i);
  else {
   assert.match(summary,/safety concern/i);
   assert.match(await page.locator('section[aria-labelledby=reported-concerns-title]').innerText(),/safety/i);
   await page.getByRole('tab',{name:/Reviews/}).click();
   const article=page.locator('#report-evidence article').filter({hasText:'natunaw ang plug'}).first();
   const text=await article.innerText();
   assert.match(text,/natunaw ang plug/i);
   assert.match(text,/safety/i);
   assert.doesNotMatch(text,/Sentiment and product context|Review-reported signals/);
  }
  if(kind==='current'){
   await page.getByRole('tab',{name:/Reviews/}).click();
   await page.getByRole('radio',{name:/^All/}).click();
   for(const needle of ['Malakas yung hangin at hindi maingay',
       'Gumagana naman magdamag ko ginamit sa powerbank', 'kasi powerbank lng gagana na',
       'gumagana nga s powerbank', 'di sya malakas sa kuryente', 'Hindi cya malakas Kumain Ng kuryente']){
    await page.getByRole('searchbox',{name:'Filter reviews by word'}).fill(needle);
    const article=page.locator('#report-evidence article').filter({hasText:needle}).first();
    await article.waitFor();assert.equal(await article.locator('.tone-caution,.tone-safety').count(),0,needle);
   }
  }
  const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Download report',exact:true}).click();const download=await downloadPromise;
  const payload=JSON.parse(fs.readFileSync(await download.path(),'utf8'));assert.deepEqual(payload.product,fixture.product);assert(payload.exported_at);assert.equal(errors.length,0);
  if(kind==='melted'){
   const r=payload.product.comments.find(c=>c.content.includes('natunaw ang plug'));
   assert(r.sentiment_analysis.review_tags.includes('safety'));
   assert(r.sentiment_analysis.review_evidence.safety.spans.some(s=>s.text.includes('natunaw')));
   const mixed=payload.product.comments.find(c=>c.content.includes('airflow is weak'));
   assert(mixed.sentiment_analysis.review_extra_tags.includes('quality'));
   assert(mixed.sentiment_analysis.review_evidence.quality.spans.some(s=>s.text.includes('airflow')));
   const fault=payload.product.comments.find(c=>c.content.includes('keeps cutting out'));
   assert(fault.sentiment_analysis.review_tags.includes('defect'));
  }
  results.push({kind,downloaded_product_exactly_preserved:true,review_count:payload.product.comments.length,summary,browser_errors:errors});
  await context.close();
 }
 fs.writeFileSync(out+'/download-ui.json',JSON.stringify(results,null,2));console.log('CURRENT AND HISTORICAL REPORT DOWNLOADS PASSED');
}finally{await browser.close();await new Promise(r=>server.close(r));}
