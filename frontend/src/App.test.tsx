// @vitest-environment jsdom
import {act, cleanup, fireEvent, render, screen, waitFor,within} from '@testing-library/react';
import {afterEach, expect, it, vi} from 'vitest';
import {App} from './App';

HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
afterEach(()=>{cleanup();vi.useRealTimers();vi.unstubAllGlobals();sessionStorage.clear();});

it('refreshes inbox without replacing selected context, summary, unsaved edits, or generating/sending',async()=>{
 const draft={id:'draft-1',recipient:'alex@example.test',context:'Original messages',fingerprint:'original',text:'Saved reply',version:1,status:'pending'};
 let inbox=[{recipient:'alex@example.test',preview:'Original preview',unread_count:1,count_capped:false}];
 const requests:{url:string;method:string}[]=[];
 const fetchMock=vi.fn(async(url:string,options?:RequestInit)=>{
  requests.push({url,method:options?.method||'GET'});
  const data=url==='/api/status'?{mode:'demo',llm:false,send_enabled:false,recipients:[draft.recipient]}:
   url==='/api/profile'?{style:'Short',examples:[]}:
   url==='/api/contacts'?[{address:draft.recipient,source:'demo'}]:
   url==='/api/drafts'?[draft]:url==='/api/inbox'?inbox:
   url.startsWith('/api/conversation?')?{recipient:draft.recipient,context:'Original messages',fingerprint:'original',summary:'Original summary',summary_kind:'ai'}:null;
  if(data===null)throw new Error('Unexpected request');
  return new Response(JSON.stringify(data));
 });
 vi.stubGlobal('fetch',fetchMock);
 sessionStorage.setItem('ghost-token','synthetic-token');
 render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Open my inbox'}));
 await screen.findByText('Original preview');
 fireEvent.click(screen.getByRole('button',{name:/alex@example\.test.*Original preview/}));
 await screen.findByText('Original summary');
 fireEvent.change(screen.getByLabelText('YOUR REPLY'),{target:{value:'My unsaved edit'}});
 const before=requests.filter(r=>r.url.startsWith('/api/conversation?')).length;
 inbox=[];
 fireEvent.click(screen.getByRole('button',{name:'Refresh inbox'}));
 await waitFor(()=>expect(screen.queryByText('Original preview')).toBeNull());
 // The chat stays listed because it still has a saved draft.
 const savedRow=screen.getByRole('button',{name:/alex@example\.test.*Original messages/});
 // The row previews their message, never your saved reply.
 expect(savedRow.textContent).not.toContain('Saved reply');
 expect((screen.getByLabelText('YOUR REPLY') as HTMLTextAreaElement).value).toBe('My unsaved edit');
 expect(screen.getByText('Original summary')).toBeTruthy();
 vi.useFakeTimers();
 inbox=[{recipient:'maya@example.test',preview:'New incoming preview',unread_count:2,count_capped:false}];
 fireEvent.click(screen.getByRole('checkbox',{name:'Auto-refresh every 30 seconds'}));
 await act(()=>vi.advanceTimersByTimeAsync(30000));
 expect(screen.getByText('New incoming preview')).toBeTruthy();
 expect((screen.getByLabelText('YOUR REPLY') as HTMLTextAreaElement).value).toBe('My unsaved edit');
 expect(screen.getByText('Original summary')).toBeTruthy();
 expect(requests.filter(r=>r.url.startsWith('/api/conversation?'))).toHaveLength(before);
 expect(requests.some(r=>r.method!=='GET')).toBe(false);
});

function sendFlow(approve:(draft:Record<string,unknown>)=>Response){
 // jsdom has no native dialog methods.
 HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
 HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
 const draft:Record<string,unknown>={id:'draft-1',recipient:'alex@example.test',context:'Original messages',fingerprint:'original',text:'Saved reply',version:1,status:'pending'};
 const server:{rows:Record<string,unknown>[];verify?:()=>Record<string,unknown>}={rows:[draft]};
 vi.stubGlobal('fetch',vi.fn(async(url:string,options?:RequestInit)=>{
  if(url==='/api/drafts/draft-1/approve'&&options?.method==='POST')return approve(draft);
  if(url==='/api/drafts/draft-1/verify')return new Response(JSON.stringify(server.verify?.()||server.rows[0]));
  if(url==='/api/drafts/draft-1/retry'){const fresh={...draft,id:'draft-2',status:'pending'};server.rows=[fresh];return new Response(JSON.stringify(fresh));}
  if(url==='/api/drafts/draft-1/discard'){server.rows=[];return new Response(JSON.stringify({...draft,status:'discarded'}));}
  const data=url==='/api/status'?{mode:'demo',llm:false,send_enabled:false,recipients:[draft.recipient]}:
   url==='/api/profile'?{style:'Short',examples:[]}:
   url==='/api/contacts'?[{address:draft.recipient,source:'demo'}]:
   url==='/api/drafts'?server.rows:url==='/api/inbox'?[]:
   url.startsWith('/api/conversation?')?{recipient:draft.recipient,context:'Original messages',fingerprint:'original',summary:'Original summary',summary_kind:'ai'}:null;
  if(data===null)throw new Error('Unexpected request');
  return new Response(JSON.stringify(data));
 }));
 sessionStorage.setItem('ghost-token','synthetic-token');
 return server;
}

async function confirmSend(){
 render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Open my inbox'}));
 fireEvent.click(await screen.findByRole('button',{name:/alex@example\.test.*Original messages/}));
 const send=await screen.findByRole('button',{name:/^Send/,hidden:true}) as HTMLButtonElement;
 await waitFor(()=>expect(send.disabled).toBe(false));
 fireEvent.click(send);
 fireEvent.click(await screen.findByRole('button',{name:'Confirm simulated send',hidden:true}));
}

