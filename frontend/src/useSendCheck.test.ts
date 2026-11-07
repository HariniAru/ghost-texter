// @vitest-environment jsdom
import {act, cleanup, renderHook} from '@testing-library/react';
import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {useSendCheck} from './useSendCheck';

beforeEach(()=>vi.useFakeTimers());
afterEach(()=>{cleanup();vi.useRealTimers();});

it('checks four times over 30 seconds, then reports the draft as finished',async()=>{
 const check=vi.fn().mockResolvedValue(undefined);
 const {result}=renderHook(()=>useSendCheck(['a'],true,check));
 await act(async()=>{});
 expect(check).toHaveBeenCalledTimes(1);
 await act(()=>vi.advanceTimersByTimeAsync(20000));
 expect(result.current).toEqual([]);
 await act(()=>vi.advanceTimersByTimeAsync(10000));
 expect(check).toHaveBeenCalledTimes(4);
 expect(result.current).toEqual(['a']);
 await act(()=>vi.advanceTimersByTimeAsync(60000));
 expect(check).toHaveBeenCalledTimes(4);
});

it('counts a failed check and does nothing while disconnected',async()=>{
 const check=vi.fn().mockRejectedValue(new Error('denied'));
 const {result,rerender}=renderHook(({connected})=>useSendCheck(['a'],connected,check),{initialProps:{connected:false}});
 await act(()=>vi.advanceTimersByTimeAsync(60000));
 expect(check).not.toHaveBeenCalled();
 rerender({connected:true});
 await act(()=>vi.advanceTimersByTimeAsync(30000));
 expect(check).toHaveBeenCalledTimes(4);
 expect(result.current).toEqual(['a']);
});
