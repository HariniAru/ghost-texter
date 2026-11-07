import {useEffect,useRef,useState,type ReactNode} from 'react';
type Pair={incoming:string;response:string};
type Voice={style:string;examples:string[];pairs:Pair[]};
export type Profile=Voice&{recipients:Record<string,Voice>};
export function normalizeProfile(value:Partial<Profile>):Profile{
 return {style:value.style||'',examples:value.examples||[],pairs:value.pairs||[],recipients:value.recipients||{}};
}
const empty=():Voice=>({style:'',examples:[],pairs:[]});
// An empty scope is the default voice; otherwise it is a contact's exact address.
export const voiceOf=(p:Profile,scope:string):Voice=>scope?p.recipients[scope]||empty():{style:p.style,examples:p.examples,pairs:p.pairs};
export const withVoice=(p:Profile,scope:string,voice:Voice):Profile=>scope?{...p,recipients:{...p.recipients,[scope]:voice}}:{...p,...voice};
export type VoiceProps={profile:Profile;saved:Profile;onChange:(p:Profile)=>void;onSave:(scope:string)=>Promise<void>;suggest:(r:string)=>Promise<{pairs:Pair[]}>};
// A voice is edited in a pop-up so the cards on the People page never move.
function VoiceDialog({title,onClose,actions,children}:{title:string;onClose:()=>void;actions:ReactNode;children:ReactNode}){
 const node=useRef<HTMLDialogElement>(null);
 useEffect(()=>{const d=node.current;d?.showModal();d?.querySelector('textarea')?.focus();return()=>d?.close();},[]);
 return <dialog ref={node} className="voice-dialog" aria-labelledby="voice-title" onCancel={e=>{e.preventDefault();onClose();}}>
  <div className="voice-dialog-head"><h2 id="voice-title">{title}</h2>{actions}<button type="button" className="secondary" onClick={onClose}>Close</button></div>
  {children}
 </dialog>;
}
export function VoiceEditor({scope,busy,profile,saved,onChange,onSave,suggest,label='Default voice'}:VoiceProps&{scope:string;busy:boolean;label?:string}){
 const [open,setOpen]=useState(false),[asking,setAsking]=useState(false),visit=useRef(0);
 const [preview,setPreview]=useState<Pair[]>([]),[chosen,setChosen]=useState<number[]>([]);
 const [loading,setLoading]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const voice=voiceOf(profile,scope);
 const dirty=JSON.stringify(voice)!==JSON.stringify(voiceOf(saved,scope));
 function update(patch:Partial<Voice>){onChange(withVoice(profile,scope,{...voice,...patch}));setNotice('');}
 function editPair(index:number,patch:Partial<Pair>){update({pairs:voice.pairs.map((p,i)=>i===index?{...p,...patch}:p)});}
 async function load(){const mine=visit.current;setLoading(true);setError('');setNotice('');setPreview([]);try{const result=await suggest(scope);if(visit.current!==mine)return;setPreview(result.pairs);setChosen([]);if(!result.pairs.length)setNotice('No reliable pairs found. Add examples manually.');}catch(e){if(visit.current===mine)setError((e as Error).message);}finally{if(visit.current===mine)setLoading(false);}}
 async function save(){const mine=visit.current;setError('');setNotice('');try{await onSave(scope);if(visit.current===mine)setNotice('Voice saved.');}catch(e){if(visit.current===mine)setError((e as Error).message);}}
 const status=<p role="status">{notice||(dirty&&'Unsaved voice changes.')}</p>;
 const saveButton=<button disabled={busy||loading} onClick={()=>void save()}>Save my voice</button>;
 const body=<><fieldset disabled={busy||loading} className="voice-fields">
 <p className="muted">{scope?'Default instructions still apply. These preferences add to them; examples here replace default examples. Leave examples empty to use defaults.':'Defaults apply when a chat has no personal examples.'}</p>
 <label>How should your replies sound?<textarea maxLength={2000} value={voice.style} onChange={e=>update({style:e.target.value})}/></label>
 <label>Examples written by you (one message per line)<textarea className="examples" value={voice.examples.join('\n')} onChange={e=>update({examples:e.target.value.split('\n')})}/></label>
 <h3>Incoming and reply examples</h3>{voice.pairs.map((pair,i)=><div className="voice-pair" key={i}><label>Incoming message {i+1}<textarea maxLength={2000} value={pair.incoming} onChange={e=>editPair(i,{incoming:e.target.value})}/></label><label>My response {i+1}<textarea maxLength={2000} value={pair.response} onChange={e=>editPair(i,{response:e.target.value})}/></label><button type="button" className="secondary" onClick={()=>update({pairs:voice.pairs.filter((_,n)=>n!==i)})}>Remove example {i+1}</button></div>)}
 <button type="button" className="secondary" disabled={voice.pairs.length>=20} onClick={()=>update({pairs:[...voice.pairs,{incoming:'',response:''}]})}>Add example pair</button>
 {scope&&<div><p className="muted">Read this chat’s recent window to suggest examples. Preview is not saved, does not call a model, and never sends messages.</p><button type="button" className="secondary" onClick={()=>void load()}>Suggest examples from this chat</button></div>}
 </fieldset>
 {loading&&<p role="status">Reading example candidates…</p>}{error&&<p className="error" role="alert">{error}</p>}
 {preview.length>0&&<section aria-label="Suggested examples"><h3>Review suggested examples</h3><p>Only selected pairs will be added. Edit them here, then add and save your voice.</p>{preview.map((pair,i)=><div className="voice-pair" key={i}><label className="auto-refresh"><input type="checkbox" checked={chosen.includes(i)} onChange={e=>setChosen(ids=>e.target.checked?[...ids,i]:ids.filter(n=>n!==i))}/>Include suggestion {i+1}</label><label>Suggested incoming message {i+1}<textarea value={pair.incoming} maxLength={2000} onChange={e=>setPreview(rows=>rows.map((p,n)=>n===i?{...p,incoming:e.target.value}:p))}/></label><label>Suggested response {i+1}<textarea value={pair.response} maxLength={2000} onChange={e=>setPreview(rows=>rows.map((p,n)=>n===i?{...p,response:e.target.value}:p))}/></label></div>)}<button type="button" disabled={busy||!chosen.length} onClick={()=>{const pairs=[...voice.pairs];for(const i of chosen){const p=preview[i];if(!pairs.some(v=>v.incoming===p.incoming&&v.response===p.response))pairs.push(p);}if(pairs.length>20){setError('Keep at most 20 pairs per voice.');return;}update({pairs});setPreview([]);}}>Add selected to voice</button> <button type="button" className="secondary" onClick={()=>setPreview([])}>Cancel suggestions</button></section>}
 <p className="muted">Examples are stored locally when you save. New drafts use the relevant saved voice with your configured model. Removing an example does not erase old draft snapshots.</p></>;
 // Closing the pop-up clears its messages and any suggestions. Only the saved voice stays.
 const leave=()=>{visit.current++;setPreview([]);setChosen([]);setNotice('');setError('');setLoading(false);setAsking(false);setOpen(false);};
 const close=()=>{if(dirty)setAsking(true);else leave();};
 const discard=()=>{onChange(withVoice(profile,scope,voiceOf(saved,scope)));leave();};
 return <div className="voice-launch"><button type="button" className="secondary" onClick={()=>setOpen(true)}>Customize voice</button>{dirty&&<small className="muted">Unsaved changes</small>}
  {open&&<VoiceDialog title={scope?'Voice for '+label:label} onClose={close} actions={<>{status}{saveButton}</>}>
   {asking&&<div className="error" role="alert"><p>Discard your unsaved changes?</p><div className="actions"><button type="button" className="secondary" onClick={()=>setAsking(false)}>Keep editing</button><button type="button" onClick={discard}>Discard changes</button></div></div>}
   <div className="voice">{body}</div>
  </VoiceDialog>}
 </div>;
}
