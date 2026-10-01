import {database} from './database.ts';
export const MEMBERS=['nactasty','jpagonis','TheChavenator','bingbongtinydong'];
export const COMMISSIONER_MEMBER='nactasty';
export function isCommissioner(user:{id:string;member:string;role:string}|null){return user?.id==='commissioner'&&user.member===COMMISSIONER_MEMBER&&user.role==='commissioner';}
export function db(){return database;}
export class UserError extends Error {constructor(message:string,public status=400){super(message)}}
const enc=new TextEncoder();
export async function digest(s:string){const b=await crypto.subtle.digest('SHA-256',enc.encode(s));return Array.from(new Uint8Array(b),x=>x.toString(16).padStart(2,'0')).join('');}
export function token(){return Array.from(crypto.getRandomValues(new Uint8Array(32)),x=>x.toString(16).padStart(2,'0')).join('');}
export async function hashPassword(password:string,salt:string){const key=await crypto.subtle.importKey('raw',enc.encode(password),'PBKDF2',false,['deriveBits']);const bits=await crypto.subtle.deriveBits({name:'PBKDF2',salt:enc.encode(salt),iterations:100000,hash:'SHA-256'},key,256);return Array.from(new Uint8Array(bits),x=>x.toString(16).padStart(2,'0')).join('');}
export async function viewer(request:Request){const cookie=request.headers.get('cookie')||'';const value=cookie.match(/(?:^|;\s*)fourmans_session=([a-f0-9]{64})(?:;|$)/)?.[1];if(!value)return null;return db().prepare('SELECT a.id,a.member,a.username,a.role FROM prediction_sessions s JOIN prediction_accounts a ON a.id=s.account_id WHERE s.hash=? AND s.expires>?').bind(await digest(value),Date.now()).first<{id:string;member:string;username:string;role:string}>();}
export async function owner(){return false;}
export async function startSession(id:string){const value=token();await db().prepare('INSERT INTO prediction_sessions(hash,account_id,expires) VALUES(?,?,?)').bind(await digest(value),id,Date.now()+30*86400000).run();return `fourmans_session=${value}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=2592000`;}
export async function seedExamples(){}
export type Prediction={id:string;season:number;author:string;title:string;criteria:string;mode:string;amount:number;deadline:number;resolve_at:number;outcome:string|null;note:string;version:number;is_test:number;created_at:number};
export type BetResponse={id:string;prediction_id:string;member:string;decision:string;amount:number;created_at:number};
export function totals(predictions:Prediction[],responses:BetResponse[]){return MEMBERS.map(member=>{let net=0,risk=0,wins=0,losses=0;for(const p of predictions){const bets=responses.filter(r=>r.prediction_id===p.id&&r.decision==='accept');const stake=p.author===member?bets.reduce((s,b)=>s+b.amount,0):bets.find(b=>b.member===member)?.amount||0;if(!stake)continue;if(!p.outcome){risk+=stake;continue;}if(p.outcome==='void')continue;const won=(p.outcome==='happened')===(p.author===member);net+=won?stake:-stake;won?wins++:losses++;}return {member,net,risk,wins,losses};}).sort((a,b)=>b.net-a.net);}

// Positive balance: the counterparty owes this member; negative: this member owes them.
export function balances(predictions:Prediction[],responses:BetResponse[]){
 const result=Object.fromEntries(MEMBERS.map(m=>[m,Object.fromEntries(MEMBERS.filter(other=>other!==m).map(other=>[other,0]))]));
 const byId=new Map(predictions.map(p=>[p.id,p]));
 for(const r of responses){const p=byId.get(r.prediction_id);if(!p||r.decision!=='accept'||!['happened','didnt'].includes(p.outcome||''))continue;const sign=p.outcome==='happened'?1:-1;result[p.author][r.member]+=sign*r.amount;result[r.member][p.author]-=sign*r.amount;}
 return result;
}
