import {useState} from 'react';
import {VoiceEditor,voiceOf,type VoiceProps} from './VoiceEditor';
import {GhostMark} from './GhostMark';
export type Contact={name:string;address:string;source:string};
export function ContactsPanel({contacts,demo,busy,locked,onAdd,onRemove,voice}:{contacts:Contact[];demo:boolean;busy:boolean;locked:boolean;onAdd:(name:string,number:string)=>Promise<boolean>;onRemove:(address:string)=>void;voice:VoiceProps}){
 const [name,setName]=useState('');
 const [number,setNumber]=useState('');
 const ready=!!name.trim()&&!!number.trim();
 return <div className="contacts">
 {demo?<p className="muted">Demo mode uses synthetic contacts. Switch to live mode to add your own.</p>:<form className="card add-contact" onSubmit={async e=>{e.preventDefault();if(ready&&await onAdd(name,number)){setName('');setNumber('');}}}>
  <label>Name<input value={name} maxLength={100} disabled={busy} onChange={e=>setName(e.target.value)}/></label>
  <label>Number (include country code)<input value={number} placeholder="+14155550123" disabled={busy} onChange={e=>setNumber(e.target.value)}/></label>
  <button disabled={busy||!ready}>Add contact</button>
  {/* <small className="muted">Include the country code.</small> */}
 </form>}
 {locked&&<p className="muted">Save or discard your reply edit before removing a contact.</p>}
 <div className="people">
 <section className="card contact default" aria-label="Default voice"><div className="contact-head"><GhostMark size={32}/><div><strong>Default voice</strong><span className="muted">Used for everyone, unless a person's card adds to it.</span></div></div><VoiceEditor scope="" busy={busy} {...voice}/></section>
 {contacts.map(c=>{const v=voiceOf(voice.saved,c.address),personal=!!(v.style.trim()||v.examples.length||v.pairs.length);return <section className="card contact" key={c.address} aria-label={c.name||c.address}><div className="contact-head"><div className="avatar" aria-hidden="true">{(c.name||c.address)[0].toUpperCase()}</div><div><strong>{c.name||c.address}</strong>{c.name&&<span className="muted">{c.address}</span>}<small className="voice-status" data-tone={personal?'ready':''}>{personal?'Personal voice':'Uses default voice'}</small></div>{c.source==='env'&&<small className="muted">from .env</small>}{c.source==='app'&&<button type="button" className="secondary" disabled={busy||locked} aria-label={'Remove '+(c.name||c.address)} onClick={()=>onRemove(c.address)}>Remove</button>}</div><VoiceEditor scope={c.address} busy={busy} label={c.name||c.address} {...voice}/></section>;})}
 </div>
 {contacts.length===0&&<p className="muted">No contacts yet.</p>}
 </div>;
}
