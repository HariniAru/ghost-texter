// @vitest-environment jsdom
import {afterEach, beforeAll, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import {SendConfirmation} from './SendConfirmation';

beforeAll(()=>{
 HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
 HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
});
afterEach(cleanup);
const draft={recipient:'alex@example.test',text:'hey! can we do 11 instead?',version:2};

it('shows exact saved recipient, body, and version without sending on open',()=>{
 const confirm=vi.fn();
 render(<SendConfirmation draft={draft} demo={false} sendEnabled={true} busy={false} onCancel={vi.fn()} onConfirm={confirm}/>);
 expect(screen.getByRole('dialog').hasAttribute('open')).toBe(true);
 expect(screen.getByText(draft.recipient)).toBeTruthy();
 expect(screen.getByText(draft.text)).toBeTruthy();
 expect(screen.getByText('SAVED REPLY · VERSION 2')).toBeTruthy();
 expect(confirm).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Confirm & send'}));
 expect(confirm).toHaveBeenCalledTimes(1);
});

it('cancel and Escape return to editing without sending',()=>{
 const cancel=vi.fn(), confirm=vi.fn();
 render(<SendConfirmation draft={draft} demo={false} sendEnabled={true} busy={false} onCancel={cancel} onConfirm={confirm}/>);
 fireEvent.click(screen.getByRole('button',{name:'Back to editing'}));
 fireEvent(screen.getByRole('dialog'),new Event('cancel',{cancelable:true}));
 expect(cancel).toHaveBeenCalledTimes(2);
 expect(confirm).not.toHaveBeenCalled();
});

it('blocks disabled live sending and explains how to enable it',()=>{
 const confirm=vi.fn();
 render(<SendConfirmation draft={draft} demo={false} sendEnabled={false} busy={false} onCancel={vi.fn()} onConfirm={confirm}/>);
 expect((screen.getByRole('button',{name:'Confirm & send'}) as HTMLButtonElement).disabled).toBe(true);
 expect(screen.getByRole('status').textContent).toContain('GHOST_SEND_ENABLED=true');
 fireEvent.click(screen.getByRole('button',{name:'Confirm & send'}));
 expect(confirm).not.toHaveBeenCalled();
});

it('demo confirmation remains simulated and works without enabling live sending',()=>{
 const confirm=vi.fn();
 render(<SendConfirmation draft={draft} demo={true} sendEnabled={false} busy={false} onCancel={vi.fn()} onConfirm={confirm}/>);
 expect(screen.getByText('This is a demo. No real text will leave the app.')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Confirm simulated send'}));
 expect(confirm).toHaveBeenCalledTimes(1);
});

it('disables confirmation and cancellation while dispatch is in progress',()=>{
 const confirm=vi.fn(),cancel=vi.fn();
 render(<SendConfirmation draft={draft} demo={true} sendEnabled={false} busy={true} onCancel={cancel} onConfirm={confirm}/>);
 expect((screen.getByRole('button',{name:'Sending…'}) as HTMLButtonElement).disabled).toBe(true);
 fireEvent(screen.getByRole('dialog'),new Event('cancel',{cancelable:true}));
 expect(cancel).not.toHaveBeenCalled();
 expect(confirm).not.toHaveBeenCalled();
});
