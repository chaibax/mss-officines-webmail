.PHONY: test probe run restreint clean

test:        ## tests unitaires (offline, aucune clé requise)
	python3 -m unittest -v

probe:       ## valide la clé + liste les search params + échantillon
	python3 extract_officines.py --probe

run:         ## voie A (public) + enrichissement + CSV/synthèse
	python3 extract_officines.py

restreint:   ## voie A + voie B (requiert une clé données restreintes)
	python3 extract_officines.py --restreint

clean:       ## supprime les sorties locales (données personnelles)
	rm -rf out __pycache__ .pytest_cache
