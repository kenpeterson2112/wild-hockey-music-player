// Regression tests for index.html: runs the real app script in a Node VM with a
// fake DOM. Run with: node tests/app.test.mjs   (exits non-zero on any failure)
import vm from 'node:vm'; import fs from 'node:fs';
const INDEX=new URL('../index.html', import.meta.url);
const code=[...fs.readFileSync(INDEX,'utf8').matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n');

function makeEnv(seed={}) {
  const store=new Map(Object.entries({spotify_access_token:'tok',spotify_token_expiry:String(Date.now()+3600000),...seed}));
  const localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
  function mk(){const e={style:{},value:'',checked:false,children:[],textContent:'',className:'',title:'',onclick:null,
    classList:{add(){},remove(){},toggle(){},contains(){return false}},
    appendChild(c){this.children.push(c);return c},get childNodes(){return this.children},
    querySelector:()=>null,set innerHTML(v){this.children=[]},get innerHTML(){return ''}};return e;}
  const els={}; const gid=id=>els[id]||(els[id]=mk());
  const document={getElementById:gid,createElement:()=>mk(),createTextNode:t=>({textContent:t}),addEventListener(){},body:{appendChild(){},removeChild(){}}};
  const win={location:{origin:'x',pathname:'/'},history:{replaceState(){}},localStorage,addEventListener(){},crypto:{getRandomValues:a=>a,subtle:{digest:async()=>new ArrayBuffer(32)}}};
  const sb={window:win,document,localStorage,fetch:()=>Promise.resolve({ok:true,status:204,json:async()=>({})}),alert:m=>{sb.__alert=m},console:{log:console.log,error(){}},setInterval:()=>0,setTimeout:(f)=>{f&&f();return 0},clearTimeout(){},clearInterval(){},crypto:win.crypto,btoa:s=>Buffer.from(s,'binary').toString('base64'),TextEncoder,URL,URLSearchParams,encodeURIComponent,Blob:class{}};
  sb.globalThis=sb; vm.createContext(sb); vm.runInContext(code,sb); sb.accessToken='tok';
  return {sb,store,gid,run:e=>vm.runInContext(e,sb)};
}
const chipTxt=b=>b.children.map(x=>x.textContent).join('');
let ok=0, bad=0; const check=(label,cond,extra='')=>{ (cond?ok++:bad++); console.log((cond?'PASS ':'FAIL ')+label+(extra?'  -> '+extra:'')); };

// ================= 1. repo songs and tags (expectations come from window.SONGS itself,
// so adding songs or tags never breaks these checks)
{ const {sb,run}=makeEnv();
  const repo=run('window.SONGS');
  const songs=sb.buildSongList();
  const N=repo.length;
  const counts=new Map(); repo.forEach(s=>(s.tags||[]).forEach(t=>counts.set(t,(counts.get(t)||0)+1)));
  const byCount=[...counts.keys()].sort((a,b)=>(counts.get(b)-counts.get(a))||a.localeCompare(b));
  const tagged=songs.filter(s=>s.tags.size>0);
  check('every repo song loads', songs.length===N, songs.length+' of '+N);
  check('tagged + untagged add up', tagged.length===repo.filter(s=>(s.tags||[]).length).length);
  check('list is alphabetical', songs.every((s,i)=>i===0||songs[i-1].name.localeCompare(s.name,undefined,{sensitivity:'base',numeric:true})<=0));

  run("openTrackSelector('Choose: Whistle 1')");
  const chips=run("document.getElementById('tag-chips').children").map(chipTxt);
  check('chips: no All chip, no X yet, tags by song count', chips.join(' | ')===byCount.map(t=>t+counts.get(t)).join(' | '), chips.join(' | '));
  check('no Between Whistles chip', !chips.some(c=>/whistle/i.test(c)));
  const rows=()=>run("document.getElementById('track-list').children.filter(r=>r.className!=='list-divider').length");
  const hasX=()=>!run("document.getElementById('chip-clear-btn').className").includes('off');
  const tap=(label)=>run("document.getElementById('tag-chips').children").find(b=>b.className.includes('chip') && !b.className.includes('chip-clear') && chipTxt(b)===label+counts.get(label)).onclick();
  const anyOf=ts=>repo.filter(s=>(s.tags||[]).some(t=>ts.includes(t))).length;
  check('everything shown by default', rows()===N);
  if (byCount.length) {
    const [t1,t2]=byCount;
    tap(t1); check('first chip = single filter + X shows on the right', rows()===counts.get(t1) && hasX(), rows());
    if (byCount.length>2) { // with exactly 2 tags, picking both = every tag = everything (checked below)
      tap(t2); check('second chip adds (any of)', rows()===anyOf([t1,t2]), rows());
      tap(t1); check('deselect one keeps the other', rows()===counts.get(t2));
      tap(t2);
    } else tap(t1);
    check('last chip off = everything, X gone', rows()===N && !hasX());
    if (byCount.length>1) {
      byCount.slice(0,-1).forEach(tap); check('all but one tag still filtering', rows()===anyOf(byCount.slice(0,-1)) && hasX(), rows());
      tap(byCount[byCount.length-1]); check('every tag selected = everything, X gone', rows()===N && !hasX());
    }
    tap(t1); run("document.getElementById('chip-clear-btn').onclick()"); check('X clears selection', rows()===N && !hasX());
  }
}

// ================= 2. old on-phone data converts once
{ const old={whistles:[{uri:'spotify:track:W1AAAAAAAAAAAAAAAAAA11',name:'Old Whistle'}],
              goalFor:[{uri:'spotify:track:G1AAAAAAAAAAAAAAAAAA11',name:'Old Goal',startSec:20}],
              penaltyFor:[{uri:'spotify:track:G1AAAAAAAAAAAAAAAAAA11',name:'Old Goal',startSec:20}],   // same song in two categories
              pregame:[{uri:'spotify:track:P1AAAAAAAAAAAAAAAAAA11',name:'Old Pregame'}],
              foo:[{uri:'spotify:track:F1AAAAAAAAAAAAAAAAAA11',name:'Junk Category'}]};
  const {sb,store,run}=makeEnv({custom_tracks:JSON.stringify(old)});
  const cs=JSON.parse(store.get('custom_songs'));
  check('old per-category data converts to a flat list', Array.isArray(cs) && cs.length===3, cs.map(s=>s.name).join(', '));
  const goal=cs.find(s=>s.name==='Old Goal');
  check('same song in two old categories is one song with both tags', goal && goal.tags.join(',')==='Goal For,Power Play' && goal.startSec===20, JSON.stringify(goal&&goal.tags));
  check('old Between Whistles songs become untagged', !cs.find(s=>s.name==='Old Whistle').tags);
  check('old Pregame songs keep a Pregame tag', cs.find(s=>s.name==='Old Pregame').tags[0]==='Pregame');
  check('unknown old category keys are ignored', !cs.some(s=>s.name==='Junk Category'));
  check('old custom_tracks entry left untouched', store.get('custom_tracks')===JSON.stringify(old));
  check('count shown is the flat length', run('customTrackCount()')===3);
  // second load does not re-migrate over later changes
  run("customSongs=[]; saveCustomSongs()");
  const again=makeEnv({custom_tracks:JSON.stringify(old),custom_songs:'[]'});
  check('once migrated, an emptied list is not re-filled from the old data', again.run('customSongs.length')===0);
}

// ================= 3. Add Custom Song form
{ const {sb,store,gid,run}=makeEnv();
  // tag chips offered: standard tags even though some have zero songs
  run('renderAddTagChips()');
  const offered=gid('custom-tag-chips').children.map(b=>b.textContent);
  const dc=new Map(run('DEFAULT_TAGS').map(t=>[t,0])); run('window.SONGS').forEach(x=>(x.tags||[]).forEach(t=>dc.set(t,(dc.get(t)||0)+1)));
  const expectOffered=[...dc.keys()].sort((a,b)=>(dc.get(b)-dc.get(a))||a.localeCompare(b));
  check('form offers every tag, most songs first', offered.join(',')===expectOffered.join(','), offered.join(','));
  // select two chips + a new tag, set link/name/start
  gid('custom-tag-chips').children.find(b=>b.textContent==='Goal For').onclick();
  gid('custom-tag-chips').children.find(b=>b.textContent==='Power Play').onclick();
  const active=gid('custom-tag-chips').children.filter(b=>b.className.includes('active')).map(b=>b.textContent);
  check('chips multi-select', active.length===2 && active.includes('Power Play') && active.includes('Goal For'), active.join(','));
  gid('custom-link-input').value='https://open.spotify.com/track/NEWAAAAAAAAAAAAAAAAAA1?si=zz';
  gid('custom-name-input').value='Brand New';
  gid('custom-start-input').value='1:05';
  gid('custom-newtag-input').value='Hype, goal for';   // goal for duplicates a selected chip
  run('addCustomTrack()');
  const cs=JSON.parse(store.get('custom_songs'));
  check('song saved with link, start time and combined tags', cs.length===1 && cs[0].uri==='spotify:track:NEWAAAAAAAAAAAAAAAAAA1' && cs[0].startSec===65 && cs[0].tags.join(',')==='Goal For,Power Play,Hype', JSON.stringify(cs[0]));
  check('status confirms it', gid('custom-add-status').textContent.includes('Added "Brand New"'), gid('custom-add-status').textContent);
  check('form cleared and chips reset', gid('custom-name-input').value==='' && !gid('custom-tag-chips').children.some(b=>b.className.includes('active')));
  check('new tag shows up as a chip for next time', gid('custom-tag-chips').children.some(b=>b.textContent==='Hype'));
  check('new song is in the main list with its tags', run("buildSongList().find(s=>s.name==='Brand New').tags.size")===3);
  // untagged add
  gid('custom-link-input').value='spotify:track:PLAINAAAAAAAAAAAAAAAA1'; gid('custom-name-input').value='Plain Whistle';
  run('addCustomTrack()');
  check('no tags = between whistles', /between whistles/.test(gid('custom-add-status').textContent) && !JSON.parse(store.get('custom_songs')).find(s=>s.name==='Plain Whistle').tags, gid('custom-add-status').textContent);
  // duplicate of a repo song
  const first=run('window.SONGS[0]');
  gid('custom-link-input').value='https://open.spotify.com/track/'+first.uri.split(':')[2]; gid('custom-name-input').value='Dup';
  run('addCustomTrack()');
  check('a song already in the repo list is refused', gid('custom-add-status').textContent==='"'+first.name+'" is already in the list.', gid('custom-add-status').textContent);
  gid('custom-link-input').value='nonsense'; gid('custom-name-input').value='X'; run('addCustomTrack()');
  check('bad link refused', /doesn't look like/.test(gid('custom-add-status').textContent));
  // removing a custom song from the picker data
  run("removeCustomByUri('spotify:track:NEWAAAAAAAAAAAAAAAAAA1')");
  check('custom song removal', JSON.parse(store.get('custom_songs')).length===1);
}

// ================= 4. export / import
{ const {sb,store,gid,run}=makeEnv({custom_songs:JSON.stringify([{uri:'spotify:track:EXPAAAAAAAAAAAAAAAAAA1',name:'Exp',tags:['Goal For']}])});
  const exp=JSON.parse(run('buildExportJson()'));
  check('export is the flat v2 format', exp.version===2 && exp.type==='custom-songs' && exp.customSongs.length===1 && exp.customSongs[0].tags[0]==='Goal For');

  const imp=(obj)=>run(`sanitizeImported(${JSON.stringify(obj)})`);
  check('imports a v2 file', imp(exp).count===1);
  check('imports a bare list', imp(exp.customSongs).count===1);
  const v1={app:'x',type:'custom-songs',version:1,customTracks:{whistles:[{uri:'spotify:track:V1AAAAAAAAAAAAAAAAAA11',name:'V1 Whistle'}],goalAgainst:[{uri:'spotify:track:V1BBBBBBBBBBBBBBBBBB22',name:'V1 Against',startSec:9}],bogus:[{uri:'spotify:track:V1CCCCCCCCCCCCCCCCCC33',name:'Nope'}]}};
  const r1=imp(v1);
  check('imports an OLD per-category file', r1.count===2 && r1.clean.find(s=>s.name==='V1 Against').tags[0]==='Goal Against' && !r1.clean.find(s=>s.name==='V1 Whistle').tags, JSON.stringify(r1.clean.map(s=>[s.name,s.tags])));
  check('bare old-style dict also works', imp({goalFor:[{uri:'spotify:track:V1DDDDDDDDDDDDDDDDDD44',name:'Bare'}]}).count===1);
  check('junk is rejected', imp({hello:'world'}).count===0 && imp([1,'x',{name:'no uri'}]).count===0 && imp(null).count===0);
  check('duplicates inside a file merge their tags', imp([{uri:'spotify:track:DUPAAAAAAAAAAAAAAAAAA1',name:'D',tags:['Goal For']},{uri:'spotify:track:DUPAAAAAAAAAAAAAAAAAA1',name:'D',tags:['Power Play']}]).clean[0].tags.join(',')==='Goal For,Power Play');

  // add vs replace via the real handlers
  const load=(obj)=>{ sb.FileReader=class{readAsText(){this.onload({target:{result:JSON.stringify(obj)}});}}; vm.runInContext('FileReader=globalThis.FileReader',sb); gid('import-file-input').files=[{name:'f.json'}]; run('handleImportFileSelect()'); };
  load([{uri:'spotify:track:EXPAAAAAAAAAAAAAAAAAA1',name:'Exp'},{uri:'spotify:track:ADDAAAAAAAAAAAAAAAAAA1',name:'Added'}]);
  run("applyImport('add')");
  check('Add skips the duplicate and appends the new song', gid('import-status').textContent.includes('Added 1 song, skipped 1 duplicate') && run('customSongs.length')===2, gid('import-status').textContent);
  load(v1); run("applyImport('replace')");
  check('Replace swaps the whole list', run('customSongs.length')===2 && /Replaced/.test(gid('import-status').textContent));
  check('everything persisted as the flat list', JSON.parse(store.get('custom_songs')).length===2);

  // reset
  sb.setTimeout=()=>0; run('resetOnDeviceSongs()'); run('resetOnDeviceSongs()');
  check('reset clears the on-device songs', run('customSongs.length')===0 && store.get('custom_songs')==='[]');
}

// ================= 5. queue unaffected
{ const {sb,store,gid,run}=makeEnv();
  run("assignSlot('gf',{uri:'spotify:track:57bgtoPSgt236HzfBOd8kj',name:'Thunderstruck',startSec:158})");
  check('queue slots keep working', JSON.parse(store.get('queue_slots')).gf.name==='Thunderstruck');
  check('tiles use the new spellings', run('QUEUE_SLOTS.map(s=>s.label).join(",")')==='Whistle 1,Whistle 2,Whistle 3,Whistle 4,Goal For,Goal Against,Power Play,Penalty Kill');
  run("editSlot('pp')");
  check('a tile opens the picker with its title', gid('track-modal-title').textContent==='Choose: Power Play');
  const names=run("document.getElementById('track-list').children.filter(r=>r.className!=='list-divider').map(r=>r.children[0].children[0].textContent)");
  check('queued song is in the queued group, the rest still listed', run("document.getElementById('track-list').children.some(r=>r.className==='list-divider')") && names.length===run('window.SONGS.length'));
}
console.log(`\n${ok} passed, ${bad} failed`);
if (bad) process.exit(1);