it('opens the send confirmation with Cmd+Enter but never sends, and ignores it with no text',async()=>{
 const approve=vi.fn(()=>new Response('{}'));
 sendFlow(approve);
 render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Open my inbox'}));
 fireEvent.click(await screen.findByRole('button',{name:/alex@example\.test.*Original messages/}));
 const box=await screen.findByLabelText('YOUR REPLY') as HTMLTextAreaElement;
 await waitFor(()=>expect(box.value).not.toBe(''));
 fireEvent.keyDown(box,{key:'Enter'});
 expect(screen.queryByRole('button',{name:'Confirm simulated send',hidden:true})).toBeNull();
 fireEvent.keyDown(box,{key:'Enter',metaKey:true});
 expect(await screen.findByRole('button',{name:'Confirm simulated send',hidden:true})).toBeTruthy();
 expect(approve).not.toHaveBeenCalled();
});

it('shows the receipt after a send and removes the sent draft from the saved list',async()=>{
 const server=sendFlow(draft=>{server.rows=[];return new Response(JSON.stringify({...draft,status:'sent',receipt:'Simulated send; no message left this app.'}));});
 await confirmSend();
 const receipt=await screen.findByRole('status',{name:'Send receipt'});
 expect(receipt.textContent).toContain('Simulated send to alex@example.test.');
 expect(receipt.textContent).toContain('No real message left this app.');
 // Said once: the backend's own "Simulated send; …" wording is not repeated after the heading.
 expect(receipt.textContent).not.toContain('Simulated send;');
 expect(receipt.textContent).toContain("That's everything for now.");
 // Nothing is left, so the ghost is resting.
 expect(receipt.querySelector('.ghost-mark')?.getAttribute('data-state')).toBe('asleep');
 // The receipt replaces the empty pane instead of sitting above the page.
 expect(receipt.closest('.conversation-detail')).toBeTruthy();
 expect(screen.queryByRole('button',{name:/alex@example\.test.*Original messages/})).toBeNull();
 expect(screen.queryByLabelText('YOUR REPLY')).toBeNull();
});

it('keeps an uncertain send visible with its warning and shows no receipt',async()=>{
 const server=sendFlow(draft=>{server.rows=[{...draft,status:'uncertain'}];return new Response(JSON.stringify({detail:'Send outcome unknown. Verify in Messages; this draft cannot be retried.'}),{status:502});});
 await confirmSend();
 expect(await screen.findByText(/Checking Messages to see whether it went through/)).toBeTruthy();
 expect(screen.getByRole('button',{name:/alex@example\.test.*Original messages/})).toBeTruthy();
 expect(screen.queryByRole('status',{name:'Send receipt'})).toBeNull();
});

async function interruptedSend(){
 const server=sendFlow(()=>new Response('{}'));
 server.rows=[{...server.rows[0],status:'uncertain'}];
 return server;
}

