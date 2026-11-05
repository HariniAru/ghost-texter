// @vitest-environment jsdom
import {act,cleanup,renderHook} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {useAutoPrepare} from './useAutoPrepare';
afterEach(cleanup);
const items=[{recipient:'a',preview:'hello',unread_count:1},{recipient:'b',preview:'hi',unread_count:1}];
it('requires opt-in, serializes work and does not repeat unchanged inbox entries',async()=>{
 const finishes:Array<(v:string)=>void>=[];
 const prepare=vi.fn(()=>new Promise<string>(resolve=>finishes.push(resolve))),receive=vi.fn();
 const {result,rerender}=renderHook(()=>useAutoPrepare(items,true,false,prepare,receive));
 expect(prepare).not.toHaveBeenCalled();
 act(()=>result.current.setEnabled(true));
 expect(prepare).toHaveBeenCalledTimes(1);
 await act(async()=>finishes[0]('first'));
 expect(prepare).toHaveBeenCalledTimes(2);
 await act(async()=>finishes[1]('second'));
 rerender();
 expect(prepare).toHaveBeenCalledTimes(2);
 expect(receive.mock.calls).toEqual([['first'],['second']]);
});
it('pauses for unsaved work and requires explicit retry after failure',async()=>{
 const prepare=vi.fn().mockRejectedValueOnce(new Error('Model unavailable')).mockResolvedValue('draft'),receive=vi.fn();
 const {result,rerender}=renderHook(({paused})=>useAutoPrepare(items.slice(0,1),true,paused,prepare,receive),{initialProps:{paused:true}});
 act(()=>result.current.setEnabled(true));
 expect(prepare).not.toHaveBeenCalled();
 rerender({paused:false});
 await act(async()=>{});
 expect(result.current.error).toBe('Model unavailable');
 rerender({paused:false});
 expect(prepare).toHaveBeenCalledTimes(1);
 await act(async()=>result.current.retry());
 expect(receive).toHaveBeenCalledWith('draft');
});
it('ignores late responses after disconnect',async()=>{
 let finish:(v:string)=>void=()=>{};
 const prepare=vi.fn(()=>new Promise<string>(resolve=>{finish=resolve;})),receive=vi.fn();
 const {result,rerender}=renderHook(({connected})=>useAutoPrepare(items,connected,false,prepare,receive),{initialProps:{connected:true}});
 act(()=>result.current.setEnabled(true));
 rerender({connected:false});
 await act(async()=>finish('late'));
 expect(receive).not.toHaveBeenCalled();
 expect(result.current.enabled).toBe(false);
});
