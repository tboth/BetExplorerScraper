SELECT teams, url, team1odds, team2odds, over25, under25, formula1, formula2, team1goals, team2goals, team1goals+team2goals as totalGoals from matches 
WHERE (matches.date != date('now') and team1goals IS NOT NULL) order by matches.date; 