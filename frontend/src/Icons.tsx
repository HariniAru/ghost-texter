// Small icon set drawn to match the ghost: 24px grid, 2px rounded stroke, Fern Ink, no fill.
const base={viewBox:'0 0 24 24',width:16,height:16,fill:'none',stroke:'currentColor',strokeWidth:2,strokeLinecap:'round' as const,strokeLinejoin:'round' as const,'aria-hidden':true,focusable:false,className:'icon'};
export const InboxIcon=()=><svg {...base}><path d="M3 13h5.5l1.2 2.5h4.6l1.2-2.5H21"/><path d="M5.2 5h13.6a1 1 0 0 1 .95.7L21 13v5a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18v-5l1.25-7.3A1 1 0 0 1 5.2 5Z"/></svg>;
export const PeopleIcon=()=><svg {...base}><circle cx="12" cy="8" r="3.5"/><path d="M5 20v-1a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v1"/></svg>;
export const SendIcon=()=><svg {...base}><path d="M21 3 10.5 13.5"/><path d="M21 3l-6.5 18-4-7.5L3 9.5 21 3Z"/></svg>;