async function afterChecksFail(){
 vi.useFakeTimers({shouldAdvanceTime:true});
 render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Open my inbox'}));
 fireEvent.click(await screen.findByRole('button',{name:/alex@example\.test.*Checking if this sent/}));
 await screen.findByText(/Checking Messages to see whether it went through/);
 expect(screen.queryByRole('button',{name:'Try again'})).toBeNull();
 expect(screen.queryByRole('button',{name:/^Send/})).toBeNull();
 expect(screen.queryByRole('button',{name:/Draft a reply/})).toBeNull();
 expect(screen.queryByRole('button',{name:'Clear'})).toBeNull();
 await act(()=>vi.advanceTimersByTimeAsync(31000));
 await screen.findByText(/couldn't find this message in Messages/);
}

it('marks an interrupted send as sent once it is found in Messages',async()=>{
 const server=await interruptedSend();
 server.verify=()=>{const found={...server.rows[0],status:'sent',receipt:'Found in Messages.'};server.rows=[];return found;};
 render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Open my inbox'}));
 expect((await screen.findByRole('status',{name:'Send receipt'})).textContent).toContain('Found in Messages.');
 expect(screen.queryByRole('button',{name:/alex@example\.test/})).toBeNull();
});

it('offers try again only after the checks fail, and needs a fresh review to send',async()=>{
 await interruptedSend();
 await afterChecksFail();
 fireEvent.click(screen.getByRole('button',{name:'Try again'}));
 await screen.findByText('Saved');
 expect((screen.getByRole('button',{name:/^Send/}) as HTMLButtonElement).disabled).toBe(false);
 expect((screen.getByLabelText('YOUR REPLY') as HTMLTextAreaElement).value).toBe('Saved reply');
 const calls=vi.mocked(fetch).mock.calls.map(c=>String(c[0]));
 expect(calls).toContain('/api/drafts/draft-1/retry');
 expect(calls.some(u=>u.endsWith('/approve'))).toBe(false);
});

it('discards a failed send so the chat leaves the inbox',async()=>{
 await interruptedSend();
 await afterChecksFail();
 fireEvent.click(screen.getByRole('button',{name:'Discard draft'}));
 await waitFor(()=>expect(screen.queryByRole('button',{name:/alex@example\.test/})).toBeNull());
 expect((screen.getByLabelText('YOUR REPLY') as HTMLTextAreaElement).value).toBe('');
 expect(vi.mocked(fetch).mock.calls.some(c=>String(c[0]).endsWith('/approve'))).toBe(false);
});

it('warns about new messages and only allows sending after moving to the latest messages',async()=>{
 let row={id:'draft-1',recipient:'alex@example.test',context:'Old messages',fingerprint:'old',text:'Saved reply',version:1,status:'pending'};
 const posts:string[]=[];
 vi.stubGlobal('fetch',vi.fn(async(url:string,options?:RequestInit)=>{
  if(url==='/api/drafts/draft-1'&&options?.method==='PATCH'){
   posts.push(url+String(options.body));
   row={...row,text:JSON.parse(String(options.body)).text,version:2};
   return new Response(JSON.stringify(row));
  }
  if(url==='/api/drafts/draft-1/refresh'&&options?.method==='POST'){
   posts.push(url+String(options.body));
   row={...row,context:'Old messages\nAlex: new message',fingerprint:'new',version:row.version+1};
   return new Response(JSON.stringify(row));
  }
  const data=url==='/api/status'?{mode:'demo',llm:false,send_enabled:false}:
   url==='/api/profile'?{style:'Short',examples:[]}:
   url==='/api/contacts'?[{address:row.recipient,source:'demo'}]:
   url==='/api/drafts'?[row]:url==='/api/inbox'?[{recipient:row.recipient,preview:'Alex: new message',unread_count:1,count_capped:false}]:
   url.startsWith('/api/conversation?')?{recipient:row.recipient,context:'Old messages\nAlex: new message',fingerprint:'new',summary:'Summary',summary_kind:'ai'}:null;
  if(data===null)throw new Error('Unexpected request');
  return new Response(JSON.stringify(data));
 }));
 sessionStorage.setItem('ghost-token','synthetic-token');
 render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Open my inbox'}));
 fireEvent.click(await screen.findByRole('button',{name:/alex@example\.test.*New messages since draft/}));
 await screen.findByText(/New messages have come in/);
 expect((screen.getByRole('button',{name:/^Send/}) as HTMLButtonElement).disabled).toBe(true);

 // An unsaved edit is saved first, so nothing typed is lost.
 fireEvent.change(screen.getByLabelText('YOUR REPLY'),{target:{value:'Edited reply'}});
 fireEvent.click(screen.getByRole('button',{name:'Use latest messages'}));
 await waitFor(()=>expect((screen.getByRole('button',{name:/^Send/}) as HTMLButtonElement).disabled).toBe(false));
 expect(screen.queryByText(/New messages have come in/)).toBeNull();
 expect((screen.getByLabelText('YOUR REPLY') as HTMLTextAreaElement).value).toBe('Edited reply');
 expect(screen.getByText('Saved')).toBeTruthy();
 expect(posts).toEqual(['/api/drafts/draft-1{"version":1,"text":"Edited reply"}','/api/drafts/draft-1/refresh{"version":2}']);
});

it('offers a way to People when there are no contacts yet',async()=>{
 vi.stubGlobal('fetch',vi.fn(async(url:string)=>{
  const data=url==='/api/status'?{mode:'imessage',llm:false,send_enabled:false,recipients:[]}:
   url==='/api/profile'?{style:'Short',examples:[]}:
   url==='/api/contacts'||url==='/api/drafts'||url==='/api/inbox'?[]:null;
  if(data===null)throw new Error('Unexpected request');
  return new Response(JSON.stringify(data));
 }));
 sessionStorage.setItem('ghost-token','synthetic-token');
 render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Open my inbox'}));
 fireEvent.click(await screen.findByRole('button',{name:'Add a contact'}));
 expect(await screen.findByLabelText(/^Number/)).toBeTruthy();
 expect(screen.queryByRole('button',{name:'Add a contact'})).toBeNull();
});

it('manages people on their own tab, saves one card at a time, and shows only those people in the inbox',async()=>{
 const phone='+14155550123',env='maya@example.test';
 const server={contacts:[{name:'',address:env,source:'env'}]};
 const convo=(recipient:string)=>({recipient,preview:'Preview for '+recipient,unread_count:1,count_capped:false});
 const requests:string[]=[];
 const saved:{style:string;recipients:Record<string,{style:string}>}[]=[];
 vi.stubGlobal('fetch',vi.fn(async(url:string,options?:RequestInit)=>{
  const method=options?.method||'GET';
  if(method!=='GET')requests.push(method+' '+url);
  if(url==='/api/contacts'&&method==='POST'){
   const {name,number}=JSON.parse(String(options?.body));
   if(number==='bad')return new Response(JSON.stringify({detail:"Could not add 'bad'."}),{status:422});
   server.contacts=[...server.contacts,{name,address:number,source:'app'}];
   return new Response(JSON.stringify(server.contacts));
  }
  if(url==='/api/profile'&&method==='PUT'){saved.push(JSON.parse(String(options?.body)));return new Response(String(options?.body));}
  if(url.startsWith('/api/contacts?')&&method==='DELETE'){
   server.contacts=server.contacts.filter(c=>c.address!==new URLSearchParams(url.split('?')[1]).get('address'));
   return new Response(JSON.stringify(server.contacts));
  }
  const data=url==='/api/status'?{mode:'imessage',llm:false,send_enabled:false,recipients:server.contacts.map(c=>c.address)}:
   url==='/api/profile'?{style:'Short',examples:[]}:
   url==='/api/contacts'?server.contacts:url==='/api/drafts'?[]:
   url==='/api/inbox'?server.contacts.map(c=>convo(c.address)):null;
  if(data===null)throw new Error('Unexpected request');
  return new Response(JSON.stringify(data));
 }));
 sessionStorage.setItem('ghost-token','synthetic-token');
 render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Open my inbox'}));
 await screen.findByText('Preview for '+env);
 expect(screen.queryByLabelText(/^Number/)).toBeNull();
 expect(screen.queryByRole('button',{name:/My voice/})).toBeNull();

 fireEvent.click(screen.getByRole('button',{name:/^People/}));
 expect(screen.queryByText('Preview for '+env)).toBeNull();
 const number=screen.getByLabelText(/^Number/) as HTMLInputElement;
 fireEvent.change(screen.getByLabelText('Name'),{target:{value:'Sam'}});
 fireEvent.change(number,{target:{value:'bad'}});
 fireEvent.click(screen.getByRole('button',{name:'Add contact'}));
 expect((await screen.findByRole('alert')).textContent).toContain("Could not add 'bad'.");
 expect(number.value).toBe('bad');

 fireEvent.change(number,{target:{value:phone}});
 fireEvent.click(screen.getByRole('button',{name:'Add contact'}));
 await screen.findByRole('button',{name:'Remove Sam'});
 expect(number.value).toBe('');

 // Saving Sam's card sends Sam's edit, not the unsaved edit on the default card.
 const sam=within(screen.getByRole('region',{name:'Sam'})),byDefault=within(screen.getByRole('region',{name:'Default voice'}));
 fireEvent.click(byDefault.getByRole('button',{name:'Customize voice'}));
 fireEvent.click(sam.getByRole('button',{name:'Customize voice'}));
 fireEvent.change(byDefault.getByLabelText('How should your replies sound?'),{target:{value:''}});
 fireEvent.change(sam.getByLabelText('How should your replies sound?'),{target:{value:'Curt'}});
 fireEvent.click(sam.getByText('Save my voice'));
 await sam.findByText('Voice saved.');
 expect(saved[0].style).toBe('Short');
 expect(saved[0].recipients[phone].style).toBe('Curt');
 expect(byDefault.getByText('Unsaved voice changes.')).toBeTruthy();

 fireEvent.click(screen.getByRole('button',{name:/^Inbox/}));
 await screen.findByText('Preview for '+phone);
 expect(screen.getByText('Sam')).toBeTruthy();

 fireEvent.click(screen.getByRole('button',{name:/^People/}));
 expect(within(screen.getByRole('region',{name:'Default voice'})).getByText('Unsaved changes')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Remove Sam'}));
 await waitFor(()=>expect(screen.queryByRole('button',{name:'Remove Sam'})).toBeNull());
 fireEvent.click(screen.getByRole('button',{name:/^Inbox/}));
 await screen.findByText('Preview for '+env);
 expect(screen.queryByText('Preview for '+phone)).toBeNull();
 expect(requests).toEqual(['POST /api/contacts','POST /api/contacts','PUT /api/profile','DELETE /api/contacts?address=%2B14155550123']);
});

// A fake server for the reply box: one unread chat, with drafts kept in memory.
function replyFlow(rows:Record<string,unknown>[]=[],unread=[{recipient:'alex@example.test',preview:'Alex: coffee?',unread_count:1,count_capped:false}]){
 HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
 HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
 const server={rows,calls:[] as string[],drafted:0,draftFails:false,typedFails:false,unread,hold:undefined as Promise<void>|undefined,holdChat:undefined as Promise<void>|undefined,holdSummary:undefined as Promise<void>|undefined,summaryFails:false,noSummary:false};
 const reply=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status});
 vi.stubGlobal('fetch',vi.fn(async(url:string,options?:RequestInit)=>{
  const method=options?.method||'GET',body=options?.body?JSON.parse(String(options.body)):undefined;
  if(method!=='GET')server.calls.push(method+' '+url+(options?.body?' '+options.body:''));
  const add=(text:string)=>{const row={id:'draft-'+(server.rows.length+1)+'-'+server.calls.length,recipient:'alex@example.test',context:'Alex: coffee?',fingerprint:'fp',text,version:1,status:'pending'};server.rows=[row,...server.rows];return row;};
  const id=url.split('/')[3];
  if(url==='/api/drafts'&&method==='POST'){await server.hold;if(server.draftFails)return reply({detail:'Model unavailable.'},502);server.drafted++;return reply(add('LLM draft '+server.drafted));}
  if(url==='/api/drafts/typed'){if(server.typedFails)return reply({detail:'New messages came in, so nothing was sent. Read them, then send again.'},409);return reply(add(body.text));}
  if(url==='/api/inbox/prepare'){return reply({created:true,reason:'created',draft:add('Automatic draft')});}
  if(method==='PATCH'){const row={...server.rows.find(r=>r.id===id),text:body.text,version:body.version+1};server.rows=server.rows.map(r=>r.id===id?row:r);return reply(row);}
  if(url.endsWith('/reject')){server.rows=server.rows.filter(r=>r.id!==id);return reply({status:'rejected'});}
  if(url.endsWith('/approve')){const row={...server.rows.find(r=>r.id===id),status:'sent',receipt:'Simulated.'};server.rows=server.rows.filter(r=>r.id!==id);return reply(row);}
  if(url.startsWith('/api/conversation?'))await server.holdChat;
  if(url.startsWith('/api/conversation/summary?')){await server.holdSummary;return server.summaryFails?reply({detail:'Model unavailable.'},502):reply({summary:'Fresh summary',summary_kind:'ai'});}
  const data=url==='/api/status'?{mode:'demo',llm:true,send_enabled:false}:
   url==='/api/profile'?{style:'Short',examples:[]}:
   url==='/api/contacts'?[{name:'',address:'alex@example.test',source:'demo'}]:
   url==='/api/drafts'?server.rows:url==='/api/inbox'?server.unread:
   url.startsWith('/api/conversation?')?{recipient:'alex@example.test',context:'You: hey!\nAlex: coffee?',fingerprint:'fp',summary:server.noSummary?null:'Summary',summary_kind:server.noSummary?null:'ai'}:null;
  if(data===null)throw new Error('Unexpected request '+url);
  return reply(data);
 }));
 sessionStorage.setItem('ghost-token','synthetic-token');
 return server;
}

