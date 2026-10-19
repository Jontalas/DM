import copy, unittest
from engine import initial_state,apply_action,oracle,event

HOST={'id':'host','name':'Ana','host':1}
GUEST={'id':'guest','name':'Luis','host':0}
class EngineTests(unittest.TestCase):
    def setUp(self): self.s=initial_state({})
    def action(self,type,**kw): apply_action(self.s,{'type':type,**kw},HOST)
    def character(self):
        self.action('character',character={'name':'Aria','abilities':[14,16,12,10,10,10]})
        return self.s['characters'][0]
    def test_raw_doubles_before_modifiers(self):
        self.assertEqual(oracle([3,3,1],'muy probable'),(4,'No',2))
        self.assertEqual(oracle([3,4,1],'muy probable'),(4,'No',0))
        self.assertEqual(oracle([6,6,6],'muy improbable'),(1,'No excepcional',3))
    def test_event_uses_table_not_bad_example(self):
        result=event(self.s,values=[8,7,5]);self.assertEqual(result['target'],'Objetivo final');self.assertEqual(result['when'],'Demorado')
    def test_turning_point_stops_income(self):
        self.s['threshold']=2;event(self.s,values=[5,2,1]);self.assertTrue(self.s['turned']);event(self.s,True,[3,2,1]);self.assertEqual(self.s['tokens'],2)
    def test_physical_range_and_known_facts(self):
        with self.assertRaises(ValueError): self.action('oracle',question='Luz',uncertain=True,physical=[11,2,3])
        self.action('oracle',question='¿Luz?',uncertain=True,physical=[7,4,2])
        with self.assertRaises(ValueError):self.action('oracle',question='Luz',uncertain=True)
    def test_voluntary_once(self):
        self.s['scene']=3;self.action('voluntary');self.assertEqual(self.s['tokens'],3)
        with self.assertRaises(ValueError):self.action('voluntary')
    def test_ownership(self):
        c=self.character()
        with self.assertRaises(PermissionError):apply_action(self.s,{'type':'move','character':c['id'],'path':[[1,0]],'acknowledge':True},GUEST)
    def test_movement_and_action_budget(self):
        c=self.character();self.action('combat');self.action('move',character=c['id'],path=[[1,1],[2,2],[3,3],[4,4]],acknowledge=True)
        self.assertEqual((c['x'],c['y']),(4,4))
        with self.assertRaises(ValueError):self.action('move',character=c['id'],path=[[5,4]],acknowledge=True)
        self.action('turn');self.action('manual',character=c['id'],reason='Ataque confirmado',resolution='d20 físico 18 +2 contra CA 15; daño físico 4',reference='Manual pendiente de verificar',hpDelta=-4,resources='Flechas 19');self.assertEqual(c['hp'],6);self.assertEqual(c['resources'],'Flechas 19')
    def test_overspeed(self):
        c=self.character();self.action('combat')
        with self.assertRaises(ValueError):self.action('move',character=c['id'],path=[[i,0] for i in range(1,8)],acknowledge=True)
        self.assertEqual(c['x'],0)
    def test_private_notes(self):
        self.action('talk',text='Secreto',kind='private');self.assertEqual(self.s['messages'][-1]['visibility'],'private')
    def test_difficult_diagonal_cost_three(self):
        c=self.character();c['speed']=2;self.action('combat');self.action('terrain',x=1,y=1,terrain='difficult')
        with self.assertRaises(ValueError):self.action('move',character=c['id'],path=[[1,1]],acknowledge=True)
        c['speed']=3;self.action('move',character=c['id'],path=[[1,1]],acknowledge=True)
        self.assertEqual((c['x'],c['y']),(1,1))
    def test_detail_table_and_npc(self):
        self.action('oracle',question='¿Buena pista?',uncertain=True,physical=[9,8,3],group='Pista')
        self.assertEqual(self.s['oracleLog'][-1]['detail'],'Buena')
        self.action('npc',name='Posadera',physical=[7,2,3],farthest='d8')
        self.assertIn('Educado',self.s['allies'][-1]);self.assertIn('Igual de capaz',self.s['allies'][-1])
    def test_spend_requires_consent_and_resolution(self):
        self.s.update(turned=True,tokens=8)
        with self.assertRaises(ValueError):self.action('spend',benefit='objeto útil')
        self.action('spend',benefit='objeto útil',consent=True,interpretation='Una cuerda abandonada');self.assertEqual(self.s['tokens'],6);self.assertEqual(len(self.s['pending']),1)

if __name__=='__main__':unittest.main()
