import {useEffect, useRef} from 'react';

type Props = {
  draft: {recipient:string; text:string; version:number};
  demo:boolean;
  sendEnabled:boolean;
  busy:boolean;
  onCancel:()=>void;
  onConfirm:()=>void;
};

export function SendConfirmation({draft,demo,sendEnabled,busy,onCancel,onConfirm}:Props){
 const dialog=useRef<HTMLDialogElement>(null);
 useEffect(()=>{const node=dialog.current;node?.showModal();return()=>node?.close();},[]);
 return <dialog ref={dialog} className="send-confirmation" aria-labelledby="send-title"
   onCancel={e=>{e.preventDefault();if(!busy)onCancel();}}>
  <h2 id="send-title">{demo?'Confirm simulated send':'Confirm message send'}</h2>
  <p>{demo?'This is a demo. No real text will leave the app.':'Confirming will send this exact saved reply through Messages.'}</p>
  <p className="eyebrow">TO</p><p className="send-recipient">{draft.recipient}</p>
  <p className="eyebrow">SAVED REPLY · VERSION {draft.version}</p><pre>{draft.text}</pre>
  {!demo&&!sendEnabled&&<p role="status" className="error">Live sending is disabled. To perform your first send, set GHOST_SEND_ENABLED=true in .env and restart the backend. You will still need to approve each message.</p>}
  <p className="muted">The conversation will be checked again before dispatch. A connector acknowledgment does not guarantee delivery.</p>
  <div className="actions"><button type="button" autoFocus className="secondary" disabled={busy} onClick={onCancel}>Back to editing</button>
   <button type="button" disabled={busy||(!demo&&!sendEnabled)} onClick={onConfirm}>{busy?'Sending…':demo?'Confirm simulated send':'Confirm & send'}</button></div>
 </dialog>;
}
