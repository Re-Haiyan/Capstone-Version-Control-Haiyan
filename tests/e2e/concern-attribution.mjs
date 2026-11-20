// Run against API-normalized read-only replay fixtures: node tests/e2e/concern-attribution.mjs <evidence-dir>
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const root=process.cwd(),out=process.argv[2];
const {chromium}=createRequire(root+'/package.json')('playwright-core');
let fixture;
const server=http.createServer((req,res)=>{
 if(req.method!=='GET'){res.writeHead(405);res.end();return;}
 const u=new URL(req.url,'http://localhost');
 if(u.pathname.startsWith('/api/')){
  res.setHeader('Content-Type','application/json');
  res.end(JSON.stringify(u.pathname.includes('detail')?fixture:u.pathname.includes('products')?{products:[fixture.product]}:u.pathname.includes('auth')?{user:null}:{}));return;
 }
 let file=path.join(root,'build',u.pathname);
 if(!fs.existsSync(file)||fs.statSync(file).isDirectory())file=path.join(root,'build/index.html');
 res.setHeader('Content-Type',file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':file.endsWith('.woff2')?'font/woff2':'text/html');
 res.end(fs.readFileSync(file));
});
await new Promise(r=>server.listen(18096,'127.0.0.1',r));
const browser=await chromium.launch({executablePath:process.env.CHROME_BINARY||'/opt/google/chrome/chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const results=[];
try{
 for(const kind of ['cube','fan','historical-cube','historical-fan','controls']){
  fixture=JSON.parse(fs.readFileSync(out+'/'+kind+'-ui-private.json','utf8'));
  const context=await browser.newContext({acceptDownloads:true}),page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const url='http://127.0.0.1:18096/scan/report?link='+encodeURIComponent(fixture.product.link);
  await page.goto(url);await page.getByRole('heading',{name:fixture.product.name,exact:true}).waitFor();
  if(await page.getByRole('button',{name:'Explore',exact:true}).isVisible()){
   await page.getByRole('button',{name:'Explore',exact:true}).click();await page.waitForURL('**/enter');await page.goto(url);
  }
  await page.getByRole('button',{name:'How was this result reached?',exact:true}).click();
  assert.equal(await page.getByRole('list',{name:'Five stages of the product review analysis'}).locator('li').count(),5);
  await page.keyboard.press('Escape');
  const guidance=await page.getByRole('group',{name:'Product review result'}).innerText();
  if(kind==='fan')assert.match(guidance,/considering this product/i);
  if(kind.startsWith('historical'))assert.match(guidance,/earlier|older|again/i);
  if(kind==='controls')assert.match(guidance,/safety concern/i);
  await page.getByRole('tab',{name:/Reviews/}).click();
  await page.getByRole('radio',{name:/^All/}).click();
  const search=page.getByRole('searchbox',{name:'Filter reviews by word'});
  let associations=0;
  for(const review of fixture.product.comments){
   const a=review.sentiment_analysis||{},flags=[...a.review_tags||[],...a.review_extra_tags||[]];
   if(!flags.length&&!review.content.includes('unlike some low-quality toys'))continue;
   await search.fill(review.content);
   const article=page.locator('#report-evidence article').filter({has:page.getByText(review.content,{exact:true})}).first();await article.waitFor();
   const text=await article.innerText();
   assert.doesNotMatch(text,/Sentiment and product context|Review-reported signals/);
   assert.equal(await article.locator('.tone-caution,.tone-safety').count(),flags.length,kind+' '+review.content+' '+JSON.stringify(flags));
   for(const flag of flags){
    const spans=a.review_evidence?.[flag]?.spans||[];
    // Historical reports are preserved, including evidence recorded by earlier checkers.
    if(!kind.startsWith('historical'))assert(spans.length,kind+' '+flag+' missing evidence');
    for(const span of spans)assert(text.includes(span.text));
    associations++;
   }
  }
  await page.getByRole('radio',{name:/^All/}).click();
  await page.getByRole('radio',{name:/^Flagged/}).click();
  if(kind==='cube')assert.equal(await page.locator('#report-evidence article').count(),0);
  else assert((await page.locator('#report-evidence article').count())>0);
  await page.getByRole('radio',{name:/^All/}).click();
  assert((await page.locator('#report-evidence article').count())>0);
  assert.equal(await page.locator('[data-review-stages]').count(),0);
  assert.doesNotMatch(await page.locator('#report-evidence').innerText(),/Sentiment and product context|Review-reported signals/);
  const waiting=page.waitForEvent('download');await page.getByRole('button',{name:'Download report',exact:true}).click();
  const download=await waiting,payload=JSON.parse(fs.readFileSync(await download.path(),'utf8'));
  assert.deepEqual(payload.product,fixture.product);assert.equal(errors.length,0);
  if(kind==='fan')assert.equal(associations,42);
  results.push({kind,reviews:payload.product.comments.length,associations,guidance,download_exact:true,filters:true,five_stages:true,cleanup_preserved:true,errors});
  await context.close();
 }
 fs.writeFileSync(out+'/browser-results.json',JSON.stringify(results,null,2));console.log('FIVE ISOLATED REPORTS, FILTERS, EVIDENCE AND DOWNLOADS PASSED');
}finally{await browser.close();await new Promise(r=>server.close(r));}
