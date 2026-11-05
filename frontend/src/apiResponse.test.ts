import {expect,it} from 'vitest';
import {readApiResponse} from './apiResponse';
it('explains an empty Vite proxy failure without exposing a JSON parse error',async()=>{
 await expect(readApiResponse(new Response('',{status:500}))).rejects.toThrow('Start or restart it on 127.0.0.1:8001');
});
it('handles HTML responses and preserves API errors and successful JSON',async()=>{
 await expect(readApiResponse(new Response('<html>wrong server</html>'))).rejects.toThrow('unexpected response');
 await expect(readApiResponse(new Response(JSON.stringify({detail:'Invalid token'}),{status:401}))).rejects.toThrow('Invalid token');
 await expect(readApiResponse(new Response(JSON.stringify({mode:'demo'})))).resolves.toEqual({mode:'demo'});
});
