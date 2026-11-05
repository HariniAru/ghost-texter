import {useCallback, useEffect, useRef, useState} from 'react';

// Refresh only inbox data. This hook cannot select chats, generate drafts, or send.
export function useInboxRefresh<T>(load:(signal:AbortSignal)=>Promise<T[]>, enabled:boolean, paused:boolean){
 const [items,setItems]=useState<T[]>([]);
 const [autoRefresh,setAutoRefresh]=useState(false);
 const [refreshing,setRefreshing]=useState(false);
 const [lastSuccess,setLastSuccess]=useState<Date>();
 const [error,setError]=useState('');
 const pending=useRef<AbortController|null>(null);
 const generation=useRef(0);
 const active=useRef(enabled);
 const pause=useRef(paused);
 const loader=useRef(load);
 active.current=enabled;pause.current=paused;loader.current=load;
 const refresh=useCallback(async()=>{
  if(!active.current||pending.current)return;
  const controller=new AbortController(), current=generation.current;
  pending.current=controller;setRefreshing(true);
  try{
   const rows=await loader.current(controller.signal);
   if(!controller.signal.aborted&&active.current&&current===generation.current){
    setItems(rows);setLastSuccess(new Date());setError('');
   }
  }catch(e){
   if(!controller.signal.aborted&&active.current&&current===generation.current)
    setError(e instanceof Error?e.message:'Unable to refresh inbox');
  }finally{
   if(pending.current===controller){pending.current=null;setRefreshing(false);}
  }
 },[]);
 useEffect(()=>{
  generation.current++;pending.current?.abort();pending.current=null;
  setItems([]);setAutoRefresh(false);setLastSuccess(undefined);setError('');setRefreshing(false);
  if(enabled)void refresh();
  return()=>{generation.current++;pending.current?.abort();pending.current=null;};
 },[enabled,load,refresh]);
 useEffect(()=>{
  if(!enabled||!autoRefresh)return;
  const timer=setInterval(()=>{if(!pause.current)void refresh();},30000);
  return()=>clearInterval(timer);
 },[enabled,autoRefresh,refresh]);
 return {items,autoRefresh,setAutoRefresh,refreshing,lastSuccess,error,refresh};
}
