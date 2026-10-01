
// Only the server-side service role may call the transaction bridge. No SQL comes from HTTP clients.
async function execute(statements:any[]){
 const key=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');if(!key)throw new Error('Backend configuration unavailable');
 const r=await fetch(Deno.env.get('SUPABASE_URL')+'/rest/v1/rpc/fourmans_transaction',{method:'POST',headers:{apikey:key,Authorization:'Bearer '+key,'Content-Type':'application/json'},body:JSON.stringify({statements})});
 const body=await r.json();if(!r.ok)throw new Error(body.code==='23505'?'UNIQUE constraint failed':body.message||'Database request failed');return body;
}
class Statement{
 sql:string;params:any[]=[];constructor(sql:string){this.sql=sql;}
 bind(...params:any[]){this.params=params;return this;}
 spec(mode:string){let sql=this.sql.replace(/MIN\(deadline,\?\)/g,'LEAST(deadline,?)');if(sql.startsWith('INSERT OR IGNORE '))sql=sql.replace('INSERT OR IGNORE ','INSERT ')+' ON CONFLICT DO NOTHING';return {sql,params:this.params,mode};}
 async first<T=any>():Promise<T|null>{return (await execute([this.spec('select')]))[0].results[0]??null;}
 async all<T=any>():Promise<{results:T[]}>{return (await execute([this.spec('select')]))[0];}
 async run(){return (await execute([this.spec('run')]))[0];}
}
export const database={prepare:(sql:string)=>new Statement(sql),batch:(s:Statement[])=>execute(s.map(x=>x.spec('run')))};
