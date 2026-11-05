// Keep infrastructure failures actionable without displaying arbitrary server output.
export async function readApiResponse(response:Response){
 const raw=await response.text();
 let value;
 try{value=JSON.parse(raw);}catch{
  if(response.status>=500||!raw.trim())throw new Error('Cannot reach the backend. Start or restart it on 127.0.0.1:8001, then try again.');
  throw new Error('The API returned an unexpected response. Check that the backend is running on port 8001 and refresh this page.');
 }
 if(!response.ok)throw new Error(typeof value?.detail==='string'?value.detail:response.status===401?'Invalid local API token. Copy it again from data/api-token.':`API request failed (${response.status}).`);
 return value;
}
