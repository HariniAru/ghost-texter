// @vitest-environment jsdom
import {act, cleanup, renderHook} from '@testing-library/react';
import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {useInboxRefresh} from './useInboxRefresh';

beforeEach(()=>vi.useFakeTimers());
afterEach(()=>{cleanup();vi.useRealTimers();});

it('loads once on connect and defaults to no periodic polling',async()=>{
 const load=vi.fn().mockResolvedValue(['first']);
 const {result}=renderHook(()=>useInboxRefresh(load,true,false));
 await act(async()=>{});
 expect(result.current.items).toEqual(['first']);
 expect(result.current.autoRefresh).toBe(false);
 await act(()=>vi.advanceTimersByTimeAsync(90000));
 expect(load).toHaveBeenCalledTimes(1);
});

it('polls every 30 seconds only while opted in',async()=>{
 const load=vi.fn().mockResolvedValue(['chat']);
 const {result}=renderHook(()=>useInboxRefresh(load,true,false));
 await act(async()=>{});
 act(()=>result.current.setAutoRefresh(true));
 await act(()=>vi.advanceTimersByTimeAsync(29999));
 expect(load).toHaveBeenCalledTimes(1);
 await act(()=>vi.advanceTimersByTimeAsync(1));
 expect(load).toHaveBeenCalledTimes(2);
 act(()=>result.current.setAutoRefresh(false));
 await act(()=>vi.advanceTimersByTimeAsync(60000));
 expect(load).toHaveBeenCalledTimes(2);
});

it('does not overlap slow requests and pauses while another action is busy',async()=>{
 let finish:(rows:string[])=>void=()=>{};
 const load=vi.fn().mockImplementation(()=>new Promise<string[]>(resolve=>{finish=resolve;}));
 const {result,rerender}=renderHook(({paused})=>useInboxRefresh(load,true,paused),{initialProps:{paused:false}});
 act(()=>result.current.setAutoRefresh(true));
 await act(()=>vi.advanceTimersByTimeAsync(60000));
 expect(load).toHaveBeenCalledTimes(1);
 await act(async()=>finish(['ready']));
 rerender({paused:true});
 await act(()=>vi.advanceTimersByTimeAsync(30000));
 expect(load).toHaveBeenCalledTimes(1);
 rerender({paused:false});
 await act(()=>vi.advanceTimersByTimeAsync(30000));
 expect(load).toHaveBeenCalledTimes(2);
});

it('keeps the last successful data/time after errors and clears errors on recovery',async()=>{
 const load=vi.fn().mockResolvedValueOnce(['original']).mockRejectedValueOnce(new Error('Connector unavailable')).mockResolvedValueOnce(['new']);
 const {result}=renderHook(()=>useInboxRefresh(load,true,false));
 await act(async()=>{});
 const first=result.current.lastSuccess;
 await act(async()=>{await result.current.refresh();});
 expect(result.current.error).toBe('Connector unavailable');
 expect(result.current.items).toEqual(['original']);
 expect(result.current.lastSuccess).toBe(first);
 await act(async()=>{await result.current.refresh();});
 expect(result.current.items).toEqual(['new']);
 expect(result.current.error).toBe('');
});

it('aborts on logout and ignores a late response from the old session',async()=>{
 let finish:(rows:string[])=>void=()=>{};
 let signal:AbortSignal|undefined;
 const load=vi.fn().mockImplementation((s:AbortSignal)=>{signal=s;return new Promise<string[]>(resolve=>{finish=resolve;});});
 const {result,rerender}=renderHook(({enabled})=>useInboxRefresh(load,enabled,false),{initialProps:{enabled:true}});
 act(()=>result.current.setAutoRefresh(true));
 rerender({enabled:false});
 expect(signal?.aborted).toBe(true);
 await act(async()=>finish(['private-old-result']));
 expect(result.current.items).toEqual([]);
 expect(result.current.autoRefresh).toBe(false);
 expect(result.current.lastSuccess).toBeUndefined();
 await act(()=>vi.advanceTimersByTimeAsync(60000));
 expect(load).toHaveBeenCalledTimes(1);
});
