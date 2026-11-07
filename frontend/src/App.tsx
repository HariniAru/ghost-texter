import {readApiResponse} from './apiResponse';
import {normalizeProfile, voiceOf, withVoice, type Profile} from './VoiceEditor';
import {useCallback, useEffect, useRef, useState, useMemo} from 'react';
import {ContactsPanel,type Contact} from './ContactsPanel';
import {SendConfirmation} from './SendConfirmation';
import {GhostMark} from './GhostMark';
import {InboxIcon,PeopleIcon,SendIcon} from './Icons';
import {splitThread,whenLabel,previewOf,lastIncoming,type Message} from './thread';
import {useInboxRefresh} from './useInboxRefresh';
import {useAutoPrepare} from './useAutoPrepare';
import {useSendCheck} from './useSendCheck';

type Draft = {id:string; recipient:string; context:string; fingerprint:string; text:string; version:number; status:string; receipt?:string};
type Conversation = {recipient:string; preview:string; unread_count:number; count_capped:boolean};
type Detail = {recipient:string; context:string; fingerprint:string; summary:string|null; summary_kind:'ai'|'excerpt'|null};
type Preparation = {created:boolean;reason:string;draft:Draft|null};
type Status = {mode:string; llm:boolean; send_enabled:boolean};
// How long after the last keystroke the reply is saved as the chat's draft.
const AUTOSAVE_MS=1200;
// The draft a chat shows: an interrupted send comes first, since it needs a decision.
const chatDraft=(rows:Draft[],recipient:string)=>rows.find(d=>d.recipient===recipient&&d.status==='uncertain')||rows.find(d=>d.recipient===recipient&&d.status==='pending');
const hasNewMessages=(d:Draft,c?:Conversation)=>!!c&&c.unread_count>0&&!d.context.includes(c.preview);
export function App(){
 const [token,setToken]=useState(sessionStorage.getItem('ghost-token')||'');
 const [connected,setConnected]=useState(false);
 const [status,setStatus]=useState<Status>();
 const [drafts,setDrafts]=useState<Draft[]>([]);
 const [detail,setDetail]=useState<Detail>();
 const [selected,setSelected]=useState('');
 const [confirmDraft,setConfirmDraft]=useState<Draft>();
 const [sentReceipt,setSentReceipt]=useState<{recipient:string;receipt?:string}>();
 const [contacts,setContacts]=useState<Contact[]>([]);
 const [removedContacts,setRemovedContacts]=useState<string[]>([]);
 const [text,setText]=useState('');
 const [error,setError]=useState('');
 const [busy,setBusy]=useState(false);
 // The chat whose reply is being drafted. Drafting only affects that chat's reply box.
 const [drafting,setDrafting]=useState('');
 const [draftError,setDraftError]=useState('');
 // Text that Clear or a new draft just replaced, so Undo can put it back. Never sent anywhere.
 const [undo,setUndo]=useState<{recipient:string;text:string;why:'cleared'|'replaced'}>();
 const [saveFailed,setSaveFailed]=useState(false),[saveReason,setSaveReason]=useState('');
 // The chat being opened. Only its row shows progress; the open chat stays until it loads.
 const [opening,setOpening]=useState('');
 const [summaryError,setSummaryError]=useState<{fingerprint:string;message:string}>();
 const [tab,setTab]=useState('inbox');
 // The Earlier messages fold starts open and only changes when the user toggles it.
 const [showMessages,setShowMessages]=useState(true);
 const [profile,setProfile]=useState<Profile>(normalizeProfile({}));
 const [savedProfile,setSavedProfile]=useState<Profile>(normalizeProfile({}));
 const draft=drafts.find(d=>d.id===selected);
 const openRecipient=useRef('');
 const replyRef=useRef<HTMLTextAreaElement>(null);
 const optionsRef=useRef<HTMLDetailsElement>(null);
 // After Clear or Undo the button you were on may disable itself, so keep your place in the box.
 const focusReply=()=>setTimeout(()=>replyRef.current?.focus(),0);
 openRecipient.current=detail?.recipient||'';
 const unsaved=!!detail&&draft?.status!=='uncertain'&&text!==(draft?.text??'');
 const nameOf=(address:string)=>contacts.find(c=>c.address===address)?.name||address;
 const api=useCallback(async(path:string,method='GET',body?:unknown,signal?:AbortSignal)=>{
  const res=await fetch('/api'+path,{method,signal,headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
  return await readApiResponse(res);
 },[token]);
 const checkSend=useCallback(async(id:string)=>{const d:Draft=await api('/drafts/'+id+'/verify','POST');if(d.status==='sent'){setSentReceipt({recipient:d.recipient,receipt:d.receipt});setDrafts(rows=>rows.filter(r=>r.id!==d.id));setDetail(v=>v?.recipient===d.recipient?undefined:v);}},[api]);
 const checkedSends=useSendCheck(drafts.filter(d=>d.status==='uncertain').map(d=>d.id),connected,checkSend);
 const loadInbox=useCallback((signal:AbortSignal)=>api('/inbox','GET',undefined,signal),[api]);
 const {items:loadedInbox,autoRefresh,setAutoRefresh,refreshing:inboxRefreshing,lastSuccess,error:inboxError,refresh:refreshInbox}=useInboxRefresh<Conversation>(loadInbox,connected,busy||!!drafting||!!opening||!!confirmDraft);
 // A removed contact leaves the list at once, even if an older refresh is still in flight.
 const inbox=useMemo(()=>loadedInbox.filter(c=>!removedContacts.includes(c.recipient)),[loadedInbox,removedContacts]);
 // Unread chats, then chats with nothing unread that still have a saved draft or a send to check.
 const chats=useMemo(()=>{const rows=[...inbox];for(const d of drafts){if(rows.some(c=>c.recipient===d.recipient))continue;if(d.status==='uncertain'||(d.status==='pending'&&contacts.some(c=>c.address===d.recipient)))rows.push({recipient:d.recipient,preview:lastIncoming(d.context),unread_count:0,count_capped:false});}return rows;},[inbox,drafts,contacts]);
 const contextChanged=draft?.status==='pending'&&detail?.recipient===draft.recipient&&detail.fingerprint!==draft.fingerprint;
 const outdated=!!draft&&draft.status==='pending'&&(contextChanged||hasNewMessages(draft,inbox.find(c=>c.recipient===draft.recipient)));
 const prepareUnread=useCallback((recipient:string,signal:AbortSignal)=>api('/inbox/prepare','POST',{recipient},signal),[api]);
 const receivePreparation=useCallback((result:Preparation)=>{if(result.created&&result.draft){const next=result.draft;setDrafts(rows=>rows.some(d=>d.id===next.id)?rows:[next,...rows]);}},[]);
 const {enabled:autoPrepare,setEnabled:setAutoPrepare,working:preparing,error:prepareError,retry:retryPreparation}=useAutoPrepare<Preparation>(inbox,connected,busy||!!drafting||!!opening||!!confirmDraft||!!unsaved||inboxRefreshing,prepareUnread,receivePreparation);
 async function refresh(){const rows=await api('/drafts');setDrafts(rows);return rows;}
 async function run(action:()=>Promise<void>){setBusy(true);setError('');setSentReceipt(undefined);try{await action();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 async function openConversation(r:string){if(unsaved&&!drafting)await saveReply();setDraftError('');setUndo(undefined);await refresh();const value:Detail=await api('/conversation?summary=false&recipient='+encodeURIComponent(r));setSelected('');setText('');setDetail(value);if(!value.summary)void loadSummary(value);}
 // Fills in the summary of the messages on screen, unless the user has moved on by then.
 async function loadSummary(d:Detail){setSummaryError(undefined);const same=(v?:Detail)=>v?.recipient===d.recipient&&v.fingerprint===d.fingerprint;try{const s=await api('/conversation/summary?recipient='+encodeURIComponent(d.recipient)+'&fingerprint='+d.fingerprint);setDetail(v=>same(v)&&v?{...v,...s}:v);}catch(e){setSummaryError({fingerprint:d.fingerprint,message:(e as Error).message});}}
 function openChat(r:string){
  if(opening)return;
  setOpening(r);setError('');setSentReceipt(undefined);
  openConversation(r).catch(e=>setError((e as Error).message)).finally(()=>setOpening(''));
 }
 async function connect(){await run(async()=>{const s=await api('/status');setStatus(s);const p=normalizeProfile(await api('/profile'));setProfile(p);setSavedProfile(p);setContacts(await api('/contacts'));await refresh();sessionStorage.setItem('ghost-token',token);setConnected(true);});}
 useEffect(()=>{if(!connected)return; const id=setInterval(()=>{if(!busy&&!drafting&&!opening)refresh().catch(()=>{});},10000);return()=>clearInterval(id);},[connected,busy,drafting,opening]);
 useEffect(()=>{if(!confirmDraft)return;const current=drafts.find(d=>d.id===confirmDraft.id);if(!current||current.status!=='pending'||current.version!==confirmDraft.version||current.text!==confirmDraft.text||current.recipient!==confirmDraft.recipient)setConfirmDraft(undefined);},[drafts,confirmDraft]);
 // The reply box follows the open chat's saved draft, including one that finishes while the chat is open.
 useEffect(()=>{
  if(!detail)return;
  if(selected&&!draft){setSelected('');setText('');return;} // Sent or discarded.
  if(draft?.status==='stale'||draft?.status==='rejected'){setSelected('');return;} // Keeps the text, so it can be sent against the latest messages.
  if(selected)return;
  const saved=chatDraft(drafts,detail.recipient);
  if(!saved)return;
  if(saved.status==='uncertain'||!text)select(saved);else setSelected(saved.id); // Never overwrite what the user is typing.
 },[detail,selected,draft,drafts,text]);
 function applyContacts(rows:Contact[]){
  const addresses=rows.map(c=>c.address);
  setContacts(rows);setRemovedContacts(gone=>[...gone.filter(a=>!addresses.includes(a)),...contacts.map(c=>c.address).filter(a=>!addresses.includes(a))]);
  if(detail&&!addresses.includes(detail.recipient)){setDetail(undefined);setSelected('');setText('');}
  void refreshInbox();
 }
 async function addContact(name:string,number:string){let added=false;await run(async()=>{applyContacts(await api('/contacts','POST',{name,number}));added=true;});return added;}
 function removeContact(address:string){void run(async()=>applyContacts(await api('/contacts?address='+encodeURIComponent(address),'DELETE')));}
 // PUT replaces the whole profile, so send this card's edits on top of what is saved. Other cards keep their unsaved edits.
 async function saveVoice(scope:string){setBusy(true);try{const voice=voiceOf(profile,scope);const result=normalizeProfile(await api('/profile','PUT',withVoice(savedProfile,scope,{...voice,examples:voice.examples.filter(e=>e.trim())})));setSavedProfile(result);setProfile(p=>withVoice(p,scope,voiceOf(result,scope)));}finally{setBusy(false);}}
 async function reloadConversation(r:string){const value:Detail=await api('/conversation?summary=false&recipient='+encodeURIComponent(r));setDetail(value);if(!value.summary)void loadSummary(value);await refresh();}
 // Replaces the reply box. If the model fails the text stays in the box, so nothing is lost.
 function replyKeys(e:React.KeyboardEvent){
  if(e.key!=='Enter'||!(e.metaKey||e.ctrlKey)||e.nativeEvent.isComposing)return;
  e.preventDefault();
  if(e.shiftKey){if(!working&&!drafting&&detail)startDraft(detail.recipient);}
  else if(!working&&text.trim()&&!contextChanged&&draft?.status!=='uncertain')run(reviewSend);
 }
 function startDraft(r:string){
  setDrafting(r);setDraftError('');setError('');setSentReceipt(undefined);
  draftReply(r,text).catch(e=>setDraftError((e as Error).message)).finally(()=>setDrafting(''));
 }
 async function draftReply(r:string,previous:string){if(draft?.status==='pending'){await rejectDraft(draft);setSelected('');}const d:Draft=await api('/drafts','POST',{recipient:r});setDrafts(rows=>[d,...rows.filter(x=>x.id!==d.id)]);if(openRecipient.current!==r){void refresh().catch(()=>{});return;}select(d);if(d.fingerprint!==detail?.fingerprint)void reloadConversation(r).catch(()=>{});if(previous.trim()&&previous!==d.text)setUndo({recipient:r,text:previous,why:'replaced'});setTimeout(()=>{if(!document.activeElement||document.activeElement===document.body)replyRef.current?.focus();},0);} // The draft shows at once. Reading the chat again only happens if new messages came in while it was written, and then in the background. If the user moved to another chat, the draft waits in this one.
 async function useLatestMessages(){const saved=await saveReply();if(!saved)return;const d=await api('/drafts/'+saved.id+'/refresh','POST',{version:saved.version});await reloadConversation(d.recipient);select(d);}
 async function retrySend(){if(!draft)return;const d:Draft=await api('/drafts/'+draft.id+'/retry','POST');if(d.status==='sent'){setSentReceipt({recipient:d.recipient,receipt:d.receipt});setDetail(undefined);setSelected('');setText('');await refresh();return;}await reloadConversation(d.recipient);select(d);}
 async function discardDraft(){if(!draft)return;await api('/drafts/'+draft.id+'/discard','POST');setSelected('');setText('');await refresh();}
 // Which dot the row shows beside its note: ready to send, waiting on a check, needs attention, or just unread.
 function rowTone(c:Conversation){const d=chatDraft(drafts,c.recipient);if(!d)return 'unread';if(d.status==='uncertain')return checkedSends.includes(d.id)?'alert':'wait';return hasNewMessages(d,c)?'alert':'ready';}
 function rowNote(c:Conversation){const d=chatDraft(drafts,c.recipient);const note=d&&(d.status==='uncertain'?(checkedSends.includes(d.id)?'Not found in Messages':'Checking if this sent'):hasNewMessages(d,c)?'New messages since draft':'Draft saved');return [c.unread_count>0&&c.unread_count+(c.count_capped?'+':'')+' unread',note].filter(Boolean).join(' · ');}
 function select(d:Draft){setSelected(d.id);setText(d.text);setError('');setSentReceipt(undefined);}
 async function rejectDraft(d:Draft){await api('/drafts/'+d.id+'/reject','POST',{version:d.version});setDrafts(rows=>rows.filter(r=>r.id!==d.id));}
 async function clearReply(){focusReply();const previous=text;if(draft?.status==='pending'){await rejectDraft(draft);setSelected('');}setText('');if(previous.trim()&&detail)setUndo({recipient:detail.recipient,text:previous,why:'cleared'});}
 // Saves the reply as the chat's pending draft. Saves run one at a time, and each one reads the current draft from the server first,
 // so a save can never use an old version or collide with another save, such as Send right after an autosave. Nothing here sends.
 const chain=useRef<Promise<unknown>>(Promise.resolve());
 function persist(recipient:string,body:string,fingerprint:string):Promise<Draft>{
  const run=chain.current.catch(()=>{}).then(async()=>{
   const rows:Draft[]=await api('/drafts');
   const pending=rows.find(d=>d.recipient===recipient&&d.status==='pending');
   if(pending)return pending.text===body?pending:await api('/drafts/'+pending.id,'PATCH',{version:pending.version,text:body});
   return await api('/drafts/typed','POST',{recipient,text:body,fingerprint});
  });
  chain.current=run;return run;
 }
 // Saves what is in the box as the chat's draft. A blank box goes back to what was saved.
 async function saveReply():Promise<Draft|undefined>{
  if(!detail||draft?.status==='uncertain')return draft;
  if(!text.trim()){setText(draft?.text??'');return draft;}
  try{const d=await persist(detail.recipient,text,detail.fingerprint);await refresh();select(d);setSaveFailed(false);return d;}
  catch(e){await reloadConversation(detail.recipient).catch(()=>{});throw e;}
 }
 // Autosave: a quiet save a moment after typing stops. It never touches the text in the box, and it pauses while anything else is running or the send dialog is open.
 useEffect(()=>{
  if(!detail||confirmDraft||drafting||opening||busy)return;
  if(draft&&draft.status!=='pending')return;
  if(!text.trim()||(draft&&text===draft.text))return;
  const recipient=detail.recipient,fingerprint=detail.fingerprint,body=text;
  const id=setTimeout(()=>{persist(recipient,body,fingerprint).then(async saved=>{setSaveFailed(false);await refresh();if(openRecipient.current===recipient)setSelected(saved.id);}).catch(e=>{setSaveReason((e as Error).message);setSaveFailed(true);});},AUTOSAVE_MS);
  return()=>clearTimeout(id);
 },[detail?.recipient,detail?.fingerprint,text,draft?.id,draft?.status,draft?.text,confirmDraft,drafting,opening,busy]);
 async function reviewSend(){const d=await saveReply();if(d)setConfirmDraft({...d});}
 function openPeople(){if(unsaved&&!drafting)void run(async()=>{await saveReply();setTab('people');});else setTab('people');}
 async function approveDraft(target:Draft){try{const result:Draft=await api('/drafts/'+target.id+'/approve','POST',{version:target.version});if(result.status==='sent'){setSentReceipt({recipient:result.recipient,receipt:result.receipt});setDrafts(rows=>rows.filter(d=>d.id!==result.id));setDetail(undefined);setSelected('');setText('');void refreshInbox();}await refresh();}catch(e){const rows:Draft[]=await refresh();if(rows.find(d=>d.id===target.id)?.status==='stale')await reloadConversation(target.recipient);throw e;}}
 // What to tell the user after a send: who it went to, then only context that adds something.
 const sent=sentReceipt&&(()=>{const demo=status?.mode==='demo',receipt=sentReceipt.receipt&&!(demo&&sentReceipt.receipt.startsWith('Simulated'))?sentReceipt.receipt:'';return {title:(demo?'Simulated send to ':'Sent to ')+nameOf(sentReceipt.recipient)+'.',detail:receipt||(demo?'No real message left this app.':'')};})();
 const sentInPane=!!sent&&tab==='inbox'&&!detail;
 const nextChat=sentReceipt?chats.find(c=>c.recipient!==sentReceipt.recipient):undefined;
 useEffect(()=>{
  const close=(e:Event)=>{const el=optionsRef.current;if(!el?.open)return;
   if(e.type==='keydown'){if((e as KeyboardEvent).key!=='Escape')return;el.open=false;el.querySelector('summary')?.focus();}
   else if(!el.contains(e.target as Node))el.open=false;};
  document.addEventListener('keydown',close);document.addEventListener('pointerdown',close);
  return()=>{document.removeEventListener('keydown',close);document.removeEventListener('pointerdown',close);};
 },[]);
 const draftingHere=!!detail&&drafting===detail.recipient;
 const working=busy||draftingHere;
 const saveError=saveFailed&&unsaved&&!!text.trim()&&draft?.status!=='uncertain';
 const saveLabel=draft?.status==='uncertain'?'Send interrupted':unsaved&&text.trim()?(saveFailed?"Couldn't save yet":'Saving…'):draft?'Saved':'Not saved yet';
 const threadRef=useRef<HTMLDivElement>(null);
 useEffect(()=>{const el=threadRef.current;if(el)el.scrollTop=el.scrollHeight;},[detail?.fingerprint,detail?.recipient]);
 const bubbles=(list:Message[])=>list.map((m,i)=><p key={i} className={'bubble'+(m.mine?' mine':'')}><span className="sr">{m.mine?'You':m.sender}: </span>{m.text}</p>);
 const parsed=detail?splitThread(detail.context,chats.find(c=>c.recipient===detail.recipient)?.unread_count):undefined;
 const thread=detail&&<>{(!parsed||parsed.earlier.length>0)&&<details open={showMessages} onToggle={e=>setShowMessages(e.currentTarget.open)}><summary>Earlier messages</summary>{parsed?<div className="earlier">{bubbles(parsed.earlier)}</div>:<pre>{detail.context}</pre>}</details>}{parsed&&parsed.unread.length>0&&<div className="unread" role="group" aria-label={'Unread from '+nameOf(detail.recipient)}><p className="muted">Unread from {nameOf(detail.recipient)}{parsed.unread[0].at&&' · '+whenLabel(parsed.unread[0].at)}</p>{bubbles(parsed.unread)}</div>}</>;
 const replyPanel = <section className="review reply"><div className="draft-label"><label htmlFor="reply">YOUR REPLY</label><small className={saveError?'save-error':undefined}>{saveLabel}</small></div>{outdated&&<div className="error" role="alert">New messages have come in since this draft. You may need to change your reply. <button type="button" className="secondary" disabled={working} onClick={()=>run(useLatestMessages)}>Use latest messages</button>{contextChanged&&<p>Use the latest messages before sending, so you approve this reply against what was actually said.</p>}</div>}<textarea id="reply" ref={replyRef} value={text} readOnly={working||!!opening} disabled={!!draft&&draft.status!=='pending'} placeholder="Write your reply, or click Draft a reply. Cmd+Enter reviews it for sending." onKeyDown={replyKeys} onChange={e=>{setText(e.target.value);setUndo(undefined);}}/>{saveError&&<p className="error" role="alert">Your reply isn't saved yet, but your text is still here. {saveReason} Keep typing or press Send to try again.</p>}<p className="muted">{status?.mode==='demo'?'Demo mode: Send does nothing, so the sample chats stay in your inbox.':'Nothing sends until you confirm this exact reply.'}</p>{undo&&undo.recipient===detail?.recipient&&<p className="undo" role="status">{undo.why==='cleared'?'Reply cleared.':'Replaced with a new draft.'} <button type="button" onClick={()=>{setText(undo.text);setUndo(undefined);focusReply();}}>Undo</button></p>}{draft?.status==='uncertain'?(checkedSends.includes(draft.id)?<div className="error" role="alert">We couldn't find this message in Messages, so it may not have sent. Check Messages if you're not sure, then choose what to do.<div className="actions"><button type="button" className="secondary" disabled={working} onClick={()=>run(discardDraft)}>Discard draft</button><button type="button" disabled={working} onClick={()=>run(retrySend)}>Try again</button></div></div>:<p className="receipt" role="status">The send was interrupted. Checking Messages to see whether it went through…</p>):<div className="actions"><button type="button" className="secondary" disabled={working||(!text&&!draft)} onClick={()=>run(clearReply)}>Clear</button><button type="button" className={'secondary'+(draftingHere?' drafting':'')} disabled={working||!!drafting} aria-busy={draftingHere} aria-keyshortcuts="Control+Shift+Enter Meta+Shift+Enter" onClick={()=>detail&&startDraft(detail.recipient)}>{draftingHere?<><GhostMark mood="drowsy" size={18}/>Drafting…</>:'Draft a reply'}</button><button type="button" disabled={working||!text.trim()||!!contextChanged} aria-keyshortcuts="Control+Enter Meta+Enter" onClick={()=>run(reviewSend)}><SendIcon/>Send<span className="keys" aria-hidden="true">Cmd+Enter</span></button></div>}{draftError&&<p className="error" role="alert">{draftError}</p>}</section>;
 if(!connected)return <main className="login"><div className="mark">g.</div><p className="eyebrow">YOUR WORDS. YOUR CALL.</p><h1>A little help<br/>keeping in touch.</h1><p>Draft thoughtful replies, make them yours, and approve every send.</p><label>Local API token<input type="password" value={token} onChange={e=>setToken(e.target.value)} autoComplete="off"/></label><small>Find it in data/api-token after starting the backend.</small><button disabled={busy||!token} onClick={connect}>Open my inbox</button>{error&&<p role="alert" className="error">{error}</p>}</main>;
 return <div className="layout"><aside><div className="brand">g<GhostMark size={15}/><span className="sr">.</span> <span>ghost texter</span></div><nav aria-label="Main"><button className={tab==='inbox'?'nav active':'nav'} aria-current={tab==='inbox'?'page':undefined} onClick={()=>setTab('inbox')}><span className="nav-label"><InboxIcon/>Inbox</span> <b>{chats.length}</b></button><button className={tab==='people'?'nav active':'nav'} aria-current={tab==='people'?'page':undefined} onClick={openPeople}><span className="nav-label"><PeopleIcon/>People</span> <b>{contacts.length}</b></button></nav><div className="aside-bottom"><span className="dot"/>{status?.mode==='demo'?'Demo workspace':'iMessage workspace'}<small>Every reply needs your approval.</small><button className="link" onClick={()=>{sessionStorage.removeItem('ghost-token');setConnected(false);}}>Lock workspace</button></div></aside><main><header><div><h1>{tab==='people'?'The people you reply to.':'Your conversations, considered.'}</h1>{tab==='people'&&<p>Your unread inbox only shows messages from these people. Customizing your voice for each one is optional.</p>}</div><span className="badge">{status?.llm?'AI drafts':'Sample drafts'} · {status?.mode}</span></header>{error&&<div className="error" role="alert">{error}</div>}{sent&&!sentInPane&&<p className="receipt" role="status" aria-label="Send receipt">{sent.title} {sent.detail}</p>}{tab==='people'?<ContactsPanel contacts={contacts} demo={status?.mode==='demo'} busy={busy} locked={!!unsaved} onAdd={addContact} onRemove={removeContact} voice={{profile,saved:savedProfile,onChange:setProfile,onSave:saveVoice,suggest:r=>api('/profile/suggestions','POST',{recipient:r})}}/>:<>
 <div className="toolbar"><p className="muted">{lastSuccess?<>Updated <time dateTime={lastSuccess.toISOString()}>{lastSuccess.toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit',second:'2-digit',hour12:true})}</time></>:'Loading inbox…'}{autoRefresh&&' · auto-refresh on'}{autoPrepare&&' · auto-drafts on'}{preparing&&' · preparing a reply…'}</p><div className="inbox-controls"><details className="inbox-options" ref={optionsRef}><summary>Options</summary><div className="inbox-options-panel"><label className="auto-refresh"><input type="checkbox" checked={autoRefresh} onChange={e=>setAutoRefresh(e.target.checked)}/>Auto-refresh every 30 seconds</label><label className="auto-refresh"><input type="checkbox" checked={autoPrepare} onChange={e=>setAutoPrepare(e.target.checked)}/>Prepare drafts automatically</label><p className="muted">Automatic drafts send unread conversations to your configured model. No message is sent without your approval.</p><p className="muted">Reading here never marks messages as read.</p></div></details><button className="secondary" disabled={busy||inboxRefreshing} onClick={()=>void refreshInbox()}>{inboxRefreshing?'Refreshing…':'Refresh inbox'}</button></div></div>
 {inboxError&&<p className="error" role="alert">Inbox refresh failed: {inboxError}. {lastSuccess?'Showing the last successful inbox.':'No inbox data has loaded yet.'}</p>}{prepareError&&<div className="error" role="alert">Automatic drafts paused: {prepareError}. <button type="button" className="secondary" disabled={preparing||busy} onClick={retryPreparation}>Retry preparation</button></div>}
 <div className="desk"><section className="list card" aria-label="Conversations">
 {chats.length===0?<div className="empty"><GhostMark asleep={!inboxError&&!inboxRefreshing&&contacts.length>0}/><h2>{inboxError?'Inbox unavailable':inboxRefreshing?'Loading inbox…':'No unread conversations.'}</h2><p>{inboxError?'Use Refresh inbox to try again.':inboxRefreshing?'Checking your contacts.':contacts.length===0?'Add someone you text to start checking for their unread messages.':'There are no unread messages or saved drafts from your contacts.'}</p>{!inboxError&&!inboxRefreshing&&contacts.length===0&&<button type="button" onClick={openPeople}><PeopleIcon/>Add a contact</button>}</div>:chats.map(c=><button disabled={busy} key={c.recipient} className={'conversation '+(detail?.recipient===c.recipient?'selected':'')} aria-current={detail?.recipient===c.recipient?'true':undefined} aria-busy={opening===c.recipient} onClick={()=>openChat(c.recipient)}><div className="avatar">{nameOf(c.recipient)[0].toUpperCase()}</div><div><span className="row-head"><strong>{nameOf(c.recipient)}</strong>{previewOf(c.preview).at&&<time dateTime={previewOf(c.preview).at!.replace(' ','T')}>{whenLabel(previewOf(c.preview).at!)}</time>}</span><span className="preview">{previewOf(c.preview).text}</span><small data-tone={opening===c.recipient?'':rowTone(c)}>{opening===c.recipient?<><span className="spinner" aria-hidden="true"/>Loading…</>:rowNote(c)}</small></div></button>)}
 </section><div className="conversation-detail">{!detail?(sent&&sentInPane?<section className="review card empty sent" role="status" aria-label="Send receipt"><GhostMark rise asleep={!nextChat}/><h2>{sent.title}</h2>{sent.detail&&<p>{sent.detail}</p>}{nextChat?<button type="button" disabled={busy||!!opening} onClick={()=>openChat(nextChat.recipient)}>Next conversation: {nameOf(nextChat.recipient)}</button>:<p>That's everything for now.</p>}</section>:<section className="review card empty"><GhostMark/><h2>Catch up at a glance.</h2><p>Select an unread conversation to see its context and summary.</p></section>):<>
 <section className="review card summary-card"><h2>{nameOf(detail.recipient)}</h2>{nameOf(detail.recipient)!==detail.recipient&&<p className="muted">{detail.recipient}</p>}{!(detail.summary_kind?detail.summary_kind==='ai':status?.llm)&&<p className="eyebrow">RECENT MESSAGE EXCERPT · AI DISABLED</p>}{detail.summary?<p className="summary">{detail.summary}</p>:summaryError?.fingerprint===detail.fingerprint?<p className="error" role="alert">Couldn't generate a summary: {summaryError.message} <button type="button" className="secondary" onClick={()=>void loadSummary(detail)}>Try again</button></p>:<p className="summary muted" role="status"><span className="spinner" aria-hidden="true"/>Generating a summary of the conversation so far…</p>}</section>
 <section className="card thread" aria-label="Conversation"><div className="thread-scroll" ref={threadRef} role="region" aria-label="Messages" tabIndex={0}>{thread}</div>{replyPanel}</section></>}</div></div>
 </>}</main>{confirmDraft&&<SendConfirmation draft={confirmDraft} demo={status?.mode==='demo'} sendEnabled={!!status?.send_enabled} busy={busy} onCancel={()=>setConfirmDraft(undefined)} onConfirm={()=>run(async()=>{try{await approveDraft(confirmDraft);}finally{setConfirmDraft(undefined);}})}/>}</div>;
}

