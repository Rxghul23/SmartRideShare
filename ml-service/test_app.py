import os, unittest, json
from datetime import datetime, timedelta
os.environ['ML_SERVICE_KEY']='unit-test-only-key'
import app
class MatchingTests(unittest.TestCase):
 def setUp(self):
  self.client=app.app.test_client();self.headers={'X-Service-Key':os.environ['ML_SERVICE_KEY']}
  self.q={'user_id':1,'origin_lat':13,'origin_lng':80,'dest_lat':13.1,'dest_lng':80.1,'departure':(datetime.now()+timedelta(days=1)).replace(microsecond=0).isoformat(),'preference':'quiet','tolerance':45}
  self.ride={**self.q,'id':2,'driver_id':2,'available_seats':1,'status':'OPEN','price':50,'rating':4}
 def recommend(self,rides):return self.client.post('/recommend',json={'request':self.q,'rides':rides,'settings':{'max_route_km':5}},headers=self.headers).get_json()['matches']
 def test_service_key_required(self):self.assertEqual(self.client.post('/health',json={}).status_code,401)
 def test_near_match_and_duplicates(self):
  result=self.recommend([self.ride,self.ride]);self.assertEqual(len(result),1);self.assertGreater(result[0]['score'],85)
 def test_excludes_distance_time_self_and_full(self):
  self.assertEqual(self.recommend([{**self.ride,'origin_lat':20},{**self.ride,'id':3,'driver_id':1},{**self.ride,'id':4,'available_seats':0},{**self.ride,'id':5,'departure':(datetime.now()+timedelta(days=3)).isoformat()}]),[])
 def test_empty_history_explained(self):
  r=self.client.post('/forecast',json={'history':[]},headers=self.headers).get_json();self.assertEqual(r['status'],'insufficient_history');self.assertEqual(r['predictions'],[])
 def test_insufficient_training_is_explicit(self):
  r=self.client.post('/train',json={'samples':[{'features':[1,1,1,1,1],'rating':5}]},headers=self.headers).get_json();self.assertEqual(r['status'],'cold_start');self.assertEqual(r['samples'],1)
 def test_haversine(self):
  self.assertEqual(app.haversine(0,0,0,0),0);self.assertAlmostEqual(app.haversine(0,0,0,1),111.195,places=2)
if __name__=='__main__':unittest.main(verbosity=2)
