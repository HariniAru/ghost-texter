// @vitest-environment jsdom
import {useState} from 'react';
import {act,cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {VoiceEditor,normalizeProfile,voiceOf} from './VoiceEditor';
HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
afterEach(cleanup);
it('keeps paired examples scoped and imports only selected, reviewed pairs',async()=>{
 const save=vi.fn(),suggest=vi.fn().mockResolvedValue({pairs:[{incoming:'coffee?',response:'sure!'}]});
 const initial=normalizeProfile({style:'warm',examples:['legacy']});
 let latest=initial;
 function Harness(){const [profile,setProfile]=useState(initial);latest=profile;const voice={profile,saved:initial,onChange:setProfile,onSave:async(scope:string)=>{save(scope);},suggest};return <>
  <div data-testid="default"><VoiceEditor scope="" busy={false} {...voice}/></div>
  <div data-testid="alex"><VoiceEditor scope="alex@example.test" busy={false} {...voice}/></div>
 </>;}
 render(<Harness/>);
 const main=within(screen.getByTestId('default')),alex=within(screen.getByTestId('alex'));
 expect(screen.queryByLabelText('How should your replies sound?')).toBeNull();
 fireEvent.click(main.getByRole('button',{name:'Customize voice'}));
 expect(main.queryByText('Suggest examples from this chat')).toBeNull();
 fireEvent.click(main.getByText('Add example pair'));
 fireEvent.change(main.getByLabelText('Incoming message 1'),{target:{value:'hello'}});
 fireEvent.change(main.getByLabelText('My response 1'),{target:{value:'hey'}});
 expect(main.getByText('Unsaved voice changes.')).toBeTruthy();
 expect(alex.queryByDisplayValue('hey')).toBeNull();
 expect(alex.queryByText('Unsaved voice changes.')).toBeNull();
 fireEvent.click(alex.getByRole('button',{name:'Customize voice'}));
 fireEvent.click(alex.getByText('Suggest examples from this chat'));
 await alex.findByText('Review suggested examples');
 expect(save).not.toHaveBeenCalled();
 fireEvent.click(alex.getByText('Cancel suggestions'));
 expect(alex.queryByDisplayValue('sure!')).toBeNull();
 fireEvent.click(alex.getByText('Suggest examples from this chat'));
 await alex.findByText('Review suggested examples');
 fireEvent.click(alex.getByLabelText('Include suggestion 1'));
 fireEvent.change(alex.getByLabelText('Suggested response 1'),{target:{value:'yes please'}});
 fireEvent.click(alex.getByText('Add selected to voice'));
 expect(save).not.toHaveBeenCalled();
 fireEvent.click(alex.getByText('Save my voice'));
 await waitFor(()=>expect(save).toHaveBeenCalledWith('alex@example.test'));
 await alex.findByText('Voice saved.');
 expect(voiceOf(latest,'').pairs).toEqual([{incoming:'hello',response:'hey'}]);
 expect(voiceOf(latest,'alex@example.test').pairs).toEqual([{incoming:'coffee?',response:'yes please'}]);
 expect(suggest).toHaveBeenCalledWith('alex@example.test');
});

it('shows a save failure on the card',async()=>{
 const profile=normalizeProfile({style:'warm'});
 render(<VoiceEditor scope="" busy={false} profile={profile} saved={profile} onChange={vi.fn()} onSave={vi.fn().mockRejectedValue(new Error('Too long'))} suggest={vi.fn()}/>);
 fireEvent.click(screen.getByRole('button',{name:'Customize voice'}));
 fireEvent.click(screen.getByText('Save my voice'));
 expect((await screen.findByRole('alert')).textContent).toBe('Too long');
});

it('opens from a button, asks before discarding unsaved edits, and restores the saved voice',()=>{
 const initial=normalizeProfile({recipients:{'alex@example.test':{style:'warm',examples:[],pairs:[]}}});
 function Harness(){const [profile,setProfile]=useState(initial);return <VoiceEditor scope="alex@example.test" label="Alex" busy={false} profile={profile} saved={initial} onChange={setProfile} onSave={async()=>{}} suggest={vi.fn()}/>;}
 render(<Harness/>);
 expect(screen.queryByLabelText('How should your replies sound?')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Customize voice'}));
 expect(screen.getByRole('heading',{name:'Voice for Alex'})).toBeTruthy();
 expect(document.activeElement).toBe(screen.getByLabelText('How should your replies sound?'));
 fireEvent.change(screen.getByLabelText('How should your replies sound?'),{target:{value:'curt'}});
 fireEvent.click(screen.getByRole('button',{name:'Close'}));
 expect(screen.getByRole('alert').textContent).toContain('Discard your unsaved changes?');
 fireEvent.click(screen.getByRole('button',{name:'Keep editing'}));
 expect((screen.getByLabelText('How should your replies sound?') as HTMLTextAreaElement).value).toBe('curt');
 fireEvent.click(screen.getByRole('button',{name:'Close'}));
 fireEvent.click(screen.getByRole('button',{name:'Discard changes'}));
 expect(screen.queryByLabelText('How should your replies sound?')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Customize voice'}));
 expect((screen.getByLabelText('How should your replies sound?') as HTMLTextAreaElement).value).toBe('warm');
});

it('starts every visit clean: notices, errors and suggestions are cleared on close, the saved voice stays',async()=>{
 const suggest=vi.fn().mockResolvedValue({pairs:[]}),onSave=vi.fn().mockRejectedValueOnce(new Error('Too long')).mockResolvedValue(undefined);
 const saved=normalizeProfile({recipients:{'alex@example.test':{style:'one word only',examples:['ok'],pairs:[]}}});
 render(<VoiceEditor scope="alex@example.test" label="Alex" busy={false} profile={saved} saved={saved} onChange={vi.fn()} onSave={onSave} suggest={suggest}/>);
 const open=()=>fireEvent.click(screen.getByRole('button',{name:'Customize voice'}));
 open();
 fireEvent.click(screen.getByText('Suggest examples from this chat'));
 expect(await screen.findByText('No reliable pairs found. Add examples manually.')).toBeTruthy();
 fireEvent.click(screen.getByText('Save my voice'));
 expect((await screen.findByRole('alert')).textContent).toBe('Too long');
 fireEvent.click(screen.getByRole('button',{name:'Close'}));
 open();
 expect(screen.queryByText('No reliable pairs found. Add examples manually.')).toBeNull();
 expect(screen.queryByRole('alert')).toBeNull();
 expect((screen.getByLabelText('How should your replies sound?') as HTMLTextAreaElement).value).toBe('one word only');
 expect((screen.getByLabelText(/Examples written by you/) as HTMLTextAreaElement).value).toBe('ok');
 fireEvent.click(screen.getByText('Save my voice'));
 await screen.findByText('Voice saved.');
 fireEvent.click(screen.getByRole('button',{name:'Close'}));
 open();
 expect(screen.queryByText('Voice saved.')).toBeNull();
});

it('ignores a suggestion that finishes after the pop-up was closed',async()=>{
 let finish:(v:{pairs:{incoming:string;response:string}[]})=>void=()=>{};
 const suggest=vi.fn(()=>new Promise<{pairs:{incoming:string;response:string}[]}>(resolve=>{finish=resolve;}));
 const saved=normalizeProfile({});
 render(<VoiceEditor scope="alex@example.test" label="Alex" busy={false} profile={saved} saved={saved} onChange={vi.fn()} onSave={vi.fn()} suggest={suggest}/>);
 fireEvent.click(screen.getByRole('button',{name:'Customize voice'}));
 fireEvent.click(screen.getByText('Suggest examples from this chat'));
 fireEvent.click(screen.getByRole('button',{name:'Close'}));
 await act(async()=>finish({pairs:[{incoming:'hi',response:'yo'}]}));
 fireEvent.click(screen.getByRole('button',{name:'Customize voice'}));
 expect(screen.queryByText('Review suggested examples')).toBeNull();
 expect((screen.getByText('Suggest examples from this chat') as HTMLButtonElement).disabled).toBe(false);
});