const box=()=>screen.getByLabelText('YOUR REPLY') as HTMLTextAreaElement;
const button=(name:string|RegExp)=>screen.getByRole('button',{name,hidden:true}) as HTMLButtonElement;

async function openChat(){
 render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Open my inbox'}));
 fireEvent.click(await screen.findByRole('button',{name:/alex@example\.test/}));
 await screen.findByLabelText('YOUR REPLY');
}

it('always shows an empty reply box, and Draft a reply fills it',async()=>{
 const server=replyFlow();
 await openChat();
 expect(box().value).toBe('');
 expect(button(/^Send/).disabled).toBe(true);
 expect(button('Clear').disabled).toBe(true);
 expect(screen.queryByRole('button',{name:'Reject'})).toBeNull();
 expect(server.calls).toEqual([]);
 fireEvent.click(button('Draft a reply'));
 await waitFor(()=>expect(box().value).toBe('LLM draft 1'));
 expect(button(/^Send/).disabled).toBe(false);
});

it('saves a typed reply on Send and only approves after the final confirmation',async()=>{
 const server=replyFlow();
 await openChat();
 fireEvent.change(box(),{target:{value:'My own words'}});
 fireEvent.click(button(/^Send/));
 const dialog=await screen.findByRole('dialog',{hidden:true});
 expect(within(dialog).getByText('My own words')).toBeTruthy();
 expect(server.drafted).toBe(0);
 expect(server.calls).toEqual(['POST /api/drafts/typed {"recipient":"alex@example.test","text":"My own words","fingerprint":"fp"}']);
 fireEvent.click(button('Confirm simulated send'));
 await screen.findByRole('status',{name:'Send receipt'});
 expect(server.calls.filter(c=>c.includes('/approve'))).toHaveLength(1);
});

