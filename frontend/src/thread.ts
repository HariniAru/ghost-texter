// Turns the conversation text the backend sends into messages for display only.
// Live Messages rows are timestamped and newest first; demo rows are plain lines, oldest first.
export type Message={mine:boolean;sender:string;text:string;at?:string};
const ROW=/^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}):\d{2}\]\s*(.*)$/;
function toMessage([row,at]:[string,string|undefined]):Message|undefined{
 const i=row.indexOf(': ');
 if(i<1)return undefined;
 const sender=row.slice(0,i).replace(/(\s*\[[^\]]*\])+$/,'').trim();
 return {mine:sender==='You',sender,text:row.slice(i+2).replace(/\\n/g,'\n').replace(/\\t/g,'\t'),...(at?{at}:{})};
}
export function splitThread(context:string,unreadCount?:number):{earlier:Message[];unread:Message[]}|undefined{
 const text=context.replace(/\\n(?=\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\])/g,'\n');
 const stamped=text.split('\n').map(l=>l.match(ROW)).filter((m):m is RegExpMatchArray=>m!==null).map((m):[string,string|undefined]=>[m[2],m[1]]);
 const rows=stamped.length?stamped.reverse():text.split('\n').map(l=>l.trim()).filter(Boolean).map((l):[string,string|undefined]=>[l,undefined]);
 const all=rows.map(toMessage);
 if(!all.length||all.some(m=>!m))return undefined;
 const messages=all as Message[];
 let start=messages.length;
 while(start>0&&!messages[start-1].mine)start--;
 if(unreadCount&&unreadCount>0)start=Math.max(start,messages.length-unreadCount);
 return {earlier:messages.slice(0,start),unread:messages.slice(start)};
}

// "Today 9:05 PM", "Yesterday 9:05 PM", or "Jan 2, 9:05 PM", on a 12-hour clock. The time is the Mac's local time, as Messages gives it.
export function whenLabel(at:string,now=new Date()):string{
 const [d,t]=at.split(' '),[y,m,day]=d.split('-').map(Number);
 const date=new Date(y,m-1,day),today=new Date(now.getFullYear(),now.getMonth(),now.getDate());
 const days=Math.round((today.getTime()-date.getTime())/86400000);
 const [hour,minute]=t.split(':').map(Number);
 const time=`${hour%12||12}:${String(minute).padStart(2,'0')} ${hour<12?'AM':'PM'}`;
 if(days===0)return 'Today '+time;
 if(days===1)return 'Yesterday '+time;
 return date.toLocaleDateString('en-US',{month:'short',day:'numeric'})+', '+time;
}

// A list row shows the time and the message, not the connector's bracketed fields. A plain demo row stays as it is.
export function previewOf(preview:string):{text:string;at?:string}{
 const m=preview.match(ROW);
 const message=m?toMessage([m[2],m[1]]):undefined;
 return message?{text:message.text,at:message.at}:{text:preview};
}

// The other person's latest message in a saved draft's conversation, as a list-row preview ('' if none).
// Live rows are newest first and demo rows oldest first, as in splitThread.
export function lastIncoming(context:string):string{
 const lines=context.replace(/\\n(?=\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\])/g,'\n').split('\n');
 const stamped=lines.filter(l=>ROW.test(l));
 if(stamped.length)return stamped.find(l=>{const m=l.match(ROW);const message=m&&toMessage([m[2],m[1]]);return message&&!message.mine;})??'';
 return [...lines].reverse().find(l=>l.trim()&&!l.startsWith('You:'))??'';
}
