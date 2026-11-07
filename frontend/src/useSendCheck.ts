import {useEffect, useRef, useState} from 'react';

const CHECKS=4,EVERY_MS=10000;

// Looks for interrupted sends in Messages over about 30 seconds. Only ever reads; never sends.
export function useSendCheck(ids:string[],connected:boolean,check:(id:string)=>Promise<unknown>){
 const [finished,setFinished]=useState<string[]>([]);
 const tries=useRef(new Map<string,number>());
 const loader=useRef(check);
 loader.current=check;
 const waiting=ids.filter(id=>!finished.includes(id)).join(' ');
 useEffect(()=>{
  if(!connected||!waiting)return;
  let running=false;
  async function run(){
   if(running)return;
   running=true;
   for(const id of waiting.split(' ')){
    const count=(tries.current.get(id)||0)+1;
    if(count>CHECKS)continue;
    tries.current.set(id,count);
    try{await loader.current(id);}catch{/* A failed check counts as not found. */}
    if(count===CHECKS)setFinished(done=>[...done,id]);
   }
   running=false;
  }
  void run();
  const timer=setInterval(()=>void run(),EVERY_MS);
  return()=>clearInterval(timer);
 },[connected,waiting]);
 return finished;
}
