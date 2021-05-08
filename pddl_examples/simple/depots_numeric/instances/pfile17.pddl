(define (problem depotprob6587) (:domain depot)
(:objects
	depot0 depot1 - depot
	distributor0 distributor1 - distributor
	truck0 truck1 truck2 truck3 - truck
	pallet0 pallet1 pallet2 pallet3 pallet4 pallet5 pallet6 pallet7 - pallet
	crate0 crate1 crate2 crate3 crate4 crate5 crate6 crate7 crate8 crate9 - crate
	hoist0 hoist1 hoist2 hoist3 hoist4 hoist5 hoist6 hoist7 - hoist)
(:init
	(located pallet0 depot0)
	(clear pallet0)
	(located pallet1 depot1)
	(clear crate4)
	(located pallet2 distributor0)
	(clear crate9)
	(located pallet3 distributor1)
	(clear crate7)
	(located pallet4 distributor0)
	(clear crate2)
	(located pallet5 distributor1)
	(clear crate1)
	(located pallet6 depot0)
	(clear crate3)
	(located pallet7 distributor1)
	(clear crate8)
	(located truck0 depot1)
	(= (current_load truck0) 0)
	(= (load_limit truck0) 462)
	(located truck1 distributor1)
	(= (current_load truck1) 0)
	(= (load_limit truck1) 261)
	(located truck2 depot1)
	(= (current_load truck2) 0)
	(= (load_limit truck2) 254)
	(located truck3 depot0)
	(= (current_load truck3) 0)
	(= (load_limit truck3) 291)
	(located hoist0 depot0)
	(available hoist0)
	(located hoist1 depot1)
	(available hoist1)
	(located hoist2 distributor0)
	(available hoist2)
	(located hoist3 distributor1)
	(available hoist3)
	(located hoist4 depot0)
	(available hoist4)
	(located hoist5 depot0)
	(available hoist5)
	(located hoist6 depot0)
	(available hoist6)
	(located hoist7 distributor1)
	(available hoist7)
	(located crate0 distributor1)
	(on crate0 pallet3)
	(= (weight crate0) 92)
	(located crate1 distributor1)
	(on crate1 pallet5)
	(= (weight crate1) 8)
	(located crate2 distributor0)
	(on crate2 pallet4)
	(= (weight crate2) 65)
	(located crate3 depot0)
	(on crate3 pallet6)
	(= (weight crate3) 14)
	(located crate4 depot1)
	(on crate4 pallet1)
	(= (weight crate4) 3)
	(located crate5 distributor1)
	(on crate5 crate0)
	(= (weight crate5) 13)
	(located crate6 distributor1)
	(on crate6 pallet7)
	(= (weight crate6) 33)
	(located crate7 distributor1)
	(on crate7 crate5)
	(= (weight crate7) 76)
	(located crate8 distributor1)
	(on crate8 crate6)
	(= (weight crate8) 31)
	(located crate9 distributor0)
	(on crate9 pallet2)
	(= (weight crate9) 91)
	(= (fuel-cost) 0)
)

(:goal (and
		(on crate1 pallet7)
		(on crate2 pallet4)
		(on crate3 crate8)
		(on crate4 pallet0)
		(on crate6 pallet1)
		(on crate7 crate3)
		(on crate8 pallet6)
	)
)

)