import {useState} from 'react';
export type Pair={incoming:string;response:string};
type Voice={style:string;examples:string[];pairs:Pair[]};
export type Profile=Voice&{recipients:Record<string,Voice>};
export function normalizeProfile(value:Partial<Profile>):Profile{
 return {style:value.style||'',examples:value.examples||[],pairs:value.pairs||[],recipients:value.recipients||{}};
}
const empty=():Voice=>({style:'',examples:[],pairs:[]});
export function VoiceEditor({profile,onChange,recipients,busy,onSave,suggest}:{profile:Profile;onChange:(p:Profile)=>void;recipients:string[];busy:boolean;onSave:()=>void;suggest:(r:string)=>Promise<{pairs:Pair[]}>}){
 const [scope,setScope]=useState(''),[preview,setPreview]=useState<Pair[]>([]),[chosen,setChosen]=useState<number[]>([]);
 const [loading,setLoading]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const voice=scope?profile.recipients[scope]||empty():profile;
 function update(patch:Partial<Voice>){const next={...voice,...patch};onChange(scope?{...profile,recipients:{...profile.recipients,[scope]:next}}:{...profile,...next});setNotice('Unsaved voice changes.');}
 function editPair(index:number,patch:Partial<Pair>){update({pairs:voice.pairs.map((p,i)=>i===index?{...p,...patch}:p)});}
 async function load(){setLoading(true);setError('');setPreview([]);try{const result=await suggest(scope);setPreview(result.pairs);setChosen([]);if(!result.pairs.length)setNotice('No reliable pairs found. Add examples manually.');}catch(e){setError((e as Error).message);}finally{setLoading(false);}}
 return <section className="voice card"><h2>Your texting style</h2><fieldset disabled={busy||loading} className="voice-fields">
 <label>Voice for<select value={scope} onChange={e=>{setScope(e.target.value);setPreview([]);setNotice('');setError('');}}><option value="">Default voice</option>{recipients.map(r=><option key={r}>{r}</option>)}</select></label>
 <p className="muted">{scope?'Default instructions still apply. These preferences add to them; examples here replace default examples. Leave examples empty to use defaults.':'Defaults apply when a chat has no personal examples.'}</p>
 <label>{scope?'Additional preferences for this person':'How should your replies sound?'}<textarea maxLength={2000} value={voice.style} onChange={e=>update({style:e.target.value})}/></label>
 <label>Examples written by you (one message per line)<textarea className="examples" value={voice.examples.join('\n')} onChange={e=>update({examples:e.target.value.split('\n')})}/></label>
 <h3>Incoming and reply examples</h3>{voice.pairs.map((pair,i)=><div className="voice-pair" key={i}><label>Incoming message {i+1}<textarea maxLength={2000} value={pair.incoming} onChange={e=>editPair(i,{incoming:e.target.value})}/></label><label>My response {i+1}<textarea maxLength={2000} value={pair.response} onChange={e=>editPair(i,{response:e.target.value})}/></label><button type="button" className="secondary" onClick={()=>update({pairs:voice.pairs.filter((_,n)=>n!==i)})}>Remove example {i+1}</button></div>)}
 <button type="button" className="secondary" disabled={voice.pairs.length>=20} onClick={()=>update({pairs:[...voice.pairs,{incoming:'',response:''}]})}>Add example pair</button>
 {scope&&<div><p className="muted">Read this chat’s recent window to suggest examples. Preview is not saved, does not call a model, and never sends messages.</p><button type="button" className="secondary" onClick={()=>void load()}>Suggest examples from this chat</button></div>}
 </fieldset>
 {loading&&<p role="status">Reading example candidates…</p>}{error&&<p className="error" role="alert">{error}</p>}
 {preview.length>0&&<section aria-label="Suggested examples"><h3>Review suggested examples</h3><p>Only selected pairs will be added. Edit them here, then add and save your voice.</p>{preview.map((pair,i)=><div className="voice-pair" key={i}><label className="auto-refresh"><input type="checkbox" checked={chosen.includes(i)} onChange={e=>setChosen(ids=>e.target.checked?[...ids,i]:ids.filter(n=>n!==i))}/>Include suggestion {i+1}</label><label>Suggested incoming message {i+1}<textarea value={pair.incoming} maxLength={2000} onChange={e=>setPreview(rows=>rows.map((p,n)=>n===i?{...p,incoming:e.target.value}:p))}/></label><label>Suggested response {i+1}<textarea value={pair.response} maxLength={2000} onChange={e=>setPreview(rows=>rows.map((p,n)=>n===i?{...p,response:e.target.value}:p))}/></label></div>)}<button type="button" disabled={busy||!chosen.length} onClick={()=>{const pairs=[...voice.pairs];for(const i of chosen){const p=preview[i];if(!pairs.some(v=>v.incoming===p.incoming&&v.response===p.response))pairs.push(p);}if(pairs.length>20){setError('Keep at most 20 pairs per voice.');return;}update({pairs});setPreview([]);}}>Add selected to voice</button> <button type="button" className="secondary" onClick={()=>setPreview([])}>Cancel suggestions</button></section>}
 <p className="muted">Examples are stored locally when you save. New drafts use the relevant saved voice with your configured model. Removing an example does not erase old draft snapshots.</p><p role="status">{notice}</p><button disabled={busy||loading} onClick={onSave}>Save my voice</button>
 </section>;
}
