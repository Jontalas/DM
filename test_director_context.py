"""Context boundary tests; no paid inference or production writes."""
import copy
import json
import unittest
from claude_dm import build_context
from engine import initial_state


class DirectorContextTests(unittest.TestCase):
    def state(self):
        state=initial_state({})
        state['secrets']='LEGACY-HOST-SECRET'
        state['directorNotes']='La posadera protege la llave.'
        state['private']={'player':'PERSONAL-NOTE'}
        state['messages']=[
            {'speaker':'Ana','kind':'action','text':'Busco la llave'},
            {'speaker':'Ana','kind':'private','text':'PRIVATE-LEGACY'},
            {'speaker':'Ana','kind':'ooc','text':'PRIVATE-VISIBILITY','visibility':'private'}]
        return state

    def test_narrator_knows_preparation_but_not_personal_notes(self):
        state=self.state();before=copy.deepcopy(state)
        context=build_context(state,'Exploro',[])
        self.assertEqual(context['directorKnowledge']['preparation'],state['directorNotes'])
        self.assertEqual(context['history'],[state['messages'][0]])
        self.assertNotIn('secrets',context['state'])
        self.assertNotIn('private',context['state'])
        for secret in ('LEGACY-HOST-SECRET','PERSONAL-NOTE','PRIVATE-LEGACY','PRIVATE-VISIBILITY'):
            self.assertNotIn(secret,json.dumps(context))
        self.assertEqual(state,before)

    def test_rules_consultation_does_not_receive_preparation(self):
        state=self.state();context=build_context(state,'¿Cómo se tira?',[],rules=True)
        self.assertNotIn('directorKnowledge',context)
        self.assertNotIn(state['directorNotes'],json.dumps(context))

    def test_empty_preparation_adds_no_context(self):
        self.assertNotIn('directorKnowledge',build_context(initial_state({}),'Hola',[]))
