// @vitest-environment jsdom
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {ContactsPanel} from './ContactsPanel';
import {normalizeProfile} from './VoiceEditor';
HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
afterEach(cleanup);
const profile=normalizeProfile({style:'warm'});
const voice={profile,saved:profile,onChange:vi.fn(),onSave:vi.fn(),suggest:vi.fn()};
const rows=[{name:'Sam',address:'+14155550123',source:'app'},{name:'',address:'maya@example.test',source:'env'}];

it('needs a name and a number, and clears the form only after success',async()=>{
 const onAdd=vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
 render(<ContactsPanel contacts={rows} demo={false} busy={false} locked={false} onAdd={onAdd} onRemove={vi.fn()} voice={voice}/>);
 const name=screen.getByLabelText('Name') as HTMLInputElement;
 const number=screen.getByLabelText(/^Number/) as HTMLInputElement;
 const button=screen.getByRole('button',{name:'Add contact'}) as HTMLButtonElement;
 expect(button.disabled).toBe(true);
 fireEvent.change(name,{target:{value:'Lee'}});
 expect(button.disabled).toBe(true);
 fireEvent.change(number,{target:{value:'+14155550100'}});
 fireEvent.click(button);
 await waitFor(()=>expect(onAdd).toHaveBeenCalledTimes(1));
 expect(onAdd).toHaveBeenCalledWith('Lee','+14155550100');
 expect(number.value).toBe('+14155550100');
 fireEvent.click(button);
 await waitFor(()=>expect(number.value).toBe(''));
 expect(name.value).toBe('');
});

it('shows names with numbers, removes only contacts added here, and marks .env contacts',()=>{
 const onRemove=vi.fn();
 render(<ContactsPanel contacts={rows} demo={false} busy={false} locked={false} onAdd={vi.fn()} onRemove={onRemove} voice={voice}/>);
 expect(screen.getByText('Sam')).toBeTruthy();
 expect(screen.getByText('+14155550123')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Remove Sam'}));
 expect(onRemove).toHaveBeenCalledWith('+14155550123');
 expect(screen.queryByRole('button',{name:'Remove maya@example.test'})).toBeNull();
 expect(screen.getByText('from .env')).toBeTruthy();
});

it('gives each contact a card with a voice button, plus one default voice card',()=>{
 render(<ContactsPanel contacts={rows} demo={false} busy={false} locked={false} onAdd={vi.fn()} onRemove={vi.fn()} voice={voice}/>);
 for(const name of ['Default voice','Sam','maya@example.test'])expect(screen.getByRole('region',{name})).toBeTruthy();
 expect(screen.getAllByRole('button',{name:'Customize voice'})).toHaveLength(3);
 expect(document.querySelector('dialog')).toBeNull();
});

it('explains why removal is blocked while an unsaved reply is open',()=>{
 render(<ContactsPanel contacts={rows} demo={false} busy={false} locked onAdd={vi.fn()} onRemove={vi.fn()} voice={voice}/>);
 expect((screen.getByRole('button',{name:'Remove Sam'}) as HTMLButtonElement).disabled).toBe(true);
 expect(screen.getByText(/Save or discard your reply edit/)).toBeTruthy();
});

it('is read-only in demo mode',()=>{
 render(<ContactsPanel contacts={[{name:'',address:'alex@example.test',source:'demo'}]} demo busy={false} locked={false} onAdd={vi.fn()} onRemove={vi.fn()} voice={voice}/>);
 expect(screen.getByText('alex@example.test')).toBeTruthy();
 expect(screen.queryByLabelText(/^Number/)).toBeNull();
 expect(screen.queryByRole('button',{name:/Remove/})).toBeNull();
 expect(screen.getByText(/Demo mode uses synthetic contacts/)).toBeTruthy();
});

it('shows on each card whether that person has a personal voice',()=>{
 const saved=normalizeProfile({style:'warm',recipients:{'+14155550123':{style:'curt',examples:[],pairs:[]}}});
 render(<ContactsPanel contacts={rows} demo={false} busy={false} locked={false} onAdd={vi.fn()} onRemove={vi.fn()} voice={{...voice,saved,profile:saved}}/>);
 expect(screen.getByRole('region',{name:'Sam'}).textContent).toContain('Personal voice');
 expect(screen.getByRole('region',{name:'maya@example.test'}).textContent).toContain('Uses default voice');
});
