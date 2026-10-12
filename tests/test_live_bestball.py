import unittest
from live_bestball import bestball_lineup

def player(pos):
    return {"position":pos,"fantasy_positions":[pos]}

class BestBallTests(unittest.TestCase):
    def setUp(self):
        self.player_map={"qb1":player("QB"),"wr1":player("WR"),"wr2":player("WR"),"rb1":player("RB"),"rb2":player("RB"),"te1":player("TE")}
    def test_bench_promotion_with_flex(self):
        row={"players":list(self.player_map),"starters":["qb1","rb1","wr1","te1"],"players_points":{"qb1":20,"rb1":5,"rb2":18,"wr1":10,"wr2":30,"te1":8}}
        result=bestball_lineup(row,["QB","RB","WR","FLEX"],self.player_map)
        self.assertEqual(result["points"],78)
        self.assertEqual(set(result["starters"]),{"qb1","rb2","wr1","wr2"})
    def test_negative_score_and_unplayed_player(self):
        row={"players":["qb1","rb1"],"starters":["qb1","rb1"],"players_points":{"qb1":-2}}
        result=bestball_lineup(row,["QB","RB"],self.player_map)
        self.assertEqual(result["points"],-2)
    def test_missing_player_metadata_fails_safely(self):
        row={"players":["missing"],"players_points":{"missing":12}}
        self.assertIsNone(bestball_lineup(row,["QB"],self.player_map))
    def test_superflex_and_no_duplicate_player(self):
        row={"players":["qb1","wr1","rb1"],"starters":["qb1","wr1"],"players_points":{"qb1":10,"wr1":22,"rb1":15}}
        result=bestball_lineup(row,["QB","SUPER_FLEX"],self.player_map)
        self.assertEqual(result["points"],32)
        self.assertEqual(len(set(result["starters"])),2)

if __name__=="__main__":
    unittest.main()
