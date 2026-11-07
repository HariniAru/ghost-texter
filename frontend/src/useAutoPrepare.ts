import {useEffect, useRef, useState} from 'react';

type Candidate={recipient:string;preview:string;unread_count:number};

// This queue only calls the draft-preparation endpoint, never approval/sending.
export function useAutoPrepare<T>(items:Candidate[],connected:boolean,paused:boolean,
 prepare:(recipient:string,signal:AbortSignal)=>Promise<T>,onResult:(result:T)=>void){
 const [enabled,setOn]=useState(false);
 const [working,setWorking]=useState(false);
 const [error,setError]=useState('');
 const [retryCount,setRetryCount]=useState(0);
 const attempted=useRef(new Set<string>());
 const failed=useRef('');
 const pending=useRef<AbortController|null>(null);
 const generation=useRef(0);
 const active=useRef(connected);
 const loader=useRef(prepare),receive=useRef(onResult);
 active.current=connected;loader.current=prepare;receive.current=onResult;
 useEffect(()=>{
  generation.current++;pending.current?.abort();pending.current=null;
  attempted.current.clear();setEnabled(false);setWorking(false);setError('');
  return()=>{generation.current++;pending.current?.abort();pending.current=null;};
 },[connected,prepare]);
 useEffect(()=>{
  if(!connected||!enabled||paused||working||error||pending.current)return;
  const key=(item:Candidate)=>JSON.stringify([item.recipient,item.preview,item.unread_count]);
  const candidate=items.find(item=>item.unread_count>0&&!attempted.current.has(key(item)));
  if(!candidate)return;
  const signature=key(candidate),controller=new AbortController(),current=generation.current;
  attempted.current.add(signature);pending.current=controller;setWorking(true);
  void loader.current(candidate.recipient,controller.signal).then(result=>{
   if(active.current&&!controller.signal.aborted&&generation.current===current)receive.current(result);
  }).catch(e=>{
   if(active.current&&!controller.signal.aborted&&generation.current===current){
    failed.current=signature;setError(e instanceof Error?e.message:'Unable to prepare a reply');
   }
  }).finally(()=>{
   if(pending.current===controller){pending.current=null;setWorking(false);}
  });
 },[items,connected,enabled,paused,working,error,retryCount]);
 // Turning it on starts over: every unread chat is looked at again, so ones tried earlier are not skipped.
 function setEnabled(on:boolean){if(on){attempted.current.clear();failed.current='';setError('');}setOn(on);}
 function retry(){attempted.current.delete(failed.current);setError('');setRetryCount(n=>n+1);}
 return {enabled,setEnabled,working,error,retry};
}
