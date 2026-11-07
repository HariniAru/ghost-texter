import {expect,it} from 'vitest';
import {lastIncoming,previewOf,splitThread,whenLabel} from './thread';

it('splits demo lines (oldest first) into earlier messages and the unread ones',()=>{
 const t=splitThread('You: hey\nAlex: hi\nAlex: coffee?');
 expect(t?.earlier.map(m=>m.text)).toEqual(['hey']);
 expect(t?.unread.map(m=>m.text)).toEqual(['hi','coffee?']);
 expect(t?.earlier[0].mine).toBe(true);
});

it('reads timestamped rows (newest first) in order, with attachments and escaped line breaks',()=>{
 const t=splitThread('[2026-01-02 09:05:00] Maya [attachment]: look\\nnice\n[2026-01-02 09:01:00] You: ok\n[2026-01-01 08:00:00] Maya: hi');
 expect(t?.earlier.map(m=>m.text)).toEqual(['hi','ok']);
 expect(t?.unread).toEqual([{mine:false,sender:'Maya',text:'look\nnice',at:'2026-01-02 09:05'}]);
});

it('limits unread to the unread count, and shows none when the last message is yours',()=>{
 expect(splitThread('Alex: a\nAlex: b\nAlex: c',2)?.unread.map(m=>m.text)).toEqual(['b','c']);
 expect(splitThread('Alex: a\nYou: b')?.unread).toEqual([]);
});

it('gives up on text it cannot read so the page can show it as it is',()=>{
 expect(splitThread('no sender here')).toBeUndefined();
});

it('labels when the first unread message arrived',()=>{
 const now=new Date(2026,0,2,15,0);
 expect(whenLabel('2026-01-02 09:05',now)).toBe('Today 9:05 AM');
 expect(whenLabel('2026-01-01 21:30',now)).toBe('Yesterday 9:30 PM');
 expect(whenLabel('2026-01-02 00:15',now)).toBe('Today 12:15 AM');
 expect(whenLabel('2026-01-02 12:00',now)).toBe('Today 12:00 PM');
 expect(whenLabel('2025-12-24 08:00',now)).toBe('Dec 24, 8:00 AM');
 expect(splitThread('Alex: hi')?.unread[0].at).toBeUndefined();
});

it('shows a list preview as the time and the message, without the bracketed fields',()=>{
 expect(previewOf('[2026-11-05 21:05:37] Valli Alagappan [iMessage] [unread]: I have like 500 points')).toEqual({text:'I have like 500 points',at:'2026-11-05 21:05'});
 expect(previewOf('[2026-11-05 21:05:37] Sam: a: b\\nc').text).toBe('a: b\nc');
});

it('leaves a plain demo preview as it is',()=>{
 expect(previewOf('Alex: coffee tomorrow at 10?')).toEqual({text:'Alex: coffee tomorrow at 10?'});
});

it("previews the other person's latest message from a saved draft's conversation, never your own",()=>{
 expect(lastIncoming('[2026-11-05 21:06:00] You [iMessage]: my draft\\n[2026-11-05 21:05:37] Valli [iMessage]: hello\\n[2026-11-05 21:00:00] Valli [iMessage]: older')).toBe('[2026-11-05 21:05:37] Valli [iMessage]: hello');
 expect(lastIncoming('Alex: hi\nAlex: coffee?\nYou: sure')).toBe('Alex: coffee?');
 expect(lastIncoming('You: only me')).toBe('');
});
