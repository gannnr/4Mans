import {db,digest,hashPassword,MEMBERS,COMMISSIONER_MEMBER,isCommissioner,owner,seedExamples,startSession,token,totals,balances,UserError,viewer,type Prediction,type BetResponse} from './predictions.ts';

function json(value:unknown,status=200,cookie?:string){return Response.json(value,{status,headers:{'Cache-Control':'no-store',...(cookie?{'Set-Cookie':cookie}:{})}});}
function clean(value:unknown,max=500){if(typeof value!=='string'||!value.trim()||value.trim().length>max)throw new UserError('Please fill in all fields within the allowed length.');return value.trim();}
function money(value:unknown){const n=Number(value);if(!Number.isFinite(n)||n<=0||n>100000||Math.abs(n*100-Math.round(n*100))>0.00001)throw new UserError('Enter a positive dollar amount with at most two decimal places.');return Math.round(n*100);}
function acceptBy(value:unknown){
 const date=String(value);if(!/^\d{4}-\d{2}-\d{2}$/.test(date))return NaN;
 const target=Date.parse(date+'T23:59:59Z');if(!Number.isFinite(target)||new Date(target).toISOString().slice(0,10)!==date)return NaN;
 const format=new Intl.DateTimeFormat('en-US',{timeZone:'America/Chicago',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
 let result=target;
 for(let i=0;i<3;i++){const parts=Object.fromEntries(format.formatToParts(result).map(p=>[p.type,p.value]));const shown=Date.parse(`${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}:${parts.second}Z`);result+=target-shown;}
 return result+999;
}
async function accountInputs(b:any){const member=String(b.member);if(!MEMBERS.includes(member))throw new UserError('Choose a 4MANS member.');const username=clean(b.username,30).toLowerCase();if(!/^[a-z0-9_]{3,30}$/.test(username))throw new UserError('Use 3–30 letters, numbers or underscores for your username.');const password=String(b.password||'');if(password.length>128||password.length<8)throw new UserError('Use a password with at least 8 characters.');const salt=token();return {member,username,salt,passwordHash:await hashPassword(password,salt)};}
export async function GET(request:Request){try{await seedExamples();const d=db();const year=Number(new URL(request.url).searchParams.get('season')||2025);const test=new URL(request.url).searchParams.get('test')==='1'?1:0;const user=await viewer(request);if(!user)return json({user:null,configured:true,canSetup:false,members:MEMBERS,predictions:[],responses:[],rulings:[],leaderboard:[],balances:{},accounts:[],seasonStatus:null});const configured=!!await d.prepare('SELECT id FROM prediction_accounts WHERE id=\'commissioner\'').first();const predictions=(await d.prepare('SELECT * FROM predictions WHERE season=? AND is_test=? ORDER BY created_at DESC,id').bind(year,test).all<Prediction>()).results;const responses=(await d.prepare('SELECT r.* FROM prediction_responses r JOIN predictions p ON p.id=r.prediction_id WHERE p.season=? AND p.is_test=?').bind(year,test).all<BetResponse>()).results;const rulings=(await d.prepare('SELECT r.* FROM prediction_rulings r JOIN predictions p ON p.id=r.prediction_id WHERE p.season=? AND p.is_test=? ORDER BY r.created_at DESC').bind(year,test).all()).results;const accounts=isCommissioner(user)?(await d.prepare('SELECT member,username,role FROM prediction_accounts').all()).results:[];return json({user,configured,canSetup:!configured&&await owner(),members:MEMBERS,seasonStatus:await d.prepare('SELECT season,is_test,closed_at,closed_by FROM prediction_seasons WHERE key=?').bind(String(year)+':'+test).first(),predictions,responses,rulings,leaderboard:totals(predictions,responses),accounts,balances:balances(predictions,responses)});}catch(e){console.error('Predictions read failed',e);return json({error:'Predictions could not load. Please try again.'},503)}}
export async function POST(request:Request){try{if(request.headers.get('origin')!=='https://gannnr.github.io')throw new UserError('Please submit from the 4MANS site.',403);if(Number(request.headers.get('content-length')||0)>12000)throw new UserError('Request too large.');const bodyText=await request.text();if(bodyText.length>12000)throw new UserError('Request too large.');const b=JSON.parse(bodyText);const d=db();const user=await viewer(request);const now=Date.now();
 if(b.action==='setup'){
  if(!await owner())throw new UserError('Only the site owner can set up the commissioner account.',403);
  if(b.member!==COMMISSIONER_MEMBER)throw new UserError('The commissioner account is reserved for nactasty.',403);
  const a=await accountInputs(b);const result=await d.prepare('INSERT INTO prediction_accounts(id,member,username,salt,password_hash,role,created_at) SELECT \'commissioner\',?,?,?,?,\'commissioner\',? WHERE NOT EXISTS(SELECT 1 FROM prediction_accounts)').bind(a.member,a.username,a.salt,a.passwordHash,now).run();if(!result.meta.changes)throw new UserError('Commissioner setup is already complete.',409);return json({ok:true},200,await startSession('commissioner'));
 }
 if(b.action==='join'){
  if(b.member===COMMISSIONER_MEMBER)throw new UserError('nactasty is reserved for the commissioner.',403);
  const a=await accountInputs(b);const invite=await digest(clean(b.code,64));const result=await d.prepare('INSERT INTO prediction_accounts(id,member,username,salt,password_hash,role,created_at) SELECT ?,?,?,?,?,\'member\',? WHERE EXISTS(SELECT 1 FROM prediction_invites WHERE member=? AND hash=? AND expires>?)').bind(crypto.randomUUID(),a.member,a.username,a.salt,a.passwordHash,now,a.member,invite,now).run();if(!result.meta.changes)throw new UserError('That invitation is invalid or expired.',403);await d.prepare('DELETE FROM prediction_invites WHERE member=?').bind(a.member).run();const arow=await d.prepare('SELECT id FROM prediction_accounts WHERE member=?').bind(a.member).first<{id:string}>();return json({ok:true},200,await startSession(arow!.id));
 }
 if(b.action==='login'){
  const username=clean(b.username,30).toLowerCase();const key=await digest(username);await d.prepare('INSERT INTO prediction_login_limits(key,attempts,expires) VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET attempts=CASE WHEN prediction_login_limits.expires<? THEN 1 ELSE prediction_login_limits.attempts+1 END,expires=CASE WHEN prediction_login_limits.expires<? THEN ? ELSE prediction_login_limits.expires END').bind(key,now+900000,now,now,now+900000).run();const limit=await d.prepare('SELECT attempts FROM prediction_login_limits WHERE key=?').bind(key).first<{attempts:number}>();if(limit!.attempts>10)throw new UserError('Too many attempts. Try again in 15 minutes.',429);const a=await d.prepare('SELECT * FROM prediction_accounts WHERE username=?').bind(username).first<any>();const computed=await hashPassword(String(b.password||''),a?.salt||'dummy-salt-for-missing-user');if(!a||computed!==a.password_hash)throw new UserError('Username or password is incorrect.',401);await d.prepare('DELETE FROM prediction_login_limits WHERE key=?').bind(key).run();return json({ok:true},200,await startSession(a.id));
 }
 if(!user)throw new UserError('Log in to participate.',401);
 if(b.action==='logout'){const raw=request.headers.get('cookie')?.match(/fourmans_session=([a-f0-9]{64})/)?.[1];if(raw)await d.prepare('DELETE FROM prediction_sessions WHERE hash=?').bind(await digest(raw)).run();return json({ok:true},200,'fourmans_session=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0');}
 if(b.action==='invite'){
  if(!isCommissioner(user))throw new UserError('Commissioner access required.',403);const member=String(b.member);if(member===COMMISSIONER_MEMBER||!MEMBERS.includes(member)||await d.prepare('SELECT id FROM prediction_accounts WHERE member=?').bind(member).first())throw new UserError('Choose a member without an account.');const code=token();await d.prepare('INSERT INTO prediction_invites(member,hash,expires) VALUES(?,?,?) ON CONFLICT(member) DO UPDATE SET hash=excluded.hash,expires=excluded.expires').bind(member,await digest(code),now+7*86400000).run();return json({code,member});
 }
 if(b.action==='close_season'){
  if(!isCommissioner(user))throw new UserError('Only the commissioner can close a season.',403);
  const year=Number(b.season),test=b.test===true?1:0;if(!Number.isInteger(year)||year<2020||year>2100||test&&year!==2025)throw new UserError('Choose a valid season.');
  const result=await d.prepare("INSERT OR IGNORE INTO prediction_seasons(key,season,is_test,closed_at,closed_by) SELECT ?,?,?,?,? WHERE NOT EXISTS(SELECT 1 FROM predictions WHERE season=? AND is_test=? AND outcome IS NULL)").bind(String(year)+':'+test,year,test,now,user.member,year,test).run();
  if(!result.meta.changes)throw new UserError('Settle or void every open prediction before closing this season. It may already be closed.',409);
  return json({ok:true});
 }
 if(b.action==='create'){
  const year=Number(b.season);if(!Number.isInteger(year)||year<2020||year>2100)throw new UserError('Choose a valid season.');
  const deadline=acceptBy(b.deadline);if(!Number.isFinite(deadline)||deadline<=now)throw new UserError('Choose an acceptance date that has not passed.');
  const test=b.test===true;if(test&&year!==2025)throw new UserError('Test predictions belong to the 2025 season.');
  const id=crypto.randomUUID();const result=await d.prepare("INSERT INTO predictions(id,season,author,title,criteria,mode,amount,deadline,resolve_at,is_test,created_at) SELECT ?,?,?,?,?,\'each\',?,?,0,?,? WHERE NOT EXISTS(SELECT 1 FROM prediction_seasons WHERE key=?)").bind(id,year,user.member,clean(b.title,160),clean(b.criteria,1000),money(b.amount),deadline,test?1:0,now,String(year)+':'+(test?1:0)).run();
  if(!result.meta.changes)throw new UserError('This prediction season is closed.',409);return json({ok:true,id});
 }
 const p=await d.prepare('SELECT * FROM predictions WHERE id=?').bind(String(b.id||'')).first<Prediction>();if(!p)throw new UserError('Prediction not found.',404);
 const seasonKey=String(p.season)+':'+p.is_test;
 if(await d.prepare('SELECT key FROM prediction_seasons WHERE key=?').bind(seasonKey).first())throw new UserError('This prediction season is closed. Its results are frozen.',409);
 if(b.action==='edit'){
  if(p.author!==user.member)throw new UserError('Only the creator can edit this prediction.',403);
  if(p.outcome)throw new UserError('Only active predictions can be edited.',409);
  const version=Number(b.version),deadline=acceptBy(b.deadline);
  if(!Number.isFinite(deadline)||deadline<=now)throw new UserError('Choose an acceptance date that has not passed.');
  const title=clean(b.title,160),criteria=clean(b.criteria,1000),amount=money(b.amount);
  const result=await d.batch([
   d.prepare('DELETE FROM prediction_responses WHERE prediction_id=? AND EXISTS(SELECT 1 FROM predictions WHERE id=? AND author=? AND version=? AND outcome IS NULL) AND NOT EXISTS(SELECT 1 FROM prediction_seasons WHERE key=?)').bind(p.id,p.id,user.member,version,seasonKey),
   d.prepare("UPDATE predictions SET title=?,criteria=?,mode='each',amount=?,deadline=?,version=version+1 WHERE id=? AND author=? AND version=? AND outcome IS NULL AND NOT EXISTS(SELECT 1 FROM prediction_seasons WHERE key=?)").bind(title,criteria,amount,deadline,p.id,user.member,version,seasonKey)
  ]);
  if(!result[1].meta.changes)throw new UserError('The prediction changed. Refresh before editing again.',409);return json({ok:true});
 }
 if(b.action==='respond'){
  if(p.author===user.member)throw new UserError('You cannot take the opposing side of your own prediction.');
  if(!['accept','decline'].includes(b.decision))throw new UserError('Choose accept or decline.');
  if(p.mode!=='each')throw new UserError('This legacy wager must be settled or voided by the commissioner.',409);
  if(!Number.isInteger(b.version)||b.version!==p.version)throw new UserError('This prediction was edited. Refresh and review the new terms before responding.',409);
  const amount=b.decision==='accept'?p.amount:0;
  const result=await d.prepare(`INSERT INTO prediction_responses(id,prediction_id,member,decision,amount,created_at)
   SELECT ?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM predictions WHERE id=? AND outcome IS NULL AND deadline>? AND version=?)
   AND NOT EXISTS(SELECT 1 FROM prediction_seasons WHERE key=?)
   ON CONFLICT(prediction_id,member) DO UPDATE SET decision=excluded.decision,amount=excluded.amount,created_at=excluded.created_at WHERE prediction_responses.decision!='accept'`).bind(crypto.randomUUID(),p.id,user.member,b.decision,amount,now,p.id,now,p.version,seasonKey).run();
  if(!result.meta.changes)throw new UserError('This prediction is closed, already accepted, or its season has closed. Refresh and try again.',409);return json({ok:true});
 }
 if(b.action==='settle'){
  if(!isCommissioner(user))throw new UserError('Only the commissioner can settle results.',403);if(!['happened','didnt','void','active'].includes(b.outcome))throw new UserError('Choose a valid outcome.');if(b.outcome==='active'&&!p.outcome)throw new UserError('This prediction is already active.',409);const note=clean(b.note,1000);const version=Number(b.version);const result=await d.batch([d.prepare('INSERT INTO prediction_rulings(id,prediction_id,commissioner,outcome,note,version,created_at) SELECT ?,?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM predictions WHERE id=? AND version=?) AND NOT EXISTS(SELECT 1 FROM prediction_seasons WHERE key=?)').bind(crypto.randomUUID(),p.id,user.member,b.outcome,note,version+1,now,p.id,version,seasonKey),d.prepare('UPDATE predictions SET outcome=?,note=?,version=version+1 WHERE id=? AND version=? AND NOT EXISTS(SELECT 1 FROM prediction_seasons WHERE key=?)').bind(b.outcome==='active'?null:b.outcome,note,p.id,version,seasonKey)]);if(!result[0].meta.changes)throw new UserError('The result changed. Refresh before ruling again.',409);return json({ok:true});
 }
 throw new UserError('Unknown action.');
 }catch(e){if(e instanceof UserError)return json({error:e.message},e.status);console.error('Predictions write failed',e);if(String(e).includes('UNIQUE'))return json({error:'That username or member already has an account.'},409);return json({error:'Could not save. Your input is still here; please try again.'},503)}}
