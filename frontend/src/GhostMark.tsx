// The ghost the product is named after. Eyes open while there is work to do, half-closed while it drafts, closed when the inbox is clear.
type GhostMood='awake'|'drowsy'|'asleep';
export function GhostMark({asleep=false,mood,rise=false,size=44}:{asleep?:boolean;mood?:GhostMood;rise?:boolean;size?:number}){
 const m=mood??(asleep?'asleep':'awake');
 return <svg className={'ghost-mark'+(rise?' rise':'')} data-state={m} viewBox="0 0 48 56" width={size} height={Math.round(size*56/48)} aria-hidden="true" focusable="false">
  <path style={{fill:'var(--avatar)',stroke:'var(--fern)'}} d="M24 4C13 4 6 12 6 24V46C6 48 8 49 9.5 47.6L14 43.5L18.5 48C19.4 48.9 20.6 48.9 21.5 48L24 45.5L26.5 48C27.4 48.9 28.6 48.9 29.5 48L34 43.5L38.5 47.6C40 49 42 48 42 46V24C42 12 35 4 24 4Z" strokeWidth={size<30?3.5:2} strokeLinejoin="round"/>
  {m==='asleep'?<path style={{stroke:'var(--fern)'}} d="M15.5 25q3 3 6 0M26.5 25q3 3 6 0" fill="none" strokeWidth={size<30?3.5:2} strokeLinecap="round"/>
   :m==='drowsy'?<path style={{fill:'var(--fern)',stroke:'var(--fern)'}} d="M15.5 25.5a3 3 0 0 1 6 0zM26.5 25.5a3 3 0 0 1 6 0z" strokeWidth="1.5" strokeLinejoin="round"/>
   :<><circle style={{fill:'var(--fern)'}} cx="18.5" cy="24" r="2.6"/><circle style={{fill:'var(--fern)'}} cx="29.5" cy="24" r="2.6"/></>}
 </svg>;
}
