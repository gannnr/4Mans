
import {GET,POST} from './route.ts';
const allowed='https://gannnr.github.io';
Deno.serve(async request=>{
 const origin=request.headers.get('origin');
 const cors={'Access-Control-Allow-Origin':allowed,'Access-Control-Allow-Headers':'authorization, content-type, apikey','Access-Control-Allow-Methods':'GET, POST, OPTIONS','Vary':'Origin','Cache-Control':'no-store'};
 if(origin&&origin!==allowed)return Response.json({error:'Use the 4MANS website.'},{status:403});
 if(request.method==='OPTIONS')return new Response(null,{status:204,headers:cors});
 if(!['GET','POST'].includes(request.method))return new Response(null,{status:405,headers:cors});
 const headers=new Headers(request.headers);headers.delete('cookie');
 const auth=headers.get('authorization')||'';const bearer=auth.match(/^Bearer ([a-f0-9]{64})$/)?.[1];
 if(bearer)headers.set('cookie','fourmans_session='+bearer);
 try{
  const forwarded=new Request(request.url,{method:request.method,headers,...(request.method==='POST'?{body:await request.text()}:{})});
  const response=await (request.method==='GET'?GET(forwarded):POST(forwarded));const body=await response.json();const cookie=response.headers.get('set-cookie');
  if(cookie){const session=cookie.match(/fourmans_session=([a-f0-9]{64})/)?.[1];if(session)body.sessionToken=session;else body.clearSession=true;}
  return Response.json(body,{status:response.status,headers:{...cors,'X-Content-Type-Options':'nosniff'}});
 }catch{console.error('4MANS request failed');return Response.json({error:'Temporarily unavailable. Please try again.'},{status:503,headers:cors});}
});