it('saves an edit before the confirmation shows it',async()=>{
 const row={id:'draft-1',recipient:'alex@example.test',context:'Alex: coffee?',fingerprint:'fp',text:'Saved reply',version:1,status:'pending'};
 const server=replyFlow([row]);
 await openChat();
 await waitFor(()=>expect(box().value).toBe('Saved reply'));
 fireEvent.change(box(),{target:{value:'Edited'}});
 fireEvent.click(button(/^Send/));
 const dialog=await screen.findByRole('dialog',{hidden:true});
 expect(within(dialog).getByText('Edited')).toBeTruthy();
 expect(within(dialog).queryByText(/version/i)).toBeNull();
 expect(server.calls.some(c=>c.includes('/approve'))).toBe(false);
});

it('keeps a typed reply when new messages make saving it fail',async()=>{
 const server=replyFlow();
 server.typedFails=true;
 await openChat();
 fireEvent.change(box(),{target:{value:'My own words'}});
 fireEvent.click(button(/^Send/));
 expect((await screen.findByRole('alert')).textContent).toContain('New messages came in');
 expect(box().value).toBe('My own words');
 expect(screen.queryByRole('dialog',{hidden:true})).toBeNull();
});

it('clears the box and rejects the saved draft',async()=>{
 const server=replyFlow();
 await openChat();
 fireEvent.click(button('Draft a reply'));
 await waitFor(()=>expect(box().value).toBe('LLM draft 1'));
 fireEvent.click(button('Clear'));
 await waitFor(()=>expect(box().value).toBe(''));
 expect(server.calls.filter(c=>c.endsWith('/reject {"version":1}'))).toHaveLength(1);
 expect(server.rows).toEqual([]);
 // The cleared text can come back. Typing dismisses the notice.
 expect(screen.getByText(/Reply cleared/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Undo'}));
 expect(box().value).toBe('LLM draft 1');
 expect(screen.queryByText(/Reply cleared/)).toBeNull();
});

it('replaces the text straight away, offers Undo, and keeps the text if the new draft fails',async()=>{
 const server=replyFlow();
 const confirm=vi.fn(()=>true);
 vi.stubGlobal('confirm',confirm);
 await openChat();
 fireEvent.change(box(),{target:{value:'Keep me'}});
 server.draftFails=true;
 fireEvent.click(button('Draft a reply'));
 const failure=await screen.findByRole('alert');
 expect(failure.textContent).toContain('Model unavailable.');
 // Shown in the reply box's card, next to the button that caused it.
 expect(failure.closest('section')?.contains(box())).toBe(true);
 expect(box().value).toBe('Keep me');
 expect(screen.queryByText(/Replaced with a new draft/)).toBeNull();

 server.draftFails=false;
 await waitFor(()=>expect(button('Draft a reply').disabled).toBe(false));
 fireEvent.click(button('Draft a reply'));
 await waitFor(()=>expect(box().value).toBe('LLM draft 1'));
 // No browser popup: the old text is one click away instead.
 expect(confirm).not.toHaveBeenCalled();
 expect(screen.getByText(/Replaced with a new draft/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Undo'}));
 expect(box().value).toBe('Keep me');
 expect(screen.queryByText(/Replaced with a new draft/)).toBeNull();
});

it('fills the box when an automatic draft finishes',async()=>{
 const server=replyFlow();
 await openChat();
 fireEvent.click(screen.getByRole('checkbox',{name:'Prepare drafts automatically'}));
 await waitFor(()=>expect(box().value).toBe('Automatic draft'));
 expect(server.calls.filter(c=>c.includes('/approve'))).toEqual([]);
});

it('saves what you typed when you leave the chat, and shows it when you come back',async()=>{
 const server=replyFlow();
 await openChat();
 fireEvent.change(box(),{target:{value:'Come back to this'}});
 fireEvent.click(button(/^People/));
 await screen.findByRole('region',{name:'Default voice'});
 expect(server.calls.filter(c=>c.startsWith('POST /api/drafts/typed'))).toHaveLength(1);
 fireEvent.click(button(/^Inbox/));
 await waitFor(()=>expect(box().value).toBe('Come back to this'));
});

it('keeps Earlier messages open or closed as the user left it',async()=>{
 replyFlow();
 await openChat();
 const messages=()=>screen.getByText('Earlier messages').closest('details') as HTMLDetailsElement;
 expect(messages().open).toBe(true);
 fireEvent.click(button('Draft a reply'));
 await waitFor(()=>expect(box().value).toBe('LLM draft 1'));
 expect(messages().open).toBe(true);
 fireEvent.click(button('Clear'));
 await waitFor(()=>expect(box().value).toBe(''));
 expect(messages().open).toBe(true);

 messages().open=false;
 fireEvent(messages(),new Event('toggle'));
 fireEvent.click(button('Draft a reply'));
 await waitFor(()=>expect(box().value).toBe('LLM draft 2'));
 expect(messages().open).toBe(false);
});

it('shows drafting progress on the button only, leaving the inbox alone',async()=>{
 const server=replyFlow();
 let finish=()=>{};
 server.hold=new Promise<void>(resolve=>{finish=resolve;});
 await openChat();
 fireEvent.click(button('Draft a reply'));
 const drafting=await screen.findByRole('button',{name:'Drafting…'}) as HTMLButtonElement;
 expect(drafting.getAttribute('aria-busy')).toBe('true');
 expect(button(/alex@example\.test/).disabled).toBe(false);
 expect(button('Refresh inbox').disabled).toBe(false);
 expect(button(/^People/).disabled).toBe(false);
 finish();
 await waitFor(()=>expect(box().value).toBe('LLM draft 1'));
 expect(screen.queryByRole('button',{name:'Drafting…'})).toBeNull();
});

it('replaces the reply box with the new draft when drafting again',async()=>{
 const server=replyFlow();
 vi.stubGlobal('confirm',()=>true);
 await openChat();
 fireEvent.click(button('Draft a reply'));
 await waitFor(()=>expect(box().value).toBe('LLM draft 1'));
 fireEvent.click(button('Draft a reply'));
 await waitFor(()=>expect(box().value).toBe('LLM draft 2'));
 expect(screen.getByText('Saved')).toBeTruthy();
 expect(server.calls.filter(c=>c.endsWith('/reject {"version":1}'))).toHaveLength(1);
});

it('removes the chat from the inbox right after its reply is sent',async()=>{
 const server=replyFlow();
 await openChat();
 fireEvent.change(box(),{target:{value:'see you then'}});
 fireEvent.click(button(/^Send/));
 await screen.findByRole('dialog',{hidden:true});
 server.unread=[];  // The backend leaves out a chat once its reply is sent.
 fireEvent.click(button('Confirm simulated send'));
 await screen.findByRole('status',{name:'Send receipt'});
 await waitFor(()=>expect(screen.queryByRole('button',{name:/alex@example\.test/})).toBeNull());
});

it('shows loading on the clicked chat only, keeping the open chat until the new one loads',async()=>{
 const server=replyFlow([],[
  {recipient:'alex@example.test',preview:'Alex: coffee?',unread_count:1,count_capped:false},
  {recipient:'maya@example.test',preview:'Maya: photos?',unread_count:1,count_capped:false},
 ]);
 await openChat();
 let finish=()=>{};
 server.holdChat=new Promise<void>(resolve=>{finish=resolve;});
 fireEvent.click(button(/maya@example\.test/));
 const maya=button(/maya@example\.test/);
 await waitFor(()=>expect(maya.getAttribute('aria-busy')).toBe('true'));
 expect(maya.textContent).toContain('Loading…');
 expect(button(/alex@example\.test/).disabled).toBe(false);
 expect(button('Refresh inbox').disabled).toBe(false);
 expect(screen.getByText('Summary')).toBeTruthy();  // The open chat stays on screen.
 expect(box().readOnly).toBe(true);
 finish();
 await waitFor(()=>expect(maya.getAttribute('aria-busy')).toBe('false'));
 expect(maya.textContent).not.toContain('Loading…');
 expect(box().readOnly).toBe(false);
});

it('opens a chat right away and shows the summary when it is ready',async()=>{
 const server=replyFlow();
 server.noSummary=true;
 let finish=()=>{};
 server.holdSummary=new Promise<void>(resolve=>{finish=resolve;});
 await openChat();
 expect(screen.getByText(/Generating a summary of the conversation so far/)).toBeTruthy();
 const thread=screen.getByRole('region',{name:'Conversation'});
 // The unread message sits right above the reply box, in the same card; earlier history is folded above it.
 const unread=within(thread).getByRole('group',{name:'Unread from alex@example.test'});
 expect(unread.textContent).toContain('Alex: coffee?');
 // Screen readers hear who wrote each bubble.
 expect(within(thread).getByText('hey!').textContent).toContain('You: hey!');
 expect(within(thread).getByText('hey!').closest('details')).toBeTruthy();
 expect(within(thread).getByLabelText('YOUR REPLY')).toBeTruthy();
 expect(unread.compareDocumentPosition(within(thread).getByLabelText('YOUR REPLY'))&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
 expect(box().readOnly).toBe(false);
 finish();
 expect(await screen.findByText('Fresh summary')).toBeTruthy();
 expect(screen.queryByText(/Generating a summary/)).toBeNull();
});

it('shows a summary failure in the summary area with a retry',async()=>{
 const server=replyFlow();
 server.noSummary=true;
 server.summaryFails=true;
 await openChat();
 const failure=await screen.findByRole('alert');
 expect(failure.textContent).toContain("Couldn't generate a summary: Model unavailable.");
 expect(box()).toBeTruthy();  // The chat itself still opened.
 server.summaryFails=false;
 fireEvent.click(within(failure).getByRole('button',{name:'Try again'}));
 expect(await screen.findByText('Fresh summary')).toBeTruthy();
});

it('keeps the inbox header light and puts the automatic options behind Options',async()=>{
 replyFlow();
 render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Open my inbox'}));
 await screen.findByRole('button',{name:/alex@example\.test/});
 // No eyebrow or intro paragraph, and no repeated "Conversations" heading above the list.
 expect(screen.queryByText('A LITTLE LESS ON YOUR PLATE')).toBeNull();
 expect(screen.queryByText('A first draft from your assistant. The final word is yours.')).toBeNull();
 expect(screen.queryByRole('heading',{name:/^Conversations/})).toBeNull();
 expect(screen.getByRole('region',{name:'Conversations'})).toBeTruthy();
 // The options start closed, and the status line reflects them without opening.
 const options=screen.getByText('Options').closest('details') as HTMLDetailsElement;
 expect(options.open).toBe(false);
 fireEvent.click(screen.getByRole('checkbox',{name:'Auto-refresh every 30 seconds'}));
 expect(await screen.findByText(/auto-refresh on/)).toBeTruthy();
 expect(options.textContent).toContain('Reading here never marks messages as read.');
 expect(options.textContent).toContain('send unread conversations to your configured model');
});

it('marks the current tab in a navigation landmark and keeps the refresh time out of live announcements',async()=>{
 replyFlow();
 render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Open my inbox'}));
 const nav=await screen.findByRole('navigation',{name:'Main'});
 const inbox=within(nav).getByRole('button',{name:/Inbox/}),people=within(nav).getByRole('button',{name:/People/});
 expect(inbox.getAttribute('aria-current')).toBe('page');
 expect(people.getAttribute('aria-current')).toBeNull();
 fireEvent.click(people);
 await waitFor(()=>expect(people.getAttribute('aria-current')).toBe('page'));
 expect(inbox.getAttribute('aria-current')).toBeNull();
 fireEvent.click(inbox);
 // "Updated …" changes on every refresh, so it must not be a live region.
 await screen.findByText(/^Updated/);
 expect(screen.getByText(/^Updated/).closest('[role=status]')).toBeNull();
});

it('offers the next conversation after a send and opens it',async()=>{
 const server=replyFlow([],[
  {recipient:'alex@example.test',preview:'Alex: coffee?',unread_count:1,count_capped:false},
  {recipient:'maya@example.test',preview:'Maya: photos?',unread_count:1,count_capped:false},
 ]);
 await openChat();
 fireEvent.change(box(),{target:{value:'see you then'}});
 fireEvent.click(button(/^Send/));
 await screen.findByRole('dialog',{hidden:true});
 server.unread=[{recipient:'maya@example.test',preview:'Maya: photos?',unread_count:1,count_capped:false}];
 fireEvent.click(button('Confirm simulated send'));
 const receipt=await screen.findByRole('status',{name:'Send receipt'});
 expect(receipt.textContent).toContain('Simulated send to alex@example.test.');
 // More is waiting, so the ghost is awake.
 expect(receipt.querySelector('.ghost-mark')?.getAttribute('data-state')).toBe('awake');
 const next=await within(receipt).findByRole('button',{name:'Next conversation: maya@example.test'});
 fireEvent.click(next);
 await waitFor(()=>expect(vi.mocked(fetch).mock.calls.some(c=>String(c[0]).includes('/api/conversation?summary=false&recipient=maya%40example.test'))).toBe(true));
 await waitFor(()=>expect(screen.queryByRole('status',{name:'Send receipt'})).toBeNull());
});

it('shows a resting ghost when the inbox is clear and an awake one before a chat is chosen',async()=>{
 replyFlow([],[]);
 render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Open my inbox'}));
 await screen.findByText('No unread conversations.');
 const list=screen.getByRole('region',{name:'Conversations'});
 expect(list.querySelector('.ghost-mark')?.getAttribute('data-state')).toBe('asleep');
 // The drawing is decoration: hidden from assistive technology.
 expect(list.querySelector('.ghost-mark')?.getAttribute('aria-hidden')).toBe('true');
 const placeholder=screen.getByText('Catch up at a glance.').closest('section') as HTMLElement;
 expect(placeholder.querySelector('.ghost-mark')?.getAttribute('data-state')).toBe('awake');
});

it('saves the reply a moment after typing stops, and never sends',async()=>{
 vi.useFakeTimers({shouldAdvanceTime:true});
 const server=replyFlow();
 await openChat();
 const saves=()=>server.calls.filter(c=>c.startsWith('POST /api/drafts/typed')||c.startsWith('PATCH'));
 fireEvent.change(box(),{target:{value:'First'}});
 expect(screen.getByText('Saving…')).toBeTruthy();
 // Typing again before the pause ends restarts it, so this is one save, not two.
 await act(()=>vi.advanceTimersByTimeAsync(800));
 fireEvent.change(box(),{target:{value:'First thought'}});
 await act(()=>vi.advanceTimersByTimeAsync(800));
 expect(saves()).toHaveLength(0);
 await act(()=>vi.advanceTimersByTimeAsync(1000));
 await screen.findByText('Saved');
 expect(saves()).toEqual(['POST /api/drafts/typed {"recipient":"alex@example.test","text":"First thought","fingerprint":"fp"}']);
 // The box keeps what was typed, and a later edit saves a new version of the same draft.
 expect(box().value).toBe('First thought');
 fireEvent.change(box(),{target:{value:'First thought, edited'}});
 await act(()=>vi.advanceTimersByTimeAsync(1500));
 await screen.findByText('Saved');
 expect(saves()[1]).toMatch(/^PATCH \/api\/drafts\/.+ \{"version":1,"text":"First thought, edited"\}$/);
 expect(server.calls.some(c=>c.includes('/approve'))).toBe(false);
 expect(screen.queryByRole('dialog',{hidden:true,name:/./})).toBeNull();
});

it('does not autosave while a draft is being written, and keeps the old text if it fails',async()=>{
 vi.useFakeTimers({shouldAdvanceTime:true});
 const server=replyFlow();
 let finish=()=>{};
 server.hold=new Promise<void>(resolve=>{finish=resolve;});
 await openChat();
 fireEvent.change(box(),{target:{value:'Half written'}});
 fireEvent.click(button('Draft a reply'));
 await act(()=>vi.advanceTimersByTimeAsync(3000));
 expect(server.calls.filter(c=>c.startsWith('POST /api/drafts/typed'))).toHaveLength(0);
 finish();
 await waitFor(()=>expect(box().value).toBe('LLM draft 1'));
});

it('explains a failed autosave in an alert and keeps the typed text',async()=>{
 vi.useFakeTimers({shouldAdvanceTime:true});
 const server=replyFlow();
 server.typedFails=true;
 await openChat();
 fireEvent.change(box(),{target:{value:'Still mine'}});
 await act(()=>vi.advanceTimersByTimeAsync(1500));
 const alert=await screen.findByRole('alert');
 expect(alert.textContent).toContain("isn't saved yet");
 expect(alert.textContent).toContain('New messages came in');
 expect(alert.textContent).toContain('Keep typing or press Send');
 expect(screen.getByText("Couldn't save yet")).toBeTruthy();
 expect(box().value).toBe('Still mine');
 server.typedFails=false;
 fireEvent.change(box(),{target:{value:'Still mine, again'}});
 await act(()=>vi.advanceTimersByTimeAsync(1500));
 await screen.findByText('Saved');
 expect(screen.queryByRole('alert')).toBeNull();
});

it('brings a typed reply back after the page is reloaded',async()=>{
 vi.useFakeTimers({shouldAdvanceTime:true});
 replyFlow();
 await openChat();
 fireEvent.change(box(),{target:{value:'Do not lose this'}});
 await act(()=>vi.advanceTimersByTimeAsync(1500));
 await screen.findByText('Saved');
 cleanup();
 render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Open my inbox'}));
 fireEvent.click(await screen.findByRole('button',{name:/alex@example\.test/}));
 await waitFor(()=>expect(box().value).toBe('Do not lose this'));
});

it('keeps the reply box usable by keyboard: it stays focusable while drafting, and focus lands in it after Clear',async()=>{
 const server=replyFlow();
 let finish=()=>{};
 server.hold=new Promise<void>(resolve=>{finish=resolve;});
 await openChat();
 fireEvent.click(button('Draft a reply'));
 await screen.findByRole('button',{name:'Drafting…'});
 // Read-only while the draft is written, but not disabled, so keyboard focus is never dropped.
 expect(box().readOnly).toBe(true);
 expect(box().disabled).toBe(false);
 finish();
 await waitFor(()=>expect(box().value).toBe('LLM draft 1'));
 expect(box().readOnly).toBe(false);
 fireEvent.click(button('Clear'));
 await waitFor(()=>expect(box().value).toBe(''));
 await waitFor(()=>expect(document.activeElement).toBe(box()));
});

it('closes the Options panel with Escape and a click elsewhere, but not a click inside it',async()=>{
 replyFlow();
 render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Open my inbox'}));
 await screen.findByRole('button',{name:/alex@example\.test/});
 const options=screen.getByText('Options').closest('details') as HTMLDetailsElement;
 options.open=true;
 fireEvent.pointerDown(screen.getByLabelText('Prepare drafts automatically'));
 expect(options.open).toBe(true);
 fireEvent.keyDown(document,{key:'Enter'});
 expect(options.open).toBe(true);
 fireEvent.keyDown(document,{key:'Escape'});
 expect(options.open).toBe(false);
 expect(document.activeElement).toBe(screen.getByText('Options'));
 options.open=true;
 fireEvent.pointerDown(document.body);
 expect(options.open).toBe(false);
});

it('calls a saved draft "Draft saved" in the list, matching the status above the box',async()=>{
 replyFlow([{id:'draft-9',recipient:'alex@example.test',context:'Alex: coffee?',fingerprint:'fp',text:'Typed so far',version:3,status:'pending'}]);
 render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Open my inbox'}));
 fireEvent.click(await screen.findByRole('button',{name:/alex@example\.test.*Draft saved/}));
 expect(await screen.findByText('Saved')).toBeTruthy();
});

it('shows a new draft at once, without waiting to read the chat and the inbox again',async()=>{
 const server=replyFlow();
 await openChat();
 // Anything that reads the conversation from here on never finishes.
 server.holdChat=new Promise<void>(()=>{});
 fireEvent.click(button('Draft a reply'));
 await waitFor(()=>expect(box().value).toBe('LLM draft 1'));
 expect(screen.getByText('Saved')).toBeTruthy();
 // The box is not left waiting: a draft that is already in the list is saved, not created twice.
 expect(server.calls.filter(c=>c.startsWith('POST /api/drafts/typed'))).toHaveLength(0);
});
