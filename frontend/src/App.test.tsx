// @vitest-environment jsdom
import {act, cleanup, fireEvent, render, screen} from '@testing-library/react';
import {afterEach, expect, it, vi} from 'vitest';
import {App} from './App';

afterEach(()=>{cleanup();vi.useRealTimers();vi.unstubAllGlobals();sessionStorage.clear();});

it('refreshes inbox without replacing selected context, summary, unsaved edits, or generating/sending',async()=>{
 const draft={id:'draft-1',recipient:'alex@example.test',context:'Original messages',text:'Saved reply',version:1,status:'pending'};
 let inbox=[{recipient:'alex@example.test',preview:'Original preview',unread_count:1,count_capped:false}];
 const requests:{url:string;method:string}[]=[];
 const fetchMock=vi.fn(async(url:string,options?:RequestInit)=>{
  requests.push({url,method:options?.method||'GET'});
  const data=url==='/api/status'?{mode:'demo',llm:false,send_enabled:false,recipients:[draft.recipient]}:
   url==='/api/profile'?{style:'Short',examples:[]}:
   url==='/api/drafts'?[draft]:url==='/api/inbox'?inbox:
   url.startsWith('/api/conversation?')?{recipient:draft.recipient,context:'Original messages',fingerprint:'original',summary:'Original summary',summary_kind:'ai'}:null;
  if(data===null)throw new Error('Unexpected request');
  return new Response(JSON.stringify(data));
 });
 vi.stubGlobal('fetch',fetchMock);
 sessionStorage.setItem('ghost-token','synthetic-token');
 render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Open my inbox →'}));
 await screen.findByText('Original preview');
 fireEvent.click(screen.getByRole('button',{name:/alex@example\.test.*Original preview/}));
 await screen.findByText('Original summary');
 fireEvent.change(screen.getByLabelText('YOUR REPLY'),{target:{value:'My unsaved edit'}});
 const before=requests.filter(r=>r.url.startsWith('/api/conversation?')).length;
 inbox=[];
 fireEvent.click(screen.getByRole('button',{name:'Refresh inbox'}));
 await screen.findByText('No unread conversations.');
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
