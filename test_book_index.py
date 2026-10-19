import unittest
from unittest.mock import Mock

from google.api_core.exceptions import InvalidArgument, PermissionDenied
from firebase_store import FirestoreStore


class BookIndexTests(unittest.TestCase):
    def client(self, limit, error=None):
        client=Mock();written={};attempts=[]
        def batch():
            pending=[];result=Mock()
            result.set.side_effect=lambda ref,data:pending.append((ref,data))
            def commit():
                attempts.append(len(pending))
                if len(pending)>limit:
                    raise error or InvalidArgument('Transaction too big. Decrease transaction size.')
                for _,data in pending:written[data['page']]=data
            result.commit.side_effect=commit
            return result
        client.batch.side_effect=batch
        return client,written,attempts

    def test_size_failure_splits_and_activates_only_complete_index(self):
        client,written,attempts=self.client(3)
        ref=client.collection.return_value.document.return_value
        ref.set.side_effect=lambda metadata:self.assertEqual(len(written),47)
        pages=[{'page':i,'text':f'Combate criatura{i} armadura'} for i in range(1,48)]
        FirestoreStore(client).index_book('reglas',pages)
        self.assertEqual(set(written),set(range(1,48)))
        self.assertEqual(written[1]['tokens'],['combate','criatura1','armadura'])
        self.assertGreater(len(attempts),3)
        ref.set.assert_called_once()
        self.assertEqual(ref.set.call_args.args[0]['pages'],47)

    def test_single_oversized_page_does_not_activate_partial_index(self):
        client,_,_=self.client(0)
        with self.assertRaisesRegex(ValueError,'página 1 de reglas'):
            FirestoreStore(client).index_book('reglas',[{'page':1,'text':'Armadura'}])
        client.collection.return_value.document.return_value.set.assert_not_called()

    def test_other_errors_are_not_retried_or_activated(self):
        for error in (PermissionDenied('Denied'),InvalidArgument('Invalid field')):
            with self.subTest(error=type(error).__name__):
                client,_,attempts=self.client(0,error)
                with self.assertRaises(type(error)):
                    FirestoreStore(client).index_book('reglas',[{'page':1,'text':'Armadura'}])
                self.assertEqual(attempts,[1])
                client.collection.return_value.document.return_value.set.assert_not_called()


if __name__=='__main__':unittest.main()
