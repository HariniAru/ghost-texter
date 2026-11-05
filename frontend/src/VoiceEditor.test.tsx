// @vitest-environment jsdom
import {useState} from 'react';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {VoiceEditor,normalizeProfile} from './VoiceEditor';
afterEach(cleanup);
it('keeps paired examples scoped and imports only selected, reviewed pairs',async()=>{
 const save=vi.fn(),suggest=vi.fn().mockResolvedValue({pairs:[{incoming:'coffee?',response:'sure!'}]});
 function Harness(){const [profile,setProfile]=useState(normalizeProfile({style:'warm',examples:['legacy']}));return <VoiceEditor profile={profile} onChange={setProfile} recipients={['alex@example.test','maya@example.test']} busy={false} suggest={suggest} onSave={()=>save(profile)}/>;}
 render(<Harness/>);
 fireEvent.click(screen.getByText('Add example pair'));
 fireEvent.change(screen.getByLabelText('Incoming message 1'),{target:{value:'hello'}});
 fireEvent.change(screen.getByLabelText('My response 1'),{target:{value:'hey'}});
 fireEvent.change(screen.getByLabelText('Voice for'),{target:{value:'alex@example.test'}});
 expect(screen.queryByDisplayValue('hey')).toBeNull();
 fireEvent.click(screen.getByText('Suggest examples from this chat'));
 await screen.findByText('Review suggested examples');
 expect(save).not.toHaveBeenCalled();
 fireEvent.click(screen.getByText('Cancel suggestions'));
 expect(screen.queryByDisplayValue('sure!')).toBeNull();
 fireEvent.click(screen.getByText('Suggest examples from this chat'));
 await screen.findByText('Review suggested examples');
 fireEvent.click(screen.getByLabelText('Include suggestion 1'));
 fireEvent.change(screen.getByLabelText('Suggested response 1'),{target:{value:'yes please'}});
 fireEvent.click(screen.getByText('Add selected to voice'));
 expect(save).not.toHaveBeenCalled();
 fireEvent.click(screen.getByText('Save my voice'));
 await waitFor(()=>expect(save).toHaveBeenCalledTimes(1));
 const profile=save.mock.calls[0][0];
 expect(profile.pairs).toEqual([{incoming:'hello',response:'hey'}]);
 expect(profile.recipients['alex@example.test'].pairs).toEqual([{incoming:'coffee?',response:'yes please'}]);
 expect(profile.recipients['maya@example.test']).toBeUndefined();
 expect(suggest).toHaveBeenCalledWith('alex@example.test');
});
